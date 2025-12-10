"""Emotion analysis service with RAG integration."""

import json
import time
from datetime import datetime, timedelta, timezone

import httpx
from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from embeau_api.config import get_settings
from embeau_api.core.exceptions import EmotionAnalysisError, NotFoundError
from embeau_api.core.logging import ActionType, research_logger
from embeau_api.models import EmotionEntry as EmotionEntryModel
from embeau_api.models import WeeklyInsight as WeeklyInsightModel
from embeau_api.schemas.emotion import (
    EmotionEntry,
    EmotionState,
    HealingColor,
    WeeklyInsightResponse,
    WeeklyStats,
)

settings = get_settings()

# Emotion to healing color mapping
EMOTION_HEALING_COLORS = {
    "anxiety": [
        {"name": "라벤더", "hex": "#E6E6FA", "effect": "마음을 진정시키고 불안을 완화합니다"},
        {"name": "페일 블루", "hex": "#AFEEEE", "effect": "평온함과 안정감을 선사합니다"},
    ],
    "stress": [
        {"name": "민트 그린", "hex": "#98FB98", "effect": "긴장을 풀어주고 스트레스를 해소합니다"},
        {"name": "스카이 블루", "hex": "#87CEEB", "effect": "마음의 휴식을 가져다줍니다"},
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


class EmotionAnalyzerService:
    """Service for emotion analysis and healing color recommendations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def analyze_emotion(self, user_id: str, text: str) -> EmotionEntry:
        """Analyze emotion from text and recommend healing colors."""
        start_time = time.time()

        research_logger.log(
            action_type=ActionType.EMOTION_ANALYZE_START,
            user_id=user_id,
            action_data={"text_length": len(text)},
        )

        try:
            # Analyze emotion using OpenAI if available, otherwise use keyword-based analysis
            if self.openai:
                emotions = await self._analyze_with_openai(text)
            else:
                emotions = self._analyze_with_keywords(text)

            # Determine dominant emotion and get healing colors
            dominant_emotion = self._get_dominant_negative_emotion(emotions)
            healing_colors = self._get_healing_colors(dominant_emotion, emotions)

            # Get RAG recommendation if available
            rag_result = await self._get_rag_recommendation(text)

            # Store emotion entry
            healing_colors_json = json.dumps(
                [{"name": c.name, "hex": c.hex, "effect": c.effect} for c in healing_colors],
                ensure_ascii=False,
            )

            emotion_entry = EmotionEntryModel(
                user_id=user_id,
                input_text=text,
                anxiety=emotions.anxiety,
                stress=emotions.stress,
                satisfaction=emotions.satisfaction,
                happiness=emotions.happiness,
                depression=emotions.depression,
                healing_colors=healing_colors_json,
                rag_color_name=rag_result.get("추천_색깔") if rag_result else None,
                rag_psychological_effect=rag_result.get("심리적_효과") if rag_result else None,
                rag_recommendation_reason=rag_result.get("추천_이유") if rag_result else None,
                rag_usage_method=rag_result.get("활용_방법") if rag_result else None,
            )
            self.db.add(emotion_entry)
            await self.db.flush()

            duration_ms = int((time.time() - start_time) * 1000)
            research_logger.log_emotion_analysis(
                user_id=user_id,
                input_text=text,
                emotions={
                    "anxiety": emotions.anxiety,
                    "stress": emotions.stress,
                    "satisfaction": emotions.satisfaction,
                    "happiness": emotions.happiness,
                    "depression": emotions.depression,
                },
                healing_colors=[{"name": c.name, "hex": c.hex} for c in healing_colors],
                duration_ms=duration_ms,
            )

            return EmotionEntry(
                id=emotion_entry.id,
                date=emotion_entry.created_at,
                text=text,
                emotions=emotions,
                healing_colors=healing_colors,
                rag_color_name=rag_result.get("추천_색깔") if rag_result else None,
                rag_psychological_effect=rag_result.get("심리적_효과") if rag_result else None,
                rag_recommendation_reason=rag_result.get("추천_이유") if rag_result else None,
                rag_usage_method=rag_result.get("활용_방법") if rag_result else None,
            )

        except Exception as e:
            raise EmotionAnalysisError(f"Failed to analyze emotion: {str(e)}")

    async def _analyze_with_openai(self, text: str) -> EmotionState:
        """Analyze emotion using OpenAI API."""
        prompt = f"""다음 텍스트에서 감정을 분석해주세요. 각 감정에 대해 0-100 사이의 점수를 JSON 형식으로 반환해주세요.

텍스트: "{text}"

다음 형식으로 응답해주세요:
{{
    "anxiety": <0-100>,
    "stress": <0-100>,
    "satisfaction": <0-100>,
    "happiness": <0-100>,
    "depression": <0-100>
}}

점수 기준:
- 0: 해당 감정 없음
- 25: 약간 있음
- 50: 보통
- 75: 강함
- 100: 매우 강함"""

        try:
            response = await self.openai.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "당신은 감정 분석 전문가입니다. 텍스트에서 감정을 정확하게 분석합니다."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            result = json.loads(response.choices[0].message.content)
            return EmotionState(
                anxiety=float(result.get("anxiety", 0)),
                stress=float(result.get("stress", 0)),
                satisfaction=float(result.get("satisfaction", 0)),
                happiness=float(result.get("happiness", 0)),
                depression=float(result.get("depression", 0)),
            )
        except Exception:
            # Fallback to keyword analysis
            return self._analyze_with_keywords(text)

    def _analyze_with_keywords(self, text: str) -> EmotionState:
        """Simple keyword-based emotion analysis."""
        # Korean emotion keywords
        anxiety_keywords = ["불안", "걱정", "두려움", "무서움", "초조", "긴장"]
        stress_keywords = ["스트레스", "피곤", "지침", "힘듦", "벅참", "압박"]
        satisfaction_keywords = ["만족", "뿌듯", "성취", "보람", "충족"]
        happiness_keywords = ["행복", "기쁨", "즐거움", "좋음", "신남", "기분좋"]
        depression_keywords = ["우울", "슬픔", "외로움", "공허", "무기력", "우울함"]

        text_lower = text.lower()

        def count_keywords(keywords: list[str]) -> float:
            count = sum(1 for keyword in keywords if keyword in text_lower)
            return min(count * 30, 100)  # Max 100, 30 per keyword

        return EmotionState(
            anxiety=count_keywords(anxiety_keywords),
            stress=count_keywords(stress_keywords),
            satisfaction=count_keywords(satisfaction_keywords),
            happiness=count_keywords(happiness_keywords),
            depression=count_keywords(depression_keywords),
        )

    def _get_dominant_negative_emotion(self, emotions: EmotionState) -> str:
        """Get the dominant negative emotion for healing color selection."""
        negative_emotions = {
            "anxiety": emotions.anxiety,
            "stress": emotions.stress,
            "depression": emotions.depression,
        }

        # If mostly positive, return satisfaction or happiness
        positive_sum = emotions.satisfaction + emotions.happiness
        negative_sum = sum(negative_emotions.values())

        if positive_sum > negative_sum:
            return "happiness" if emotions.happiness > emotions.satisfaction else "satisfaction"

        # Return the highest negative emotion
        return max(negative_emotions, key=negative_emotions.get)

    def _get_healing_colors(self, dominant_emotion: str, emotions: EmotionState) -> list[HealingColor]:
        """Get healing colors based on emotional state."""
        colors = EMOTION_HEALING_COLORS.get(dominant_emotion, EMOTION_HEALING_COLORS["stress"])
        return [HealingColor(**c) for c in colors]

    async def _get_rag_recommendation(self, text: str) -> dict | None:
        """Get RAG-based color recommendation."""
        try:
            # Call RAG API if available (from reference/embeau_project)
            response = await self.http_client.post(
                "http://localhost:8002/recommend",
                json={"query": text},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    async def get_emotion_history(self, user_id: str, limit: int = 30) -> list[EmotionEntry]:
        """Get emotion history for a user."""
        result = await self.db.execute(
            select(EmotionEntryModel)
            .where(EmotionEntryModel.user_id == user_id)
            .order_by(EmotionEntryModel.created_at.desc())
            .limit(limit)
        )
        entries = result.scalars().all()

        research_logger.log(
            action_type=ActionType.EMOTION_HISTORY_VIEW,
            user_id=user_id,
            action_data={"entry_count": len(entries), "limit": limit},
        )

        return [
            EmotionEntry(
                id=entry.id,
                date=entry.created_at,
                text=entry.input_text,
                emotions=EmotionState(
                    anxiety=entry.anxiety,
                    stress=entry.stress,
                    satisfaction=entry.satisfaction,
                    happiness=entry.happiness,
                    depression=entry.depression,
                ),
                healing_colors=[HealingColor(**c) for c in json.loads(entry.healing_colors)],
                rag_color_name=entry.rag_color_name,
                rag_psychological_effect=entry.rag_psychological_effect,
                rag_recommendation_reason=entry.rag_recommendation_reason,
                rag_usage_method=entry.rag_usage_method,
            )
            for entry in entries
        ]

    async def get_weekly_insight(self, user_id: str) -> WeeklyInsightResponse:
        """Generate weekly insight based on emotion history."""
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        # Check for cached insight
        result = await self.db.execute(
            select(WeeklyInsightModel).where(
                WeeklyInsightModel.user_id == user_id,
                WeeklyInsightModel.week_start == week_start,
            )
        )
        cached_insight = result.scalar_one_or_none()

        if cached_insight:
            research_logger.log(
                action_type=ActionType.WEEKLY_INSIGHT_VIEW,
                user_id=user_id,
                action_data={"cached": True, "week_start": week_start.isoformat()},
            )
            return self._insight_to_response(cached_insight)

        # Calculate aggregated emotions for the week
        entries_result = await self.db.execute(
            select(EmotionEntryModel).where(
                EmotionEntryModel.user_id == user_id,
                EmotionEntryModel.created_at >= week_start,
                EmotionEntryModel.created_at < week_end,
            )
        )
        entries = entries_result.scalars().all()

        if not entries:
            # Return default insight if no entries
            return WeeklyInsightResponse(
                week_start=week_start,
                week_end=week_end,
                emotion_distribution=EmotionState(
                    anxiety=0, stress=0, satisfaction=0, happiness=0, depression=0
                ),
                improvement="이번 주에 기록된 감정이 없습니다. 매일 감정을 기록해보세요!",
                next_week_suggestion="다음 주에는 하루에 한 번씩 감정을 기록해보는 것은 어떨까요?",
                stats=WeeklyStats(
                    active_days=0,
                    color_improvement=0,
                    mood_improvement=0,
                    stress_relief=0,
                ),
            )

        # Calculate averages
        avg_anxiety = sum(e.anxiety for e in entries) / len(entries)
        avg_stress = sum(e.stress for e in entries) / len(entries)
        avg_satisfaction = sum(e.satisfaction for e in entries) / len(entries)
        avg_happiness = sum(e.happiness for e in entries) / len(entries)
        avg_depression = sum(e.depression for e in entries) / len(entries)

        # Count active days
        active_days = len(set(e.created_at.date() for e in entries))

        # Generate insights
        if self.openai:
            improvement, suggestion = await self._generate_ai_insight(
                avg_anxiety, avg_stress, avg_satisfaction, avg_happiness, avg_depression
            )
        else:
            improvement, suggestion = self._generate_simple_insight(
                avg_anxiety, avg_stress, avg_satisfaction, avg_happiness, avg_depression
            )

        # Calculate improvement metrics (compare with previous week)
        prev_week_start = week_start - timedelta(days=7)
        prev_result = await self.db.execute(
            select(
                func.avg(EmotionEntryModel.happiness),
                func.avg(EmotionEntryModel.stress),
            ).where(
                EmotionEntryModel.user_id == user_id,
                EmotionEntryModel.created_at >= prev_week_start,
                EmotionEntryModel.created_at < week_start,
            )
        )
        prev_data = prev_result.first()
        prev_happiness = prev_data[0] or 50
        prev_stress = prev_data[1] or 50

        mood_improvement = ((avg_happiness - prev_happiness) / max(prev_happiness, 1)) * 100
        stress_relief = ((prev_stress - avg_stress) / max(prev_stress, 1)) * 100

        # Store insight
        insight = WeeklyInsightModel(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            avg_anxiety=avg_anxiety,
            avg_stress=avg_stress,
            avg_satisfaction=avg_satisfaction,
            avg_happiness=avg_happiness,
            avg_depression=avg_depression,
            improvement=improvement,
            next_week_suggestion=suggestion,
            active_days=active_days,
            total_entries=len(entries),
            color_improvement=min(active_days * 15, 100),  # More active = more color improvement
            mood_improvement=max(min(mood_improvement, 100), -100),
            stress_relief=max(min(stress_relief, 100), -100),
        )
        self.db.add(insight)
        await self.db.flush()

        research_logger.log(
            action_type=ActionType.WEEKLY_INSIGHT_VIEW,
            user_id=user_id,
            action_data={"cached": False, "week_start": week_start.isoformat()},
        )

        return self._insight_to_response(insight)

    async def _generate_ai_insight(
        self,
        anxiety: float,
        stress: float,
        satisfaction: float,
        happiness: float,
        depression: float,
    ) -> tuple[str, str]:
        """Generate AI-powered weekly insight."""
        prompt = f"""다음은 사용자의 이번 주 평균 감정 점수입니다 (0-100):
- 불안: {anxiety:.1f}
- 스트레스: {stress:.1f}
- 만족감: {satisfaction:.1f}
- 행복: {happiness:.1f}
- 우울: {depression:.1f}

1. 이번 주 감정 상태에 대한 간단한 분석 (2-3문장)
2. 다음 주를 위한 따뜻한 조언 (1-2문장)

JSON 형식으로 응답해주세요:
{{"improvement": "...", "suggestion": "..."}}"""

        try:
            response = await self.openai.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "당신은 따뜻하고 공감 능력이 뛰어난 상담 전문가입니다."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("improvement", ""), result.get("suggestion", "")
        except Exception:
            return self._generate_simple_insight(anxiety, stress, satisfaction, happiness, depression)

    def _generate_simple_insight(
        self,
        anxiety: float,
        stress: float,
        satisfaction: float,
        happiness: float,
        depression: float,
    ) -> tuple[str, str]:
        """Generate simple insight without AI."""
        positive_score = (satisfaction + happiness) / 2
        negative_score = (anxiety + stress + depression) / 3

        if positive_score > negative_score:
            improvement = "이번 주는 전반적으로 긍정적인 감정이 우세했습니다. 좋은 한 주였네요!"
            suggestion = "다음 주에도 현재의 긍정적인 상태를 유지하면서 작은 기쁨들을 찾아보세요."
        else:
            if stress > 60:
                improvement = "이번 주는 스트레스가 높았던 것 같습니다. 충분한 휴식이 필요해 보여요."
                suggestion = "다음 주에는 자신을 위한 시간을 조금 더 가져보는 건 어떨까요?"
            elif anxiety > 60:
                improvement = "불안한 마음이 많았던 한 주였네요. 당신의 감정은 충분히 이해됩니다."
                suggestion = "깊은 호흡과 함께 천천히 마음을 가라앉혀 보세요."
            else:
                improvement = "다양한 감정을 경험한 한 주였습니다."
                suggestion = "다음 주에는 힐링 컬러와 함께 마음의 평화를 찾아보세요."

        return improvement, suggestion

    def _insight_to_response(self, insight: WeeklyInsightModel) -> WeeklyInsightResponse:
        """Convert insight model to response schema."""
        return WeeklyInsightResponse(
            week_start=insight.week_start,
            week_end=insight.week_end,
            emotion_distribution=EmotionState(
                anxiety=insight.avg_anxiety,
                stress=insight.avg_stress,
                satisfaction=insight.avg_satisfaction,
                happiness=insight.avg_happiness,
                depression=insight.avg_depression,
            ),
            improvement=insight.improvement,
            next_week_suggestion=insight.next_week_suggestion,
            stats=WeeklyStats(
                active_days=insight.active_days,
                color_improvement=insight.color_improvement,
                mood_improvement=insight.mood_improvement,
                stress_relief=insight.stress_relief,
            ),
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()
