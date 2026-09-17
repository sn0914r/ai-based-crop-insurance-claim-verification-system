from fastapi import APIRouter, status
from app.providers.weather_provider import weather_provider
from app.core.weather_engine import weather_engine
from app.core.multimodal_engine import multimodal_engine
from app.modules.weather.weather_schema import WeatherVerifyRequest, StandardResponse

router = APIRouter(prefix="/api/weather", tags=["Weather"])

@router.post(
    "/verify",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Verify Historical Weather & Anomaly"
)
def verify_weather(request: WeatherVerifyRequest):
    """
    Queries public meteorological records (ERA5/NOAA) for the farm's GPS coordinates and date.
    Calculates the continuous Weather Impact Score (0-100%) and determines the damage cause.
    """
    raw_weather = weather_provider.get_weather_data(
        latitude=request.latitude,
        longitude=request.longitude,
        incident_date=request.incidentDate
    )

    assessment = weather_engine.evaluate_weather(weather_data=raw_weather)
    fusion = multimodal_engine.fuse_assessments(
        visual_damage=request.visualDamage,
        weather_assessment=assessment
    )
    assessment["damageCause"] = fusion["damageCause"]

    return StandardResponse(
        success=True,
        message="Historical weather verified successfully.",
        data=assessment
    )

@router.get(
    "/benchmark",
    response_model=StandardResponse,
    summary="List Weather Dataset Samples"
)
def get_benchmarks(limit: int = 20):
    """
    Returns verified historical weather records from the local public dataset (ERA5/NOAA).
    """
    records = weather_provider._read_dataset_data(limit=limit)
    return StandardResponse(
        success=True,
        message=f"Retrieved {len(records)} sample weather records from dataset.",
        data=records
    )
