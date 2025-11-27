# backend/app.py

import os
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

import google.generativeai as genai

# ------------------------------------------------------
# Load Environment Variables
# ------------------------------------------------------
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing in .env")

# ------------------------------------------------------
# Configure Gemini (v1 API, SDK 0.8.5)
# ------------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={
        "temperature": 0,
        "max_output_tokens": 2048,
        # "response_mime_type": "application/json" # Lite model might not support this
    }
)

MANDATORY_HASHTAGS = [
    "#snssquare",
    "#snsihub",
    "#snsdesignthinking",
    "#designthinkers"
]

# ------------------------------------------------------
# Request / Response Models
# ------------------------------------------------------
class AnalyzeRequest(BaseModel):
    platform: str
    content: str
    title: Optional[str] = None
    hashtags: Optional[List[str]] = None
    geo: Optional[str] = None
    niche: Optional[str] = None
    target_audience: Optional[str] = None


class AnalyzeResponse(BaseModel):
    raw_json: dict

# ------------------------------------------------------
# Helper Functions
# ------------------------------------------------------
def enforce_mandatory_hashtags(data: dict) -> dict:
    """Ensure mandatory hashtags are included in final output & suggestions."""

    data.setdefault("final_output", {})
    data.setdefault("hashtags", {})

    final_pack = data["final_output"].get("final_hashtag_pack", [])
    suggested = data["hashtags"].get("suggested_replacements", [])

    for tag in MANDATORY_HASHTAGS:
        if tag not in final_pack:
            final_pack.append(tag)

        if tag not in suggested:
            suggested.append(tag)

    data["final_output"]["final_hashtag_pack"] = final_pack
    data["hashtags"]["suggested_replacements"] = suggested

    return data


def build_prompt(req: AnalyzeRequest):
    return f"""
You are a strict content QA Agent.

Mandatory hashtags:
{", ".join(MANDATORY_HASHTAGS)}

Analyze content below and return ONLY VALID JSON:

Platform: {req.platform}
Title: {req.title}
Content: {req.content}
Existing Hashtags: {req.hashtags}
Geo: {req.geo}
Niche: {req.niche}
Target Audience: {req.target_audience}

Return JSON with:
- overall_score (0-100)
- scores_breakdown:
    - quality_score (0-100)
    - seo_score (0-100)
    - engagement_score (0-100)
    - structure_score (0-100)
- issues_found (list of strings)
- content_checks:
    - grammar_summary
    - tone_summary
    - cta_status
- hashtags:
    - trending (list of trending hashtag suggestions relevant to {req.niche or 'the content'})
    - suggested_replacements (list of hashtag suggestions)
- improvements:
    - cta_variants (list of call-to-action suggestions)
- final_output:
    - optimized_title
    - optimized_content
    - final_hashtag_pack (list including mandatory hashtags)
"""


# ------------------------------------------------------
# FastAPI App Setup
# ------------------------------------------------------
app = FastAPI(title="SNS QA Agent - Gemini 1.5 Flash")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent

@app.get("/")
async def read_root():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/script.js")
async def read_script():
    return FileResponse(BASE_DIR / "script.js")

@app.get("/styles.css")
async def read_styles():
    return FileResponse(BASE_DIR / "styles.css")

@app.get("/logo.png")
async def read_logo():
    return FileResponse(BASE_DIR / "logo.png")

# ------------------------------------------------------
# Analyze Endpoint
# ------------------------------------------------------
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_content(payload: AnalyzeRequest):
    try:
        prompt = build_prompt(payload)

        response = model.generate_content(prompt)

        # NEW v1 API returns clean JSON directly
        raw = response.text

        # Clean potential markdown code blocks since we disabled native JSON mode
        import re
        raw = raw.strip()
        raw = re.sub(r"^```json", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"^```", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()

        parsed = json.loads(raw)

        # Add mandatory hashtags
        parsed = enforce_mandatory_hashtags(parsed)

        return AnalyzeResponse(raw_json=parsed)

    except json.JSONDecodeError:
        raise HTTPException(500, "Model returned invalid JSON")
    except Exception as e:
        raise HTTPException(500, f"Model error: {str(e)}")


# For Vercel Python Runtime
handler = app
