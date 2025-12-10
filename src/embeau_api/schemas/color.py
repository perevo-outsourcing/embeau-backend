"""Color analysis schemas."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from embeau_api.schemas.base import BaseSchema

PersonalColorSeason = Literal["spring", "summer", "autumn", "winter"]
PersonalColorTone = Literal["warm", "cool"]


class ColorItem(BaseSchema):
    """Individual color item."""

    name: str
    hex: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    description: str | None = None


class ColorAnalyzeRequest(BaseSchema):
    """Color analysis request."""

    image: str = Field(..., description="Base64 encoded image data")


class PersonalColorResult(BaseSchema):
    """Personal color analysis result."""

    season: PersonalColorSeason
    tone: PersonalColorTone
    description: str
    recommended_colors: list[ColorItem] = Field(..., alias="recommendedColors")
    analyzed_at: datetime = Field(..., alias="analyzedAt")

    # Optional detailed data
    confidence: float | None = None
    subtype: str | None = None
    facial_expression: str | None = Field(None, alias="facialExpression")


class DailyHealingColorResponse(BaseSchema):
    """Daily healing color response."""

    color: ColorItem
    calm_effect: str = Field(..., alias="calmEffect")
    personal_fit: str = Field(..., alias="personalFit")
    daily_affirmation: str = Field(..., alias="dailyAffirmation")
    date: datetime


class ColorAnalysisResponse(BaseSchema):
    """Full color analysis response from Color Tone API."""

    tone: dict
    palette: dict
    emotion: dict
    reasoning: str | None = None
    explanation: str | None = None
    warnings: list[str] | None = None
