import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from core.config import get_settings

try:
    from groq import Groq
except Exception:
    Groq = None


class SimilarityGrader:
    """Grades student answers for MCQ, FITB, and theory questions.

    MCQ        -- compares student_answer to mcq_answer directly. No AI.
    FITB       -- compares student_answer to fitb_answer (case-insensitive). No AI.
    Theory     -- AI grades student_answer against question_text. No lecturer answer ever.

    All images must be passed as base64-encoded strings by the caller.
    Returns (score: Decimal 0.00-1.00, reason: str).
    """

    def __init__(self, model: str = "meta-llama/llama-4-scout-17b-16e-instruct", api_key: Optional[str] = None):
        self.model = model
        self.client = None
        if Groq is not None:
            key = api_key
            if not key:
                settings = get_settings()
                key = settings.GROQ_API_KEY
            if key:
                try:
                    self.client = Groq(api_key=key)
                except Exception as e:
                    print(f"SimilarityGrader: failed to create Groq client: {e}")

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
            Pass fitb_answer (correct text answer) and optional fitb_variations (list of acceptable answers).
            Case-insensitive exact match against fitb_answer or any variation. No AI. reason is always "-".

        Theory:
            Pass question_text. AI grades student_answer against the question only.
            question_image_b64 / student_image_b64 must be base64 strings if provided.
        """
        if question_type == "multiple_choice":
            if not mcq_answer:
                return Decimal("0.00"), "No MCQ answer provided"
            correct = student_answer.strip().lower() == mcq_answer.strip().lower()
            return (Decimal("1.00"), "-") if correct else (Decimal("0.00"), "-")

        if question_type == "fill_in_blanks":
            if not fitb_answer:
                return Decimal("0.00"), "No FITB answer provided"
            student_clean = student_answer.strip().lower()
            correct_clean = fitb_answer.strip().lower()
            # Check exact match against main answer
            if student_clean == correct_clean:
                return Decimal("1.00"), "-"
            # Check against acceptable variations
            if fitb_variations:
                for variation in fitb_variations:
                    if student_clean == variation.strip().lower():
                        return Decimal("1.00"), "-"
            return Decimal("0.00"), "-"

        if self.client is None:
            return Decimal("0.00"), "Error: Groq client not available. Set GROQ_API_KEY or pass api_key."

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

        try:
            chat = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            res = json.loads(chat.choices[0].message.content)
            score = Decimal(str(res.get("score", "0.0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            score = max(Decimal("0.00"), min(Decimal("1.00"), score))
            return score, res.get("reason", "No reason provided")
        except Exception as e:
            return Decimal("0.00"), f"Error: {str(e)}"
