"""
AWS credential configuration utility.
"""
import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

def configure_aws_credentials():
    """
    Configure AWS credentials for boto3.
    
    This function will always look for credentials in environment variables.
    If not found, it will raise an error.
    
    Returns:
        bool: True if credentials were configured successfully, False otherwise
    """
    # Check for credentials in environment variables
    if 'AWS_ACCESS_KEY_ID' in os.environ and 'AWS_SECRET_ACCESS_KEY' in os.environ:
        logger.info("AWS credentials found in environment variables")
        return True
    else:
        logger.error("AWS credentials not found in environment variables")
        return False