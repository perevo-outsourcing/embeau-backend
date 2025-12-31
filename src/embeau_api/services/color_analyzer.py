"""Color analysis service - uses ChatGPT Vision API for analysis."""

import base64
import json
import logging
import time
from datetime import datetime, timedelta, timezone

from openai import AsyncOpenAI
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
    """Service for color analysis operations using ChatGPT Vision API."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def analyze_image(self, user_id: str, image_data: str) -> PersonalColorResult:
        """Analyze an image to determine personal color using ChatGPT Vision API."""
        start_time = time.time()

        research_logger.log(
            action_type=ActionType.COLOR_ANALYZE_START,
            user_id=user_id,
            action_data={"image_size": len(image_data)},
        )

        try:
            # Ensure base64 has proper prefix for API
            if "," in image_data:
                base64_image = image_data.split(",")[1]
                image_url = f"data:image/jpeg;base64,{base64_image}"
            else:
                image_url = f"data:image/jpeg;base64,{image_data}"

            # Analyze with ChatGPT Vision API
            analysis_data = await self._analyze_with_vision_api(image_url)

            # Parse response
            tone_data = analysis_data.get("tone", {})
            emotion_data = analysis_data.get("emotion", {})

            # Validate season - must be one of: spring, summer, autumn, winter
            valid_seasons = {"spring", "summer", "autumn", "winter"}
            raw_season = tone_data.get("season", "summer").lower()
            season = raw_season if raw_season in valid_seasons else "summer"

            # Validate subtype
            valid_subtypes = {"warm", "cool", "clear", "soft", "deep", "light"}
            raw_subtype = tone_data.get("subtype", "cool").lower()
            subtype = raw_subtype if raw_subtype in valid_subtypes else "cool"

            confidence = tone_data.get("confidence", 0.85)

            # Determine tone from subtype - must be "warm" or "cool"
            tone = "cool" if subtype in {"cool", "clear", "soft"} else "warm"

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

    async def _analyze_with_vision_api(self, image_url: str) -> dict:
        """Analyze image using ChatGPT Vision API (gpt-4o for best accuracy)."""
        if not self.openai:
            logger.warning("OpenAI API key not configured, using fallback")
            return self._fallback_analysis()

        prompt = """이 얼굴 이미지를 분석하여 퍼스널 컬러와 표정을 판단해주세요.

분석 항목:
1. 피부 언더톤 (웜톤/쿨톤)
2. 피부 밝기 (밝음/중간/어두움)
3. 계절 타입 - 반드시 다음 중 하나: spring, summer, autumn, winter
4. 세부 타입 - 반드시 다음 중 하나: warm, cool, clear, soft, deep, light
5. 표정 (happy/neutral/calm/sad/surprised/angry)

중요: 이미지가 불분명하거나 얼굴이 잘 보이지 않아도, 가장 가능성이 높은 값을 선택해주세요.
절대로 "unknown", "unclear", "cannot determine" 같은 값을 사용하지 마세요.

다음 JSON 형식으로만 응답해주세요:
{
    "tone": {
        "season": "spring 또는 summer 또는 autumn 또는 winter 중 하나만",
        "subtype": "warm 또는 cool 또는 clear 또는 soft 또는 deep 또는 light 중 하나만",
        "confidence": 0.0-1.0,
        "undertone": "warm|cool|neutral",
        "brightness": "light|medium|dark",
        "analysis_reason": "분석 이유 설명"
    },
    "emotion": {
        "facial_expression": "happy|neutral|calm|sad|surprised|angry",
        "facial_expression_confidence": 0.0-1.0
    }
}"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o",  # 이미지 분석에 최적화된 모델
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 전문 퍼스널 컬러 컨설턴트입니다. 피부 톤, 언더톤, 색상 조화를 정확하게 분석합니다."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url, "detail": "high"}
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=500,
                temperature=0.3,
            )

            result = json.loads(response.choices[0].message.content)
            result["source"] = "gpt-4o-vision"
            return result

        except Exception as e:
            logger.warning(f"Vision API failed: {e}, using fallback")
            return self._fallback_analysis()

    def _fallback_analysis(self) -> dict:
        """Fallback analysis when API is unavailable."""
        return {
            "tone": {
                "season": "summer",
                "subtype": "cool",
                "confidence": 0.7,
                "undertone": "cool",
                "brightness": "medium",
                "analysis_reason": "API 분석 실패로 기본값 사용"
            },
            "emotion": {
                "facial_expression": "neutral",
                "facial_expression_confidence": 0.5
            },
            "source": "fallback",
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
        """Cleanup resources."""
        pass  # OpenAI client doesn't require explicit cleanup
