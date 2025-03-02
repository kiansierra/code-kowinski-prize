from typing import List, Dict, Any, Optional, Tuple, Union
import pandas as pd
from sqlalchemy import create_engine, text
import os
from dataclasses import dataclass
from smolagents import tool

@dataclass
class FileInfo:
    """Information about a file in the repository."""
    id: int
    relative_folder: str
    file_name: str
    file_extension: str
    line_count: int
    full_path: str  # Combines relative_folder and file_name
    content: Optional[str] = None
@dataclass
class FunctionInfo:
    """Information about a Python function or method."""
    id: int
    name: str
    start_line: int
    end_line: int
    args: str
    is_method: bool
    class_name: Optional[str]
    is_async: bool
    decorators: str
    docstring: Optional[str]
    file_id: int
    file_path: str

@dataclass
class ClassInfo:
    """Information about a Python class."""
    id: int
    name: str
    start_line: int
    end_line: int
    base_classes: str
    decorators: str
    docstring: Optional[str]
    file_id: int
    file_path: str

@dataclass
class VariableInfo:
    """Information about a Python variable."""
    id: int
    name: str
    line: int
    value_repr: str
    is_module_level: bool
    class_name: Optional[str]
    file_id: int
    file_path: str

@dataclass
class CodeEntity:
    """
    A unified representation of a code entity (function, class, or variable).
    
    This class represents any type of code entity with consistent attributes,
    making it easier for an AI to reason about different code elements.
    """
    entity_type: str  # "function", "class", or "variable"
    id: int
    name: str
    file_id: int
    file_path: str
    start_line: int
    end_line: Optional[int] = None  # Variables don't have end_line
    docstring: Optional[str] = None
    parent_name: Optional[str] = None  # Class name for methods, None for module-level entities
    details: Dict[str, Any] = None  # Additional type-specific details

def repository_querier(db_path: str = "repository.db"):
    """
    A class to query the repository database and retrieve information for an AI agent.
    
    This class provides methods to explore and understand a code repository's structure,
    helping an AI agent to navigate, analyze, and reason about the codebase.
    """
    

    engine = create_engine(f"sqlite:///{db_path}")
        
        
    @tool
    def get_folders() -> List[str]:
        """
        Get all unique folder paths in the repository.
        
        Returns:
            A list of all relative folder paths in the repository, sorted alphabetically.
        """
        query = "SELECT DISTINCT relative_folder FROM repofile ORDER BY relative_folder"
        with engine.connect() as conn:
            result = pd.read_sql(query, conn)
        return result['relative_folder'].tolist()
    
    @tool
    def get_files_in_folder( folder_path: str) -> List[FileInfo]:
        """
        Get all files in a specific folder.
        
        Args:
            folder_path: The relative folder path to query.
            
        Returns:
            A list of FileInfo objects representing the files in the specified folder.
        """
        query = """
        SELECT id, relative_folder, file_name, file_extension, line_count
        FROM repofile
        WHERE relative_folder = :folder
        ORDER BY file_name
        """
        with engine.connect() as conn:
            result = pd.read_sql(text(query), conn, params={"folder": folder_path})
        
        files = []
        for _, row in result.iterrows():
            full_path = os.path.join(row['relative_folder'], row['file_name'])
            files.append(FileInfo(
                id=row['id'],
                relative_folder=row['relative_folder'],
                file_name=row['file_name'],
                file_extension=row['file_extension'],
                line_count=row['line_count'],
                full_path=full_path
            ))
        return files
    
    @tool
    def get_files_by_extension( extension: str) -> List[FileInfo]:
        """
        Get all files with a specific extension.
        
        Args:
            extension: The file extension to filter by (without the dot, e.g., 'py' not '.py').
            
        Returns:
            A list of FileInfo objects for all files with the specified extension.
        """
        query = """
        SELECT id, relative_folder, file_name, file_extension, line_count
        FROM repofile
        WHERE file_extension = :ext
        ORDER BY relative_folder, file_name
        """
        with engine.connect() as conn:
            result = pd.read_sql(text(query), conn, params={"ext": extension})
        
        files = []
        for _, row in result.iterrows():
            full_path = os.path.join(row['relative_folder'], row['file_name'])
            files.append(FileInfo(
                id=row['id'],
                relative_folder=row['relative_folder'],
                file_name=row['file_name'],
                file_extension=row['file_extension'],
                line_count=row['line_count'],
                full_path=full_path
            ))
        return files
    
    @tool
    def get_file_by_path( file_path: str) -> Optional[FileInfo]:
        """
        Get file information for a specific file path.
        
        Args:
            file_path: The relative path to the file, including folder and filename.
            
        Returns:
            A FileInfo object for the specified file, or None if not found.
        """
        # Split the path into folder and filename
        parts = os.path.split(file_path)
        if len(parts) == 2:
            folder, filename = parts
        else:
            folder, filename = "", file_path
        
        query = """
        SELECT id, relative_folder, file_name, file_extension, line_count, content
        FROM repofile
        WHERE relative_folder = :folder AND file_name = :filename
        """
        with engine.connect() as conn:
            result = pd.read_sql(text(query), conn, params={
                "folder": folder,
                "filename": filename
            })
        
        if len(result) == 0:
            return None
        
        row = result.iloc[0]
        full_path = os.path.join(row['relative_folder'], row['file_name'])
        return FileInfo(
            id=row['id'],
            relative_folder=row['relative_folder'],
            file_name=row['file_name'],
            file_extension=row['file_extension'],
            line_count=row['line_count'],
            full_path=full_path,
            content=row['content']
        )
    
    @tool
    def get_file_content(file_path: str) -> Optional[str]:
        """
        Get the content of a file by path.
        
        Args:
            file_path: The relative path to the file, including folder and filename.
            
        Returns:
            The content of the file as a string, or None if the file is not found.
        """
        file_info = get_file_by_path(file_path)
        if file_info is None:
            return None
        
        return file_info.content
    
    @tool
    def get_entity_at_line( file_path: str, line_number: int) -> Optional[CodeEntity]:
        """
        Find the code entity (function, class, or variable) at a specific line in a file.
        
        Args:
            file_path: The relative path to the file, including folder and filename.
            line_number: The line number to check.
            
        Returns:
            A CodeEntity object representing the entity at the specified line, or None if not found.
        """
        file_info = get_file_by_path(file_path)
        if file_info is None:
            return None
        
        # Check if the line is in a function
        query = """
        SELECT id, name, start_line, end_line, args, is_method, class_name, is_async, decorators, docstring
        FROM pythonfunction
        WHERE file_id = :file_id AND :line BETWEEN start_line AND end_line
        ORDER BY (end_line - start_line) ASC
        LIMIT 1
        """
        with engine.connect() as conn:
            func_result = pd.read_sql(text(query), conn, params={
                "file_id": file_info.id,
                "line": line_number
            })
        
        if len(func_result) > 0:
            row = func_result.iloc[0]
            return CodeEntity(
                entity_type="function",
                id=row['id'],
                name=row['name'],
                file_id=file_info.id,
                file_path=file_info.full_path,
                start_line=row['start_line'],
                end_line=row['end_line'],
                docstring=row['docstring'],
                parent_name=row['class_name'],
                details={
                    "args": row['args'],
                    "is_method": bool(row['is_method']),
                    "is_async": bool(row['is_async']),
                    "decorators": row['decorators']
                }
            )
        
        # Check if the line is in a class
        query = """
        SELECT id, name, start_line, end_line, base_classes, decorators, docstring
        FROM pythonclass
        WHERE file_id = :file_id AND :line BETWEEN start_line AND end_line
        ORDER BY (end_line - start_line) ASC
        LIMIT 1
        """
        with engine.connect() as conn:
            class_result = pd.read_sql(text(query), conn, params={
                "file_id": file_info.id,
                "line": line_number
            })
        
        if len(class_result) > 0:
            row = class_result.iloc[0]
            return CodeEntity(
                entity_type="class",
                id=row['id'],
                name=row['name'],
                file_id=file_info.id,
                file_path=file_info.full_path,
                start_line=row['start_line'],
                end_line=row['end_line'],
                docstring=row['docstring'],
                parent_name=None,
                details={
                    "base_classes": row['base_classes'],
                    "decorators": row['decorators']
                }
            )
        
        # Check if the line has a variable
        query = """
        SELECT id, name, line, value_repr, is_module_level, class_name
        FROM pythonvariable
        WHERE file_id = :file_id AND line = :line
        LIMIT 1
        """
        with engine.connect() as conn:
            var_result = pd.read_sql(text(query), conn, params={
                "file_id": file_info.id,
                "line": line_number
            })
        
        if len(var_result) > 0:
            row = var_result.iloc[0]
            return CodeEntity(
                entity_type="variable",
                id=row['id'],
                name=row['name'],
                file_id=file_info.id,
                file_path=file_info.full_path,
                start_line=row['line'],
                end_line=None,
                docstring=None,
                parent_name=row['class_name'],
                details={
                    "value_repr": row['value_repr'],
                    "is_module_level": bool(row['is_module_level'])
                }
            )
        
        return None
    
    @tool
    def get_function_by_name( function_name: str, class_name: Optional[str] = None, 
                             file_path: Optional[str] = None) -> List[FunctionInfo]:
        """
        Find functions or methods by name, optionally filtering by class and file.
        
        Args:
            function_name: The name of the function or method to find.
            class_name: Optional class name to filter by (for methods).
            file_path: Optional file path to limit the search to a specific file.
            
        Returns:
            A list of FunctionInfo objects matching the criteria.
        """
        query_parts = ["SELECT f.*, r.relative_folder, r.file_name FROM pythonfunction f JOIN repofile r ON f.file_id = r.id WHERE f.name = :func_name"]
        params = {"func_name": function_name}
        
        if class_name is not None:
            query_parts.append("AND f.class_name = :class_name")
            params["class_name"] = class_name
        
        if file_path is not None:
            folder, filename = os.path.split(file_path) if os.path.split(file_path)[0] else ("", file_path)
            query_parts.append("AND r.relative_folder = :folder AND r.file_name = :filename")
            params["folder"] = folder
            params["filename"] = filename
        
        query = " ".join(query_parts)
        with engine.connect() as conn:
            result = pd.read_sql(text(query), conn, params=params)
        
        functions = []
        for _, row in result.iterrows():
            file_path = os.path.join(row['relative_folder'], row['file_name'])
            functions.append(FunctionInfo(
                id=row['id'],
                name=row['name'],
                start_line=row['start_line'],
                end_line=row['end_line'],
                args=row['args'],
                is_method=bool(row['is_method']),
                class_name=row['class_name'],
                is_async=bool(row['is_async']),
                decorators=row['decorators'],
                docstring=row['docstring'],
                file_id=row['file_id'],
                file_path=file_path
            ))
        return functions
    
    @tool
    def get_class_by_name( class_name: str, file_path: Optional[str] = None) -> List[ClassInfo]:
        """
        Find classes by name, optionally filtering by file.
        
        Args:
            class_name: The name of the class to find.
            file_path: Optional file path to limit the search to a specific file.
            
        Returns:
            A list of ClassInfo objects matching the criteria.
        """
        query_parts = ["SELECT c.*, r.relative_folder, r.file_name FROM pythonclass c JOIN repofile r ON c.file_id = r.id WHERE c.name = :class_name"]
        params = {"class_name": class_name}
        
        if file_path is not None:
            folder, filename = os.path.split(file_path) if os.path.split(file_path)[0] else ("", file_path)
            query_parts.append("AND r.relative_folder = :folder AND r.file_name = :filename")
            params["folder"] = folder
            params["filename"] = filename
        
        query = " ".join(query_parts)
        with engine.connect() as conn:
            result = pd.read_sql(text(query), conn, params=params)
        
        classes = []
        for _, row in result.iterrows():
            file_path = os.path.join(row['relative_folder'], row['file_name'])
            classes.append(ClassInfo(
                id=row['id'],
                name=row['name'],
                start_line=row['start_line'],
                end_line=row['end_line'],
                base_classes=row['base_classes'],
                decorators=row['decorators'],
                docstring=row['docstring'],
                file_id=row['file_id'],
                file_path=file_path
            ))
        return classes
    
    @tool
    def get_class_methods( class_name: str, file_path: Optional[str] = None) -> List[FunctionInfo]:
        """
        Get all methods defined in a specific class.
        
        Args:
            class_name: The name of the class to find methods for.
            file_path: Optional file path to limit the search to a specific file.
            
        Returns:
            A list of FunctionInfo objects representing the methods of the class.
        """
        query_parts = ["""
            SELECT f.*, r.relative_folder, r.file_name
            FROM pythonfunction f
            JOIN repofile r ON f.file_id = r.id
            WHERE f.class_name = :class_name AND f.is_method = 1
        """]
        params = {"class_name": class_name}
        
        if file_path is not None:
            folder, filename = os.path.split(file_path) if os.path.split(file_path)[0] else ("", file_path)
            query_parts.append("AND r.relative_folder = :folder AND r.file_name = :filename")
            params["folder"] = folder
            params["filename"] = filename
        
        query = " ".join(query_parts)
        with engine.connect() as conn:
            result = pd.read_sql(text(query), conn, params=params)
        
        methods = []
        for _, row in result.iterrows():
            file_path = os.path.join(row['relative_folder'], row['file_name'])
            methods.append(FunctionInfo(
                id=row['id'],
                name=row['name'],
                start_line=row['start_line'],
                end_line=row['end_line'],
                args=row['args'],
                is_method=bool(row['is_method']),
                class_name=row['class_name'],
                is_async=bool(row['is_async']),
                decorators=row['decorators'],
                docstring=row['docstring'],
                file_id=row['file_id'],
                file_path=file_path
            ))
        return methods
    
    @tool
    def get_file_structure( file_path: str) -> Dict[str, Any]:
        """
        Get the complete structure of a Python file including functions, classes, and variables.
        
        Args:
            file_path: The relative path to the file, including folder and filename.
            
        Returns:
            A dictionary with keys 'classes', 'functions', and 'variables', each containing
            a list of corresponding objects in order of appearance in the file.
        """
        file_info = get_file_by_path(file_path)
        if file_info is None:
            return {"classes": [], "functions": [], "variables": []}
        
        # Get classes
        query = """
        SELECT id, name, start_line, end_line, base_classes, decorators, docstring
        FROM pythonclass
        WHERE file_id = :file_id
        ORDER BY start_line
        """
        with engine.connect() as conn:
            classes_df = pd.read_sql(text(query), conn, params={"file_id": file_info.id})
        
        classes = []
        for _, row in classes_df.iterrows():
            classes.append(ClassInfo(
                id=row['id'],
                name=row['name'],
                start_line=row['start_line'],
                end_line=row['end_line'],
                base_classes=row['base_classes'],
                decorators=row['decorators'],
                docstring=row['docstring'],
                file_id=file_info.id,
                file_path=file_info.full_path
            ))
        
        # Get functions
        query = """
        SELECT id, name, start_line, end_line, args, is_method, class_name, is_async, decorators, docstring
        FROM pythonfunction
        WHERE file_id = :file_id
        ORDER BY start_line
        """
        with engine.connect() as conn:
            functions_df = pd.read_sql(text(query), conn, params={"file_id": file_info.id})
        
        functions = []
        for _, row in functions_df.iterrows():
            functions.append(FunctionInfo(
                id=row['id'],
                name=row['name'],
                start_line=row['start_line'],
                end_line=row['end_line'],
                args=row['args'],
                is_method=bool(row['is_method']),
                class_name=row['class_name'],
                is_async=bool(row['is_async']),
                decorators=row['decorators'],
                docstring=row['docstring'],
                file_id=file_info.id,
                file_path=file_info.full_path
            ))
        
        # Get variables
        query = """
        SELECT id, name, line, value_repr, is_module_level, class_name
        FROM pythonvariable
        WHERE file_id = :file_id
        ORDER BY line
        """
        with engine.connect() as conn:
            variables_df = pd.read_sql(text(query), conn, params={"file_id": file_info.id})
        
        variables = []
        for _, row in variables_df.iterrows():
            variables.append(VariableInfo(
                id=row['id'],
                name=row['name'],
                line=row['line'],
                value_repr=row['value_repr'],
                is_module_level=bool(row['is_module_level']),
                class_name=row['class_name'],
                file_id=file_info.id,
                file_path=file_info.full_path
            ))
        
        return {
            "classes": classes,
            "functions": functions,
            "variables": variables
        }
    
    @tool
    def get_code_segment( file_path: str, start_line: int, end_line: int) -> str:
        """
        Get a segment of code from a file between the specified line numbers.
        
        Args:
            file_path: The relative path to the file, including folder and filename.
            start_line: The starting line number (1-based).
            end_line: The ending line number (1-based, inclusive).
            
        Returns:
            The requested segment of code as a string.
        """
        content = get_file_content(file_path=file_path)
        if content is None:
            return ""
        
        lines = content.splitlines()
        if start_line > len(lines) or start_line < 1:
            return ""
        
        end_line = min(end_line, len(lines))
        return "\n".join(lines[start_line-1:end_line])
    

    return {
        "get_folders": get_folders,
        "get_files_in_folder": get_files_in_folder,
        "get_files_by_extension": get_files_by_extension,
        "get_file_by_path": get_file_by_path,
        "get_file_content": get_file_content,
        "get_entity_at_line": get_entity_at_line,
        "get_function_by_name": get_function_by_name,
        "get_class_by_name": get_class_by_name,
        "get_class_methods": get_class_methods,
        "get_file_structure": get_file_structure,
        "get_code_segment": get_code_segment
    }
    