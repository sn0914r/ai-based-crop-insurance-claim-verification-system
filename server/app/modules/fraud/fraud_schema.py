from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class FraudEvaluateRequest(BaseModel):
    claimedDamage: float = Field(..., ge=0.0, le=100.0, description="Farmer claimed crop damage percentage (0-100%)", example=85.0)
    visualDamage: Optional[float] = Field(None, ge=0.0, le=100.0, description="AI leaf-level visual damage percentage (0-100%)", example=80.0)
    weatherScore: Optional[float] = Field(None, ge=0.0, le=100.0, description="Meteorological severity impact score (0-100%)", example=90.0)
    weatherHazard: Optional[str] = Field(None, description="Hazard type: FLOOD, DROUGHT, STORM_LODGING, or NORMAL", example="FLOOD")
    satelliteDamagedArea: Optional[float] = Field(None, ge=0.0, le=100.0, description="Sentinel-2 verified damaged field acreage (0-100%)", example=85.0)
    ndviVegetationDrop: Optional[float] = Field(None, ge=0.0, le=1.0, description="Pre- vs Post-disaster NDVI drop (0.0 to 1.0)", example=0.45)
    isDuplicateImage: Optional[bool] = Field(False, description="True if perceptual hash indicates image reuse", example=False)
    claimsFrequency12m: Optional[int] = Field(1, ge=1, description="Number of claims filed by farmer in last 12 months", example=1)

class FraudAssessmentData(BaseModel):
    fraudRiskScore: float = Field(..., description="Continuous fraud probability from XGBoost model (0.00 to 1.00)")
    fraudRiskLevel: str = Field(..., description="Risk tier: LOW_RISK, MEDIUM_RISK, or HIGH_RISK")
    decision: str = Field(..., description="Automated claim decision: APPROVED, MANUAL_REVIEW, or REJECTED")
    recommendedPayout: float = Field(..., description="Fair recommended payout percentage based on verified ground-truth")
    verifiedGroundTruthDamage: float = Field(..., description="Verified multimodal physical damage: 0.5 * Visual + 0.5 * Satellite")
    fraudFlags: List[str] = Field(default_factory=list, description="Specific discrepancy and anomaly flags detected")
    featureVector: Dict[str, Any] = Field(..., description="The 10 numerical features passed to the XGBoost classifier")

class FraudModelMetrics(BaseModel):
    accuracy: float
    rocAuc: float

class StandardResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None
