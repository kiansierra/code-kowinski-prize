import ast
import os
from typing import Optional, List, Dict, Any, Tuple
from sqlmodel import Field, SQLModel, create_engine, Session
import pandas as pd

# Define models for database tables
class PythonFunction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="repofile.id", index=True)
    name: str
    start_line: int
    end_line: int
    args: str  # Comma-separated list of arguments
    is_method: bool = False
    class_name: Optional[str] = None  # If it's a method, which class it belongs to
    is_async: bool = False
    decorators: str = ""  # Comma-separated list of decorators
    docstring: Optional[str] = None

class PythonClass(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="repofile.id", index=True)
    name: str
    start_line: int
    end_line: int
    base_classes: str = ""  # Comma-separated list of base classes
    decorators: str = ""  # Comma-separated list of decorators
    docstring: Optional[str] = None

class PythonVariable(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="repofile.id", index=True)
    name: str
    line: int
    value_repr: str = ""  # String representation of the value
    is_module_level: bool = True
    class_name: Optional[str] = None  # If within a class but outside methods

# AST Visitor to extract Python code elements
class PythonCodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = []
        self.classes = []
        self.variables = []
        self.current_class = None
        
    def visit_FunctionDef(self, node):
        # Extract function information
        args = [arg.arg for arg in node.args.args]
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        # Get docstring if it exists
        docstring = ast.get_docstring(node)
        
        # Check if it's a method
        is_method = self.current_class is not None
        class_name = self.current_class if is_method else None
        
        self.functions.append({
            'name': node.name,
            'start_line': node.lineno,
            'end_line': self._get_last_line(node),
            'args': ", ".join(args),
            'is_method': is_method,
            'class_name': class_name,
            'is_async': False,
            'decorators': ", ".join(decorators),
            'docstring': docstring
        })
        
        # Continue visiting child nodes (for nested functions/classes)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        # Similar to FunctionDef but mark as async
        args = [arg.arg for arg in node.args.args]
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        docstring = ast.get_docstring(node)
        
        is_method = self.current_class is not None
        class_name = self.current_class if is_method else None
        
        self.functions.append({
            'name': node.name,
            'start_line': node.lineno,
            'end_line': self._get_last_line(node),
            'args': ", ".join(args),
            'is_method': is_method,
            'class_name': class_name,
            'is_async': True,
            'decorators': ", ".join(decorators),
            'docstring': docstring
        })
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        # Extract class information
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(self._get_attribute_name(base))
        
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        docstring = ast.get_docstring(node)
        
        self.classes.append({
            'name': node.name,
            'start_line': node.lineno,
            'end_line': self._get_last_line(node),
            'base_classes': ", ".join(base_classes),
            'decorators': ", ".join(decorators),
            'docstring': docstring
        })
        
        # Save previous class context
        prev_class = self.current_class
        # Set current class for methods
        self.current_class = node.name
        
        # Visit all class contents
        self.generic_visit(node)
        
        # Restore previous class context
        self.current_class = prev_class
    
    def visit_Assign(self, node):
        # Handle variable assignments
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Simple variable assignment at module level
                value_repr = self._get_value_repr(node.value)
                self.variables.append({
                    'name': target.id,
                    'line': node.lineno,
                    'value_repr': value_repr,
                    'is_module_level': self.current_class is None,
                    'class_name': self.current_class
                })
            elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self':
                # Handle class instance variables like self.x = y
                # These are usually in methods, so we skip them as they're not module or class level
                pass
        
        self.generic_visit(node)
    
    def visit_AnnAssign(self, node):
        # Handle annotated assignments (x: int = 5)
        if isinstance(node.target, ast.Name):
            value_repr = self._get_value_repr(node.value) if node.value else ""
            self.variables.append({
                'name': node.target.id,
                'line': node.lineno,
                'value_repr': value_repr,
                'is_module_level': self.current_class is None,
                'class_name': self.current_class
            })
        
        self.generic_visit(node)
    
    def _get_last_line(self, node):
        """Get the last line number of a node"""
        # For simple nodes with end_lineno attribute
        if hasattr(node, 'end_lineno') and node.end_lineno is not None:
            return node.end_lineno
            
        # For more complex nodes, find max line number
        max_line = node.lineno
        for child in ast.iter_child_nodes(node):
            if hasattr(child, 'lineno'):
                child_last_line = self._get_last_line(child)
                max_line = max(max_line, child_last_line)
        return max_line
    
    def _get_decorator_name(self, node):
        """Get the name of a decorator"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return self._get_attribute_name(node.func)
        elif isinstance(node, ast.Attribute):
            return self._get_attribute_name(node)
        return "unknown_decorator"
    
    def _get_attribute_name(self, node):
        """Get the full name of an attribute (e.g., module.Class)"""
        if isinstance(node, ast.Attribute):
            parent = self._get_attribute_name(node.value)
            return f"{parent}.{node.attr}"
        elif isinstance(node, ast.Name):
            return node.id
        return "unknown"
    
    def _get_value_repr(self, node):
        """Get a string representation of a value"""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return "[...]"
        elif isinstance(node, ast.Dict):
            return "{...}"
        elif isinstance(node, ast.Tuple):
            return "(...)"
        elif isinstance(node, ast.Set):
            return "{...}"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f"{node.func.id}(...)"
            elif isinstance(node.func, ast.Attribute):
                return f"{self._get_attribute_name(node.func)}(...)"
        return "..."

def analyze_python_files(db_path="repository.db"):
    """
    Analyze Python files in the repository database and extract code structure information.
    
    Args:
        db_path (str): Path to the SQLite database
    
    Returns:
        dict: Summary of the parsed Python structures
    """
    # Create database engine
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    
    # Read all Python files from the database
    with Session(engine) as session:
        # Get all files with .py extension
        query = "SELECT id, relative_folder, file_name, content FROM repofile WHERE file_extension = 'py'"
        conn = engine.connect()
        python_files = pd.read_sql(query, conn).to_dict('records')
        conn.close()
        
        # Counter for parsed elements
        stats = {
            'total_python_files': len(python_files),
            'total_functions': 0,
            'total_classes': 0,
            'total_variables': 0,
            'files_with_parse_errors': 0
        }
        
        # Process each Python file
        for py_file in python_files:
            file_id = py_file['id']
            file_path = os.path.join(py_file['relative_folder'], py_file['file_name'])
            content = py_file['content']
            
            try:
                # Parse the Python code
                tree = ast.parse(content)
                visitor = PythonCodeVisitor()
                visitor.visit(tree)
                
                # Store functions
                for func_data in visitor.functions:
                    function = PythonFunction(
                        file_id=file_id,
                        **func_data
                    )
                    session.add(function)
                stats['total_functions'] += len(visitor.functions)
                
                # Store classes
                for class_data in visitor.classes:
                    python_class = PythonClass(
                        file_id=file_id,
                        **class_data
                    )
                    session.add(python_class)
                stats['total_classes'] += len(visitor.classes)
                
                # Store variables
                for var_data in visitor.variables:
                    variable = PythonVariable(
                        file_id=file_id,
                        **var_data
                    )
                    session.add(variable)
                stats['total_variables'] += len(visitor.variables)
                
            except SyntaxError as e:
                print(f"Syntax error in file {file_path}: {e}")
                stats['files_with_parse_errors'] += 1
            except Exception as e:
                print(f"Error parsing file {file_path}: {e}")
                stats['files_with_parse_errors'] += 1
        
        # Commit all the data
        session.commit()
    
    print(f"Python file analysis complete. Results:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return stats
