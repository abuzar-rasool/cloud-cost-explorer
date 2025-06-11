#!/usr/bin/env python3
"""
Run the cloud cost explorer pipeline with flexible database configuration.

This script provides a command-line interface for running the data pipeline
with various database connection options.
"""
import argparse
import asyncio
import os
import sys
from app.utils.db_config import format_connection_string
from app.pipeline import run_pipeline


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Cloud Cost Explorer Pipeline")
    
    # Database connection options
    db_group = parser.add_argument_group("Database Connection")
    db_group.add_argument("--db-url", help="Full database connection URL")
    db_group.add_argument("--db-host", help="Database hostname")
    db_group.add_argument("--db-port", type=int, default=5432, help="Database port (default: 5432)")
    db_group.add_argument("--db-name", help="Database name")
    db_group.add_argument("--db-user", help="Database username")
    db_group.add_argument("--db-password", help="Database password")
    
    return parser.parse_args()


def main():
    """Run the pipeline with the specified configuration."""
    args = parse_args()
    
    # Set database connection URL if provided directly
    if args.db_url:
        os.environ["DATABASE_URL"] = args.db_url
    
    # Set individual components if provided
    elif all([args.db_host, args.db_name, args.db_user, args.db_password]):
        os.environ["DB_HOST"] = args.db_host
        os.environ["DB_PORT"] = str(args.db_port)
        os.environ["DB_NAME"] = args.db_name
        os.environ["DB_USER"] = args.db_user
        os.environ["DB_PASSWORD"] = args.db_password
        
        # Also set the DATABASE_URL for convenience
        connection_url = format_connection_string(
            user=args.db_user,
            password=args.db_password,
            host=args.db_host,
            port=str(args.db_port),
            database=args.db_name
        )
        os.environ["DATABASE_URL"] = connection_url
    
    # Run the pipeline
    try:
        asyncio.run(run_pipeline())
        return 0
    except Exception as e:
        print(f"Pipeline execution failed: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 