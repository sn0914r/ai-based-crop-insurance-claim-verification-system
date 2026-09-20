import base64
import io
import logging
from typing import Union
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

class ImageHashUtil:
    """
    Perceptual Image Hashing Utility for duplicate/recycled crop photo detection.
    Uses Difference Hash (dHash) to generate a 64-bit visual fingerprint.
    """

    @staticmethod
    def compute_dhash(image_input: Union[str, bytes, Path, Image.Image], hash_size: int = 8) -> str:
        """
        Computes 64-bit difference hash (dHash) from image input.
        Input can be a PIL Image, bytes, file path, or base64 data URI string.
        """
        try:
            if isinstance(image_input, Image.Image):
                img = image_input
            elif isinstance(image_input, (str, Path)) and str(image_input).startswith("data:image"):
                # Base64 data URI
                b64_data = str(image_input).split(",", 1)[1] if "," in str(image_input) else str(image_input)
                raw_bytes = base64.b64decode(b64_data)
                img = Image.open(io.BytesIO(raw_bytes))
            elif isinstance(image_input, (str, Path)) and Path(image_input).exists():
                img = Image.open(image_input)
            elif isinstance(image_input, str):
                # Raw base64 string
                raw_bytes = base64.b64decode(image_input)
                img = Image.open(io.BytesIO(raw_bytes))
            elif isinstance(image_input, bytes):
                img = Image.open(io.BytesIO(image_input))
            else:
                return "0" * 16

            # 1. Convert to grayscale and resize to (width=hash_size + 1, height=hash_size)
            img = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            pixels = list(img.getdata())

            # 2. Compare adjacent horizontal pixels
            difference = []
            for row in range(hash_size):
                row_start = row * (hash_size + 1)
                for col in range(hash_size):
                    pixel_left = pixels[row_start + col]
                    pixel_right = pixels[row_start + col + 1]
                    difference.append(pixel_left > pixel_right)

            # 3. Convert boolean array to hex string
            decimal_value = 0
            hex_string = []
            for index, value in enumerate(difference):
                if value:
                    decimal_value += 2 ** (index % 4)
                if (index % 4) == 3:
                    hex_string.append(hex(decimal_value)[2:])
                    decimal_value = 0

            return "".join(hex_string)

        except Exception as e:
            logger.warning(f"Failed to compute image hash: {str(e)}")
            return "0" * 16

    @staticmethod
    def hamming_distance(hash1: str, hash2: str) -> int:
        """
        Calculates Hamming bit distance between two hexadecimal hashes.
        Distance <= 5 indicates identical or near-duplicate recycled images.
        """
        if not hash1 or not hash2 or len(hash1) != len(hash2):
            return 64
        try:
            return bin(int(hash1, 16) ^ int(hash2, 16)).count("1")
        except ValueError:
            return 64

    @classmethod
    def is_duplicate(cls, new_hash: str, existing_hash: str, threshold: int = 5) -> bool:
        """
        Checks if two hashes represent identical or near-duplicate images.
        """
        if not new_hash or not existing_hash:
            return False
        dist = cls.hamming_distance(new_hash, existing_hash)
        return dist <= threshold

    compute_hash_from_bytes = compute_dhash

image_hash_util = ImageHashUtil()
image_hasher = image_hash_util
ImageHasher = ImageHashUtil
