# backend/app.py
import os
from dotenv import load_dotenv

load_dotenv()
import re
import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import google.generativeai as genai

# ---------- Config ----------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini if API key is available
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
else:
    model = None


# ---------- Models ----------

class AnalyzeRequest(BaseModel):
    platform: str              # "instagram" | "youtube" | "blog"
    content: str
    title: Optional[str] = None
    hashtags: Optional[List[str]] = None
    geo: Optional[str] = None
    niche: Optional[str] = None
    target_audience: Optional[str] = None


class AnalyzeResponse(BaseModel):
    raw_json: dict


# ---------- Constants ----------

MANDATORY_HASHTAGS = ["#snssquare", "#snsihub", "#snsdesignthinking", "#designthinkers"]


# ---------- Utils ----------

def clean_model_json(raw: str) -> dict:
    """
    Gemini sometimes returns JSON inside code fences.
    This will extract the JSON and parse it.
    """
    # Remove code fences like ```json ... ```
    raw = raw.strip()
    raw = re.sub(r"^```json", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"^```", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from model response: {e}\nRaw: {raw[:500]}...")


def add_mandatory_hashtags(hashtags: List[str]) -> List[str]:
    """
    Add mandatory hashtags to the list, avoiding duplicates.
    """
    existing = set(tag.lower() for tag in hashtags)
    result = list(hashtags)
    
    for tag in MANDATORY_HASHTAGS:
        if tag.lower() not in existing:
            result.append(tag)
    
    return result


def ensure_mandatory_in_response(response_data: dict) -> dict:
    """
    Ensure mandatory hashtags are included in the final hashtag pack.
    """
    if "final_output" not in response_data:
        response_data["final_output"] = {}
    
    final_pack = response_data["final_output"].get("final_hashtag_pack", [])
    response_data["final_output"]["final_hashtag_pack"] = add_mandatory_hashtags(final_pack)
    
    # Also update hashtags section
    if "hashtags" not in response_data:
        response_data["hashtags"] = {}
    
    suggested = response_data["hashtags"].get("suggested_replacements", [])
    response_data["hashtags"]["suggested_replacements"] = add_mandatory_hashtags(suggested)
    
    return response_data


def build_prompt(data: AnalyzeRequest) -> str:
    platform = data.platform.lower()
    platform_name = platform.capitalize()

    existing_hashtags = ", ".join(data.hashtags or []) if data.hashtags else "None"
    mandatory_tags = ", ".join(MANDATORY_HASHTAGS)

    # This prompt is aligned with your PDF spec
    prompt = f"""
You are a strict social media + blog QA Agent.

YOUR JOB:
Check the quality of {platform_name} content (Instagram / YouTube / Blog), review hashtags, and suggest better + trending hashtags before publishing.

IMPORTANT: The following hashtags are MANDATORY and must be included in all final hashtag packs:
{mandatory_tags}

INPUT DATA:
- Platform: {platform_name}
- Title: {data.title or "N/A"}
- Content:
{data.content}

- Existing hashtags: {existing_hashtags}
- Geo: {data.geo or "N/A"}
- Niche: {data.niche or "N/A"}
- Target audience: {data.target_audience or "N/A"}

REQUIREMENTS:

1. Content Quality Checks
- Grammar and spelling inspection
- Tone consistency check
- Clarity and readability scoring (0-100)
- Relevance to target audience (0-100)
- Engagement score prediction (0-100)
- Clickbait risk check (low/medium/high)
- Call to Action check (present / missing / weak)

2. Platform-Specific Validation
For INSTAGRAM:
- Caption length check and feedback
- Emoji usage check
- Engagement keywords check
- Hashtag quantity check (<= 30)
- Line spacing and structure feedback

For YOUTUBE:
- Title effectiveness
- Description keyword usage
- Thumbnail text suggestion
- Chapters suggestions
- SEO keywords check
- Community guidelines risk notes (if any)

For BLOG:
- Title quality score
- Keyword density (approx)
- Headings structure (H1/H2/H3) feedback
- Internal linking suggestions
- Meta description suggestions

3. Hashtag Review
- Validate existing hashtags
- Detect banned / shadowban-risk hashtags (if suspect)
- Identify irrelevant hashtags
- Suggest better replacements

4. Trending Hashtags Suggestions
- Platform-specific trending hashtag suggestions
- Geo-based tags (if possible from context)
- Niche-based tags
- Competition level per hashtag: low / medium / high

5. Content Improvement Suggestions
- Rewrite weak sentences
- Generate alternate caption/title versions (2-3)
- Create short CTA variations (3-5)

6. Final Output Summary
- Overall score: 0 to 100
- Breakdown: quality_score, seo_score, engagement_score, structure_score
- Issues found (list)
- Fix suggestions (list)
- Final approved version with:
  - optimized_title
  - optimized_content (ready to publish)
  - validated_hashtags (final pack)

VERY IMPORTANT:
Return a SINGLE VALID JSON object with the following schema (no extra text):

{{
  "overall_score": 0-100,
  "scores_breakdown": {{
    "quality_score": 0-100,
    "seo_score": 0-100,
    "engagement_score": 0-100,
    "structure_score": 0-100
  }},
  "platform": "{platform_name}",
  "issues_found": [
    "string"
  ],
  "content_checks": {{
    "grammar_summary": "string",
    "tone_summary": "string",
    "readability_score": 0-100,
    "relevance_score": 0-100,
    "engagement_prediction": 0-100,
    "clickbait_risk": "low|medium|high",
    "cta_status": "missing|weak|good"
  }},
  "platform_rules": {{
    "notes": "string with key points for this platform"
  }},
  "hashtags": {{
    "existing_valid": ["#tag"],
    "existing_irrelevant": ["#tag"],
    "banned_or_risky": ["#tag"],
    "suggested_replacements": ["#tag"],
    "trending": [
      {{
        "tag": "#example",
        "competition_level": "low|medium|high"
      }}
    ]
  }},
  "improvements": {{
    "weak_sentences_rewrite": ["string"],
    "alternate_titles": ["string"],
    "alternate_captions": ["string"],
    "cta_variants": ["string"]
  }},
  "final_output": {{
    "optimized_title": "string or null",
    "optimized_content": "string",
    "final_hashtag_pack": ["#tag"]
  }}
}}
"""
    return prompt


# ---------- FastAPI App ----------

app = FastAPI(title="Content QA Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_content(payload: AnalyzeRequest):
    try:
        if not model:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured on the server.")

        prompt = build_prompt(payload)

        response = model.generate_content(prompt)
        raw_text = response.text

        parsed = clean_model_json(raw_text)
        
        # Ensure mandatory hashtags are in the final response
        parsed = ensure_mandatory_in_response(parsed)

        return AnalyzeResponse(raw_json=parsed)

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model error: {e}")

# Vercel serverless function handler
handler = app
