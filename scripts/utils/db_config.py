"""
Database configuration utilities.
"""
import os
from urllib.parse import urlparse, ParseResult

import dotenv

dotenv.load_dotenv()


def get_database_url() -> str:
    """
    Get the database URL from environment variables.
    
    Returns:
        str: The database URL
        
    Raises:
        ValueError: If DATABASE_URL is not set
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    return database_url


def parse_database_url() -> ParseResult:
    """
    Parse the database URL into components.
    
    Returns:
        ParseResult: The parsed database URL
    """
    return urlparse(get_database_url())


def format_connection_string(
    user: str, password: str, host: str, port: str, database: str
) -> str:
    """
    Format a connection string from components.
    
    Args:
        user: Database username
        password: Database password
        host: Database host
        port: Database port
        database: Database name
        
    Returns:
        str: Formatted connection string
    """
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_connection_params() -> dict:
    """
    Get database connection parameters from the environment.
    
    Returns:
        dict: Database connection parameters
    """
    # Try to get individual components first
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    
    print(f"DB_HOST: {db_host}")
    print(f"DB_PORT: {db_port}")
    print(f"DB_USER: {db_user}")
    print(f"DB_PASSWORD: {db_pass}")
    print(f"DB_NAME: {db_name}")
    
    # If all components are available, use them
    if all([db_host, db_user, db_pass, db_name]):
        return {
            "host": db_host,
            "port": db_port,
            "user": db_user,
            "password": db_pass,
            "database": db_name,
        }
    
    # Otherwise, parse from DATABASE_URL
    try:
        parsed = parse_database_url()
        return {
            "host": parsed.hostname or "localhost",
            "port": str(parsed.port or 5432),
            "user": parsed.username or "clouduser",
            "password": parsed.password or "cloudpassword",
            "database": parsed.path.lstrip("/") or "cloudcosts",
        }
    except ValueError:
        # Return defaults if nothing is configured
        return {
            "host": "localhost",
            "port": "5432",
            "user": "clouduser",
            "password": "cloudpassword",
            "database": "cloudcosts",
        } 