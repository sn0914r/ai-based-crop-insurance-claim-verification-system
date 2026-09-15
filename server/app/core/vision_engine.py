import base64
import io
import os
from pathlib import Path
from typing import Dict, Any, Tuple, List
from PIL import Image
import numpy as np

from app.configs.settings import settings, get_resolved_path, SERVER_DIR
from app.errors.app_error import AppError
import app.errors.error_codes as error_codes

class VisionEngine:
    """
    Core AI Vision Engine for MobileNetV2 damage assessment.
    Loads the trained .h5 model and evaluates crop images.
    """
    _model = None

    @classmethod
    def get_model_path(cls) -> Path:
        configured_path = get_resolved_path(settings.VISION_MODEL_PATH)
        if configured_path.exists():
            return configured_path
        
        # Fallbacks in models_saved
        fallbacks = [
            SERVER_DIR / "models_saved" / "vision_model.h5",
            SERVER_DIR / "models_saved" / "vision_model_initial.h5"
        ]
        for fallback in fallbacks:
            if fallback.exists():
                return fallback
        
        raise AppError(
            message=f"Vision model file not found at {configured_path}",
            status_code=500,
            error_code=error_codes.MODEL_NOT_FOUND
        )

    @classmethod
    def load_model(cls):
        if cls._model is None:
            model_path = cls.get_model_path()
            try:
                import os
                import keras
                # Disable verbose logging
                os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
                
                # Handle Keras 3 serialization variations (quantization_config keyword)
                class CompatibleDense(keras.layers.Dense):
                    def __init__(self, *args, **kwargs):
                        kwargs.pop("quantization_config", None)
                        super().__init__(*args, **kwargs)

                cls._model = keras.models.load_model(
                    str(model_path),
                    compile=False,
                    custom_objects={"Dense": CompatibleDense}
                )
            except ImportError:
                raise AppError(
                    message="Keras or TensorFlow is not installed in the current environment.",
                    status_code=500,
                    error_code=error_codes.MODEL_INFERENCE_FAILED
                )
            except Exception as e:
                raise AppError(
                    message=f"Failed to load vision model: {str(e)}",
                    status_code=500,
                    error_code=error_codes.MODEL_NOT_FOUND
                )
        return cls._model

    @staticmethod
    def decode_and_save_image(image_input: str, filename_prefix: str) -> Tuple[Image.Image, str]:
        """
        Decodes base64 string (with or without data URI prefix) and saves to uploads folder.
        """
        try:
            # Handle data URI prefix e.g. "data:image/jpeg;base64,"
            if "," in image_input:
                base64_data = image_input.split(",", 1)[1]
            else:
                base64_data = image_input

            image_bytes = base64.b64decode(base64_data)
            pil_image = Image.open(io.BytesIO(image_bytes))
            rgb_image = pil_image.convert("RGB")

            # Save image file to uploads directory
            uploads_dir = get_resolved_path(settings.UPLOADS_DIR)
            uploads_dir.mkdir(parents=True, exist_ok=True)
            
            clean_filename = f"{filename_prefix}.jpg"
            save_path = uploads_dir / clean_filename
            rgb_image.save(save_path, format="JPEG", quality=90)

            # Return relative path for database storage
            relative_path = f"data/uploads/{clean_filename}"
            return rgb_image, relative_path

        except Exception as e:
            raise AppError(
                message=f"Invalid image format or decoding error: {str(e)}",
                status_code=400,
                error_code=error_codes.IMAGE_INVALID
            )

    @classmethod
    def assess_image(cls, image_input: str, claim_id: str) -> Dict[str, Any]:
        """
        Processes image and runs MobileNetV2 inference.
        Returns visual class, continuous damage severity (0-100), and confidence.
        """
        # 1. Decode and persist image
        rgb_image, relative_path = cls.decode_and_save_image(image_input, claim_id)

        # 2. Preprocess image for MobileNetV2 (224 x 224 x 3)
        try:
            resized_image = rgb_image.resize((224, 224), Image.Resampling.BILINEAR)
            img_array = np.array(resized_image, dtype=np.float32)
            # Batch dimension: (1, 224, 224, 3)
            # Pixel values [0, 255] are rescaled internally by the model pipeline
            input_tensor = np.expand_dims(img_array, axis=0)
        except Exception as e:
            raise AppError(
                message=f"Failed to preprocess image: {str(e)}",
                status_code=400,
                error_code=error_codes.IMAGE_PROCESSING_FAILED
            )

        # 3. Load model and predict
        model = cls.load_model()
        try:
            prediction = model.predict(input_tensor, verbose=0)
            probability = float(prediction[0][0])
        except Exception as e:
            raise AppError(
                message=f"Vision model prediction failed: {str(e)}",
                status_code=500,
                error_code=error_codes.MODEL_INFERENCE_FAILED
            )

        # 4. Map probability to continuous damage severity and classification
        # Colab trained classes: 0 = healthy, 1 = damaged
        if probability >= 0.50:
            visual_class = "DAMAGED"
            # Continuous severity: 50% to 100%
            damage_severity = round(probability * 100.0, 1)
            confidence = round(probability, 4)
        else:
            visual_class = "HEALTHY"
            # Healthy crop continuous severity: 0% to 15%
            damage_severity = round(probability * 30.0, 1)
            confidence = round(1.0 - probability, 4)

        return {
            "visualClass": visual_class,
            "damageSeverity": damage_severity,
            "confidence": confidence,
            "rawProbability": round(probability, 4),
            "imagePath": relative_path
        }

    @classmethod
    def assess_multiple_images(cls, image_inputs: List[str], claim_id: str) -> Dict[str, Any]:
        """
        Processes multiple crop photographs for a claim.
        Computes both individual per-image assessments and aggregated field-level severity.
        """
        if not image_inputs:
            raise AppError(
                message="At least one crop image must be provided for visual assessment.",
                status_code=400,
                error_code=error_codes.IMAGE_INVALID
            )

        individual_assessments = []
        for idx, img_b64 in enumerate(image_inputs):
            img_prefix = f"{claim_id}_{idx + 1}" if len(image_inputs) > 1 else claim_id
            single_result = cls.assess_image(img_b64, img_prefix)
            single_result["imageIndex"] = idx + 1
            individual_assessments.append(single_result)

        # Compute field-level aggregated metrics
        severities = [item["damageSeverity"] for item in individual_assessments]
        confidences = [item["confidence"] for item in individual_assessments]
        raw_probs = [item["rawProbability"] for item in individual_assessments]
        image_paths = [item["imagePath"] for item in individual_assessments]

        mean_severity = round(sum(severities) / len(severities), 1)
        mean_confidence = round(sum(confidences) / len(confidences), 4)
        mean_prob = round(sum(raw_probs) / len(raw_probs), 4)

        # Field class: DAMAGED if mean severity >= 50%
        overall_class = "DAMAGED" if mean_severity >= 50.0 else "HEALTHY"

        return {
            "visualClass": overall_class,
            "damageSeverity": mean_severity,
            "confidence": mean_confidence,
            "rawProbability": mean_prob,
            "imageCount": len(individual_assessments),
            "imagePath": image_paths[0] if image_paths else None,
            "imagePaths": image_paths,
            "imageAssessments": individual_assessments
        }
