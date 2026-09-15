from typing import Dict, Any, List
from app.core.vision_engine import VisionEngine

class MLProvider:
    """
    ML Provider decouples business logic from TensorFlow and model execution.
    """
    @staticmethod
    def assess_crop_image(image_base64: str, claim_id: str) -> Dict[str, Any]:
        """
        Executes vision model inference on a single crop image.
        """
        return VisionEngine.assess_image(image_input=image_base64, claim_id=claim_id)

    @staticmethod
    def assess_crop_images(images: List[str], claim_id: str) -> Dict[str, Any]:
        """
        Executes vision model inference on multiple crop images.
        Returns aggregated damage severity, visual class, confidence, and per-image breakdown.
        """
        return VisionEngine.assess_multiple_images(image_inputs=images, claim_id=claim_id)

ml_provider = MLProvider()
