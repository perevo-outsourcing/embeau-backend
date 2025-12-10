"""Report API endpoints."""

from fastapi import APIRouter
from fastapi.responses import Response

from embeau_api.deps import CurrentUser, ReportServiceDep

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/weekly")
async def get_weekly_report(
    current_user: CurrentUser,
    report_service: ReportServiceDep,
) -> Response:
    """
    Download weekly PDF report.

    Generates a comprehensive PDF report containing:
    - Personal color analysis summary
    - Weekly emotion statistics
    - Improvement insights
    - Recommendations
    """
    pdf_bytes = await report_service.generate_weekly_report(current_user.id)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=embeau_weekly_report.pdf"
        },
    )
