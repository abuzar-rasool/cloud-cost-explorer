# Cloud Cost Explorer

A data pipeline to collect and analyze cloud computing costs across AWS, GCP, and Azure.

## Architecture

The application is designed with a decoupled architecture:
- **PostgreSQL Database**: Runs in Docker, stores cloud pricing data
- **Python Data Pipeline**: Runs locally, collects and processes cloud provider pricing information
- **Prisma ORM**: Provides database access layer

The pipeline runs locally but connects to the database that can be hosted anywhere.

## Setup

### Prerequisites
- Docker and Docker Compose (for database)
- Python 3.10+ (for local pipeline execution)
- PostgreSQL 15+ (if running database elsewhere)

### Database Configuration

The application supports multiple ways to configure the database connection:

1. **Environment Variables (recommended)**:

   Set the `DATABASE_URL` environment variable:
   ```
   DATABASE_URL=postgresql://username:password@hostname:5432/database_name
   ```

2. **Individual Connection Parameters**:

   Set individual database connection components:
   ```
   DB_HOST=hostname
   DB_PORT=5432
   DB_USER=username
   DB_PASSWORD=password
   DB_NAME=database_name
   ```

3. **Local Development**:
   
   For local development with Docker database, set:
   ```
   DATABASE_URL=postgresql://clouduser:cloudpassword@localhost:5432/cloudcosts
   ```

### Starting the Database

Start the PostgreSQL database using Docker Compose:
```
docker-compose up -d
```

This will start only the database service, making it available on port 5432.

### Running the Pipeline Locally

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Generate the Prisma client:
   ```
   python -m prisma generate
   ```

3. Set up the database schema:
   ```
   python setup_db.py
   ```

4. Run the pipeline using environment variables:
   ```
   export DATABASE_URL=postgresql://clouduser:cloudpassword@localhost:5432/cloudcosts
   python run_pipeline.py
   ```

5. Or run with command line options:
   ```
   python run_pipeline.py --db-host=localhost --db-user=clouduser --db-password=cloudpassword --db-name=cloudcosts
   ```
   
   Alternatively:
   ```
   python run_pipeline.py --db-url=postgresql://clouduser:cloudpassword@localhost:5432/cloudcosts
   ```

### Database Structure

The application creates three tables:
- `aws-instance-compute`: AWS EC2 instance data
- `gcp-instance-compute`: GCP Compute Engine instance data
- `azure-instance-compute`: Azure VM instance data

Each table contains basic VM information that can be expanded with additional columns as needed.

### Manual Pipeline Execution

To manually run the pipeline:
```
python run_pipeline.py
``` 