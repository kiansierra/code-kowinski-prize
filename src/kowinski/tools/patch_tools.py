from typing import Dict, List, Any, Optional, Union
import difflib
import re
from smolagents import tool

def patch_tools():
    """
    A set of tools for analyzing and patching files to fix GitHub issues.
    
    These tools help an agent understand a file's context, generate patches,
    and understand relevant code patterns to fix the identified issues.
    """
    
    @tool
    def generate_diff(original_content: str, modified_content: str, file_path: str) -> str:
        """
        Generate a unified diff between original and modified content.
        
        Args:
            original_content: Original file content
            modified_content: Modified file content
            file_path: Path to the file
            
        Returns:
            Unified diff as a string
        """
        original_lines = original_content.splitlines(keepends=True)
        modified_lines = modified_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=3  # Context lines
        )
        
        return ''.join(diff)
    
    @tool
    def extract_method_context(file_content: str, method_name: str) -> Dict[str, Any]:
        """
        Extract a method and its surrounding context from a file.
        
        Args:
            file_content: Content of the file
            method_name: Name of the method to find
            
        Returns:
            Dictionary with start_line, end_line, content, and surrounding context
        """
        lines = file_content.splitlines()
        pattern = fr"(?:def|class)\s+{re.escape(method_name)}\s*\("
        
        # Find the method definition
        method_start = None
        method_end = None
        indentation = ""
        
        for i, line in enumerate(lines):
            if method_start is None:
                if re.search(pattern, line):
                    method_start = i
                    indentation = re.match(r"^\s*", line).group(0)
            elif line.strip() and not line.startswith(indentation):
                # End of method found (less indentation)
                method_end = i - 1
                break
                
        if method_start is None:
            return {
                "found": False,
                "message": f"Method '{method_name}' not found in the file"
            }
        
        # If we didn't find the end, assume it's the end of the file
        if method_end is None:
            method_end = len(lines) - 1
            
        method_content = "\n".join(lines[method_start:method_end+1])
        
        # Get context before and after
        context_before_start = max(0, method_start - 10)
        context_before = "\n".join(lines[context_before_start:method_start])
        
        context_after_end = min(len(lines) - 1, method_end + 10)
        context_after = "\n".join(lines[method_end+1:context_after_end+1])
        
        return {
            "found": True,
            "start_line": method_start + 1,  # 1-indexed for user display
            "end_line": method_end + 1,
            "content": method_content,
            "context_before": context_before,
            "context_after": context_after,
            "full_range": (method_start, method_end)
        }
    
    @tool
    def identify_issue_patterns(file_content: str, issue_description: str) -> List[Dict[str, Any]]:
        """
        Identify patterns in the file that may be causing the issue.
        
        Args:
            file_content: Content of the file
            issue_description: Description of the GitHub issue
            
        Returns:
            List of dictionaries with information about each potential issue location
        """
        lines = file_content.splitlines()
        results = []
        
        # Extract error messages from the issue description
        error_patterns = []
        traceback_pattern = r"Traceback[^\n]*\n((?:[ ]*File \"[^\"]*\", line \d+[^\n]*\n)+)"
        tracebacks = re.findall(traceback_pattern, issue_description, re.MULTILINE)
        
        for traceback in tracebacks:
            # Extract file paths and line numbers
            file_line_pattern = r"File \"([^\"]*)\", line (\d+)"
            locations = re.findall(file_line_pattern, traceback)
            
            for filepath, line_num in locations:
                filename = filepath.split("/")[-1]
                error_patterns.append({
                    "type": "traceback",
                    "file": filename,
                    "line": int(line_num),
                    "context": traceback
                })
        
        # Look for specific error types mentioned in the issue
        error_types = [
            "TypeError", "ValueError", "AttributeError", "ImportError",
            "KeyError", "IndexError", "SyntaxError", "NameError"
        ]
        
        for error_type in error_types:
            if error_type in issue_description:
                error_msg_pattern = fr"{error_type}:\s*([^\n]+)"
                error_msgs = re.findall(error_msg_pattern, issue_description)
                
                for error_msg in error_msgs:
                    error_patterns.append({
                        "type": error_type,
                        "message": error_msg
                    })
        
        # Look for mentioned variables or functions
        mentioned_items = {}
        
        # Match potential function or method names in issue description
        func_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for match in re.finditer(func_pattern, issue_description):
            func_name = match.group(1)
            if func_name not in mentioned_items and len(func_name) > 2:  # Avoid common words
                mentioned_items[func_name] = "function"
        
        # Match potential variable names
        var_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        for match in re.finditer(var_pattern, issue_description):
            var_name = match.group(1)
            if var_name not in mentioned_items and len(var_name) > 2:
                mentioned_items[var_name] = "variable"
        
        # Now search for the identified patterns in the file
        for item_name, item_type in mentioned_items.items():
            if item_type == "function":
                # Look for function definitions or calls
                def_pattern = fr"def\s+{re.escape(item_name)}\s*\("
                call_pattern = fr"[^a-zA-Z0-9_]{re.escape(item_name)}\s*\("
                
                for i, line in enumerate(lines):
                    if re.search(def_pattern, line):
                        results.append({
                            "type": "function_definition",
                            "name": item_name,
                            "line": i + 1,
                            "content": line
                        })
                    elif re.search(call_pattern, line):
                        results.append({
                            "type": "function_call",
                            "name": item_name,
                            "line": i + 1,
                            "content": line
                        })
            else:
                # Look for variable assignments or usages
                for i, line in enumerate(lines):
                    if re.search(fr"[^a-zA-Z0-9_]{re.escape(item_name)}\s*=", line):
                        results.append({
                            "type": "variable_assignment",
                            "name": item_name,
                            "line": i + 1,
                            "content": line
                        })
                    elif re.search(fr"[^a-zA-Z0-9_]{re.escape(item_name)}[^a-zA-Z0-9_]", line):
                        results.append({
                            "type": "variable_usage",
                            "name": item_name,
                            "line": i + 1,
                            "content": line
                        })
        
        # Match line numbers from tracebacks to the file
        for pattern in error_patterns:
            if pattern["type"] == "traceback" and "line" in pattern:
                line_num = pattern["line"] - 1  # Convert to 0-indexed
                if 0 <= line_num < len(lines):
                    results.append({
                        "type": "traceback_line",
                        "line": pattern["line"],
                        "content": lines[line_num],
                        "context": pattern["context"]
                    })
        
        return results
    
    @tool
    def apply_patch_to_content(original_content: str, patch_operations: List[Dict[str, Any]]) -> str:
        """
        Apply a series of patch operations to the file content.
        
        Args:
            original_content: Original file content
            patch_operations: List of operations to apply, each being a dict with:
                - operation: "replace", "insert", or "delete"
                - start_line: Starting line number (1-indexed)
                - end_line: Ending line number for replace/delete (1-indexed)
                - content: New content for replace/insert operations
                
        Returns:
            The modified file content
        """
        lines = original_content.splitlines()
        
        # Sort operations in reverse order by line number
        # to prevent line number shifts affecting later operations
        sorted_ops = sorted(patch_operations, key=lambda op: op["start_line"], reverse=True)
        
        for op in sorted_ops:
            operation = op["operation"]
            # Convert to 0-indexed for internal operations
            start_idx = op["start_line"] - 1
            
            if operation == "replace":
                end_idx = op["end_line"] - 1
                new_content = op["content"].splitlines()
                lines[start_idx:end_idx+1] = new_content
            
            elif operation == "insert":
                new_content = op["content"].splitlines()
                lines[start_idx:start_idx] = new_content
            
            elif operation == "delete":
                end_idx = op["end_line"] - 1
                lines[start_idx:end_idx+1] = []
        
        return "\n".join(lines)
    
    return {
        "generate_diff": generate_diff,
        "extract_method_context": extract_method_context,
        "identify_issue_patterns": identify_issue_patterns,
        "apply_patch_to_content": apply_patch_to_content
    }