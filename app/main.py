"""
Main FastAPI application.
"""
import logging
from typing import Dict
import uuid

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.pricing_service import PricingService
from app.models.enums import ErrorSource
from app.models.base_schemas import ErrorResponse
from app.models.compute_schemas import ComputePricingRequest, ComputePricingResponse
from app.models.storage_schemas import StoragePricingRequest, StoragePricingResponse
from app.models.enums import Region

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Cloud Pricing Comparison API",
    description=(
        "API for comparing prices across cloud providers for compute and storage resources. "
        "\n---\n"
        "### Example Usage\n"
        "- To get pricing for Europe, set `region` to `europe` in your request.\n"
        "- Example compute request body:\n"
        "```json\n"
        "{\n  \"region\": \"europe\",\n  \"specs\": {\n    \"vcpu\": 2,\n    \"ram_gib\": 8\n  }\n}\n"
        "```\n"
        "- Example storage request body:\n"
        "```json\n"
        "{\n  \"region\": \"europe\",\n  \"specs\": {\n    \"tier\": \"FrequentAccess\"\n  }\n}\n"
        "```\n"
    ),
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pricing service instance
_pricing_service = None


# Dependency for pricing service
async def get_pricing_service() -> PricingService:
    """
    Get or create the pricing service.
    
    Returns:
        Pricing service instance
    """
    global _pricing_service
    
    if _pricing_service is None:
        _pricing_service = PricingService()
        
    return _pricing_service


# Register shutdown event to close clients
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global _pricing_service
    if _pricing_service:
        await _pricing_service.close()


@app.get("/", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint returning service status."""
    return {"status": "healthy", "message": "Cloud Pricing Comparison API is running"}


@app.post(
    "/pricing/compute",
    response_model=ComputePricingResponse,
    responses={
        200: {"model": ComputePricingResponse, "description": "Successful compute pricing comparison"},
        400: {"model": ErrorResponse, "description": "Bad request or validation error"},
        404: {"model": ErrorResponse, "description": "No pricing data found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["Pricing"],
    description=(
        "## AWS Compute Pricing Assumptions\n"
        "- Only On-Demand EC2 instance pricing is supported (no Reserved/Spot).\n"
        "- Only Linux OS, Shared tenancy, and no pre-installed software are considered.\n"
        "- Only instances with exact vCPU and RAM match are returned.\n"
        "- Pricing is fetched from the AWS Pricing API (region: us-east-1).\n"
        "- For compute, only 'Used' capacity status is considered.\n"
        "- Results are filtered by the selected continent/region, not individual AWS region codes.\n"
        "\n### AWS Region Mapping\n"
        "| Region Enum         | AWS Region Code      | AWS Region Name                |\n"
        "|---------------------|---------------------|-------------------------------|\n"
        "| NORTH_AMERICA       | us-east-1           | US East (N. Virginia)         |\n"
        "|                     | us-east-2           | US East (Ohio)                |\n"
        "|                     | us-west-1           | US West (N. California)       |\n"
        "|                     | us-west-2           | US West (Oregon)              |\n"
        "|                     | ca-central-1        | Canada (Central)              |\n"
        "|                     | ca-west-1           | Canada West (Calgary)         |\n"
        "|                     | mx-central-1        | Mexico (Central)              |\n"
        "|                     | us-gov-west-1       | AWS GovCloud (US-West)        |\n"
        "|                     | us-gov-east-1       | AWS GovCloud (US-East)        |\n"
        "| SOUTH_AMERICA       | sa-east-1           | South America (Sao Paulo)     |\n"
        "| EUROPE              | eu-central-1        | EU (Frankfurt)                |\n"
        "|                     | eu-central-2        | Europe (Zurich)               |\n"
        "|                     | eu-west-1           | EU (Ireland)                  |\n"
        "|                     | eu-west-2           | EU (London)                   |\n"
        "|                     | eu-west-3           | EU (Paris)                    |\n"
        "|                     | eu-south-1          | EU (Milan)                    |\n"
        "|                     | eu-south-2          | Europe (Spain)                |\n"
        "|                     | eu-north-1          | EU (Stockholm)                |\n"
        "| ASIA                | ap-east-1           | Asia Pacific (Hong Kong)      |\n"
        "|                     | ap-south-1          | Asia Pacific (Mumbai)         |\n"
        "|                     | ap-south-2          | Asia Pacific (Hyderabad)      |\n"
        "|                     | ap-northeast-1      | Asia Pacific (Tokyo)          |\n"
        "|                     | ap-northeast-2      | Asia Pacific (Seoul)          |\n"
        "|                     | ap-northeast-3      | Asia Pacific (Osaka)          |\n"
        "|                     | ap-southeast-1      | Asia Pacific (Singapore)      |\n"
        "|                     | ap-southeast-3      | Asia Pacific (Jakarta)        |\n"
        "|                     | ap-southeast-5      | Asia Pacific (Malaysia)       |\n"
        "|                     | ap-southeast-7      | Asia Pacific (Thailand)       |\n"
        "|                     | il-central-1        | Israel (Tel Aviv)             |\n"
        "|                     | me-south-1          | Middle East (Bahrain)         |\n"
        "|                     | me-central-1        | Middle East (UAE)             |\n"
        "| OCEANIA             | ap-southeast-2      | Asia Pacific (Sydney)         |\n"
        "|                     | ap-southeast-4      | Asia Pacific (Melbourne)      |\n"
        "| AFRICA              | af-south-1          | Africa (Cape Town)            |\n"
        "\n---\n"
        "### Example Usage\n"
        "```json\n"
        "{\n  \"region\": \"europe\",\n  \"specs\": {\n    \"vcpu\": 2,\n    \"ram_gib\": 8\n  }\n}\n"
        "```\n"
    ),
)
async def compare_compute_pricing(
    request: ComputePricingRequest,
    pricing_service: PricingService = Depends(get_pricing_service),
) -> ComputePricingResponse:
    """
    Compare compute instance prices across cloud providers.

    AWS Compute Pricing Assumptions:
    - Only On-Demand EC2 instance pricing is supported (no Reserved/Spot).
    - Only Linux OS, Shared tenancy, and no pre-installed software are considered.
    - Only instances with exact vCPU and RAM match are returned.
    - Pricing is fetched from the AWS Pricing API (region: us-east-1).
    - For compute, only 'Used' capacity status is considered.
    - Results are filtered by the selected continent/region, not individual AWS region codes.

    AWS Region Mapping:
      NORTH_AMERICA: us-east-1 (US East N. Virginia), us-east-2 (US East Ohio), us-west-1 (US West N. California), us-west-2 (US West Oregon), ca-central-1 (Canada Central), ca-west-1 (Canada West Calgary), mx-central-1 (Mexico Central), us-gov-west-1 (AWS GovCloud US-West), us-gov-east-1 (AWS GovCloud US-East)
      SOUTH_AMERICA: sa-east-1 (South America Sao Paulo)
      EUROPE: eu-central-1 (EU Frankfurt), eu-central-2 (Europe Zurich), eu-west-1 (EU Ireland), eu-west-2 (EU London), eu-west-3 (EU Paris), eu-south-1 (EU Milan), eu-south-2 (Europe Spain), eu-north-1 (EU Stockholm)
      ASIA: ap-east-1 (Asia Pacific Hong Kong), ap-south-1 (Asia Pacific Mumbai), ap-south-2 (Asia Pacific Hyderabad), ap-northeast-1 (Asia Pacific Tokyo), ap-northeast-2 (Asia Pacific Seoul), ap-northeast-3 (Asia Pacific Osaka), ap-southeast-1 (Asia Pacific Singapore), ap-southeast-3 (Asia Pacific Jakarta), ap-southeast-5 (Asia Pacific Malaysia), ap-southeast-7 (Asia Pacific Thailand), il-central-1 (Israel Tel Aviv), me-south-1 (Middle East Bahrain), me-central-1 (Middle East UAE)
      OCEANIA: ap-southeast-2 (Asia Pacific Sydney), ap-southeast-4 (Asia Pacific Melbourne)
      AFRICA: af-south-1 (Africa Cape Town)

    Example Usage:
      {
        "region": "europe",
        "specs": {
          "vcpu": 2,
          "ram_gib": 8
        }
      }

    If region is set to ALL, prices from all available regions will be returned.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Processing compute pricing request")
    
    try:
        response = await pricing_service.get_compute_pricing(request.region, request.specs)
        
        if not response.results and not response.errors:
            region_desc = "any region" if request.region == Region.ALL else f"region {request.region}"
            error_msg = f"No matching compute prices found in {region_desc}"
            logger.warning(f"[{request_id}] {error_msg}")
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error=error_msg,
                    source=ErrorSource.GENERAL,
                    details={"region": request.region.value}
                ).dict(),
            )
        
        logger.info(f"[{request_id}] Request completed successfully with {len(response.results)} price results")
        return response
        
    except ValueError as e:
        logger.error(f"[{request_id}] Value error: {str(e)}")
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=str(e),
                source=ErrorSource.GENERAL,
                details={"type": "ValueError"}
            ).dict(),
        )
        
    except Exception as e:
        logger.exception(f"[{request_id}] Error comparing compute prices: {str(e)}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=f"Error comparing compute prices: {str(e)}",
                source=ErrorSource.GENERAL,
                details={"type": type(e).__name__}
            ).dict(),
        )


@app.post(
    "/pricing/storage",
    response_model=StoragePricingResponse,
    responses={
        200: {"model": StoragePricingResponse, "description": "Successful storage pricing comparison"},
        400: {"model": ErrorResponse, "description": "Bad request or validation error"},
        404: {"model": ErrorResponse, "description": "No pricing data found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    tags=["Pricing"],
    description=(
        "## AWS Storage Pricing Assumptions\n"
        "- Storage pricing maps custom tiers to AWS S3 storage classes.\n"
        "- Pricing is fetched from the AWS Pricing API (region: us-east-1).\n"
        "- For storage, only 'Storage' product family and relevant storageClass are queried.\n"
        "- Results are filtered by the selected continent/region, not individual AWS region codes.\n"
        "\n### AWS Region Mapping\n"
        "| Region Enum         | AWS Region Code      | AWS Region Name                |\n"
        "|---------------------|---------------------|-------------------------------|\n"
        "| NORTH_AMERICA       | us-east-1           | US East (N. Virginia)         |\n"
        "|                     | us-east-2           | US East (Ohio)                |\n"
        "|                     | us-west-1           | US West (N. California)       |\n"
        "|                     | us-west-2           | US West (Oregon)              |\n"
        "|                     | ca-central-1        | Canada (Central)              |\n"
        "|                     | ca-west-1           | Canada West (Calgary)         |\n"
        "|                     | mx-central-1        | Mexico (Central)              |\n"
        "|                     | us-gov-west-1       | AWS GovCloud (US-West)        |\n"
        "|                     | us-gov-east-1       | AWS GovCloud (US-East)        |\n"
        "| SOUTH_AMERICA       | sa-east-1           | South America (Sao Paulo)     |\n"
        "| EUROPE              | eu-central-1        | EU (Frankfurt)                |\n"
        "|                     | eu-central-2        | Europe (Zurich)               |\n"
        "|                     | eu-west-1           | EU (Ireland)                  |\n"
        "|                     | eu-west-2           | EU (London)                   |\n"
        "|                     | eu-west-3           | EU (Paris)                    |\n"
        "|                     | eu-south-1          | EU (Milan)                    |\n"
        "|                     | eu-south-2          | Europe (Spain)                |\n"
        "|                     | eu-north-1          | EU (Stockholm)                |\n"
        "| ASIA                | ap-east-1           | Asia Pacific (Hong Kong)      |\n"
        "|                     | ap-south-1          | Asia Pacific (Mumbai)         |\n"
        "|                     | ap-south-2          | Asia Pacific (Hyderabad)      |\n"
        "|                     | ap-northeast-1      | Asia Pacific (Tokyo)          |\n"
        "|                     | ap-northeast-2      | Asia Pacific (Seoul)          |\n"
        "|                     | ap-northeast-3      | Asia Pacific (Osaka)          |\n"
        "|                     | ap-southeast-1      | Asia Pacific (Singapore)      |\n"
        "|                     | ap-southeast-3      | Asia Pacific (Jakarta)        |\n"
        "|                     | ap-southeast-5      | Asia Pacific (Malaysia)       |\n"
        "|                     | ap-southeast-7      | Asia Pacific (Thailand)       |\n"
        "|                     | il-central-1        | Israel (Tel Aviv)             |\n"
        "|                     | me-south-1          | Middle East (Bahrain)         |\n"
        "|                     | me-central-1        | Middle East (UAE)             |\n"
        "| OCEANIA             | ap-southeast-2      | Asia Pacific (Sydney)         |\n"
        "|                     | ap-southeast-4      | Asia Pacific (Melbourne)      |\n"
        "| AFRICA              | af-south-1          | Africa (Cape Town)            |\n"
        "\n---\n"
        "### Storage Tier to AWS Storage Class Mapping\n"
        "| Storage Tier         | AWS Storage Classes                                 |\n"
        "|----------------------|-----------------------------------------------------|\n"
        "| SMART                | Intelligent-Tiering                                 |\n"
        "| FREQUENT_ACCESS      | General Purpose, Non-Critical Data, High Performance|\n"
        "| OCCASIONAL_ACCESS    | Standard-IA, One Zone-IA                           |\n"
        "| RARE_ACCESS          | Glacier Instant Retrieval, Glacier Flexible Retrieval|\n"
        "| SHORT_TERM_ARCHIVE   | Glacier Flexible Retrieval                          |\n"
        "| LONG_TERM_ARCHIVE    | Deep Archive                                        |\n"
        "\n---\n"
        "### Example Usage\n"
        "```json\n"
        "{\n  \"region\": \"europe\",\n  \"specs\": {\n    \"tier\": \"FrequentAccess\"\n  }\n}\n"
        "```\n"
    ),
)
async def compare_storage_pricing(
    request: StoragePricingRequest,
    pricing_service: PricingService = Depends(get_pricing_service),
) -> StoragePricingResponse:
    """
    Compare storage prices across cloud providers.

    AWS Storage Pricing Assumptions:
    - Storage pricing maps custom tiers to AWS S3 storage classes.
    - Pricing is fetched from the AWS Pricing API (region: us-east-1).
    - For storage, only 'Storage' product family and relevant storageClass are queried.
    - Results are filtered by the selected continent/region, not individual AWS region codes.

    AWS Region Mapping:
      NORTH_AMERICA: us-east-1 (US East N. Virginia), us-east-2 (US East Ohio), us-west-1 (US West N. California), us-west-2 (US West Oregon), ca-central-1 (Canada Central), ca-west-1 (Canada West Calgary), mx-central-1 (Mexico Central), us-gov-west-1 (AWS GovCloud US-West), us-gov-east-1 (AWS GovCloud US-East)
      SOUTH_AMERICA: sa-east-1 (South America Sao Paulo)
      EUROPE: eu-central-1 (EU Frankfurt), eu-central-2 (Europe Zurich), eu-west-1 (EU Ireland), eu-west-2 (EU London), eu-west-3 (EU Paris), eu-south-1 (EU Milan), eu-south-2 (Europe Spain), eu-north-1 (EU Stockholm)
      ASIA: ap-east-1 (Asia Pacific Hong Kong), ap-south-1 (Asia Pacific Mumbai), ap-south-2 (Asia Pacific Hyderabad), ap-northeast-1 (Asia Pacific Tokyo), ap-northeast-2 (Asia Pacific Seoul), ap-northeast-3 (Asia Pacific Osaka), ap-southeast-1 (Asia Pacific Singapore), ap-southeast-3 (Asia Pacific Jakarta), ap-southeast-5 (Asia Pacific Malaysia), ap-southeast-7 (Asia Pacific Thailand), il-central-1 (Israel Tel Aviv), me-south-1 (Middle East Bahrain), me-central-1 (Middle East UAE)
      OCEANIA: ap-southeast-2 (Asia Pacific Sydney), ap-southeast-4 (Asia Pacific Melbourne)
      AFRICA: af-south-1 (Africa Cape Town)

    Storage Tier to AWS Storage Class Mapping:
      SMART: Intelligent-Tiering
      FREQUENT_ACCESS: General Purpose, Non-Critical Data, High Performance
      OCCASIONAL_ACCESS: Standard-IA, One Zone-IA
      RARE_ACCESS: Glacier Instant Retrieval, Glacier Flexible Retrieval
      SHORT_TERM_ARCHIVE: Glacier Flexible Retrieval
      LONG_TERM_ARCHIVE: Deep Archive

    Example Usage:
      {
        "region": "europe",
        "specs": {
          "tier": "FrequentAccess"
        }
      }

    If region is set to ALL, prices from all available regions will be returned.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Processing storage pricing request")
    
    try:
        response = await pricing_service.get_storage_pricing(request.region, request.specs)
        
        if not response.results and not response.errors:
            region_desc = "any region" if request.region == Region.ALL else f"region {request.region}"
            error_msg = f"No matching storage prices found in {region_desc}"
            logger.warning(f"[{request_id}] {error_msg}")
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error=error_msg,
                    source=ErrorSource.GENERAL,
                    details={"region": request.region.value}
                ).dict(),
            )
        
        logger.info(f"[{request_id}] Request completed successfully with {len(response.results)} price results")
        return response
        
    except ValueError as e:
        logger.error(f"[{request_id}] Value error: {str(e)}")
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=str(e),
                source=ErrorSource.GENERAL,
                details={"type": "ValueError"}
            ).dict(),
        )
        
    except Exception as e:
        logger.exception(f"[{request_id}] Error comparing storage prices: {str(e)}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=f"Error comparing storage prices: {str(e)}",
                source=ErrorSource.GENERAL,
                details={"type": type(e).__name__}
            ).dict(),
        ) 