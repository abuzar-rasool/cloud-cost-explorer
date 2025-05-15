# cloud-cost-explorer

## Requirements
- Python 3.9

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set the required AWS credentials as environment variables:
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key-id
   export AWS_SECRET_ACCESS_KEY=your-secret-access-key
   ```

## Running the Application
Run the following command to start the application:
```bash
python run.py
```

## API Documentation
Once running, visit [http://localhost:8002/docs](http://localhost:8002/docs) for the interactive Swagger UI.

---

## Project Structure

```
cost-explorer-cloud/
│
├── app/
│   ├── api/                # Main service logic (e.g., PricingService)
│   ├── clients/            # Cloud provider integrations and interface
│   │   ├── aws_provider.py         # AWS implementation
│   │   ├── provider_interface.py   # Abstract base class for providers
│   │   ├── provider_factory.py     # Provider registration/selection
│   ├── models/             # Pydantic schemas and enums for requests/responses
│   ├── utils/              # Shared utility modules
│   └── main.py             # FastAPI app entrypoint
│
├── requirements.txt
├── run.py                  # App runner
└── README.md
```

- **app/clients/provider_interface.py**: Defines the `CloudProviderInterface` that all providers must implement.
- **app/clients/provider_factory.py**: Handles registration and instantiation of all supported providers.
- **app/models/**: Contains shared schemas and enums for compute/storage specs and results.

---

## How to Add a New Cloud Provider

1. **Create a new provider class** in `app/clients/`, e.g., `gcp_provider.py` or `azure_provider.py`.
2. **Subclass `CloudProviderInterface`** and implement the required methods:
   - `async def get_compute_pricing(self, region, specs) -> List[ComputePrice]`
   - `async def get_storage_pricing(self, region, specs) -> List[StoragePrice]`
   - Raise `ProviderError` for provider-specific errors.
3. **Register your provider** in `ProviderFactory`:
   - Open `app/clients/provider_factory.py`.
   - In the `_initialize_providers` method, import and instantiate your provider, then append it to `self._providers`.
   - Example:
     ```python
     from app.clients.gcp_provider import GcpProvider
     ...
     try:
         gcp_provider = GcpProvider()
         self._providers.append(gcp_provider)
     except Exception as e:
         logger.error(f"Failed to initialize GCP provider: {str(e)}")
     ```
4. **(Optional) Add any new enums or schemas** to `app/models/enums.py` or the relevant schema file if your provider requires new types.
5. **Test your provider** by making requests to the API endpoints and verifying the results.
