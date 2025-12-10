"""Recommendation service for personalized color-based suggestions."""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from embeau_api.core.logging import ActionType, research_logger
from embeau_api.models import ColorResult, RecommendationCache
from embeau_api.schemas.color import ColorItem
from embeau_api.schemas.recommendation import Recommendation, RecommendationItem

# Static recommendation data organized by color/season
FASHION_RECOMMENDATIONS = {
    "spring": [
        {"id": "f1", "type": "fashion", "title": "코랄 블라우스", "description": "화사한 봄을 위한 코랄 컬러 블라우스", "color": "#FF7F50"},
        {"id": "f2", "type": "fashion", "title": "피치 스카프", "description": "부드러운 피치 톤 실크 스카프", "color": "#FFDAB9"},
        {"id": "f3", "type": "fashion", "title": "아이보리 니트", "description": "따뜻한 아이보리 캐시미어 니트", "color": "#FFFFF0"},
    ],
    "summer": [
        {"id": "f4", "type": "fashion", "title": "라벤더 원피스", "description": "우아한 라벤더 컬러 린넨 원피스", "color": "#E6E6FA"},
        {"id": "f5", "type": "fashion", "title": "스카이 블루 셔츠", "description": "시원한 스카이 블루 면 셔츠", "color": "#87CEEB"},
        {"id": "f6", "type": "fashion", "title": "소프트 핑크 카디건", "description": "부드러운 핑크 톤 가디건", "color": "#FFB6C1"},
    ],
    "autumn": [
        {"id": "f7", "type": "fashion", "title": "테라코타 재킷", "description": "따뜻한 테라코타 울 재킷", "color": "#E2725B"},
        {"id": "f8", "type": "fashion", "title": "머스타드 스웨터", "description": "깊은 머스타드 컬러 니트", "color": "#FFDB58"},
        {"id": "f9", "type": "fashion", "title": "올리브 코트", "description": "클래식한 올리브 그린 코트", "color": "#808000"},
    ],
    "winter": [
        {"id": "f10", "type": "fashion", "title": "로얄 블루 드레스", "description": "선명한 로얄 블루 이브닝 드레스", "color": "#4169E1"},
        {"id": "f11", "type": "fashion", "title": "퓨어 화이트 셔츠", "description": "깔끔한 화이트 포플린 셔츠", "color": "#FFFFFF"},
        {"id": "f12", "type": "fashion", "title": "블랙 테일러드 재킷", "description": "세련된 블랙 테일러드 재킷", "color": "#000000"},
    ],
}

FOOD_RECOMMENDATIONS = {
    "spring": [
        {"id": "fd1", "type": "food", "title": "딸기 요거트 볼", "description": "신선한 딸기와 요거트로 만든 건강 볼", "color": "#FF6B6B"},
        {"id": "fd2", "type": "food", "title": "연어 샐러드", "description": "오메가3 풍부한 연어 아보카도 샐러드", "color": "#FA8072"},
        {"id": "fd3", "type": "food", "title": "망고 스무디", "description": "비타민 가득 망고 스무디", "color": "#FFD700"},
    ],
    "summer": [
        {"id": "fd4", "type": "food", "title": "블루베리 스무디", "description": "항산화 성분 가득 블루베리 스무디", "color": "#4169E1"},
        {"id": "fd5", "type": "food", "title": "수박 주스", "description": "시원한 수박 주스", "color": "#FF6B6B"},
        {"id": "fd6", "type": "food", "title": "민트 레모네이드", "description": "청량한 민트 레모네이드", "color": "#98FB98"},
    ],
    "autumn": [
        {"id": "fd7", "type": "food", "title": "단호박 수프", "description": "달콤한 단호박 크림 수프", "color": "#FF8C00"},
        {"id": "fd8", "type": "food", "title": "고구마 라떼", "description": "따뜻한 고구마 라떼", "color": "#D2691E"},
        {"id": "fd9", "type": "food", "title": "버섯 리조또", "description": "깊은 풍미의 버섯 리조또", "color": "#8B4513"},
    ],
    "winter": [
        {"id": "fd10", "type": "food", "title": "석류 주스", "description": "진한 석류 원액 주스", "color": "#DC143C"},
        {"id": "fd11", "type": "food", "title": "검은콩 죽", "description": "영양 가득 검은콩 죽", "color": "#2F4F4F"},
        {"id": "fd12", "type": "food", "title": "핫초코", "description": "진한 다크 핫초콜릿", "color": "#8B4513"},
    ],
}

ACTIVITY_RECOMMENDATIONS = {
    "spring": [
        {"id": "a1", "type": "activity", "title": "벚꽃 산책", "description": "봄꽃 가득한 공원에서 가벼운 산책", "color": "#FFB6C1"},
        {"id": "a2", "type": "activity", "title": "꽃꽂이 클래스", "description": "봄 꽃으로 하는 플라워 아레인지먼트", "color": "#98FB98"},
    ],
    "summer": [
        {"id": "a3", "type": "activity", "title": "수영", "description": "시원한 물에서 즐기는 수영", "color": "#87CEEB"},
        {"id": "a4", "type": "activity", "title": "요가 명상", "description": "마음을 차분하게 하는 요가 명상", "color": "#E6E6FA"},
    ],
    "autumn": [
        {"id": "a5", "type": "activity", "title": "단풍 트레킹", "description": "가을 단풍을 즐기는 산행", "color": "#FF8C00"},
        {"id": "a6", "type": "activity", "title": "도자기 만들기", "description": "마음을 담은 도자기 공예", "color": "#D2691E"},
    ],
    "winter": [
        {"id": "a7", "type": "activity", "title": "독서", "description": "따뜻한 실내에서 즐기는 독서", "color": "#8B4513"},
        {"id": "a8", "type": "activity", "title": "미술관 방문", "description": "예술 작품 감상하기", "color": "#4169E1"},
    ],
}

# Healing color to recommendation mapping
HEALING_COLOR_ITEMS = {
    "#E6E6FA": {  # 라벤더
        "fashion": [{"id": "hf1", "type": "fashion", "title": "라벤더 캐시미어 스웨터", "description": "부드러운 라벤더 톤으로 마음을 진정시켜주는 니트", "color": "#E6E6FA"}],
        "food": [{"id": "hfd1", "type": "food", "title": "라벤더 허브티", "description": "마음을 진정시키는 라벤더 허브티", "color": "#E6E6FA"}],
    },
    "#87CEEB": {  # 스카이 블루
        "fashion": [{"id": "hf2", "type": "fashion", "title": "스카이 블루 린넨 셔츠", "description": "시원하고 청량한 느낌의 셔츠", "color": "#87CEEB"}],
        "food": [{"id": "hfd2", "type": "food", "title": "블루베리 요거트", "description": "상큼하고 건강한 블루베리 요거트", "color": "#87CEEB"}],
    },
    "#98FB98": {  # 민트 그린
        "fashion": [{"id": "hf3", "type": "fashion", "title": "민트 그린 카디건", "description": "상쾌한 느낌의 민트 카디건", "color": "#98FB98"}],
        "food": [{"id": "hfd3", "type": "food", "title": "민트 모히또", "description": "청량감 가득한 민트 음료", "color": "#98FB98"}],
    },
}


class RecommendationService:
    """Service for personalized recommendations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_recommendations(self, user_id: str) -> Recommendation:
        """Get personalized recommendations based on user's color profile."""
        # Get user's personal color
        result = await self.db.execute(
            select(ColorResult).where(ColorResult.user_id == user_id)
        )
        color_result = result.scalar_one_or_none()

        season = color_result.season if color_result else "summer"
        primary_color = None

        if color_result:
            colors = json.loads(color_result.recommended_colors)
            if colors:
                primary_color = ColorItem(**colors[0])

        if not primary_color:
            primary_color = ColorItem(name="라벤더", hex="#E6E6FA", description="차분한 라벤더")

        # Get recommendations for the season
        fashion_items = [
            RecommendationItem(**item)
            for item in FASHION_RECOMMENDATIONS.get(season, FASHION_RECOMMENDATIONS["summer"])
        ]
        food_items = [
            RecommendationItem(**item)
            for item in FOOD_RECOMMENDATIONS.get(season, FOOD_RECOMMENDATIONS["summer"])
        ]
        activity_items = [
            RecommendationItem(**item)
            for item in ACTIVITY_RECOMMENDATIONS.get(season, ACTIVITY_RECOMMENDATIONS["summer"])
        ]

        research_logger.log(
            action_type=ActionType.RECOMMENDATION_VIEW,
            user_id=user_id,
            action_data={
                "season": season,
                "fashion_count": len(fashion_items),
                "food_count": len(food_items),
            },
        )

        return Recommendation(
            color=primary_color,
            items=fashion_items,
            foods=food_items,
            activities=activity_items,
        )

    async def get_recommendations_by_color(self, user_id: str, color_hex: str) -> Recommendation:
        """Get recommendations for a specific healing color."""
        # Normalize color hex
        color_hex = color_hex.upper()
        if not color_hex.startswith("#"):
            color_hex = f"#{color_hex}"

        # Find matching recommendations
        color_items = HEALING_COLOR_ITEMS.get(color_hex)

        if color_items:
            fashion_items = [RecommendationItem(**item) for item in color_items.get("fashion", [])]
            food_items = [RecommendationItem(**item) for item in color_items.get("food", [])]
        else:
            # Default to general recommendations
            result = await self.db.execute(
                select(ColorResult).where(ColorResult.user_id == user_id)
            )
            color_result = result.scalar_one_or_none()
            season = color_result.season if color_result else "summer"

            fashion_items = [
                RecommendationItem(**item)
                for item in FASHION_RECOMMENDATIONS.get(season, [])[:2]
            ]
            food_items = [
                RecommendationItem(**item)
                for item in FOOD_RECOMMENDATIONS.get(season, [])[:2]
            ]

        # Find color name from hex
        color_name = "힐링 컬러"
        for hex_code, items in HEALING_COLOR_ITEMS.items():
            if hex_code == color_hex:
                for category in items.values():
                    if category:
                        color_name = category[0].get("title", "").split()[0]
                        break

        research_logger.log(
            action_type=ActionType.RECOMMENDATION_VIEW,
            user_id=user_id,
            action_data={"color_hex": color_hex, "type": "by_color"},
        )

        return Recommendation(
            color=ColorItem(name=color_name, hex=color_hex),
            items=fashion_items,
            foods=food_items,
            activities=[],
        )
