"""
Shared Gemini client and the single AI error type.

The client lives here (instead of inside analyzer.py) to avoid a circular
import: analyzer imports similarity, and similarity needs the client too.
Everything AI-related imports from this module; nothing imports upward.
"""

from django.conf import settings
from google import genai


class AIAnalysisError(Exception):
    """User-facing error raised when AI analysis cannot complete."""


def get_client():
    """
    Build a Gemini client from Django settings.

    Raises AIAnalysisError when no API key is configured so callers can show
    a clear setup message instead of a confusing SDK error.
    """
    if not settings.GEMINI_API_KEY:
        raise AIAnalysisError(
            "AI analysis is not configured. Add GEMINI_API_KEY to your .env file."
        )

    return genai.Client(api_key=settings.GEMINI_API_KEY)
