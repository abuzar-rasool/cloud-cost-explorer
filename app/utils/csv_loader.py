import csv
import asyncio
from typing import List, Dict, Any, Optional, Callable
from prisma import Prisma
from pathlib import Path


class CSVBatchLoader:
    """
    Utility for loading data from CSV files into the database using Prisma client.
    Supports batch processing and custom transformations.
    """
    
    def __init__(self, prisma_client: Prisma, batch_size: int = 100):
        """
        Initialize the CSV batch loader.
        
        Args:
            prisma_client: An initialized and connected Prisma client
            batch_size: Number of records to insert in a single batch operation
        """
        self.prisma = prisma_client
        self.batch_size = batch_size
    
    async def load_csv(
        self,
        file_path: str, 
        model_name: str,
        mapping: Dict[str, str] = None,
        transform_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        skip_header: bool = True,
    ) -> int:
        """
        Load data from a CSV file into the specified Prisma model.
        
        Args:
            file_path: Path to the CSV file
            model_name: Name of the Prisma model to insert data into (e.g., 'awsinstancecompute')
            mapping: Optional mapping of CSV column names to database field names
            transform_func: Optional function to transform each row before insertion
            skip_header: Whether to skip the first row of the CSV (header row)
            
        Returns:
            Number of records inserted
            
        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            AttributeError: If the specified model doesn't exist in Prisma client
        """
        # Verify the file exists
        csv_path = Path(file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        # Get the appropriate model from Prisma client
        if not hasattr(self.prisma, model_name.lower()):
            raise AttributeError(f"Model '{model_name}' not found in Prisma client")
        
        model = getattr(self.prisma, model_name.lower())
        records_inserted = 0
        batch = []
        
        # Read and process the CSV file
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Skip header if needed
            if skip_header and not hasattr(reader, 'fieldnames'):
                next(reader, None)
            
            # Process each row
            for row in reader:
                data = {}
                
                # Apply column mapping if provided
                if mapping:
                    for csv_col, db_field in mapping.items():
                        if csv_col in row:
                            data[db_field] = row[csv_col]
                else:
                    # Use data as-is if no mapping provided
                    data = {k: v for k, v in row.items()}
                
                # Apply custom transformation if provided
                if transform_func:
                    data = transform_func(data)
                
                batch.append(data)
                
                # When batch size is reached, insert the batch
                if len(batch) >= self.batch_size:
                    await self._insert_batch(model, batch)
                    records_inserted += len(batch)
                    batch = []
            
            # Insert any remaining records
            if batch:
                await self._insert_batch(model, batch)
                records_inserted += len(batch)
                
        return records_inserted
    
    async def _insert_batch(self, model: Any, batch: List[Dict[str, Any]]):
        """
        Insert a batch of records into the database.
        
        Args:
            model: Prisma model to insert into
            batch: List of data dictionaries to insert
        """
        try:
            # Use create_many for efficient batch insertion
            await model.create_many(data=batch)
        except Exception as e:
            print(f"Error inserting batch: {str(e)}")
            # Fall back to individual inserts if batch insert fails
            for item in batch:
                try:
                    await model.create(data=item)
                except Exception as item_error:
                    print(f"Error inserting item {item}: {str(item_error)}")

    async def load_multiple_csvs(
        self,
        csv_configs: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Load multiple CSV files in parallel.
        
        Args:
            csv_configs: List of dictionaries, each with parameters for load_csv
                Each dict should have: file_path, model_name, and optionally mapping, 
                transform_func, and skip_header
                
        Returns:
            Dictionary mapping file paths to number of records inserted
        """
        tasks = []
        for config in csv_configs:
            file_path = config['file_path']
            model_name = config['model_name']
            mapping = config.get('mapping')
            transform_func = config.get('transform_func')
            skip_header = config.get('skip_header', True)
            
            task = asyncio.create_task(
                self.load_csv(
                    file_path=file_path,
                    model_name=model_name,
                    mapping=mapping,
                    transform_func=transform_func,
                    skip_header=skip_header
                )
            )
            tasks.append((file_path, task))
        
        results = {}
        for file_path, task in tasks:
            try:
                records = await task
                results[file_path] = records
            except Exception as e:
                print(f"Error loading {file_path}: {str(e)}")
                results[file_path] = 0
                
        return results 