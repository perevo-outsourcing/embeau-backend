"""Recommendation schemas."""

from typing import Literal

from pydantic import Field

from embeau_api.schemas.base import BaseSchema
from embeau_api.schemas.color import ColorItem


class RecommendationItem(BaseSchema):
    """Individual recommendation item."""

    id: str
    type: Literal["fashion", "food", "activity"]
    title: str
    description: str | None = None
    image_url: str | None = Field(None, alias="imageUrl")
    color: str  # hex color


class Recommendation(BaseSchema):
    """Full recommendation response."""

    color: ColorItem
    items: list[RecommendationItem]
    foods: list[RecommendationItem]
    activities: list[RecommendationItem] | None = None


class RAGRecommendationResponse(BaseSchema):
    """RAG-based recommendation response."""

    recommended_color: str = Field(..., alias="추천_색깔")
    psychological_effect: str = Field(..., alias="심리적_효과")
    recommendation_reason: str = Field(..., alias="추천_이유")
    usage_method: str = Field(..., alias="활용_방법")
