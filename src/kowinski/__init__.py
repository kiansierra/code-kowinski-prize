"""
Kowinski - A toolkit for code repository analysis and exploration.

This package provides tools for parsing, analyzing, and querying code repositories,
with a focus on Python codebases.
"""

from kowinski.parser.repo_parser import parse_repository
from kowinski.parser.file_parser import analyze_python_files
from kowinski.tools.code_analysis import repository_querier
from kowinski.agents.code_agent import create_analysis_agent, create_code_agent

__all__ = [
    'parse_repository',
    'analyze_python_files',
    'repository_querier',
    'create_analysis_agent',
    'create_code_agent'
]
