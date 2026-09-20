from typing import Optional, Any, List, Dict
from pydantic import BaseModel, Field, model_validator

class SingleImageAssessment(BaseModel):
    imageIndex: int
    imagePath: str
    visualClass: str
    damageSeverity: float
    confidence: float
    rawProbability: Optional[float] = None

class SubmitClaimRequest(BaseModel):
    farmerId: str = Field(..., description="Unique ID of the farmer submitting the claim", example="FARMER_102")
    cropType: str = Field(..., description="Type of crop: rice, wheat, corn", example="rice")
    claimedDamage: float = Field(..., ge=0.0, le=100.0, description="Farmer self-reported damage percentage (0-100)", example=65.0)
    latitude: Optional[float] = Field(None, description="GPS latitude of the agricultural field", example=16.5)
    longitude: Optional[float] = Field(None, description="GPS longitude of the agricultural field", example=80.6)
    incidentDate: Optional[str] = Field(None, description="Disaster or claim date (YYYY-MM-DD)", example="2024-09-02")
    fieldBoundary: Optional[List[List[float]]] = Field(
        None,
        description="List of GPS coordinate pairs [[latitude, longitude], ...] defining the field boundary (at least 3 vertices required)",
        example=[[16.501, 80.601], [16.505, 80.601], [16.505, 80.607], [16.501, 80.607]]
    )
    image: Optional[str] = Field(None, description="Single base64-encoded crop photograph")
    images: Optional[List[str]] = Field(None, description="List of base64-encoded crop photographs from different angles or field spots")

    @model_validator(mode="after")
    def validate_request_inputs(self):
        has_single = bool(self.image and len(self.image.strip()) > 0)
        has_multiple = bool(self.images and len(self.images) > 0)
        if not has_single and not has_multiple:
            raise ValueError("At least one crop image must be provided using 'image' or 'images'.")

        if self.fieldBoundary is not None:
            if len(self.fieldBoundary) < 3:
                raise ValueError(
                    "fieldBoundary must contain at least 3 GPS coordinate vertices [[latitude, longitude], ...]."
                )
            for idx, pt in enumerate(self.fieldBoundary):
                if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                    raise ValueError(
                        f"Vertex at index {idx} in fieldBoundary is invalid. Each vertex must be a [latitude, longitude] pair."
                    )
                lat, lon = pt[0], pt[1]
                if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
                    raise ValueError(
                        f"Vertex at index {idx} has out-of-range coordinates ({lat}, {lon})."
                    )
        return self

    def get_image_list(self) -> List[str]:
        if self.images and len(self.images) > 0:
            return [img for img in self.images if img and len(img.strip()) > 0]
        if self.image and len(self.image.strip()) > 0:
            return [self.image]
        return []

class VisualAssessmentData(BaseModel):
    visualClass: str = Field(..., description="Overall field class: HEALTHY or DAMAGED")
    damageSeverity: float = Field(..., description="Mean continuous AI assessed damage percentage (0-100)")
    confidence: float = Field(..., description="Mean model confidence score")
    imageCount: int = Field(1, description="Number of crop images evaluated")
    imagePaths: List[str] = Field(default_factory=list, description="Saved paths of all uploaded photos")
    imageAssessments: Optional[List[SingleImageAssessment]] = Field(default=None, description="Individual assessment per photograph")
    rawProbability: Optional[float] = None
    imagePath: Optional[str] = None

class ClaimResponseData(BaseModel):
    claimId: str
    farmerId: str
    cropType: str
    claimedDamage: float
    imagePath: Optional[str] = None
    imageHash: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    incidentDate: Optional[str] = None
    fieldBoundary: Optional[List[List[float]]] = None
    status: str
    decision: Optional[str] = None
    damageCause: Optional[str] = None
    fraudRiskScore: Optional[float] = None
    fraudRiskLevel: Optional[str] = None
    recommendedPayout: Optional[float] = None
    fraudFlags: Optional[List[str]] = None
    visualAssessment: Optional[VisualAssessmentData] = None
    weatherAssessment: Optional[Dict[str, Any]] = None
    satelliteAssessment: Optional[Dict[str, Any]] = None
    fraudAssessment: Optional[Dict[str, Any]] = None
    createdAt: Optional[str] = None

class StandardResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None
