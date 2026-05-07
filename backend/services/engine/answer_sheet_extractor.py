"""AnswerSheetParser — extracts student answers from scanned answer sheet images.

Given base64 page images of a student's answer sheet and the list of questions
for the exam, the vision model reads each page and returns:
  { question_number: answer_text_or_option_letter }

The caller then maps question numbers → question IDs and feeds the result
into the existing SubmissionService._grade_answers() pipeline.
"""

import json
from typing import List, Dict, Any, Optional

from .base import GroqEngineBase


class AnswerSheetParser(GroqEngineBase):
    """Reads scanned answer sheet pages and extracts per-question answers."""

    def _parse_chunk(
        self,
        pages: List[str],
        question_index: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Send a chunk of pages to Groq and return {question_number: answer}."""

        # Build a compact question reference so the model knows what to look for
        q_ref = "\n".join(
            f"Q{q['number']} ({q['qtype']})"
            + (f" options: {', '.join(o['label'] for o in q['options'])}" if q.get("options") else "")
            for q in question_index
        )

        content = [
            {
                "type": "text",
                "text": (
                    "You are reading a student's handwritten or printed answer sheet. "
                    "Extract the student's answer for each question number listed below.\n\n"
                    f"QUESTIONS ON THIS EXAM:\n{q_ref}\n\n"
                    "Rules:\n"
                    "- For multiple_choice questions return only the selected option letter (e.g. 'b').\n"
                    "- For theory questions return the full written answer text.\n"
                    "- If a question has no visible answer, return null.\n"
                    "- Match answers to question numbers exactly as they appear on the sheet."
                ),
            }
        ]

        for b64 in pages:
            content.append(self.build_image_block(b64))

        content.append({
            "type": "text",
            "text": (
                "Return ONLY a JSON object where each key is the question number string "
                "and the value is the student's answer string (or null if unanswered).\n"
                'Example: {"1": "b", "2": "The mitochondria is...", "3": null}'
            ),
        })

        try:
            chat = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            return json.loads(chat.choices[0].message.content)
        except Exception as e:
            print(f"AnswerSheetParser: error on chunk: {e}")
            return {}

    def parse(
        self,
        pages: List[str],
        question_index: List[Dict[str, Any]],
    ) -> Dict[str, Optional[str]]:
        """Parse all answer sheet pages and return {question_number: answer}.

        Args:
            pages: base64 image strings of the answer sheet (one per page)
            question_index: list of dicts with keys: number, qtype, options (for MCQ)

        Returns:
            Dict mapping question number string → answer string (or None)
        """
        if self.client is None:
            raise RuntimeError("Groq client not available. Set GROQ_API_KEYS or pass api_key.")

        merged: Dict[str, Optional[str]] = {}

        for i in range(0, len(pages), self.MAX_IMAGES_PER_REQUEST):
            chunk = pages[i: i + self.MAX_IMAGES_PER_REQUEST]
            result = self._parse_chunk(chunk, question_index)
            # Later chunks override earlier ones for the same question number
            merged.update(result)

        return merged
