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
        "Currently supports AWS, with a design for extending to other providers in the future."
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
)
async def compare_compute_pricing(
    request: ComputePricingRequest,
    pricing_service: PricingService = Depends(get_pricing_service),
) -> ComputePricingResponse:
    """
    Compare compute instance prices across cloud providers.
    
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
)
async def compare_storage_pricing(
    request: StoragePricingRequest,
    pricing_service: PricingService = Depends(get_pricing_service),
) -> StoragePricingResponse:
    """
    Compare storage prices across cloud providers.
    
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