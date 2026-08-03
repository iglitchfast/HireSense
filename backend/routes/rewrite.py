from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.gemini_client import call_gemini_structured, stream_gemini_text
from backend.prompts import PASS2_SYSTEM_PROMPT, build_pass2_user_prompt
from backend.schemas import BulletRewriteResult, GEMINI_BULLET_REWRITE_SCHEMA, RewriteRequest

router = APIRouter()


def _priority_keywords(body: RewriteRequest) -> list[str]:
    if not body.keywordAnalysis:
        return []
    return [
        k.keyword
        for k in (body.keywordAnalysis.missingKeywords + body.keywordAnalysis.weaklyEmphasizedKeywords)
        if k.importance == "high"
    ]


@router.post("/api/rewrite", response_model=BulletRewriteResult)
def rewrite(body: RewriteRequest) -> BulletRewriteResult:
    if not body.jobDescription.strip() or not body.resumeMarkdown.strip():
        raise HTTPException(status_code=400, detail="Both jobDescription and resumeMarkdown are required.")

    user_prompt = build_pass2_user_prompt(body.jobDescription, body.resumeMarkdown, _priority_keywords(body))

    try:
        result = call_gemini_structured(
            PASS2_SYSTEM_PROMPT, user_prompt, GEMINI_BULLET_REWRITE_SCHEMA, BulletRewriteResult
        )
        return result
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/rewrite/stream")
def rewrite_stream(body: RewriteRequest):
    """
    Same as /api/rewrite but streams Gemini's raw text output live as it's
    generated, so the frontend can render a real-time "typing" effect. The
    stream is plain text chunks (not SSE) — the frontend reads the fetch
    response body directly via a ReadableStream reader.
    """
    if not body.jobDescription.strip() or not body.resumeMarkdown.strip():
        raise HTTPException(status_code=400, detail="Both jobDescription and resumeMarkdown are required.")

    user_prompt = build_pass2_user_prompt(body.jobDescription, body.resumeMarkdown, _priority_keywords(body))

    def _generate():
        try:
            for chunk in stream_gemini_text(PASS2_SYSTEM_PROMPT, user_prompt, GEMINI_BULLET_REWRITE_SCHEMA):
                yield chunk
        except Exception as exc:  # noqa: BLE001
            # Emit a sentinel error marker the frontend can detect mid-stream
            yield f"\n__STREAM_ERROR__:{exc}"

    return StreamingResponse(_generate(), media_type="text/plain")
