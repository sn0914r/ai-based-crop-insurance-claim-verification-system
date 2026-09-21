import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb

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

FEATURE_LABELS = {
    "claimed_damage": "Farmer Claimed Damage",
    "visual_damage_severity": "Leaf Photo AI Damage Severity",
    "weather_score": "ERA5 Historical Weather Severity",
    "weather_hazard_match": "Weather Hazard Consistency",
    "satellite_damaged_area": "Sentinel-2 Damaged Land Area",
    "ndvi_vegetation_drop": "NDVI Vegetation Drop",
    "visual_vs_claim_gap": "Leaf Photo Discrepancy Gap",
    "satellite_vs_claim_gap": "Satellite Land Discrepancy Gap",
    "is_duplicate_image": "Perceptual Duplicate Image Check",
    "claims_frequency_12m": "12-Month Past Claims History"
}

class ExplainableAIEngine:
    """
    Explainable AI (XAI) Engine using Tree SHAP (SHapley Additive exPlanations).
    Fulfills Mentor Requirements (Section 6 & Contribution 3).
    
    Translates mathematical Tree SHAP contributions from the trained XGBoost model
    into plain-English factor breakdowns and visual waterfall charts.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.booster = None
        self.feature_names = FEATURE_NAMES
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
                    else:
                        self.model = artifact

                    # Extract underlying XGBoost booster for C++ Tree SHAP
                    if hasattr(self.model, "get_booster"):
                        self.booster = self.model.get_booster()
                    elif isinstance(self.model, xgb.Booster):
                        self.booster = self.model
                    logger.info(f"Loaded XGBoost model for SHAP XAI from {p}")
                    return
                except Exception as e:
                    logger.error(f"Error loading model for SHAP from {p}: {e}")

        logger.warning("No pre-trained XGBoost model found for SHAP. Heuristic XAI will be used.")

    def explain_claim(self, feature_vector: Dict[str, Any], decision: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates exact Tree SHAP feature contributions and generates
        human-readable plain-English explanations.
        """
        # 1. Prepare features DataFrame
        row_dict = {}
        for f in self.feature_names:
            row_dict[f] = float(feature_vector.get(f, 0.0))

        df = pd.DataFrame([row_dict])[self.feature_names]

        # 2. Compute Tree SHAP contributions
        raw_shap_values: Dict[str, float] = {}
        base_value: float = 0.0

        if self.booster is not None:
            try:
                dmat = xgb.DMatrix(df)
                # Native C++ Tree SHAP calculation
                contribs = self.booster.predict(dmat, pred_contribs=True)[0]
                # First 10 values are feature Shapley values; the 11th value is the base/bias value
                for i, f in enumerate(self.feature_names):
                    raw_shap_values[f] = round(float(contribs[i]), 4)
                base_value = round(float(contribs[-1]), 4)
            except Exception as e:
                logger.error(f"Tree SHAP calculation failed: {e}. Using calibrated approximation.")
                raw_shap_values, base_value = self._fallback_shap(row_dict)
        else:
            raw_shap_values, base_value = self._fallback_shap(row_dict)

        # 3. Calculate percentage contributions
        total_abs_shap = sum(abs(v) for v in raw_shap_values.values())
        if total_abs_shap == 0:
            total_abs_shap = 1.0

        factors: List[Dict[str, Any]] = []
        for f in self.feature_names:
            shap_val = raw_shap_values[f]
            observed_val = row_dict[f]
            label = FEATURE_LABELS.get(f, f)
            impact_pct = round((abs(shap_val) / total_abs_shap) * 100.0, 1)

            direction = "INCREASES_RISK" if shap_val > 0.0 else ("LOWERS_RISK" if shap_val < 0.0 else "NEUTRAL")
            explanation_sentence = self._generate_sentence(f, observed_val, shap_val, direction)

            factors.append({
                "feature": f,
                "label": label,
                "observedValue": observed_val,
                "shapValue": shap_val,
                "relativeImportancePct": impact_pct,
                "direction": direction,
                "explanation": explanation_sentence
            })

        # 4. Partition factors into risk-increasing and risk-mitigating
        risk_increasing = [f for f in factors if f["shapValue"] > 0.0]
        risk_increasing.sort(key=lambda x: x["shapValue"], reverse=True)

        risk_mitigating = [f for f in factors if f["shapValue"] < 0.0]
        risk_mitigating.sort(key=lambda x: x["shapValue"])  # Most negative first

        # Top 3 drivers overall
        factors_by_magnitude = sorted(factors, key=lambda x: abs(x["shapValue"]), reverse=True)
        top_drivers = factors_by_magnitude[:4]

        # 5. Executive Plain-English Summary
        summary = self._generate_executive_summary(
            decision=decision,
            risk_increasing=risk_increasing,
            risk_mitigating=risk_mitigating,
            row=row_dict
        )

        return {
            "baseValue": base_value,
            "shapValues": raw_shap_values,
            "factors": factors,
            "topDrivers": top_drivers,
            "riskIncreasingFactors": risk_increasing,
            "riskMitigatingFactors": risk_mitigating,
            "executiveSummary": summary
        }

    def _generate_sentence(self, feature: str, value: float, shap_val: float, direction: str) -> str:
        """
        Creates intuitive, plain-English explanation sentences for each feature.
        """
        if feature == "satellite_vs_claim_gap":
            if value > 25.0:
                return f"Farmer claimed {value:.1f}% higher damage than verified by Sentinel-2 satellite field observations."
            elif value < -15.0:
                return "Satellite observations show damage across the field consistent with or exceeding the claim."
            return "Satellite-observed damaged acreage closely aligns with the claimed loss percentage."

        elif feature == "visual_vs_claim_gap":
            if value > 25.0:
                return f"Crop leaf photographs show {value:.1f}% less physical damage than claimed by the farmer."
            elif value < -15.0:
                return "Photographed leaf damage is severe and substantiates the damage claim."
            return "Photographed leaf damage severity aligns reasonably with the claimed damage."

        elif feature == "weather_score":
            if value < 20.0 and direction == "INCREASES_RISK":
                return f"Weather records indicate calm baseline conditions (severity score {value:.1f}%), contradicting an acute disaster."
            elif value >= 60.0:
                return f"Historical weather data confirms severe weather conditions occurred (severity score {value:.1f}%)."
            return f"Weather impact was moderate (score: {value:.1f}%)."

        elif feature == "weather_hazard_match":
            if int(value) == 1:
                return "Meteorological hazard type (Flood, Drought, or Storm) directly verified by public climate records."
            return "No official meteorological disaster was registered in climate records for this date and location."

        elif feature == "is_duplicate_image":
            if int(value) == 1:
                return "Perceptual image hashing detected that this photograph was recycled from a previously filed claim."
            return "Photograph is unique and has not been recycled from previous claims."

        elif feature == "claims_frequency_12m":
            if value >= 4:
                return f"High submission frequency: Farmer has submitted {int(value)} claims within the past 12 months."
            return f"Normal submission frequency ({int(value)} claims in the past year)."

        elif feature == "satellite_damaged_area":
            return f"Sentinel-2 multispectral remote sensing measured {value:.1f}% damaged field acreage."

        elif feature == "ndvi_vegetation_drop":
            if value >= 0.35:
                return f"Vegetation greenness dropped significantly (Delta NDVI: {value:.3f}), indicating substantial crop loss."
            return f"Vegetation greenness drop was minor (Delta NDVI: {value:.3f})."

        elif feature == "visual_damage_severity":
            return f"MobileNetV2 leaf-level visual inspection measured {value:.1f}% physical crop damage."

        elif feature == "claimed_damage":
            return f"Farmer self-reported {value:.1f}% total crop loss across the field."

        return f"{FEATURE_LABELS.get(feature, feature)} value was {value}."

    def _generate_executive_summary(
        self,
        decision: Optional[str],
        risk_increasing: List[Dict[str, Any]],
        risk_mitigating: List[Dict[str, Any]],
        row: Dict[str, float]
    ) -> str:
        """
        Creates an executive paragraph suitable for an insurance claim letter.
        """
        if decision == "APPROVED":
            if risk_mitigating:
                top_support = risk_mitigating[0]["label"].lower()
                return (
                    f"The claim was approved because independent physical evidence aligns with the reported loss. "
                    f"Verification was primarily substantiated by {top_support}."
                )
            return "The claim was approved because all independent evidence sources confirm legitimate crop loss."

        elif decision == "REJECTED":
            reasons = []
            if row.get("is_duplicate_image", 0) == 1:
                reasons.append("duplicate photograph reuse was detected")
            if row.get("satellite_vs_claim_gap", 0) > 30.0:
                reasons.append("satellite imagery showed healthy field acreage contradicting the reported damage")
            if row.get("claimed_damage", 0) >= 50.0 and row.get("weather_score", 0) < 25.0:
                reasons.append("meteorological climate records showed normal weather conditions without a disaster")
            if row.get("visual_vs_claim_gap", 0) > 30.0:
                reasons.append("photographs of crop leaves showed healthy plants")

            if reasons:
                reasons_str = "; ".join(reasons)
                return f"The claim was rejected because {reasons_str}."
            return "The claim was rejected due to significant contradictions across independent evidence sources."

        else:  # MANUAL_REVIEW
            drivers = [f["label"] for f in risk_increasing[:2]]
            drivers_str = " and ".join(drivers) if drivers else "minor discrepancies"
            return (
                f"The claim was routed for human surveyor review due to borderline consistency metrics, "
                f"principally involving {drivers_str}."
            )

    def _fallback_shap(self, row: Dict[str, float]) -> tuple:
        """
        Calibrated fallback heuristic contributions if XGBoost booster is unavailable.
        """
        shaps = {}
        shaps["is_duplicate_image"] = 2.5 if row.get("is_duplicate_image", 0) == 1 else -0.1
        shaps["satellite_vs_claim_gap"] = round((row.get("satellite_vs_claim_gap", 0) - 10.0) * 0.05, 4)
        shaps["visual_vs_claim_gap"] = round((row.get("visual_vs_claim_gap", 0) - 10.0) * 0.04, 4)
        shaps["weather_score"] = -0.5 if row.get("weather_score", 0) >= 50 else 0.4
        shaps["claims_frequency_12m"] = 0.5 if row.get("claims_frequency_12m", 1) >= 4 else -0.1
        for f in self.feature_names:
            if f not in shaps:
                shaps[f] = 0.0
        return shaps, 0.0

xai_engine = ExplainableAIEngine()
