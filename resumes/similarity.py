"""
Semantic similarity between two texts using Gemini embeddings (free tier).

This is a supplementary quantitative signal for the ATS analysis: how close
in meaning the resume is to the job description (0 = unrelated, 1 = nearly
identical meaning).

Design rule: failures here are NON-FATAL. If embeddings are unavailable or
the call fails for any reason, the main LLM analysis still runs — it just
proceeds without this extra signal.
"""

import logging
import math

from django.conf import settings
from google.genai import types

from .ai_client import AIAnalysisError, get_client

logger = logging.getLogger(__name__)

# gemini-embedding-2 accepts at most 8192 tokens per request.
# 12k English characters is roughly 3-4k tokens, comfortably inside that.
MAX_EMBED_CHARS = 12000

# Documented task prefix for gemini-embedding-2 (symmetric similarity task).
# It replaces the old task_type parameter and must be used on both inputs.
TASK_PREFIX = "task: sentence similarity | query: "

# 768 dims (instead of the 3072 default) keeps the payload small; the docs
# show almost identical quality, and the model auto-normalizes the vector.
OUTPUT_DIMENSIONS = 768


def _cosine_similarity(vector_a, vector_b):
    """
    Cosine similarity in pure Python — just two vectors, no numpy needed.

    Returns a value in [-1, 1] (in practice ~0..1 for natural text) or None
    when either vector is degenerate.
    """
    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return None

    return dot / (norm_a * norm_b)


def semantic_similarity(resume_text, job_description):
    """
    Embed both texts and return their cosine similarity, or None.

    gemini-embedding-2 returns ONE aggregated embedding when given a plain
    list of strings, so each text is wrapped in its own Content object to
    get two separate vectors.
    """
    if not resume_text or not job_description:
        return None

    try:
        client = get_client()

        result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_text(
                            text=TASK_PREFIX + resume_text[:MAX_EMBED_CHARS]
                        )
                    ]
                ),
                types.Content(
                    parts=[
                        types.Part.from_text(
                            text=TASK_PREFIX + job_description[:MAX_EMBED_CHARS]
                        )
                    ]
                ),
            ],
            config=types.EmbedContentConfig(output_dimensionality=OUTPUT_DIMENSIONS),
        )

        vectors = [embedding.values for embedding in result.embeddings]

        if len(vectors) != 2:
            logger.warning(
                "Expected 2 embeddings, got %s — skipping similarity.", len(vectors)
            )
            return None

        return _cosine_similarity(vectors[0], vectors[1])
    except AIAnalysisError:
        # Not configured — the analyzer raises its own clearer error later.
        return None
    except Exception:
        logger.exception("Embedding similarity failed; continuing without it.")
        return None
