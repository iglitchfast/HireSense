from fastapi import APIRouter, HTTPException

from app.gemini_client import call_gemini_structured
from app.prompts import PASS1_SYSTEM_PROMPT, build_pass1_user_prompt
from app.schemas import AnalyzeRequest, GEMINI_KEYWORD_ANALYSIS_SCHEMA, KeywordAnalysisResult

router = APIRouter()


@router.post("/api/analyze", response_model=KeywordAnalysisResult)
def analyze(body: AnalyzeRequest) -> KeywordAnalysisResult:
    if not body.jobDescription.strip() or not body.resumeMarkdown.strip():
        raise HTTPException(status_code=400, detail="Both jobDescription and resumeMarkdown are required.")

    user_prompt = build_pass1_user_prompt(body.jobDescription, body.resumeMarkdown)

    try:
        result = call_gemini_structured(
            PASS1_SYSTEM_PROMPT, user_prompt, GEMINI_KEYWORD_ANALYSIS_SCHEMA, KeywordAnalysisResult
        )
        result.matchScore = max(0.0, min(100.0, result.matchScore))
        return result
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
