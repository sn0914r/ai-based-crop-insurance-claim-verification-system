import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class ClaimDecisionEngine:
    """
    Automated Claim Decision and Payout Estimation Engine.
    Corresponds directly to Mentor Requirements (Section 7).
    
    Translates multimodal fraud risk probability and physical damage observations
    into binding insurance claim decisions (APPROVED, MANUAL_REVIEW, REJECTED)
    and fair, evidence-based recommended payouts.
    """

    # Configurable insurance policy thresholds
    LOW_RISK_THRESHOLD = 0.35
    HIGH_RISK_THRESHOLD = 0.70

    @classmethod
    def classify_risk_tier(cls, fraud_risk_score: float) -> Tuple[str, str]:
        """
        Maps continuous fraud risk score to an automated decision and risk tier.
        
        Thresholds:
        - 0.00 to 0.35: LOW_RISK -> APPROVED
        - 0.36 to 0.70: MEDIUM_RISK -> MANUAL_REVIEW
        - 0.71 to 1.00: HIGH_RISK -> REJECTED
        """
        score = float(fraud_risk_score)
        if score <= cls.LOW_RISK_THRESHOLD:
            return "APPROVED", "LOW_RISK"
        elif score <= cls.HIGH_RISK_THRESHOLD:
            return "MANUAL_REVIEW", "MEDIUM_RISK"
        else:
            return "REJECTED", "HIGH_RISK"

    @classmethod
    def calculate_payout(
        cls,
        decision: str,
        claimed_damage: float,
        visual_damage: float,
        satellite_damaged_area: float
    ) -> Tuple[float, float]:
        """
        Calculates the fair recommended payout percentage based on verified ground-truth physical damage.
        
        Formula:
        Verified Physical Damage = 0.5 * Visual Damage + 0.5 * Satellite Damaged Area
        
        Rules:
        - If REJECTED: Payout = 0.0%
        - If APPROVED or MANUAL_REVIEW: Payout = min(Claimed Damage, Verified Physical Damage)
        """
        claimed_val = max(0.0, float(claimed_damage))
        vis_val = max(0.0, float(visual_damage))
        sat_val = max(0.0, float(satellite_damaged_area))

        verified_physical = round(0.5 * vis_val + 0.5 * sat_val, 2)

        if decision == "REJECTED":
            recommended_payout = 0.0
        else:
            recommended_payout = round(min(claimed_val, verified_physical), 2)

        return recommended_payout, verified_physical

    @classmethod
    def make_decision(
        cls,
        fraud_risk_score: float,
        claimed_damage: float,
        visual_damage: float,
        satellite_damaged_area: float,
        is_duplicate_image: bool = False
    ) -> Dict[str, Any]:
        """
        Complete decision execution combining risk evaluation and payout estimation.
        """
        decision, risk_level = cls.classify_risk_tier(fraud_risk_score)

        # Duplicate photos are automatically rejected
        if is_duplicate_image:
            decision = "REJECTED"
            risk_level = "HIGH_RISK"

        payout, verified_physical = cls.calculate_payout(
            decision=decision,
            claimed_damage=claimed_damage,
            visual_damage=visual_damage,
            satellite_damaged_area=satellite_damaged_area
        )

        if decision == "APPROVED":
            action_note = "Claim verified by multimodal evidence. Automated payout approved."
        elif decision == "MANUAL_REVIEW":
            action_note = "Minor discrepancy detected between claim and observations. Forwarded for human surveyor review."
        else:
            action_note = "Severe contradiction or fraudulent evidence detected. Claim denied."

        return {
            "decision": decision,
            "fraudRiskLevel": risk_level,
            "recommendedPayout": payout,
            "verifiedGroundTruthDamage": verified_physical,
            "actionNote": action_note
        }

claim_decision_engine = ClaimDecisionEngine()
