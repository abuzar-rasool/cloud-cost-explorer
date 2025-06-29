import asyncio
import os
import time
import glob
from typing import Optional
from prisma import Prisma
from scripts.utils.db_config import get_database_url, get_connection_params, format_connection_string
from scripts.utils.csv_loader import CSVBatchLoader
from scripts.utils.transform_data_types import transform_vm_data, transform_storage_data

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
        await prisma.storagepricing.delete_many()
        
        # Pipeline starts here and generates csvs for each provider
        # TODO: Implement pipeline
        
        # Initialize CSV batch loader
        csv_loader = CSVBatchLoader(prisma, batch_size=200)
        
        # Define data directory
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        
        # Scan for all CSV files in the data directory
        all_csv_files = glob.glob(os.path.join(data_dir, '*.csv'))
        
        # Categorize CSV files based on their endings
        instances_configs = []
        storage_configs = []
        
        for csv_file in all_csv_files:
            filename = os.path.basename(csv_file)
            
            if filename.endswith('instances.csv'):
                instances_configs.append({
                    'file_path': csv_file,
                    'model_name': 'ondemandvmpricing',
                    'transform_func': transform_vm_data
                })
                print(f"Found instances file: {filename}")
                
            elif filename.endswith('storage.csv'):
                storage_configs.append({
                    'file_path': csv_file,
                    'model_name': 'storagepricing',
                    'transform_func': transform_storage_data
                })
                print(f"Found storage file: {filename}")
        
        # Combine all configurations
        all_csv_configs = instances_configs + storage_configs
        
        if all_csv_configs:
            print(f"\nLoading data from {len(all_csv_configs)} CSV files...")
            print(f"- {len(instances_configs)} instances files -> ondemandvmpricing table")
            print(f"- {len(storage_configs)} storage files -> storagepricing table")
            
            results = await csv_loader.load_multiple_csvs(all_csv_configs)
            
            print("\nLoad Results:")
            for file_path, count in results.items():
                filename = os.path.basename(file_path)
                table = "ondemandvmpricing" if filename.endswith('instances.csv') else "storagepricing"
                print(f"Loaded {count} records from {filename} -> {table}")
        else:
            print("No CSV files found in the data directory.")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_pipeline()) 