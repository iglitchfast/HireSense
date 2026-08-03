from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class KeywordItem(BaseModel):
    keyword: str
    category: Literal["skill", "tool", "qualification", "soft_skill"]
    importance: Literal["high", "medium", "low"]


class WeakKeywordItem(KeywordItem):
    reason: str = Field(default="", description="Why this keyword is underemphasized in the resume")


class KeywordAnalysisResult(BaseModel):
    matchScore: float
    matchedKeywords: List[KeywordItem] = Field(default_factory=list)
    missingKeywords: List[KeywordItem] = Field(default_factory=list)
    weaklyEmphasizedKeywords: List[WeakKeywordItem] = Field(default_factory=list)
    summary: str = ""


class RewrittenBullet(BaseModel):
    id: str
    original: str
    rewritten: str
    hasPlaceholderMetric: bool = False
    changeNotes: str = ""


class BulletRewriteResult(BaseModel):
    rewrites: List[RewrittenBullet]


class AnalyzeRequest(BaseModel):
    jobDescription: str
    resumeMarkdown: str


class RewriteRequest(BaseModel):
    jobDescription: str
    resumeMarkdown: str
    keywordAnalysis: Optional[KeywordAnalysisResult] = None


# ---- Minimal hand-written JSON schemas for Gemini's response_schema ----
# Gemini only supports a narrow subset of JSON Schema: type, properties, items,
# required, enum, description. NO default/minimum/maximum/additionalProperties —
# those cause "unknown field for schema" errors. Do not auto-generate these from
# the Pydantic models above; write them by hand and keep them in sync manually.

_KEYWORD_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "keyword": {"type": "string"},
        "category": {"type": "string", "enum": ["skill", "tool", "qualification", "soft_skill"]},
        "importance": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["keyword", "category", "importance"],
}

_WEAK_KEYWORD_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "keyword": {"type": "string"},
        "category": {"type": "string", "enum": ["skill", "tool", "qualification", "soft_skill"]},
        "importance": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason": {"type": "string"},
    },
    "required": ["keyword", "category", "importance", "reason"],
}

GEMINI_KEYWORD_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "matchScore": {"type": "number", "description": "Overall alignment score from 0 to 100"},
        "matchedKeywords": {"type": "array", "items": _KEYWORD_ITEM_SCHEMA},
        "missingKeywords": {"type": "array", "items": _KEYWORD_ITEM_SCHEMA},
        "weaklyEmphasizedKeywords": {"type": "array", "items": _WEAK_KEYWORD_ITEM_SCHEMA},
        "summary": {"type": "string"},
    },
    "required": ["matchScore", "matchedKeywords", "missingKeywords", "weaklyEmphasizedKeywords", "summary"],
}

_REWRITTEN_BULLET_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "original": {"type": "string"},
        "rewritten": {"type": "string"},
        "hasPlaceholderMetric": {"type": "boolean"},
        "changeNotes": {"type": "string"},
    },
    "required": ["id", "original", "rewritten", "hasPlaceholderMetric", "changeNotes"],
}

GEMINI_BULLET_REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "rewrites": {"type": "array", "items": _REWRITTEN_BULLET_SCHEMA},
    },
    "required": ["rewrites"],
}
