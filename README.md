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

## Standardized CSV Output Format For Compute Instances

The data collection scripts for each cloud provider (AWS, Azure, and eventually GCP) are designed to produce a CSV file with a standardized format. This allows for consistent processing and analysis.

Please note: We only add OnDemand instances.

The CSV file has the following columns:

| Field Name            | Data Type      | Description                                                                                                                                     | Example (for a GCP instance)                |
| --------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| `vm_name`             | String         | The official name/type of the VM instance (e.g., instance name type).                                                                           | `"n2-standard-2"`                           |
| `provider_name`       | String         | The name of the cloud provider. This will be one of `AWS`, `AZURE`, or `GCP`.                                                                   | `"GCP"`                                     |
| `virtual_cpu_count`   | Integer        | The number of virtual CPUs (vCPUs) for the instance.                                                                                            | `2`                                         |
| `memory_gb`           | Float          | The amount of memory (RAM) for the instance, specified in Gibibytes (GiB).                                                                      | `8.0`                                       |
| `cpu_arch`            | String         | The CPU architecture. Common values are `"x86_64"` and `"ARM64"`.                                                                                 | `"x86_64"`                                  |
| `price_per_hour_usd`  | Float          | The on-demand (pay-as-you-go) price for the instance per hour, in US Dollars.                                                                   | `0.095`                                     |
| `gpu_count`           | Integer        | The number of GPUs attached to the instance. Should be `0` if none.                                                                             | `1`                                         |
| `gpu_name`            | String         | The name or model of the attached GPU (e.g., "NVIDIA Tesla T4"). Should be empty or null if `gpu_count` is 0.                                    | `"NVIDIA Tesla T4"`                         |
| `gpu_memory`          | Float          | The total memory for all GPUs attached, in Gibibytes (GiB). Should be `0.0` if `gpu_count` is 0.                                                 | `16.0`                                      |
| `os_type`             | String (Enum)  | The general operating system family. Possible values are: `LINUX`, `WINDOWS`, `OTHER`.                                                          | `"LINUX"`                                   |
| `region`              | String (Enum)  | The geographical continent where the instance is located. Possible values are: `north_america`, `south_america`, `europe`, `asia`, `africa`, `oceania`, `antarctica`. | `"north_america"`                           |
| `other_details`       | String (JSON)  | A single JSON string containing provider-specific details. In the output CSV, this entire string is enclosed in double quotes (`"`), and any internal double quotes are escaped. | `"{""key"":""value""}"`                      |



## Standardized CSV Output Format For Storage (TODO)
