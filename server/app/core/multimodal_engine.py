from typing import Dict, Any, Optional

class MultimodalEngine:
    """
    Multimodal Decision Fusion Engine.
    Combines Visual AI (MobileNetV2) and Meteorological Evidence (ERA5/NOAA)
    to classify the ground-truth cause of crop damage.
    """

    @staticmethod
    def classify_damage_cause(
        visual_damage: Optional[float],
        weather_hazard: str
    ) -> str:
        """
        Applies the Multimodal Decision Matrix.
        Combines visual damage severity with verified meteorological hazard.
        """
        # When visual damage is not provided (weather-only check)
        if visual_damage is None:
            return weather_hazard

        # Normal condition: crop has negligible visual damage (<25%)
        if visual_damage < 25.0:
            return "NORMAL"

        # Crop is damaged: check if an acute meteorological hazard occurred
        if weather_hazard in ["FLOOD", "DROUGHT", "STORM_LODGING"]:
            return weather_hazard

        # Crop is damaged but weather was completely calm -> biological plant disease or pest
        return "PLANT_DISEASE"

    @classmethod
    def fuse_assessments(
        cls,
        visual_damage: Optional[float],
        weather_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fuses visual damage assessment with meteorological evaluation.
        """
        weather_hazard = weather_assessment.get("weatherHazard", "NORMAL")
        weather_score = float(weather_assessment.get("weatherScore", 0.0))
        damage_cause = cls.classify_damage_cause(visual_damage, weather_hazard)

        # Environmental consistency check
        if visual_damage is not None and visual_damage >= 50.0 and weather_score < 20.0:
            consistency_note = "Crop damage observed during calm weather; biological disease confirmed."
        elif visual_damage is not None and visual_damage >= 50.0 and weather_score >= 50.0:
            consistency_note = f"Crop damage verified by acute weather hazard ({weather_hazard})."
        else:
            consistency_note = "Evidence is consistent with environmental baseline."

        return {
            "damageCause": damage_cause,
            "weatherHazard": weather_hazard,
            "consistencyNote": consistency_note
        }

multimodal_engine = MultimodalEngine()
