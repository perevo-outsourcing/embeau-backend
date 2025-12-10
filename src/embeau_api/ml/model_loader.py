"""ML Model loader for BiSeNet and DenseNet121 emotion model."""

import logging
import os
from typing import Any

import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import DenseNet121_Weights, densenet121

from embeau_api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Device configuration
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Global model instances
_FACE_SEGMENTER: Any = None
_EMOTION_MODEL: Any = None

# Emotion labels
EMOTION_LABELS = ["surprise", "fear", "disgust", "happy", "sad", "angry", "neutral"]

# Transforms
SEGMENTATION_TRANSFORM = transforms.Compose([
    transforms.Resize((512, 512)),
    transforms.ToTensor(),
    transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
])

EMOTION_TRANSFORM = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def get_face_segmenter() -> Any:
    """Load and cache BiSeNet face segmentation model."""
    global _FACE_SEGMENTER

    if _FACE_SEGMENTER is not None:
        return _FACE_SEGMENTER

    if not settings.use_local_models:
        logger.info("Local models disabled, skipping BiSeNet load")
        return None

    weights_path = settings.bisenet_weights
    if not os.path.exists(weights_path):
        logger.warning(f"BiSeNet weights not found at {weights_path}")
        return None

    try:
        from embeau_api.ml.face_parsing.model import BiSeNet

        logger.info("Loading BiSeNet face segmentation model...")
        model = BiSeNet(n_classes=19)
        model.to(DEVICE)
        model.load_state_dict(torch.load(weights_path, map_location=DEVICE))
        model.eval()
        _FACE_SEGMENTER = model
        logger.info(f"BiSeNet loaded successfully on {DEVICE}")
        return _FACE_SEGMENTER
    except Exception as e:
        logger.error(f"Failed to load BiSeNet: {e}")
        return None


def get_emotion_model() -> Any:
    """Load and cache DenseNet121 emotion recognition model."""
    global _EMOTION_MODEL

    if _EMOTION_MODEL is not None:
        return _EMOTION_MODEL

    if not settings.use_local_models:
        logger.info("Local models disabled, skipping emotion model load")
        return None

    weights_path = settings.emotion_model_weights
    if not os.path.exists(weights_path):
        logger.warning(f"Emotion model weights not found at {weights_path}")
        return None

    try:
        logger.info("Loading DenseNet121 emotion model...")
        model = densenet121(weights=DenseNet121_Weights.DEFAULT)
        model.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(model.classifier.in_features, 7),
        )
        model.load_state_dict(torch.load(weights_path, map_location=DEVICE))
        model.eval()
        model = model.to(DEVICE)
        _EMOTION_MODEL = model
        logger.info(f"Emotion model loaded successfully on {DEVICE}")
        return _EMOTION_MODEL
    except Exception as e:
        logger.error(f"Failed to load emotion model: {e}")
        return None


def segment_face(image_pil: Image.Image) -> tuple[Image.Image, np.ndarray]:
    """
    Segment face and extract skin region using BiSeNet.

    Returns:
        filled_pil: Image with non-skin areas filled with median skin color
        skin_mask: Binary mask of skin region
    """
    model = get_face_segmenter()

    if model is None:
        # Fallback: return original image with full mask
        logger.warning("BiSeNet not available, using fallback")
        return image_pil, np.ones((image_pil.height, image_pil.width), dtype=np.uint8) * 255

    original_size = image_pil.size  # (w, h)
    img_resized = image_pil.resize((512, 512), Image.BILINEAR)
    tensor = SEGMENTATION_TRANSFORM(img_resized).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        out = model(tensor)[0]
        parsing = out.squeeze(0).cpu().numpy().argmax(0)  # 512x512

    # Skin classes: skin(1) + neck(14)
    skin_512 = np.isin(parsing, [1, 14]).astype(np.uint8) * 255

    # Upsample to original size
    skin_mask = cv2.resize(skin_512, original_size, interpolation=cv2.INTER_NEAREST)

    # Morphological closing to fill holes
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
    skin_mask_3ch = cv2.merge([skin_mask] * 3)

    # Fill non-skin with median skin color
    img_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
    skin_pixels = img_cv[skin_mask > 0]

    if skin_pixels.size > 0:
        median_bgr = np.median(skin_pixels, axis=0).astype(np.uint8)
    else:
        median_bgr = np.array([128, 128, 128], dtype=np.uint8)

    bg = np.full_like(img_cv, median_bgr)
    filled = np.where(skin_mask_3ch > 0, img_cv, bg)
    filled_rgb = cv2.cvtColor(filled, cv2.COLOR_BGR2RGB)

    return Image.fromarray(filled_rgb), skin_mask


def detect_emotion(face_image: Image.Image) -> tuple[str, float]:
    """
    Detect facial emotion using DenseNet121.

    Returns:
        emotion: Predicted emotion label
        confidence: Prediction confidence
    """
    model = get_emotion_model()

    if model is None:
        # Fallback: return neutral with low confidence
        logger.warning("Emotion model not available, using fallback")
        return "neutral", 0.5

    input_tensor = EMOTION_TRANSFORM(face_image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        logits = model(input_tensor)
        probs = torch.nn.functional.softmax(logits, dim=1)[0].cpu().numpy()

    emotion_idx = int(np.argmax(probs))
    emotion = EMOTION_LABELS[emotion_idx]
    confidence = float(probs[emotion_idx])

    return emotion, confidence


def crop_face_for_emotion(image_pil: Image.Image) -> Image.Image:
    """Crop face region for emotion detection using DeepFace."""
    try:
        from deepface import DeepFace

        rgb = np.array(image_pil)
        faces = DeepFace.extract_faces(
            rgb,
            enforce_detection=False,
            detector_backend="retinaface"
        )

        if faces:
            facial_area = faces[0].get("facial_area", {})
            x, y, w, h = (
                facial_area.get("x", 0),
                facial_area.get("y", 0),
                facial_area.get("w", image_pil.width),
                facial_area.get("h", image_pil.height),
            )

            # Add padding
            padding = 0.1
            x = max(0, int(x - w * padding))
            y = max(0, int(y - h * padding))
            w = int(w * (1 + 2 * padding))
            h = int(h * (1 + 2 * padding))

            return image_pil.crop((x, y, x + w, y + h))
    except Exception as e:
        logger.warning(f"Face crop failed: {e}")

    # Fallback: return center crop
    w, h = image_pil.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    return image_pil.crop((left, top, left + min_dim, top + min_dim))


def initialize_models() -> dict[str, bool]:
    """Initialize all ML models and return status."""
    status = {
        "bisenet": False,
        "emotion_model": False,
        "device": str(DEVICE),
    }

    if get_face_segmenter() is not None:
        status["bisenet"] = True

    if get_emotion_model() is not None:
        status["emotion_model"] = True

    return status
