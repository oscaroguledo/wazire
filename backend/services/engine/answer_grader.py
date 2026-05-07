#!/usr/bin/env python3
"""
Professional Question Answering System using Groq AI

Inherits from GroqEngineBase for shared client initialisation.
Groq HTTP calls are wrapped in asyncio.to_thread so the event loop
is never blocked. Retry logic (3 attempts: 1s, 2s, 4s) is applied
on 429 / transient errors.
"""

import asyncio
import base64
import json
import os
import sys
import csv
import random
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Union, Optional

from models.academic.question import AnswerEnum
from .base import GroqEngineBase

# Make pandas optional so the module can be imported in environments
# where pandas is not installed (e.g. minimal API containers).
try:
    import pandas as pd
except Exception:
    pd = None

# Retry configuration
_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]  # seconds


class QuestionAnswerer(GroqEngineBase):
    """Professional AI-powered question answering system.

    Inherits Groq client initialisation from GroqEngineBase.
    All Groq HTTP calls are non-blocking (asyncio.to_thread).
    """

    def _get_image_b64(self, row: Dict[str, Any], key: str) -> Union[str, None]:
        """Return a base64 image string from row[key].

        Accepts either a pre-encoded base64 string or a file path (legacy).
        Callers should prefer passing base64 strings directly.
        """
        value = row.get(key)
        if not value:
            return None
        # Already a base64 string (no path separators, not a file)
        if isinstance(value, str) and os.path.sep not in value and not os.path.exists(value):
            return value
        # Fallback: treat as file path
        if os.path.exists(str(value)):
            with open(value, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        return None

    async def answer_question(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Answer a single question with AI-powered freestyle detection.

        Non-blocking: Groq HTTP call is wrapped in asyncio.to_thread.
        Retries up to 3 times on 429 / transient errors (1s, 2s, 4s delays).

        Args:
            row: Question data dictionary with 'id', 'question', 'topic' keys,
                 optionally 'qtype', 'options'.

        Returns:
            Dictionary with answer, confidence, key_points, word_count.
        """
        qtype = row.get("qtype", "theory")
        options = row.get("options", [])

        # Normalize options — handle pandas NaN, JSON strings, etc.
        if pd is not None:
            try:
                if pd.isna(options):
                    options = []
            except Exception:
                pass
        else:
            if isinstance(options, float) and options != options:
                options = []

        if isinstance(options, str):
            s = options.strip()
            if not s:
                options = []
            else:
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, (list, dict)):
                        options = parsed
                    else:
                        options = s
                except Exception:
                    options = s
        elif not isinstance(options, (list, dict)):
            options = []

        row["options"] = options

        is_multiple_choice = (qtype == "multiple_choice") or (options and len(options) > 0)

        if is_multiple_choice and options:
            return await self._answer_multiple_choice(row)
        else:
            return await self._answer_theory_question(row)

    async def _answer_multiple_choice(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Answer a multiple choice question by selecting the correct option."""
        if self.client is None:
            return {"answer": "Error: Groq client not available", "confidence": 0.0, "key_points": [], "word_count": 0}

        question_text = row["question"]
        options = row.get("options", [])
        topic = row.get("topic", "")

        parsed_options = []
        if isinstance(options, list):
            for i, option in enumerate(options):
                if isinstance(option, dict):
                    label = str(option.get("label", chr(97 + i))).lower()
                    text = str(option.get("text", "")).strip()
                    if text:
                        parsed_options.append({"label": label, "text": text})
                elif isinstance(option, str):
                    parsed_options.append({"label": chr(97 + i), "text": option.strip()})
        elif isinstance(options, dict):
            for label, text in options.items():
                parsed_options.append({"label": str(label).lower(), "text": str(text).strip()})

        if not parsed_options:
            return {"answer": "Error: No valid options provided", "confidence": 0.0, "key_points": [], "word_count": 0}

        content = [
            {"type": "text", "text": f"You are an expert {topic} educator. Analyze the following multiple choice question and select the correct answer."},
            {"type": "text", "text": f"QUESTION: {question_text}"},
            {"type": "text", "text": "OPTIONS:\n" + "\n".join([f"{opt['label'].upper()}. {opt['text']}" for opt in parsed_options])},
        ]

        q_img = self._get_image_b64(row, "question_image_b64")
        if q_img:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{q_img}"}})

        content.append({"type": "text", "text": f"""Analyze this {topic} multiple choice question and select the correct answer.

Instructions:
- Carefully read the question and all options
- Consider the context and subject matter
- Select the single best answer
- Return ONLY the letter of the correct answer (a, b, c, d, etc.)

Return ONLY a JSON object with:
- answer: string (single lowercase letter: a, b, c, d, etc.)
- confidence: float (0.0-1.0, confidence in your selection)
- key_points: array of strings (brief explanation for your choice)
- word_count: integer (always 0 for multiple choice)

JSON format example: {{"answer": "b", "confidence": 0.95, "key_points": ["Option B is correct because...", "Other options are incorrect because..."], "word_count": 0}}
"""})

        messages = [{"role": "user", "content": content}]
        last_error = "Unknown error"

        for retry_idx, backoff in enumerate(zip(range(_MAX_RETRIES), _RETRY_DELAYS)):
            idx, delay = backoff
            try:
                chat = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                res = json.loads(chat.choices[0].message.content)
                answer_letter = res.get("answer", "").lower().strip()
                valid_labels = [opt["label"] for opt in parsed_options]
                if answer_letter not in valid_labels:
                    answer_letter = valid_labels[0] if valid_labels else "a"
                try:
                    AnswerEnum(answer_letter)
                except ValueError:
                    answer_letter = valid_labels[0] if valid_labels else "a"
                return {
                    "answer": answer_letter,
                    "confidence": max(Decimal("0.00"), min(Decimal("1.00"), Decimal(str(res.get("confidence", "0.0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))),
                    "key_points": res.get("key_points", []),
                    "word_count": 0,
                }
            except json.JSONDecodeError as e:
                return {"answer": "Error: Invalid JSON response", "confidence": Decimal("0.00"), "key_points": [], "word_count": 0}
            except Exception as e:
                last_error = str(e)
                if "invalid_api_key" in last_error.lower() or "authentication" in last_error.lower():
                    break
                if idx < _MAX_RETRIES - 1:
                    await asyncio.sleep(delay)

        return {"answer": f"Error: {last_error}", "confidence": 0.0, "key_points": [], "word_count": 0}

    async def _answer_theory_question(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Answer a theory question with AI-powered freestyle detection."""
        if self.client is None:
            return {"answer": "Error: Groq client not available", "confidence": 0.0, "key_points": [], "word_count": 0}

        question_text = row["question"]
        content = [
            {"type": "text", "text": f"You are an expert {row['topic']} educator. Provide a comprehensive and accurate answer to the following question."},
            {"type": "text", "text": f"QUESTION: {question_text}"},
        ]

        q_img = self._get_image_b64(row, "question_image_b64")
        if q_img:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{q_img}"}})

        content.append({"type": "text", "text": f"""Provide a concise answer to the {row['topic']} question following these guidelines:
- Focus: Direct answer to the question
- Style: Professional and educational
- Clarity: Use clear, accessible language
- Word Count: Respect any word limits mentioned in the question
- Response Type: Determine if this requires a creative/freestyle response based on the question content. If the question asks for creative writing, personal expression, opinions, artistic work, essays, compositions, OR if the subject is English/Language Arts/Literature/Writing, return "freestyle" as the answer and explain why in the key points. Otherwise, provide a structured answer.

Return ONLY a JSON object with:
- answer: string (answer following the guidelines, or "freestyle" if creative question)
- confidence: float (0.0-1.0, confidence in the answer)
- key_points: array of strings (2-3 main points for structured answers, or explanation of why freestyle is needed)
- word_count: integer (actual word count of the answer, or 0 for freestyle)

JSON format examples:
For structured: {{"answer": "Your answer here...", "confidence": 0.95, "key_points": ["Point 1", "Point 2"], "word_count": 45}}
For freestyle: {{"answer": "freestyle", "confidence": 1.0, "key_points": ["Creative expression required", "No single correct answer", "Graded on expression and effort"], "word_count": 0}}
"""})

        messages = [{"role": "user", "content": content}]
        last_error = "Unknown error"

        for retry_idx, backoff in enumerate(zip(range(_MAX_RETRIES), _RETRY_DELAYS)):
            idx, delay = backoff
            try:
                chat = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                res = json.loads(chat.choices[0].message.content)
                return {
                    "answer": res.get("answer", "No answer provided"),
                    "confidence": max(Decimal("0.00"), min(Decimal("1.00"), Decimal(str(res.get("confidence", "0.0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))),
                    "key_points": res.get("key_points", []),
                    "word_count": res.get("word_count", len(res.get("answer", "").split())),
                }
            except json.JSONDecodeError:
                return {"answer": "Error: Invalid JSON response", "confidence": Decimal("0.00"), "key_points": [], "word_count": 0}
            except Exception as e:
                last_error = str(e)
                if "invalid_api_key" in last_error.lower() or "authentication" in last_error.lower():
                    break
                if idx < _MAX_RETRIES - 1:
                    await asyncio.sleep(delay)

        return {"answer": f"Error: {last_error}", "confidence": Decimal("0.00"), "key_points": [], "word_count": 0}

    async def process(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a list of question dicts and generate answers.

        Args:
            questions: List of question dictionaries.

        Returns:
            List of merged dicts (original fields + answer fields).
        """
        print(f"🚀 Processing {len(questions)} questions...")
        results = []
        for i, question in enumerate(questions, 1):
            print(f"📝 Processing question {i}/{len(questions)}: {question.get('id', 'Unknown')}")
            result = await self.answer_question(question)
            results.append({**question, **result})
        return results


# ---------------------------------------------------------------------------
# CSV utilities (unchanged public API)
# ---------------------------------------------------------------------------

def process_csv_to_dict_list(csv_file: str) -> List[Dict[str, Any]]:
    """Convert CSV file to list of dictionaries with proper error handling."""
    if pd is not None:
        try:
            df = pd.read_csv(csv_file)
            return df.to_dict("records")
        except FileNotFoundError:
            print(f"❌ Error: File '{csv_file}' not found.")
            return []
        except Exception as e:
            print(f"❌ Error reading '{csv_file}' with pandas: {e}")
            return []
    else:
        try:
            with open(csv_file, newline='', encoding='utf-8') as fh:
                reader = csv.DictReader(fh)
                return [dict(row) for row in reader]
        except FileNotFoundError:
            print(f"❌ Error: File '{csv_file}' not found.")
            return []
        except Exception as e:
            print(f"❌ Error reading '{csv_file}': {e}")
            return []


def main() -> None:
    """Main function with proper argument parsing and processing."""
    input_file = "questions.csv"
    questions = process_csv_to_dict_list(input_file)
    if not questions:
        sys.exit(1)

    answerer = QuestionAnswerer()
    results = asyncio.run(answerer.process(questions))
    if not results:
        sys.exit(1)

    output_cols = ["id", "question", "topic", "answer", "confidence", "key_points", "word_count"]

    if pd is not None:
        try:
            df_results = pd.DataFrame(results)
            df_results[output_cols].to_csv("answer.csv", index=False)
        except Exception as e:
            print(f"❌ Error writing results with pandas: {e}")
            sys.exit(1)
    else:
        try:
            with open("answer.csv", "w", newline='', encoding='utf-8') as fh:
                writer = csv.DictWriter(fh, fieldnames=output_cols)
                writer.writeheader()
                for row in results:
                    out = {k: row.get(k, '') for k in output_cols}
                    if isinstance(out.get('key_points'), (list, tuple)):
                        out['key_points'] = json.dumps(out['key_points'])
                    writer.writerow(out)
        except Exception as e:
            print(f"❌ Error writing results to CSV: {e}")
            sys.exit(1)

    print(f"✅ Done! Processed {len(results)} questions. Saved to answer.csv")


if __name__ == "__main__":
    main()
