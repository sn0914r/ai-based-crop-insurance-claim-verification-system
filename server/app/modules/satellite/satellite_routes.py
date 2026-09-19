import logging
from fastapi import APIRouter, HTTPException, status
from app.modules.satellite.satellite_schema import (
    SatelliteVerificationRequest,
    SatelliteVerificationResponse
)
from app.providers.satellite_provider import satellite_provider
from app.core.satellite_engine import satellite_engine
from app.errors.app_error import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/satellite", tags=["Satellite Remote Sensing"])

@router.post(
    "/verify",
    response_model=SatelliteVerificationResponse,
    summary="Verify field vegetation damage via Sentinel-2 satellite NDVI",
    description="Analyzes pre-disaster and post-disaster Sentinel-2 satellite imagery for a field boundary polygon, calculating NDVI drop and percentage of damaged land area."
)
def verify_satellite_land_damage(payload: SatelliteVerificationRequest):
    try:
        raw_satellite = satellite_provider.get_satellite_data(
            field_boundary=payload.fieldBoundary,
            incident_date=payload.incidentDate
        )
        assessment = satellite_engine.evaluate_field(
            field_boundary=payload.fieldBoundary,
            satellite_data=raw_satellite
        )
        return SatelliteVerificationResponse(
            success=True,
            preDisasterNdvi=assessment["preDisasterNdvi"],
            postDisasterNdvi=assessment["postDisasterNdvi"],
            ndviDrop=assessment["ndviDrop"],
            damagedAreaPercentage=assessment["damagedAreaPercentage"],
            satelliteScore=assessment["satelliteScore"],
            damageClassification=assessment["damageClassification"],
            fieldAreaHectares=assessment["fieldAreaHectares"],
            damagedAreaHectares=assessment["damagedAreaHectares"],
            cloudCoverPercentage=assessment["cloudCoverPercentage"],
            preDate=assessment.get("preDate"),
            postDate=assessment.get("postDate"),
            spatialZoning=assessment.get("spatialZoning"),
            dataSource=assessment["dataSource"],
            summary=assessment["summary"]
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Satellite assessment error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Satellite assessment failed: {str(e)}"
        )
