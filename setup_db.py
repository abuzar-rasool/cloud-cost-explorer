#!/usr/bin/env python3
"""
Database setup script for Cloud Cost Explorer.

This script runs Prisma migrations to set up the database schema.
It can be run independently of the main pipeline.
"""
import os
import subprocess
import sys
from app.utils.db_config import get_database_url, get_connection_params, format_connection_string


def setup_database():
    """Set up the database schema using Prisma."""
    print("Setting up database schema...")
    
    # Try to get the database URL
    try:
        # Try the DATABASE_URL environment variable first
        try:
            database_url = get_database_url()
            print(f"Using DATABASE_URL from environment: {database_url.split('@')[1]}")
        except ValueError:
            # Build from components if DATABASE_URL is not set
            params = get_connection_params()
            database_url = format_connection_string(
                user=params["user"],
                password=params["password"],
                host=params["host"],
                port=params["port"],
                database=params["database"]
            )
            print(f"Using database connection: {params['host']}:{params['port']}/{params['database']}")
            
        # Set the environment variable for Prisma
        os.environ["DATABASE_URL"] = database_url
        
        # Run Prisma generate
        print("Generating Prisma client...")
        subprocess.run(["python", "-m", "prisma", "generate"], check=True)
        
        # Run Prisma migrations
        print("Applying database migrations...")
        subprocess.run(["python", "-m", "prisma", "db", "push"], check=True)
        
        print("Database setup complete!")
        return True
        
    except Exception as e:
        print(f"Error setting up database: {str(e)}")
        return False


if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1) 