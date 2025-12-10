"""Color analysis service - integrates local PyTorch models and external APIs."""

import base64
import io
import json
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from embeau_api.config import get_settings
from embeau_api.core.exceptions import ColorAnalysisError, NotFoundError
from embeau_api.core.logging import ActionType, research_logger
from embeau_api.models import ColorResult, DailyHealingColor
from embeau_api.schemas.color import (
    ColorItem,
    DailyHealingColorResponse,
    PersonalColorResult,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Color palette data from reference API
COLOR_PALETTES = {
    "spring_warm": [
        {"name": "코랄", "hex": "#FF7F50", "description": "따뜻하고 생기 있는 코랄"},
        {"name": "피치", "hex": "#FFDAB9", "description": "부드러운 복숭아빛"},
        {"name": "골든 옐로우", "hex": "#FFD700", "description": "밝고 화사한 금색"},
        {"name": "라이트 그린", "hex": "#90EE90", "description": "싱그러운 연두색"},
        {"name": "아이보리", "hex": "#FFFFF0", "description": "따뜻한 아이보리"},
    ],
    "spring_clear": [
        {"name": "브라이트 코랄", "hex": "#FF6B6B", "description": "선명한 코랄"},
        {"name": "터콰이즈", "hex": "#40E0D0", "description": "맑은 청록색"},
        {"name": "선 옐로우", "hex": "#FFEF00", "description": "맑고 밝은 노랑"},
        {"name": "페퍼민트", "hex": "#98FF98", "description": "상쾌한 민트색"},
        {"name": "퓨어 화이트", "hex": "#FFFFFF", "description": "깨끗한 순백색"},
    ],
    "summer_cool": [
        {"name": "라벤더", "hex": "#E6E6FA", "description": "차분한 라벤더"},
        {"name": "스카이 블루", "hex": "#87CEEB", "description": "시원한 하늘색"},
        {"name": "소프트 핑크", "hex": "#FFB6C1", "description": "부드러운 분홍"},
        {"name": "민트 그린", "hex": "#98FB98", "description": "청량한 민트"},
        {"name": "페일 그레이", "hex": "#D3D3D3", "description": "세련된 회색"},
    ],
    "summer_soft": [
        {"name": "더스티 핑크", "hex": "#D8A9A9", "description": "차분한 더스티 핑크"},
        {"name": "세이지 그린", "hex": "#9DC183", "description": "부드러운 세이지"},
        {"name": "모브", "hex": "#E0B0FF", "description": "우아한 모브"},
        {"name": "블루 그레이", "hex": "#6699CC", "description": "세련된 블루 그레이"},
        {"name": "로즈 베이지", "hex": "#C4A484", "description": "따뜻한 로즈 베이지"},
    ],
    "autumn_warm": [
        {"name": "테라코타", "hex": "#E2725B", "description": "따뜻한 테라코타"},
        {"name": "머스타드", "hex": "#FFDB58", "description": "깊은 머스타드"},
        {"name": "올리브 그린", "hex": "#808000", "description": "자연스러운 올리브"},
        {"name": "버건디", "hex": "#800020", "description": "깊은 버건디"},
        {"name": "카멜", "hex": "#C19A6B", "description": "클래식한 카멜"},
    ],
    "autumn_deep": [
        {"name": "초콜릿", "hex": "#7B3F00", "description": "깊은 초콜릿 브라운"},
        {"name": "포레스트 그린", "hex": "#228B22", "description": "깊은 숲색"},
        {"name": "퍼플 와인", "hex": "#722F37", "description": "고급스러운 와인색"},
        {"name": "브릭 레드", "hex": "#CB4154", "description": "따뜻한 벽돌색"},
        {"name": "골드", "hex": "#D4AF37", "description": "우아한 골드"},
    ],
    "winter_cool": [
        {"name": "로얄 블루", "hex": "#4169E1", "description": "선명한 로얄 블루"},
        {"name": "퓨시아", "hex": "#FF00FF", "description": "강렬한 퓨시아"},
        {"name": "에메랄드", "hex": "#50C878", "description": "선명한 에메랄드"},
        {"name": "퓨어 화이트", "hex": "#FFFFFF", "description": "순수한 화이트"},
        {"name": "실버", "hex": "#C0C0C0", "description": "차가운 실버"},
    ],
    "winter_clear": [
        {"name": "트루 레드", "hex": "#FF0000", "description": "선명한 빨강"},
        {"name": "일렉트릭 블루", "hex": "#7DF9FF", "description": "강렬한 일렉트릭 블루"},
        {"name": "핫 핑크", "hex": "#FF69B4", "description": "화려한 핫 핑크"},
        {"name": "블랙", "hex": "#000000", "description": "깊은 블랙"},
        {"name": "아이시 블루", "hex": "#A5F2F3", "description": "차가운 아이시 블루"},
    ],
}

# Season descriptions
SEASON_DESCRIPTIONS = {
    "spring": "봄 타입은 밝고 따뜻한 색조가 잘 어울립니다. 피부에 황색 베이스가 있으며, 생기 있고 화사한 컬러가 얼굴을 환하게 밝혀줍니다.",
    "summer": "여름 타입은 부드럽고 시원한 색조가 잘 어울립니다. 피부에 핑크빛 베이스가 있으며, 파스텔 톤과 그레이시한 컬러가 우아함을 더해줍니다.",
    "autumn": "가을 타입은 따뜻하고 깊은 색조가 잘 어울립니다. 피부에 황금빛 베이스가 있으며, 어스 톤과 깊이 있는 컬러가 고급스러움을 연출합니다.",
    "winter": "겨울 타입은 선명하고 차가운 색조가 잘 어울립니다. 피부에 푸른 베이스가 있으며, 대비가 강한 컬러가 세련된 인상을 줍니다.",
}

# Healing colors based on emotions
HEALING_COLORS = {
    "anxiety": [
        {"name": "라벤더", "hex": "#E6E6FA", "effect": "마음을 진정시키고 불안을 완화합니다"},
        {"name": "스카이 블루", "hex": "#87CEEB", "effect": "평온함과 안정감을 선사합니다"},
    ],
    "stress": [
        {"name": "민트 그린", "hex": "#98FB98", "effect": "긴장을 풀어주고 스트레스를 해소합니다"},
        {"name": "페일 블루", "hex": "#AFEEEE", "effect": "마음의 휴식을 가져다줍니다"},
    ],
    "depression": [
        {"name": "소프트 옐로우", "hex": "#FFFACD", "effect": "밝은 에너지로 기분을 북돋웁니다"},
        {"name": "피치", "hex": "#FFDAB9", "effect": "따뜻함으로 마음을 감싸줍니다"},
    ],
    "happiness": [
        {"name": "코랄", "hex": "#FF7F50", "effect": "행복한 에너지를 더욱 증폭시킵니다"},
        {"name": "골드", "hex": "#FFD700", "effect": "긍정적인 기운을 더해줍니다"},
    ],
    "satisfaction": [
        {"name": "세이지 그린", "hex": "#9DC183", "effect": "만족감을 지속시키고 균형을 유지합니다"},
        {"name": "소프트 베이지", "hex": "#F5F5DC", "effect": "안정감과 편안함을 선사합니다"},
    ],
}


class ColorAnalyzerService:
    """Service for color analysis operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def analyze_image(self, user_id: str, image_data: str) -> PersonalColorResult:
        """Analyze an image to determine personal color using local models."""
        start_time = time.time()

        research_logger.log(
            action_type=ActionType.COLOR_ANALYZE_START,
            user_id=user_id,
            action_data={"image_size": len(image_data)},
        )

        try:
            # Decode base64 image
            if "," in image_data:
                image_data = image_data.split(",")[1]
            image_bytes = base64.b64decode(image_data)
            image_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # Use local models if available
            if settings.use_local_models:
                analysis_data = await self._analyze_with_local_models(image_pil)
            else:
                # Fallback to external API
                analysis_data = await self._analyze_with_external_api(image_bytes)

            # Parse response
            tone_data = analysis_data.get("tone", {})
            emotion_data = analysis_data.get("emotion", {})

            season = tone_data.get("season", "summer").lower()
            subtype = tone_data.get("subtype", "cool").lower()
            confidence = tone_data.get("confidence", 0.8)

            # Determine tone from subtype
            tone = "cool" if "cool" in subtype else "warm"

            # Get recommended colors
            palette_key = f"{season}_{subtype}"
            if palette_key not in COLOR_PALETTES:
                palette_key = f"{season}_{tone}"
            colors = COLOR_PALETTES.get(palette_key, COLOR_PALETTES["summer_cool"])

            # Create or update color result
            result = await self.db.execute(
                select(ColorResult).where(ColorResult.user_id == user_id)
            )
            color_result = result.scalar_one_or_none()

            recommended_colors_json = json.dumps(colors, ensure_ascii=False)

            if color_result:
                color_result.season = season
                color_result.tone = tone
                color_result.subtype = f"{season}_{subtype}".title()
                color_result.confidence = confidence
                color_result.description = SEASON_DESCRIPTIONS.get(season, "")
                color_result.recommended_colors = recommended_colors_json
                color_result.facial_expression = emotion_data.get("facial_expression")
                color_result.facial_expression_confidence = emotion_data.get(
                    "facial_expression_confidence"
                )
                color_result.raw_analysis_data = json.dumps(analysis_data, ensure_ascii=False)
                color_result.analyzed_at = datetime.now(timezone.utc)
            else:
                color_result = ColorResult(
                    user_id=user_id,
                    season=season,
                    tone=tone,
                    subtype=f"{season}_{subtype}".title(),
                    confidence=confidence,
                    description=SEASON_DESCRIPTIONS.get(season, ""),
                    recommended_colors=recommended_colors_json,
                    facial_expression=emotion_data.get("facial_expression"),
                    facial_expression_confidence=emotion_data.get("facial_expression_confidence"),
                    raw_analysis_data=json.dumps(analysis_data, ensure_ascii=False),
                )
                self.db.add(color_result)

            await self.db.flush()

            duration_ms = int((time.time() - start_time) * 1000)
            research_logger.log_color_analysis(
                user_id=user_id,
                result={
                    "season": season,
                    "tone": tone,
                    "confidence": confidence,
                },
                duration_ms=duration_ms,
            )

            return PersonalColorResult(
                season=season,  # type: ignore
                tone=tone,  # type: ignore
                description=SEASON_DESCRIPTIONS.get(season, ""),
                recommended_colors=[ColorItem(**c) for c in colors],
                analyzed_at=color_result.analyzed_at,
                confidence=confidence,
                subtype=f"{season}_{subtype}".title(),
                facial_expression=emotion_data.get("facial_expression"),
            )

        except Exception as e:
            logger.exception("Color analysis failed")
            raise ColorAnalysisError(f"Failed to analyze image: {str(e)}")

    async def _analyze_with_local_models(self, image_pil: Image.Image) -> dict:
        """Analyze image using local PyTorch models (BiSeNet + DenseNet121)."""
        from embeau_api.ml import crop_face_for_emotion, detect_emotion, segment_face

        # 1. Face segmentation and skin extraction
        filled_pil, skin_mask = segment_face(image_pil)

        # 2. Analyze skin tone from segmented image
        season, subtype, confidence = self._analyze_skin_tone(filled_pil, skin_mask)

        # 3. Emotion detection
        face_crop = crop_face_for_emotion(image_pil)
        emotion, emotion_confidence = detect_emotion(face_crop)

        return {
            "tone": {
                "season": season,
                "subtype": subtype,
                "confidence": confidence,
            },
            "emotion": {
                "facial_expression": emotion,
                "facial_expression_confidence": emotion_confidence,
            },
            "source": "local_models",
        }

    def _analyze_skin_tone(
        self, filled_pil: Image.Image, skin_mask: np.ndarray
    ) -> tuple[str, str, float]:
        """Analyze skin tone from segmented face image."""
        import cv2

        # Convert to numpy and extract skin pixels
        img_rgb = np.array(filled_pil)
        skin_pixels = img_rgb[skin_mask > 0]

        if skin_pixels.size == 0:
            return "summer", "cool", 0.5

        # Calculate average skin color in Lab color space
        img_lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
        skin_lab = img_lab[skin_mask > 0]

        avg_l = np.mean(skin_lab[:, 0])  # Lightness
        avg_a = np.mean(skin_lab[:, 1])  # Green-Red
        avg_b = np.mean(skin_lab[:, 2])  # Blue-Yellow

        # Determine warm/cool based on a* and b* values
        # Higher b* = warmer (yellow undertone)
        # Lower b* = cooler (blue undertone)
        is_warm = avg_b > 135  # b* > 135 indicates warm undertone

        # Determine season based on lightness and undertone
        if avg_l > 170:  # Light skin
            if is_warm:
                season, subtype = "spring", "light"
            else:
                season, subtype = "summer", "light"
        elif avg_l > 130:  # Medium skin
            if is_warm:
                season, subtype = "autumn", "warm"
            else:
                season, subtype = "summer", "cool"
        else:  # Dark skin
            if is_warm:
                season, subtype = "autumn", "deep"
            else:
                season, subtype = "winter", "deep"

        # Confidence based on how clearly the undertone is determined
        undertone_strength = abs(avg_b - 135) / 30  # How far from neutral
        confidence = min(0.95, 0.6 + undertone_strength * 0.3)

        return season, subtype, confidence

    async def _analyze_with_external_api(self, image_bytes: bytes) -> dict:
        """Fallback to external Color Tone API."""
        try:
            response = await self.http_client.post(
                f"{settings.color_tone_api_url}/analyze",
                files={"file": ("image.jpg", image_bytes, "image/jpeg")},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.warning(f"External API failed: {e}, using mock")
            return self._mock_analysis()

    def _mock_analysis(self) -> dict:
        """Generate mock analysis data when external API is unavailable."""
        import random

        seasons = ["spring", "summer", "autumn", "winter"]
        subtypes = ["warm", "cool", "clear", "soft", "deep"]
        emotions = ["happy", "neutral", "calm", "surprised"]

        return {
            "tone": {
                "season": random.choice(seasons),
                "subtype": random.choice(subtypes),
                "confidence": random.uniform(0.7, 0.95),
            },
            "palette": {"hex": ["#E6E6FA", "#87CEEB", "#FFB6C1", "#98FB98", "#D3D3D3"]},
            "emotion": {
                "facial_expression": random.choice(emotions),
                "facial_expression_confidence": random.uniform(0.6, 0.9),
            },
        }

    async def get_color_result(self, user_id: str) -> PersonalColorResult:
        """Get stored color analysis result for a user."""
        result = await self.db.execute(
            select(ColorResult).where(ColorResult.user_id == user_id)
        )
        color_result = result.scalar_one_or_none()

        if not color_result:
            raise NotFoundError("Color result", user_id)

        research_logger.log(
            action_type=ActionType.COLOR_RESULT_VIEW,
            user_id=user_id,
            action_data={"season": color_result.season, "tone": color_result.tone},
        )

        colors = json.loads(color_result.recommended_colors)
        return PersonalColorResult(
            season=color_result.season,  # type: ignore
            tone=color_result.tone,  # type: ignore
            description=color_result.description,
            recommended_colors=[ColorItem(**c) for c in colors],
            analyzed_at=color_result.analyzed_at,
            confidence=color_result.confidence,
            subtype=color_result.subtype,
            facial_expression=color_result.facial_expression,
        )

    async def get_daily_healing_color(self, user_id: str) -> DailyHealingColorResponse:
        """Get or generate daily healing color for a user."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # Check if we already have a healing color for today
        result = await self.db.execute(
            select(DailyHealingColor).where(
                DailyHealingColor.user_id == user_id,
                DailyHealingColor.date >= today,
                DailyHealingColor.date < today + timedelta(days=1),
            )
        )
        daily_color = result.scalar_one_or_none()

        if daily_color:
            research_logger.log(
                action_type=ActionType.DAILY_HEALING_VIEW,
                user_id=user_id,
                action_data={"color_hex": daily_color.color_hex, "cached": True},
            )
            return DailyHealingColorResponse(
                color=ColorItem(
                    name=daily_color.color_name,
                    hex=daily_color.color_hex,
                    description=daily_color.color_description,
                ),
                calm_effect=daily_color.calm_effect,
                personal_fit=daily_color.personal_fit,
                daily_affirmation=daily_color.daily_affirmation,
                date=daily_color.date,
            )

        # Generate new healing color based on user's personal color
        color_result = await self.db.execute(
            select(ColorResult).where(ColorResult.user_id == user_id)
        )
        personal_color = color_result.scalar_one_or_none()

        # Select appropriate healing color
        if personal_color:
            palette_key = f"{personal_color.season}_{personal_color.tone}"
            colors = COLOR_PALETTES.get(palette_key, COLOR_PALETTES["summer_cool"])
        else:
            colors = COLOR_PALETTES["summer_cool"]

        # Pick a color for today (rotate based on day of year)
        day_of_year = today.timetuple().tm_yday
        selected_color = colors[day_of_year % len(colors)]

        # Generate personalized content
        affirmations = [
            "오늘 하루도 당신은 충분히 멋집니다.",
            "작은 것에도 감사하는 하루가 되길 바랍니다.",
            "당신의 존재 자체가 빛나는 하루입니다.",
            "오늘의 색상이 당신에게 평온을 가져다주길 바랍니다.",
            "자신을 믿고 한 걸음씩 나아가세요.",
        ]

        daily_color = DailyHealingColor(
            user_id=user_id,
            color_name=selected_color["name"],
            color_hex=selected_color["hex"],
            color_description=selected_color.get("description"),
            calm_effect=f"{selected_color['name']}은(는) 마음을 편안하게 해주고 일상의 스트레스를 완화하는 효과가 있습니다.",
            personal_fit=f"당신의 퍼스널 컬러와 조화롭게 어울려 자연스러운 아름다움을 더해줍니다.",
            daily_affirmation=affirmations[day_of_year % len(affirmations)],
            date=today,
        )
        self.db.add(daily_color)
        await self.db.flush()

        research_logger.log(
            action_type=ActionType.DAILY_HEALING_VIEW,
            user_id=user_id,
            action_data={"color_hex": daily_color.color_hex, "cached": False},
        )

        return DailyHealingColorResponse(
            color=ColorItem(
                name=daily_color.color_name,
                hex=daily_color.color_hex,
                description=daily_color.color_description,
            ),
            calm_effect=daily_color.calm_effect,
            personal_fit=daily_color.personal_fit,
            daily_affirmation=daily_color.daily_affirmation,
            date=daily_color.date,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()
