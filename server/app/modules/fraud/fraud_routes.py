from fastapi import APIRouter, status, UploadFile, File, Form, HTTPException
from typing import Optional
from app.core.fraud_engine import fraud_engine
from app.core.claim_decision_engine import claim_decision_engine
from app.core.xai_engine import xai_engine
from app.core.image_hash import image_hasher
from app.modules.fraud.fraud_schema import FraudEvaluateRequest, ExplainRequest, StandardResponse

router = APIRouter(prefix="/api/fraud", tags=["Fraud & Decision"])

@router.post(
    "/evaluate",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Evaluate Multimodal Fraud Risk & Claim Decision"
)
def evaluate_fraud(request: FraudEvaluateRequest):
    """
    Evaluates a claim using the multimodal AI fusion model (XGBoost).
    Combines claimed damage, visual evidence, meteorological scores,
    satellite acreage, and image hash signals to output a fraud risk score,
    an automated decision (APPROVED / MANUAL_REVIEW / REJECTED),
    and a fair recommended payout percentage.
    """
    result = fraud_engine.evaluate(
        claimed_damage=request.claimedDamage,
        visual_damage=request.visualDamage,
        weather_score=request.weatherScore,
        weather_hazard=request.weatherHazard,
        satellite_damaged_area=request.satelliteDamagedArea,
        ndvi_vegetation_drop=request.ndviVegetationDrop,
        is_duplicate_image=bool(request.isDuplicateImage),
        claims_frequency_12m=int(request.claimsFrequency12m or 1),
        allow_duplicate_images=bool(request.allowDuplicateImages)
    )

    return StandardResponse(
        success=True,
        message="Multimodal fraud evaluation completed successfully.",
        data=result
    )

@router.post(
    "/explain",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Generate Explainable AI (SHAP) Factor Breakdown"
)
def explain_claim(request: ExplainRequest):
    """
    Generates Tree SHAP explanations for any multimodal claim feature vector.
    Fulfills Mentor Requirements (Section 6: Explainable AI).
    Outputs exact mathematical Shapley values and plain-English factor explanations.
    """
    # If a full feature vector is provided directly
    if request.featureVector:
        features = request.featureVector
        claimed = features.get("claimed_damage", 50.0)
        vis = features.get("visual_damage_severity", 50.0)
        sat = features.get("satellite_damaged_area", 50.0)
        dup = bool(features.get("is_duplicate_image", 0))
    else:
        # Evaluate first to construct standardized feature vector
        eval_result = fraud_engine.evaluate(
            claimed_damage=request.claimedDamage or 50.0,
            visual_damage=request.visualDamage,
            weather_score=request.weatherScore,
            weather_hazard=request.weatherHazard,
            satellite_damaged_area=request.satelliteDamagedArea,
            ndvi_vegetation_drop=request.ndviVegetationDrop,
            is_duplicate_image=bool(request.isDuplicateImage),
            claims_frequency_12m=int(request.claimsFrequency12m or 1),
            allow_duplicate_images=bool(request.allowDuplicateImages)
        )
        features = eval_result["featureVector"]
        decision = eval_result["decision"]

    decision_info = claim_decision_engine.make_decision(
        fraud_risk_score=0.5,
        claimed_damage=features.get("claimed_damage", 50.0),
        visual_damage=features.get("visual_damage_severity", 50.0),
        satellite_damaged_area=features.get("satellite_damaged_area", 50.0),
        is_duplicate_image=bool(features.get("is_duplicate_image", 0))
    )
    decision = decision_info["decision"]

    xai_result = xai_engine.explain_claim(features, decision=decision)

    return StandardResponse(
        success=True,
        message="Explainable AI (SHAP) factor breakdown generated successfully.",
        data=xai_result
    )

@router.get(
    "/model-info",
    response_model=StandardResponse,
    summary="Get Fraud Model Architecture and Performance Metrics"
)
def get_model_info():
    """
    Returns information about the trained XGBoost multimodal fraud classifier,
    including features and benchmark validation metrics.
    """
    return StandardResponse(
        success=True,
        message="Fraud model details retrieved successfully.",
        data={
            "modelType": "XGBoost Classifier (150 trees, max_depth=5)",
            "benchmarkDataset": "5,000 calibrated multimodal research claims (Section 12 compliant)",
            "features": fraud_engine.feature_names,
            "metrics": fraud_engine.metrics,
            "thresholds": {
                "lowRisk": "score <= 0.35 -> APPROVED",
                "mediumRisk": "0.35 < score <= 0.70 -> MANUAL_REVIEW",
                "highRisk": "score > 0.70 -> REJECTED"
            },
            "explainableAi": "Tree SHAP (SHapley Additive exPlanations) compliant with Mentor Section 6"
        }
    )

@router.post(
    "/check-image-duplicate",
    response_model=StandardResponse,
    summary="Compute Perceptual Image Hash and Test Similarity"
)
async def check_image_duplicate(
    file1: UploadFile = File(..., description="First crop damage photograph"),
    file2: Optional[UploadFile] = File(None, description="Optional second photo to compare against")
):
    """
    Computes 64-bit difference hash (dHash) for an uploaded crop image.
    If a second image is provided, computes Hamming distance and similarity.
    """
    try:
        content1 = await file1.read()
        hash1 = image_hasher.compute_hash_from_bytes(content1)

        result = {
            "file1": file1.filename,
            "hash1": hash1
        }

        if file2 is not None:
            content2 = await file2.read()
            hash2 = image_hasher.compute_hash_from_bytes(content2)
            distance = image_hasher.hamming_distance(hash1, hash2)
            is_dup = image_hasher.is_duplicate(hash1, hash2)

            result.update({
                "file2": file2.filename,
                "hash2": hash2,
                "hammingDistance": distance,
                "isDuplicate": is_dup,
                "similarityPercentage": round((1.0 - (distance / 64.0)) * 100.0, 2)
            })

        return StandardResponse(
            success=True,
            message="Image hash analysis completed successfully.",
            data=result
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image hash evaluation failed: {str(e)}"
        )
