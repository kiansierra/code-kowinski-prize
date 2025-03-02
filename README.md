# Kowinski

A toolkit for code repository analysis and exploration, with a focus on Python codebases.

## Installation

```bash
pip install -e .
```

## Usage

### Analyzing a GitHub Issue

```bash
kowinski-analyze --repo-path /path/to/repo --issue-data /path/to/issues.parquet --issue-index 0
```

### Using in Python

```python
from kowinski import parse_repository, analyze_python_files, repository_querier
from kowinski.agents.code_agent import create_analysis_agent, create_code_agent

# Parse and analyze a repository
parse_repository("/path/to/repo")
analyze_python_files()

# Create tools for querying the repository
tools = repository_querier().values()

# Create an analysis agent
analysis_agent = create_analysis_agent(
    model_id="gemini-2.0-flash",
    name="analysis_agent",
    description="This agent analyzes the codebase to find issues."
)

# Create a main agent
agent = create_code_agent(
    model_id="gemini-2.0-flash",
    analysis_agent=analysis_agent,
)

# Run the agent on a task
result = agent.run("Find the bug in the repository")
print(result)
```

## Features

- Repository parsing and analysis
- Python code structure extraction
- AI-powered code exploration and issue analysis
- Flexible agent configuration

## Requirements

- Python 3.8+
- Dependencies listed in setup.py
