from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.pdf_export import markdown_resume_to_pdf_bytes

router = APIRouter()


class ExportPdfRequest(BaseModel):
    resumeMarkdown: str


@router.post("/api/export-pdf")
def export_pdf(body: ExportPdfRequest):
    if not body.resumeMarkdown.strip():
        raise HTTPException(status_code=400, detail="resumeMarkdown is required.")

    try:
        pdf_bytes = markdown_resume_to_pdf_bytes(body.resumeMarkdown)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="resume.pdf"'},
    )