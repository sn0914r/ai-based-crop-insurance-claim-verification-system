from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class SatelliteVerificationRequest(BaseModel):
    fieldBoundary: List[List[float]] = Field(
        ...,
        description="List of GPS coordinate pairs [[latitude, longitude], ...] defining the field boundary (at least 3 vertices required)",
        example=[[16.501, 80.601], [16.505, 80.601], [16.505, 80.607], [16.501, 80.607]]
    )
    incidentDate: str = Field(
        ...,
        description="Date of the weather event or disaster (YYYY-MM-DD)",
        example="2024-09-02"
    )
    cropType: Optional[str] = Field(
        default="crop",
        description="Crop type under cultivation (e.g. rice, wheat, corn)"
    )

    @field_validator("fieldBoundary")
    @classmethod
    def validate_boundary_vertices(cls, v: List[List[float]]) -> List[List[float]]:
        if not v or len(v) < 3:
            raise ValueError(
                "fieldBoundary must contain at least 3 GPS coordinate vertices [[latitude, longitude], ...]."
            )
        for idx, pt in enumerate(v):
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                raise ValueError(
                    f"Vertex at index {idx} is invalid. Each vertex must be a [latitude, longitude] pair."
                )
            lat, lon = pt[0], pt[1]
            if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
                raise ValueError(
                    f"Vertex at index {idx} has out-of-range coordinates ({lat}, {lon})."
                )
        return v

class SatelliteVerificationResponse(BaseModel):
    success: bool = True
    preDisasterNdvi: float
    postDisasterNdvi: float
    ndviDrop: float
    damagedAreaPercentage: float
    satelliteScore: float
    damageClassification: str
    fieldAreaHectares: float
    damagedAreaHectares: float
    cloudCoverPercentage: float
    preDate: Optional[str] = None
    postDate: Optional[str] = None
    spatialZoning: Optional[Dict[str, Any]] = None
    dataSource: str
    summary: str
