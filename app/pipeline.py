import asyncio
import os
import time
from typing import Optional
from prisma import Prisma
from app.utils.db_config import get_database_url, get_connection_params, format_connection_string
from app.utils.csv_loader import CSVBatchLoader
from app.utils.transform_data_types import transform_vm_data

class DatabaseConnection:
    def __init__(self, connection_url: Optional[str] = None):
        """
        Initialize database connection with flexible configuration options.
        
        Args:
            connection_url: Optional explicit connection URL
        """
        # Try explicit connection URL first
        self.connection_url = connection_url
        
        # If not provided, try environment variable or build from components
        if not self.connection_url:
            try:
                # Try to get from DATABASE_URL environment variable
                self.connection_url = get_database_url()
            except ValueError:
                # Build connection string from individual components
                params = get_connection_params()
                self.connection_url = format_connection_string(
                    user=params["user"],
                    password=params["password"],
                    host=params["host"],
                    port=params["port"],
                    database=params["database"]
                )
                
        # Override Prisma's database connection URL
        os.environ["DATABASE_URL"] = self.connection_url
        self.prisma = Prisma()
        
    async def connect(self, retry_count: int = 5, retry_delay: int = 2):
        """
        Connect to database with retry logic.
        
        Args:
            retry_count: Number of connection attempts
            retry_delay: Seconds between retry attempts
            
        Returns:
            Prisma client instance
            
        Raises:
            ConnectionError: If connection fails after all retries
        """
        connected = False
        attempt = 0
        
        while not connected and attempt < retry_count:
            try:
                print(f"Connecting to database (attempt {attempt+1}/{retry_count})...")
                await self.prisma.connect()
                connected = True
                print("Database connection established")
            except Exception as e:
                attempt += 1
                print(f"Connection failed: {str(e)}")
                if attempt < retry_count:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise ConnectionError(f"Failed to connect to database after {retry_count} attempts") from e
        
        return self.prisma
    
    async def disconnect(self):
        """Safely disconnect from the database"""
        try:
            print("Disconnecting from database")
            await self.prisma.disconnect()
        except Exception as e:
            print(f"Error during disconnect: {str(e)}")

async def run_pipeline():
    # Initialize database connection
    db = DatabaseConnection()
    prisma = await db.connect()

    try:
        # delete all data from the source table
        await prisma.ondemandvmpricing.delete_many()
        
        # Pipeline starts here and generates csvs for each provider
        # TODO: Implement pipeline
        
        # Initialize CSV batch loader
        csv_loader = CSVBatchLoader(prisma, batch_size=200)
        
        # Define CSV file paths
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        aws_csv_path = os.path.join(data_dir, 'aws_instances.csv')
        gcp_csv_path = os.path.join(data_dir, 'gcp_instances.csv')
        azure_csv_path = os.path.join(data_dir, 'azure_instances.csv')
        
        
        # Check if CSV files exist and load data in parallel
        csv_configs = []
        
        if os.path.exists(aws_csv_path):
            csv_configs.append({
                'file_path': aws_csv_path,
                'model_name': 'ondemandvmpricing',
                'transform_func': transform_vm_data
            })
            
        if os.path.exists(gcp_csv_path):
            csv_configs.append({
                'file_path': gcp_csv_path,
                'model_name': 'ondemandvmpricing',
                'transform_func': transform_vm_data
            })
            
        if os.path.exists(azure_csv_path):
            csv_configs.append({
                'file_path': azure_csv_path,
                'model_name': 'ondemandvmpricing',
                'transform_func': transform_vm_data
            })
            
        if csv_configs:
            print("Loading data from CSV files...")
            results = await csv_loader.load_multiple_csvs(csv_configs)
            
            for file_path, count in results.items():
                print(f"Loaded {count} records from {os.path.basename(file_path)}")
        else:
            print("No CSV files found. Using sample data instead.")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_pipeline()) 