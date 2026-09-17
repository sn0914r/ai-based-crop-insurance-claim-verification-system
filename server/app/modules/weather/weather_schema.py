from typing import Optional, Any
from pydantic import BaseModel, Field

class WeatherVerifyRequest(BaseModel):
    latitude: float = Field(..., description="GPS latitude of the agricultural field", example=16.5)
    longitude: float = Field(..., description="GPS longitude of the agricultural field", example=80.6)
    incidentDate: str = Field(..., description="Disaster or claim date (YYYY-MM-DD)", example="2024-09-02")
    visualDamage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Optional AI visual damage score (0-100) to classify damage cause", example=85.0)

class WeatherMetrics(BaseModel):
    rainfallMm: float
    tempMaxC: float
    tempMinC: float
    windSpeedKmh: float
    consecutiveDryDays: int

class WeatherAssessmentData(BaseModel):
    weatherScore: float = Field(..., description="Continuous meteorological damage severity (0-100%)")
    weatherHazard: Optional[str] = Field(None, description="Meteorological hazard: FLOOD, DROUGHT, STORM_LODGING, or NORMAL")
    damageCause: str = Field(..., description="FLOOD, DROUGHT, STORM_LODGING, PLANT_DISEASE, or NORMAL")
    anomalyDetected: bool = Field(..., description="True if weather score >= 50%")
    metrics: WeatherMetrics
    region: Optional[str] = None
    dataSource: Optional[str] = None

class StandardResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None
