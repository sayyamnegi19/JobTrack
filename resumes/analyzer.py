"""
ATS scoring with Gemini structured output.

This module owns:
  - the response schema (Pydantic) and the scoring rubric prompt
  - truncation / token guards
  - one API call per analysis
  - response validation and normalization
  - mapping SDK failures to user-facing AIAnalysisError messages

The public entry point is `analyze_resume(resume_text, job_description=None)`,
which returns a plain dict the view can map directly onto a ResumeAnalysis
row. It does not touch the database itself.
"""

import logging
from typing import Literal

from django.conf import settings
from google.genai import errors
from pydantic import BaseModel, Field

from .ai_client import AIAnalysisError, get_client
from .similarity import semantic_similarity

logger = logging.getLogger(__name__)

# Cost/quality knobs
MAX_OUTPUT_TOKENS = 2048
TEMPERATURE = 0.2
THINKING_LEVEL = "low"

# Storage guards (a chatty model must not bloat the JSON column)
MAX_KEYWORDS = 30
MAX_STRENGTHS = 10
MAX_IMPROVEMENTS = 10
MAX_TEXT_FIELD = 600


class CategoryScore(BaseModel):
    """One rubric category with its score and feedback."""

    key: str = Field(
        description="Stable identifier, e.g. 'keyword_match', 'formatting'."
    )
    label: str = Field(
        description="Human readable name, e.g. 'Keyword Match', 'ATS Formatting'."
    )
    score: int = Field(ge=0, le=100, description="0-100 score for this category.")
    feedback: str = Field(
        description="One or two sentences of specific, evidence-based feedback."
    )


class Improvement(BaseModel):
    """One actionable suggested edit, with a priority."""

    priority: Literal["high", "medium", "low"]
    suggestion: str = Field(
        description="A concrete, actionable change to make to the resume."
    )


class ATSResult(BaseModel):
    """The complete structured result returned by the model."""

    overall_score: int = Field(
        ge=0,
        le=100,
        description="Holistic ATS score, not a plain average of the categories.",
    )
    summary: str = Field(description="2-4 sentence overall assessment.")
    categories: list[CategoryScore] = Field(
        description="Exactly five category scores as defined by the rubric."
    )
    matched_keywords: list[str] = Field(
        description="Keywords/skills from the job description present in the resume."
    )
    missing_keywords: list[str] = Field(
        description="Important keywords/skills from the job description missing from the resume."
    )
    strengths: list[str] = Field(description="Specific things the resume does well.")
    improvements: list[Improvement] = Field(
        description="Prioritized, concrete suggestions, highest priority first."
    )


SYSTEM_INSTRUCTION = (
    "You are an expert ATS (Applicant Tracking System) evaluator and technical "
    "recruiter. You score resumes exactly as a real ATS and recruiter screening "
    "pipeline would: parsing structure, matching keywords, and judging the impact "
    "of experience. You are strict, specific and evidence-based."
)

RUBRIC = """Score the resume on these five categories (each 0-100):

1. keyword_match — How well the resume's skills, tools and terminology match the job
   description. In general mode (no job description), judge keyword strength against
   the roles the resume targets.
2. formatting — ATS parse-ability: standard section headings, simple single-column
   layout, consistent date formats, no reliance on tables/graphics/text boxes for meaning.
3. skills_sections — Presence and quality of skills, education, certifications and
   contact info (email, phone, LinkedIn/GitHub where relevant).
4. experience_impact — Quantified achievements, strong action verbs, relevance and
   career progression. Reward numbers ("reduced latency 40%"), not duties
   ("responsible for...").
5. readability — Length, bullet structure, clarity, absence of fluff and redundancy.

Calibration (use the full range; do not inflate):
- 90-100: exceptional; would pass almost any ATS and impress a recruiter immediately.
- 70-89: strong; solid match with a few clear improvement areas.
- 50-69: average; notable gaps in keywords, structure or impact.
- Below 50: weak; major problems that would cause rejection or parsing failures.

Rules:
- Ground every claim in the resume text. Never invent experience or qualifications.
- matched_keywords: lowercase keywords/skills from the job description that ARE in
  the resume.
- missing_keywords: important keywords/skills from the job description that are NOT
  in the resume. In general mode, list keywords worth adding for the roles the resume
  targets.
- improvements: concrete, actionable edits, highest priority first.
- overall_score is your holistic judgment, not a plain average of the categories.
- Be honest: an inflated score does the candidate no favors."""


def _truncate(text, limit):
    """Cut text to the token-cost guard, marking that it was cut."""
    if text is None or len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def build_prompt(resume_text, job_description=None, similarity=None):
    """Assemble the rubric, mode instructions, optional similarity, and inputs."""
    parts = [RUBRIC]

    if job_description:
        parts.append(
            "MODE: job match. Compare the resume against the job description below. "
            "The keyword lists must be derived from this job description."
        )

        if similarity is not None:
            parts.append(
                "Supplementary signal (computed separately, not by you): the cosine "
                "semantic similarity between the resume and the job description is "
                f"{similarity:.2f} (0 = unrelated, 1 = identical meaning). Consider "
                "it as one supporting signal when judging keyword_match, but do not "
                "let it override the evidence in the text."
            )

        parts.append(f"<job_description>\n{job_description}\n</job_description>")
    else:
        parts.append(
            "MODE: general analysis. No job description was provided. Infer the roles "
            "and industries the resume targets, then judge keyword strength, impact "
            "and structure against general ATS best practices for those roles. Put "
            "keywords worth adding for those target roles in missing_keywords."
        )

    parts.append(f"<resume>\n{resume_text}\n</resume>")
    parts.append("Return only the JSON object that matches the required schema.")

    return "\n\n".join(parts)


def _clamp(score):
    """Belt-and-suspenders: schema validates, but this is persisted data."""
    return max(0, min(100, int(score)))


def _shorten(text, limit):
    """Collapse whitespace and cap length."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _clean_keywords(keywords):
    """Lowercase, strip punctuation, dedupe, and cap a keyword list."""
    seen = set()
    cleaned = []

    for keyword in keywords:
        keyword = " ".join(str(keyword).split()).lower().strip(" .,;:-")
        if keyword and keyword not in seen:
            seen.add(keyword)
            cleaned.append(keyword)

    return cleaned[:MAX_KEYWORDS]


def _normalize(parsed: ATSResult):
    """Turn the validated model into the exact dict we persist."""
    data = parsed.model_dump()

    data["overall_score"] = _clamp(data["overall_score"])
    data["summary"] = _shorten(data["summary"], MAX_TEXT_FIELD)

    for category in data["categories"]:
        category["score"] = _clamp(category["score"])
        category["label"] = _shorten(category["label"], 60)
        category["feedback"] = _shorten(category["feedback"], MAX_TEXT_FIELD)

    data["matched_keywords"] = _clean_keywords(data["matched_keywords"])
    data["missing_keywords"] = _clean_keywords(data["missing_keywords"])

    data["strengths"] = [
        _shorten(item, MAX_TEXT_FIELD) for item in data["strengths"][:MAX_STRENGTHS]
    ]

    data["improvements"] = [
        {
            "priority": item["priority"],
            "suggestion": _shorten(item["suggestion"], MAX_TEXT_FIELD),
        }
        for item in data["improvements"][:MAX_IMPROVEMENTS]
    ]

    return data


def _map_client_error(exc):
    """Translate an SDK 4xx error into a human message."""
    code = getattr(exc, "code", None)

    if code == 429:
        return AIAnalysisError(
            "The AI service is at its limit right now. Please try again in a minute."
        )
    if code in (401, 403):
        return AIAnalysisError(
            "The AI service rejected our API key. Please check GEMINI_API_KEY in .env."
        )
    if code == 400:
        return AIAnalysisError(
            "The AI service rejected this request. If it persists, check GEMINI_MODEL."
        )

    return AIAnalysisError(
        "The AI service returned an unexpected error. Please try again."
    )


def analyze_resume(resume_text, job_description=None):
    """
    Score a resume, optionally against a job description.

    Returns a dict:
        {
            "mode": "JOB_MATCH" | "GENERAL",
            "overall_score": int,
            "result": {...},          # full normalized AI payload (JSON-safe)
            "ai_model": str,
            "prompt_tokens": int | None,
            "output_tokens": int | None,
            "semantic_similarity": float | None,
        }

    Raises AIAnalysisError with a user-safe message on any failure.
    """
    resume_text = (resume_text or "").strip()
    job_description = (job_description or "").strip() or None

    if not resume_text:
        raise AIAnalysisError("There is no resume text to analyze.")

    mode = "JOB_MATCH" if job_description else "GENERAL"

    resume_input = _truncate(resume_text, settings.ATS_MAX_RESUME_CHARS)
    job_input = (
        _truncate(job_description, settings.ATS_MAX_JD_CHARS)
        if job_description
        else None
    )

    # Fail fast on missing configuration before doing any work.
    client = get_client()

    # Supplementary signal; never fatal, returns None on failure.
    similarity = semantic_similarity(resume_input, job_input) if job_input else None

    prompt = build_prompt(resume_input, job_input, similarity)

    try:
        interaction = client.interactions.create(
            model=settings.GEMINI_MODEL,
            input=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": ATSResult.model_json_schema(),
            },
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "thinking_level": THINKING_LEVEL,
            },
        )
    except errors.ClientError as exc:
        raise _map_client_error(exc) from exc
    except errors.ServerError as exc:
        raise AIAnalysisError(
            "The AI service is temporarily unavailable. Please try again."
        ) from exc
    except errors.APIError as exc:
        raise AIAnalysisError(
            "The AI service returned an unexpected error. Please try again."
        ) from exc

    raw = interaction.output_text or ""

    if not raw.strip():
        raise AIAnalysisError("The AI returned an empty response. Please try again.")

    try:
        parsed = ATSResult.model_validate_json(raw)
    except Exception as exc:
        logger.error("AI returned invalid JSON: %s", raw[:500])
        raise AIAnalysisError(
            "The AI returned an unexpected result. Please try again."
        ) from exc

    result = _normalize(parsed)

    usage = getattr(interaction, "usage", None)

    return {
        "mode": mode,
        "overall_score": result["overall_score"],
        "result": result,
        "ai_model": settings.GEMINI_MODEL,
        "prompt_tokens": getattr(usage, "total_input_tokens", None) if usage else None,
        "output_tokens": getattr(usage, "total_output_tokens", None) if usage else None,
        "semantic_similarity": similarity,
    }
