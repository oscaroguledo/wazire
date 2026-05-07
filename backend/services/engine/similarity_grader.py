"""SimilarityGrader — grades student answers using Groq AI.

Inherits from GroqEngineBase for shared client initialisation.
Supports MCQ (direct compare), FITB (case-insensitive match), and
theory (AI-graded via a single async Groq call wrapped in asyncio.to_thread).
"""
from __future__ import annotations

import asyncio
import json
import random
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from .base import GroqEngineBase

# Retry configuration
_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]  # seconds


class SimilarityGrader(GroqEngineBase):
    """Grades student answers for MCQ, FITB, and theory questions.

    MCQ        -- compares student_answer to mcq_answer directly. No AI.
    FITB       -- compares student_answer to fitb_answer (case-insensitive). No AI.
    Theory     -- AI grades student_answer against question_text via a single
                  non-blocking Groq call (asyncio.to_thread).

    All images must be passed as base64-encoded strings by the caller.
    Returns (score: Decimal 0.00-1.00, reason: str).
    """

    async def grade(
        self,
        question_type: str,
        industry: str,
        student_answer: str,
        mcq_answer: Optional[str] = None,
        fitb_answer: Optional[str] = None,
        fitb_variations: Optional[list] = None,
        question_text: Optional[str] = None,
        rules: Optional[str] = None,
        question_image_b64: Optional[str] = None,
        student_image_b64: Optional[str] = None,
    ) -> Tuple[Decimal, str]:
        """Grade a single answer and return (score, reason).

        MCQ:
            Pass mcq_answer (correct option letter, already fetched by caller).
            Direct string comparison, no AI. reason is always "-".

        FITB (Fill-in-the-Blanks):
            Pass fitb_answer (correct text answer) and optional fitb_variations.
            Case-insensitive exact match. No AI. reason is always "-".

        Theory:
            Pass question_text. AI grades student_answer against the question only.
            question_image_b64 / student_image_b64 must be base64 strings if provided.
            The Groq HTTP call is wrapped in asyncio.to_thread so the event loop
            is never blocked.
        """
        # ------------------------------------------------------------------ #
        # MCQ — direct comparison, no AI                                       #
        # ------------------------------------------------------------------ #
        if question_type == "multiple_choice":
            if not mcq_answer:
                return Decimal("0.00"), "No MCQ answer provided"
            correct = student_answer.strip().lower() == mcq_answer.strip().lower()
            return (Decimal("1.00"), "-") if correct else (Decimal("0.00"), "-")

        # ------------------------------------------------------------------ #
        # FITB — case-insensitive exact match, no AI                           #
        # ------------------------------------------------------------------ #
        if question_type == "fill_in_blanks":
            if not fitb_answer:
                return Decimal("0.00"), "No FITB answer provided"
            student_clean = student_answer.strip().lower()
            if student_clean == fitb_answer.strip().lower():
                return Decimal("1.00"), "-"
            if fitb_variations:
                for variation in fitb_variations:
                    if student_clean == variation.strip().lower():
                        return Decimal("1.00"), "-"
            return Decimal("0.00"), "-"

        # ------------------------------------------------------------------ #
        # Theory — AI grading via Groq (non-blocking)                          #
        # ------------------------------------------------------------------ #
        if self.client is None:
            return Decimal("0.00"), "Error: Groq client not available. Set GROQ_API_KEYS or pass api_key."

        content = [
            {"type": "text", "text": f"You are an expert {industry} grader."},
            {"type": "text", "text": "QUESTION: " + (question_text or "(no question text provided)")},
        ]

        if question_image_b64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{question_image_b64}"}})

        content.append({"type": "text", "text": f"STUDENT ANSWER: {student_answer}"})

        if student_image_b64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{student_image_b64}"}})

        if rules:
            content.append({"type": "text", "text": f"GRADING RULES: {rules}"})

        content.append({"type": "text", "text": (
            "Grade the student answer based on accuracy, completeness, and depth of knowledge."
            " Apply any GRADING RULES provided.\n\n"
            "Return ONLY a JSON object with:\n"
            "- score: float (0.0-1.0, two decimal places)\n"
            "- reason: string (concise explanation of the grade)\n\n"
            'Examples:\n'
            '{"score": 0.85, "reason": "Correctly identified the main concept but missed one key detail."}\n'
            '{"score": 1.0, "reason": "Complete and accurate answer covering all key points."}\n'
            '{"score": 0.0, "reason": "Answer is entirely incorrect or irrelevant."}'
        )})

        messages = [{"role": "user", "content": content}]

        # Retry loop with exponential backoff
        last_error: str = "Unknown error"
        for attempt_num, delay in enumerate(zip(range(_MAX_RETRIES), _RETRY_DELAYS), start=1):
            retry_idx, backoff = delay
            try:
                # Wrap the synchronous Groq call in asyncio.to_thread so the
                # event loop is not blocked during the HTTP round-trip.
                chat = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                res = json.loads(chat.choices[0].message.content)
                score = Decimal(str(res.get("score", "0.0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                score = max(Decimal("0.00"), min(Decimal("1.00"), score))
                return score, res.get("reason", "No reason provided")

            except Exception as e:
                err_str = str(e)
                last_error = err_str
                # Do not retry on permanent errors (invalid API key, auth failures)
                if "invalid_api_key" in err_str.lower() or "authentication" in err_str.lower():
                    break
                # Retry on 429 (rate limit) or transient errors
                if retry_idx < _MAX_RETRIES - 1:
                    await asyncio.sleep(backoff)

        return Decimal("0.00"), f"Error: {last_error}"
