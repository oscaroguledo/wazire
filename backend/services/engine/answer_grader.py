#!/usr/bin/env python3
"""
Professional Question Answering System using Groq AI

This module provides intelligent question answering capabilities with:
- Structured answers for academic subjects
- AI-powered freestyle detection
- Word limit handling
- CSV processing utilities
- Professional error handling
"""

import base64
import json
import os
import sys
import csv
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Union, Optional

from core.config import get_settings
from models.academic.question import AnswerEnum

# Make pandas optional so the module can be imported in environments
# where pandas is not installed (e.g. minimal API containers).
try:
    import pandas as pd
except Exception:
    pd = None

# Try importing the Groq client from known locations and provide
# helpful fallback/error messages when it's not available.
try:
    from groq import Groq
except Exception:
    Groq = None
    try:
        # Some installs may expose a client submodule
        from groq.client import Groq as GroqClient
        Groq = GroqClient
    except Exception:
        Groq = None


class QuestionAnswerer:
    """Professional AI-powered question answering system."""
    
    def __init__(self, model: str = "meta-llama/llama-4-scout-17b-16e-instruct", api_key: Optional[str] = None):
        """
        Initialize the QuestionAnswerer with specified model.
        
        Args:
            model: Groq model name for answer generation
            api_key: Optional custom API key. Uses GROQ_API_KEY from config if not provided.
        """
        self.model = model
        self.client = None
        self._api_key = api_key
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Groq client with API key."""
        if Groq is not None:
            key = self._api_key
            if not key:
                settings = get_settings()
                key = settings.GROQ_API_KEY
            if key:
                try:
                    self.client = Groq(api_key=key)
                except Exception as e:
                    print(f"QuestionAnswerer: failed to create Groq client: {e}")
                    self.client = None
            else:
                print("Warning: GROQ_API_KEY not set; Groq client will not be available.")
    
    def _get_image_b64(self, row: Dict[str, Any], key: str) -> Union[str, None]:
        """Return a base64 image string from row[key].

        Accepts either a pre-encoded base64 string or a file path (legacy).
        Callers should prefer passing base64 strings directly.
        """
        value = row.get(key)
        if not value:
            return None
        # Already a base64 string (no path separators, not a file)
        if isinstance(value, str) and not os.path.sep in value and not os.path.exists(value):
            return value
        # Fallback: treat as file path
        if os.path.exists(str(value)):
            with open(value, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        return None
    
    def answer_question(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Answer a single question with AI-powered freestyle detection and multiple choice support.
        
        Args:
            row: Question data dictionary with 'id', 'question', 'topic' keys, optionally 'qtype', 'options'
            
        Returns:
            Dictionary with answer, confidence, key_points, word_count
        """
        qtype = row.get("qtype", "theory")
        options = row.get("options", [])

        # Normalize options to avoid pandas NaN (float) or other unexpected types.
        # Acceptable shapes: list, dict, JSON string, legacy labeled string. Fallback to empty list.
        # Normalize pandas NaN if pandas is available, otherwise
        # handle common NaN float case (NaN != NaN) as a fallback.
        if pd is not None:
            try:
                if pd.isna(options):
                    options = []
            except Exception:
                # pd.isna may fail for some types; ignore and continue
                pass
        else:
            # float('nan') is the common NaN representation; detect via x != x
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
                        # keep as legacy string for downstream parsing
                        options = s
                except Exception:
                    # keep as legacy labeled string
                    options = s
        elif not isinstance(options, (list, dict)):
            # covers float (NaN), numbers, None, etc.
            options = []

        # write normalized options back to row for downstream functions
        row["options"] = options

        # Check if this is a multiple choice question
        is_multiple_choice = (qtype == "multiple_choice") or (options and len(options) > 0)
        
        if is_multiple_choice and options:
            return self._answer_multiple_choice(row)
        else:
            return self._answer_theory_question(row)
    
    def _answer_multiple_choice(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Answer a multiple choice question by selecting the correct option.
        
        Args:
            row: Question data with options
            
        Returns:
            Dictionary with AnswerEnum answer, confidence, key_points, word_count
        """
        question_text = row["question"]
        options = row.get("options", [])
        topic = row.get("topic", "")
        
        # Parse options to ensure consistent format
        parsed_options = []
        if isinstance(options, list):
            for i, option in enumerate(options):
                if isinstance(option, dict):
                    label = str(option.get("label", chr(97 + i))).lower()  # a, b, c, etc.
                    text = str(option.get("text", "")).strip()
                    if text:
                        parsed_options.append({"label": label, "text": text})
                elif isinstance(option, str):
                    label = chr(97 + i)  # a, b, c, etc.
                    parsed_options.append({"label": label, "text": option.strip()})
        elif isinstance(options, dict):
            for label, text in options.items():
                parsed_options.append({"label": str(label).lower(), "text": str(text).strip()})
        
        if not parsed_options:
            return {
                "answer": "Error: No valid options provided",
                "confidence": 0.0,
                "key_points": [],
                "word_count": 0
            }
        
        # Prepare content for AI
        content = [{
            "type": "text", 
            "text": f"You are an expert {topic} educator. Analyze the following multiple choice question and select the correct answer."
        }]
        
        content.append({
            "type": "text", 
            "text": f"QUESTION: {question_text}"
        })
        
        # Add options
        options_text = "\n".join([f"{opt['label'].upper()}. {opt['text']}" for opt in parsed_options])
        content.append({
            "type": "text", 
            "text": f"OPTIONS:\n{options_text}"
        })
        
        # Add image if available
        q_img = self._get_image_b64(row, "question_image_b64")
        if q_img: 
            content.append({
                "type": "image_url", 
                "image_url": {"url": f"data:image/jpeg;base64,{q_img}"}
            })
        
        # Final prompt for multiple choice
        prompt_text = f"""Analyze this {topic} multiple choice question and select the correct answer.

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
            """
        
        content.append({
            "type": "text", 
            "text": prompt_text
        })
        
        try:
            chat = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"},
                temperature=0.1  # Lower temperature for more deterministic MCQ answers
            )
        except Exception as e:
            print(f"⚠️ Error on question {row.get('id')}: {e}")
            return {
                "answer": f"Error: {str(e)}",
                "confidence": 0.0,
                "key_points": [],
                "word_count": 0
            }
        
        # Parse JSON response
        try:
            res = json.loads(chat.choices[0].message.content)
            answer_letter = res.get("answer", "").lower().strip()
            
            # Validate answer against available options
            valid_labels = [opt["label"] for opt in parsed_options]
            if answer_letter not in valid_labels:
                # Fallback to first option if invalid
                answer_letter = valid_labels[0] if valid_labels else "a"
            
            # Validate against AnswerEnum
            try:
                AnswerEnum(answer_letter)
            except ValueError:
                # If not a valid AnswerEnum, use first valid option
                answer_letter = valid_labels[0] if valid_labels else "a"
            
            return {
                "answer": answer_letter,
                "confidence": max(Decimal("0.00"), min(Decimal("1.00"), Decimal(str(res.get("confidence", "0.0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))),
                "key_points": res.get("key_points", []),
                "word_count": 0  # Always 0 for multiple choice
            }
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON decode error on question {row.get('id')}: {e}")
            return {
                "answer": "Error: Invalid JSON response",
                "confidence": Decimal("0.00"),
                "key_points": [],
                "word_count": 0
            }
    
    def _answer_theory_question(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Answer a theory question with AI-powered freestyle detection.
        
        Args:
            row: Question data dictionary
            
        Returns:
            Dictionary with answer, confidence, key_points, word_count
        """
        question_text = row["question"]
        
        # Prepare content for AI
        content = [{
            "type": "text", 
            "text": f"You are an expert {row['topic']} educator. Provide a comprehensive and accurate answer to the following question."
        }]
        
        content.append({
            "type": "text", 
            "text": f"QUESTION: {question_text}"
        })
        
        # Add image if available
        q_img = self._get_image_b64(row, "question_image_b64")
        if q_img: 
            content.append({
                "type": "image_url", 
                "image_url": {"url": f"data:image/jpeg;base64,{q_img}"}
            })
        
        # Final prompt for structured output
        prompt_text = f"""Provide a concise answer to the {row['topic']} question following these guidelines:
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
            """
        
        content.append({
            "type": "text", 
            "text": prompt_text
        })
        
        try:
            chat = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
        except Exception as e:
            print(f"⚠️ Error on question {row.get('id')}: {e}")
            return {
                "answer": f"Error: {str(e)}",
                "confidence": 0.0,
                "key_points": [],
                "word_count": 0
            }
        
        # Parse JSON response
        try:
            res = json.loads(chat.choices[0].message.content)
            return {
                "answer": res.get("answer", "No answer provided"),
                "confidence": max(Decimal("0.00"), min(Decimal("1.00"), Decimal(str(res.get("confidence", "0.0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))),
                "key_points": res.get("key_points", []),
                "word_count": res.get("word_count", len(res.get("answer", "").split()))
            }
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON decode error on question {row.get('id')}: {e}")
            return {
                "answer": f"Error: Invalid JSON response",
                "confidence": Decimal("0.00"),
                "key_points": [],
                "word_count": 0
            }
    
    
    
    def process(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process questions from CSV file and generate answers.
        
        Args:
            questions: List of question dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        print(f"🚀 Processing {len(questions)} questions...")
        
        # Process each question and merge original question fields into the result
        results = []
        for i, question in enumerate(questions, 1):
            print(f"📝 Processing question {i}/{len(questions)}: {question.get('id', 'Unknown')}")
            result = self.answer_question(question)
            # Ensure output keeps original identifiers and question text
            merged = {**question, **result}
            results.append(merged)

        return results
def process_csv_to_dict_list(csv_file: str) -> List[Dict[str, Any]]:
    """
    Convert CSV file to list of dictionaries with proper error handling.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        List of dictionaries representing rows
    """
    # Prefer pandas when available for robust CSV parsing. If pandas is
    # not installed, fall back to the standard library `csv` module.
    if pd is not None:
        try:
            df = pd.read_csv(csv_file)
            return df.to_dict("records")
        except FileNotFoundError:
            print(f"❌ Error: File '{csv_file}' not found.")
            return []
        except Exception as e:
            # pandas can raise a variety of errors (including EmptyDataError)
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
    """
    Main function with proper argument parsing and processing.
    """
    # Parse command line arguments
    input_file = "questions.csv"

    # Read the questions
    questions = process_csv_to_dict_list(input_file)
    if not questions:
        sys.exit(1)

    # Create answerer and process
    answerer = QuestionAnswerer()
    results = answerer.process(questions)
    if not results:
        sys.exit(1)

    # Select columns for output
    output_cols = ["id", "question", "topic", "answer", "confidence", "key_points", "word_count"]

    # Write results using pandas when available, otherwise use csv
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
                    # Serialize key_points list if present
                    if isinstance(out.get('key_points'), (list, tuple)):
                        out['key_points'] = json.dumps(out['key_points'])
                    writer.writerow(out)
        except Exception as e:
            print(f"❌ Error writing results to CSV: {e}")
            sys.exit(1)

    print(f"✅ Done! Processed {len(results)} questions. Saved to answer.csv")
    


if __name__ == "__main__":
    main()
