"""ExamParser — extracts structured questions from base64 exam page images using Groq vision.

Input:  list of base64 image strings (one per page, already stripped of the data URI prefix
        by the caller, or with it — both are handled)
Output: list of dicts matching QuestionCreate fields, ready for QuestionService.create()
"""

import json
from typing import List, Dict, Any, Optional

from .base import GroqEngineBase


class ExamParser(GroqEngineBase):
    """Parses exam paper images into structured question data."""

    def _parse_chunk(self, pages: List[str], industry: str, exam_id: Optional[str], mark_per_question: Optional[float]) -> List[Dict[str, Any]]:
        """Send a chunk of pages (≤ MAX_IMAGES_PER_REQUEST) to Groq and return extracted questions."""
        content = [
            {
                "type": "text",
                "text": (
                    f"You are an expert {industry} exam paper parser. "
                    "Extract every question from the exam paper pages provided. "
                    "For each question identify: its number, full text, type (multiple_choice, fill_in_blanks, or theory), "
                    "and for multiple choice questions all options with their labels (a, b, c, d...)."
                ),
            }
        ]

        for b64 in pages:
            content.append(self.build_image_block(b64))

        mark_hint = f" Use {mark_per_question} as the mark for each question." if mark_per_question else ""
        exam_hint = f' Use "{exam_id}" as the exam_id for all questions.' if exam_id else ""

        content.append({
            "type": "text",
            "text": (
                f"Extract all questions and return ONLY a JSON object with a single key 'questions' "
                f"containing a list. Each item must have:\n"
                f"- number: string (e.g. '1', '2a')\n"
                f"- text: string (full question text, use ____ or ______ for blanks in FITB)\n"
                f"- qtype: 'multiple_choice', 'fill_in_blanks', or 'theory'\n"
                f"- options: list of {{label, text}} dicts for MCQ, null for theory/FITB\n"
                f"- answer: string (correct option label e.g. 'b' for MCQ, or correct text for FITB) if visible, null otherwise\n"
                f"- mark: number (marks for this question, null if not shown){mark_hint}\n"
                f"- rules: string (any special grading instructions visible, null otherwise)\n"
                f"- industry: '{industry}'\n"
                f"{exam_hint}\n\n"
                f"FITB questions contain blanks (____) where students fill in words.\n"
                f"Example MCQ:\n"
                f'{{"questions": [{{'
                f'"number":"1","text":"What is...","qtype":"multiple_choice",'
                f'"options":[{{"label":"a","text":"Option A"}},{{"label":"b","text":"Option B"}}],'
                f'"answer":"a","mark":2,"rules":null,"industry":"{industry}"'
                f'}}]}}\n\n'
                f"Example FITB:\n"
                f'{{"questions": [{{'
                f'"number":"3","text":"The process of ____ converts sunlight into energy.",'
                f'"qtype":"fill_in_blanks","options":null,"answer":"photosynthesis",'
                f'"mark":2,"rules":null,"industry":"{industry}"'
                f'}}]}}'
            ),
        })

        try:
            chat = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            res = json.loads(chat.choices[0].message.content)
            return res.get("questions", [])
        except Exception as e:
            print(f"ExamParser: error parsing chunk: {e}")
            return []

    def parse(
        self,
        pages: List[str],
        industry: str,
        exam_id: Optional[str] = None,
        mark_per_question: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Parse all pages and return a flat list of question dicts.

        Pages are chunked to respect Groq's image-per-request limit.
        Results from all chunks are merged and question numbers de-duplicated.

        Args:
            pages: list of base64 image strings (data URI or raw)
            industry: subject area passed to the model for context
            exam_id: optional exam UUID string to embed in each question dict
            mark_per_question: fallback mark to use when not visible on the paper

        Returns:
            List of dicts with keys matching QuestionCreate fields.
        """
        if self.client is None:
            raise RuntimeError("Groq client not available. Set GROQ_API_KEY or pass api_key.")

        all_questions: List[Dict[str, Any]] = []

        # Chunk pages
        for i in range(0, len(pages), self.MAX_IMAGES_PER_REQUEST):
            chunk = pages[i: i + self.MAX_IMAGES_PER_REQUEST]
            questions = self._parse_chunk(chunk, industry, exam_id, mark_per_question)
            all_questions.extend(questions)

        # De-duplicate by question number (last occurrence wins if same number appears across chunks)
        seen: Dict[str, Dict[str, Any]] = {}
        for q in all_questions:
            num = str(q.get("number", "")).strip()
            if num:
                seen[num] = q

        return list(seen.values())
