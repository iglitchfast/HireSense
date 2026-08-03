import json
import os
from typing import Iterator, Type, TypeVar

import requests
from pydantic import BaseModel

GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_STREAM_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
)

T = TypeVar("T", bound=BaseModel)


def _get_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in environment (.env)")
    return api_key.strip()


def call_gemini_structured(
    system_prompt: str, user_prompt: str, gemini_schema: dict, response_model: Type[T]
) -> T:
    """
    Calls Gemini's REST API directly with the API key passed in the
    x-goog-api-key header. Google's newer "Authorization" API keys
    (format: AQ.Ab...) require this header — they are rejected with a 401
    ACCESS_TOKEN_TYPE_UNSUPPORTED error if passed as the older ?key=... query
    param, which only works with legacy "Standard" keys (format: AIzaSy...).
    See: https://ai.google.dev/gemini-api/docs/generate-content/api-key

    Forces structured JSON output matching gemini_schema (a minimal hand-written
    JSON schema — see schemas.py), then validates the result into response_model.
    """
    api_key = _get_api_key()
    url = GEMINI_ENDPOINT.format(model=GEMINI_MODEL)

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": gemini_schema,
            "temperature": 0.4,
        },
    }

    resp = requests.post(
        url,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        json=payload,
        timeout=60,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

    body = resp.json()
    try:
        raw_text = body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Gemini response shape: {json.dumps(body)[:500]}") from exc

    data = json.loads(raw_text)
    return response_model(**data)


def stream_gemini_text(system_prompt: str, user_prompt: str, gemini_schema: dict) -> Iterator[str]:
    """
    Calls Gemini's streamGenerateContent (SSE) endpoint and yields each text
    delta as it arrives, so the caller can forward partial output to a client
    in real time. Since responseMimeType is still application/json, the FULL
    accumulated text only becomes valid JSON once the stream completes — this
    generator yields raw text chunks for live display; the caller is
    responsible for accumulating + parsing the final JSON once the stream ends.
    """
    api_key = _get_api_key()
    url = GEMINI_STREAM_ENDPOINT.format(model=GEMINI_MODEL)

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": gemini_schema,
            "temperature": 0.4,
        },
    }

    with requests.post(
        url,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        json=payload,
        stream=True,
        timeout=120,
    ) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.startswith("data:"):
                continue
            data_str = raw_line[len("data:") :].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                chunk = json.loads(data_str)
                text_piece = chunk["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, json.JSONDecodeError):
                continue
            if text_piece:
                yield text_piece
