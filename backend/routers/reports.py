from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from surveil.report import generate_docx, generate_markdown

from ..deps import load_engagement

router = APIRouter(prefix="/api/engagements/{eng_id}/report", tags=["reports"])

_MEDIA_TYPES = {
    "md": "text/markdown",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("")
def get_report(eng_id: str, format: str = "md"):
    if format not in _MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="format must be 'md' or 'docx'")

    engagement = load_engagement(eng_id)
    out_dir = Path(tempfile.mkdtemp(prefix="surveil-report-"))
    out_path = out_dir / f"report_{engagement.id}.{format}"

    if format == "md":
        generate_markdown(engagement, out_path=out_path)
    else:
        generate_docx(engagement, out_path=out_path)

    return FileResponse(
        path=out_path,
        media_type=_MEDIA_TYPES[format],
        filename=out_path.name,
    )
