import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import joblib

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "claimed_damage",
    "visual_damage_severity",
    "weather_score",
    "weather_hazard_match",
    "satellite_damaged_area",
    "ndvi_vegetation_drop",
    "visual_vs_claim_gap",
    "satellite_vs_claim_gap",
    "is_duplicate_image",
    "claims_frequency_12m"
]

class FraudEngine:
    """
    Multimodal AI Fusion and Fraud Detection Engine.
    Fuses visual evidence, weather analytics, satellite remote sensing,
    and historical claim frequency to predict fraud risk score,
    automated decision, and fair recommended payout.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.feature_names = FEATURE_NAMES
        self.metrics = {}
        self._load_model(model_path)

    def _load_model(self, model_path: Optional[str] = None):
        if model_path:
            candidates = [Path(model_path)]
        else:
            candidates = [
                Path("/app/models_saved/xgboost_fraud.pkl"),
                Path(__file__).resolve().parent.parent.parent / "models_saved" / "xgboost_fraud.pkl",
                Path("models_saved/xgboost_fraud.pkl"),
                Path("server/models_saved/xgboost_fraud.pkl")
            ]

        for p in candidates:
            if p.exists():
                try:
                    artifact = joblib.load(p)
                    if isinstance(artifact, dict) and "model" in artifact:
                        self.model = artifact["model"]
                        self.feature_names = artifact.get("feature_names", FEATURE_NAMES)
                        self.metrics = artifact.get("metrics", {})
                    else:
                        self.model = artifact
                    logger.info(f"Loaded XGBoost fraud model successfully from {p}")
                    return
                except Exception as e:
                    logger.error(f"Error loading model from {p}: {e}")

        logger.warning("No pre-trained XGBoost fraud model found. Fallback heuristic evaluation will be used.")

    def evaluate(
        self,
        claimed_damage: float,
        visual_damage: Optional[float] = None,
        weather_score: Optional[float] = None,
        weather_hazard: Optional[str] = None,
        satellite_damaged_area: Optional[float] = None,
        ndvi_vegetation_drop: Optional[float] = None,
        is_duplicate_image: bool = False,
        claims_frequency_12m: int = 1
    ) -> Dict[str, Any]:
        """
        Evaluates a claim using multimodal AI fusion.
        Returns fraud risk score, risk level, decision, recommended payout, and flags.
        """
        # 1. Impute and standardize inputs
        claimed_val = float(claimed_damage)
        
        # If visual damage wasn't provided, use claimed_damage as default
        visual_val = float(visual_damage) if visual_damage is not None else claimed_val
        
        # If weather score wasn't provided, default to moderate 50.0
        weather_val = float(weather_score) if weather_score is not None else 50.0
        
        # Weather hazard match: 1 if verified meteorological hazard occurred
        hazard_match = 1 if (weather_hazard and weather_hazard.upper() not in ["NORMAL", "NONE"] and weather_val >= 35.0) else 0
        
        # Satellite damaged area: default to claimed_damage if not available
        sat_area_val = float(satellite_damaged_area) if satellite_damaged_area is not None else claimed_val
        
        # NDVI drop: default to standard proportional drop if not available
        if ndvi_vegetation_drop is not None:
            ndvi_drop_val = float(ndvi_vegetation_drop)
        else:
            ndvi_drop_val = float(np.clip(0.15 + (sat_area_val / 100.0) * 0.45, 0.0, 1.0))
            
        duplicate_flag = 1 if is_duplicate_image else 0
        freq_val = max(1, int(claims_frequency_12m))

        # Discrepancy gaps
        visual_gap = round(claimed_val - visual_val, 2)
        sat_gap = round(claimed_val - sat_area_val, 2)

        # 2. Rule-based discrepancy flag detection
        flags: List[str] = []
        if visual_gap > 30.0 or sat_gap > 35.0:
            flags.append("DAMAGE_EXAGGERATION_SUSPECTED")
        if claimed_val >= 50.0 and weather_val < 25.0:
            flags.append("WEATHER_CONTRADICTION")
        if claimed_val >= 50.0 and sat_area_val < 25.0:
            flags.append("SATELLITE_VEGETATION_CONTRADICTION")
        if is_duplicate_image:
            flags.append("DUPLICATE_IMAGE_DETECTED")
        if freq_val >= 4:
            flags.append("HIGH_CLAIM_FREQUENCY")

        # 3. Model inference
        features_dict = {
            "claimed_damage": claimed_val,
            "visual_damage_severity": visual_val,
            "weather_score": weather_val,
            "weather_hazard_match": hazard_match,
            "satellite_damaged_area": sat_area_val,
            "ndvi_vegetation_drop": ndvi_drop_val,
            "visual_vs_claim_gap": visual_gap,
            "satellite_vs_claim_gap": sat_gap,
            "is_duplicate_image": duplicate_flag,
            "claims_frequency_12m": freq_val
        }

        features_df = pd.DataFrame([features_dict])[self.feature_names]

        if self.model is not None:
            try:
                probabilities = self.model.predict_proba(features_df)[0]
                # Index 1 corresponds to Fraud probability
                fraud_risk_score = round(float(probabilities[1]), 4)
            except Exception as e:
                logger.error(f"XGBoost inference failed: {e}. Using calibrated heuristic.")
                fraud_risk_score = self._heuristic_risk_score(features_dict)
        else:
            fraud_risk_score = self._heuristic_risk_score(features_dict)

        # Perceptual hash duplicate override: recycled photos always result in high risk
        if is_duplicate_image:
            fraud_risk_score = max(fraud_risk_score, 0.95)

        # 4. Delegate to Claim Decision Engine for automated policy decision & payout estimation
        from app.core.claim_decision_engine import claim_decision_engine
        decision_info = claim_decision_engine.make_decision(
            fraud_risk_score=fraud_risk_score,
            claimed_damage=claimed_val,
            visual_damage=visual_val,
            satellite_damaged_area=sat_area_val,
            is_duplicate_image=is_duplicate_image
        )

        return {
            "fraudRiskScore": fraud_risk_score,
            "fraudRiskLevel": decision_info["fraudRiskLevel"],
            "decision": decision_info["decision"],
            "recommendedPayout": decision_info["recommendedPayout"],
            "verifiedGroundTruthDamage": decision_info["verifiedGroundTruthDamage"],
            "actionNote": decision_info["actionNote"],
            "fraudFlags": flags,
            "featureVector": features_dict
        }

    def _heuristic_risk_score(self, f: Dict[str, Any]) -> float:
        """
        Calibrated fallback heuristic scoring if XGBoost model is unavailable.
        """
        score = 0.05
        if f["is_duplicate_image"]:
            score += 0.85
        if f["visual_vs_claim_gap"] > 30.0:
            score += 0.35
        if f["satellite_vs_claim_gap"] > 35.0:
            score += 0.35
        if f["claimed_damage"] >= 50.0 and f["weather_score"] < 25.0:
            score += 0.30
        if f["claims_frequency_12m"] >= 4:
            score += 0.15
        return round(float(np.clip(score, 0.0, 1.0)), 4)

fraud_engine = FraudEngine()
