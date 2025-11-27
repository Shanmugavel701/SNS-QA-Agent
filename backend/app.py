# backend/app.py

import os
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    print("WARNING: GEMINI_API_KEY missing in environment variables")
    # We do not raise RuntimeError here to allow the app to start
    # and fail only when the endpoint is called.

# ------------------------------------------------------
# Configure Gemini (v1 API)
# ------------------------------------------------------
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={
            "temperature": 0,
            "max_output_tokens": 4096,
        }
    )
else:
    model = None

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
- overall_score
- issues_found
- hashtag analysis
- improvements
- final_output (optimized title, optimized content, final_hashtag_pack)
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

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SNS QA Agent Backend is running"}

# ------------------------------------------------------
# Analyze Endpoint
# ------------------------------------------------------
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_content(payload: AnalyzeRequest):
    if not model:
        raise HTTPException(500, "GEMINI_API_KEY is not set. Please configure it in Vercel settings.")

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
