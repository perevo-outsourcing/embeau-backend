"""Report generation service for PDF exports."""

import io
from datetime import datetime, timedelta, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from embeau_api.core.logging import ActionType, research_logger
from embeau_api.models import ColorResult, EmotionEntry, User, WeeklyInsight


class ReportService:
    """Service for generating PDF reports."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._register_fonts()

    def _register_fonts(self) -> None:
        """Register Korean-compatible fonts."""
        # Try to register a Korean font, fall back to default if not available
        try:
            pdfmetrics.registerFont(TTFont("NanumGothic", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"))
        except Exception:
            pass  # Will use default font

    async def generate_weekly_report(self, user_id: str) -> bytes:
        """Generate a weekly PDF report for a user."""
        # Get user data
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        # Get date range
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        # Get color result
        color_result = await self.db.execute(
            select(ColorResult).where(ColorResult.user_id == user_id)
        )
        color = color_result.scalar_one_or_none()

        # Get emotion entries
        entries_result = await self.db.execute(
            select(EmotionEntry)
            .where(
                EmotionEntry.user_id == user_id,
                EmotionEntry.created_at >= week_start,
                EmotionEntry.created_at < week_end,
            )
            .order_by(EmotionEntry.created_at)
        )
        entries = entries_result.scalars().all()

        # Get weekly insight
        insight_result = await self.db.execute(
            select(WeeklyInsight).where(
                WeeklyInsight.user_id == user_id,
                WeeklyInsight.week_start == week_start,
            )
        )
        insight = insight_result.scalar_one_or_none()

        # Generate PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        # Build content
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center
        )

        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
        )

        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontSize=11,
            spaceAfter=6,
        )

        # Title
        story.append(Paragraph("EMBEAU Weekly Report", title_style))
        story.append(Paragraph(
            f"{week_start.strftime('%Y.%m.%d')} - {(week_end - timedelta(days=1)).strftime('%Y.%m.%d')}",
            body_style,
        ))
        story.append(Spacer(1, 20))

        # User Info
        story.append(Paragraph("User Information", heading_style))
        if user:
            story.append(Paragraph(f"Email: {user.email}", body_style))
            story.append(Paragraph(f"Participant ID: {user.participant_id}", body_style))
        story.append(Spacer(1, 10))

        # Personal Color
        story.append(Paragraph("Personal Color", heading_style))
        if color:
            story.append(Paragraph(
                f"Season: {color.season.title()} | Tone: {color.tone.title()}",
                body_style,
            ))
            story.append(Paragraph(f"Description: {color.description}", body_style))
        else:
            story.append(Paragraph("No personal color analysis yet.", body_style))
        story.append(Spacer(1, 10))

        # Emotion Summary
        story.append(Paragraph("Weekly Emotion Summary", heading_style))
        if entries:
            # Calculate averages
            avg_data = [
                ["Emotion", "Average Score"],
                ["Anxiety", f"{sum(e.anxiety for e in entries) / len(entries):.1f}"],
                ["Stress", f"{sum(e.stress for e in entries) / len(entries):.1f}"],
                ["Satisfaction", f"{sum(e.satisfaction for e in entries) / len(entries):.1f}"],
                ["Happiness", f"{sum(e.happiness for e in entries) / len(entries):.1f}"],
                ["Depression", f"{sum(e.depression for e in entries) / len(entries):.1f}"],
            ]

            table = Table(avg_data, colWidths=[100, 100])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)
            story.append(Paragraph(f"Total entries this week: {len(entries)}", body_style))
        else:
            story.append(Paragraph("No emotion entries this week.", body_style))
        story.append(Spacer(1, 10))

        # Weekly Insight
        story.append(Paragraph("Weekly Insight", heading_style))
        if insight:
            story.append(Paragraph(f"Improvement: {insight.improvement}", body_style))
            story.append(Paragraph(f"Suggestion: {insight.next_week_suggestion}", body_style))
            story.append(Spacer(1, 10))

            # Stats
            stats_data = [
                ["Metric", "Value"],
                ["Active Days", str(insight.active_days)],
                ["Mood Improvement", f"{insight.mood_improvement:.1f}%"],
                ["Stress Relief", f"{insight.stress_relief:.1f}%"],
                ["Color Improvement", f"{insight.color_improvement:.1f}%"],
            ]

            stats_table = Table(stats_data, colWidths=[120, 80])
            stats_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(stats_table)
        else:
            story.append(Paragraph("No weekly insight available.", body_style))

        # Footer
        story.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.grey,
            alignment=1,
        )
        story.append(Paragraph(
            f"Generated by EMBEAU on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            footer_style,
        ))

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        research_logger.log(
            action_type=ActionType.REPORT_DOWNLOAD,
            user_id=user_id,
            action_data={
                "week_start": week_start.isoformat(),
                "entry_count": len(entries),
                "pdf_size": len(pdf_bytes),
            },
        )

        return pdf_bytes
