#!/usr/bin/env python3
"""
Script to analyze GitHub issues in a repository.

This script takes a repository path and issue data, parses the repository,
and uses AI agents to analyze the issue and identify problematic files.
"""

import os
import argparse
import pandas as pd
from IPython.display import Markdown
from dotenv import load_dotenv

from kowinski.parser.repo_parser import parse_repository
from kowinski.parser.file_parser import analyze_python_files
from kowinski.agents.code_agent import create_analysis_agent, create_code_agent, create_model

def main():
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Analyze GitHub issues in a repository")
    parser.add_argument("--repo-path", required=True, help="Path to the repository")
    parser.add_argument("--issue-data", required=True, help="Path to the issue data parquet file")
    parser.add_argument("--issue-index", type=int, default=0, help="Index of the issue to analyze")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Model to use for analysis")
    parser.add_argument("--db-path", default="repository.db", help="Path to the SQLite database")
    args = parser.parse_args()
    
    # Check if database exists and remove it if it does
    if os.path.exists(args.db_path):
        os.remove(args.db_path)
    
    # Load issue data
    issue_data = pd.read_parquet(args.issue_data)
    row = issue_data.iloc[args.issue_index]
    
    # Parse repository
    print(f"Parsing repository: {args.repo_path}")
    parse_repository(args.repo_path, db_path=args.db_path)
    
    # Analyze Python files
    print("Analyzing Python files...")
    analyze_python_files(db_path=args.db_path)

    model = create_model(model_id=args.model)
    
    # Create analysis agent
    analysis_agent = create_analysis_agent(
        model=model,
        name="analysis_agent",
        description="This agent is responsible for analyzing the codebase and determining what files are causing the issue."
    )
    
    # Create main agent
    agent = create_code_agent(
        model=model,
        analysis_agent=analysis_agent,
    )
    
    # Display system prompt (for debugging)
    print(Markdown(agent.system_prompt))
    
    # Create task description
    task = f"""You are tasked with understanding an issue in the following github repository {row['repo']}.
    You will be given a description of the issue and tools to search the codebase.
    Your job is to determine, what file or files are causing the issue.
    The tools provided will allow you to search the codebase and find the files that are causing the issue.
    Determine what is the function or class where this issue is happening
    ### Issue Description
    {row['problem_statement']}"""
    
    # Run the agent
    print("Running analysis...")
    result = agent.run(task)
    
    # Print result
    print("\nAnalysis Result:")
    print(result)

if __name__ == "__main__":
    main() 