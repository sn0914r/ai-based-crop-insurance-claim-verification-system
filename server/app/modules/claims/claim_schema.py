from typing import Optional, Any, List
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
    image: Optional[str] = Field(None, description="Single base64-encoded crop photograph")
    images: Optional[List[str]] = Field(None, description="List of base64-encoded crop photographs from different angles or field spots")

    @model_validator(mode="after")
    def validate_images(self):
        has_single = bool(self.image and len(self.image.strip()) > 0)
        has_multiple = bool(self.images and len(self.images) > 0)
        if not has_single and not has_multiple:
            raise ValueError("At least one crop image must be provided using 'image' or 'images'.")
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
    imagePath: Optional[str]
    status: str
    visualAssessment: Optional[VisualAssessmentData] = None
    createdAt: Optional[str] = None

class StandardResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None
