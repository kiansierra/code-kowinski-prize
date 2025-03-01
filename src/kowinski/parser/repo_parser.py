import os
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session
import pathlib

# Define the File model
class RepoFile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    relative_folder: str = Field(index=True)
    file_name: str = Field(index=True)
    file_extension: str = Field(index=True)
    content: str
    line_count: int

# Function to create the database engine
def get_engine(db_path="repository.db"):
    sqlite_url = f"sqlite:///{db_path}"
    engine = create_engine(sqlite_url, echo=False)
    SQLModel.metadata.create_all(engine)
    return engine

# Main function to parse repository and store files
def parse_repository(repo_path, db_path="repository.db"):
    """
    Parse a repository and store file information in a SQLite database.
    
    Args:
        repo_path (str): Path to the repository
        db_path (str): Path where the SQLite database will be stored
    
    Returns:
        int: Number of files processed
    """
    # Create database engine
    engine = get_engine(db_path)
    
    # Convert repo_path to absolute path if it's not already
    repo_path = os.path.abspath(repo_path)
    
    # Counter for processed files
    processed_files = 0
    
    # Walk through the repository
    with Session(engine) as session:
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            
            # Process each file
            for file_name in files:
                file_path = os.path.join(root, file_name)
                
                # Skip if it's a directory somehow
                if os.path.isdir(file_path):
                    continue
                
                # Get relative path from repo root
                relative_path = os.path.relpath(root, repo_path)
                if relative_path == '.':
                    relative_path = ''
                
                # Get file extension
                file_extension = pathlib.Path(file_name).suffix.lstrip('.')
                
                try:
                    # Try to read the file as text
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        line_count = content.count('\n') + 1
                except UnicodeDecodeError:
                    # If we can't read it as text, mark it as binary
                    content = "[BINARY FILE]"
                    line_count = 0
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                    continue
                
                # Create and add the RepoFile object
                repo_file = RepoFile(
                    relative_folder=relative_path,
                    file_name=file_name,
                    file_extension=file_extension,
                    content=content,
                    line_count=line_count
                )
                
                session.add(repo_file)
                processed_files += 1
                
                # Commit every 100 files to avoid memory issues
                if processed_files % 100 == 0:
                    session.commit()
        
        # Final commit
        session.commit()
    
    print(f"Repository parsing complete. Processed {processed_files} files.")
    return processed_files

# Example usage
