from __future__ import annotations

from typing import Optional, List, Literal, Any, Dict
from uuid import UUID
from datetime import datetime
import re
from models.academic.question import AnswerEnum, Industry
from pydantic import BaseModel, ConfigDict, model_validator
from typing import TypeVar
import json

from core.utils.response import ResponseModel as _BaseResponseModel, MetaModel as _MetaModel, LinksModel as _LinksModel


class QuestionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    number: str
    text: str
    images: Optional[List[str]] = None
    industry: Optional[Industry] = None
    parent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    qtype: Literal["multiple_choice", "theory", "fill_in_blanks"] = "theory"
    options: Optional[Any] = None
    answer: Optional[AnswerEnum] = None
    exam_ids: Optional[List[UUID]] = None
    answer_id: Optional[UUID] = None
    mark: Optional[float] = None
    rules: Optional[str] = None


class QuestionCreate(QuestionBase):
    industry: Industry
    @model_validator(mode="after")
    def check_options(self):
        # On create, options are only allowed when qtype is multiple_choice
        if self.options is not None:
            if self.qtype not in ["multiple_choice", "fill_in_blanks"]:
                raise ValueError("Options are only allowed for multiple_choice or fill_in_blanks questions")
            # allow: labeled string, JSON string, list, or dict; service will normalize
            # Basic shape checks here; detailed label validation happens in service
            if isinstance(self.options, str):
                if self.options.strip() == "":
                    raise ValueError("Multiple choice/fill_in_blanks questions require non-empty options")
            elif isinstance(self.options, (list, dict)):
                if isinstance(self.options, list) and len(self.options) == 0:
                    raise ValueError("Options list cannot be empty for multiple_choice/fill_in_blanks questions")
            else:
                raise ValueError("Unsupported options type; must be labeled string, JSON string, list, or dict")
        return self


class QuestionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    number: Optional[str] = None
    text: Optional[str] = None
    images: Optional[List[str]] = None
    industry: Optional[Industry] = None
    parent_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    qtype: Optional[Literal["multiple_choice", "theory", "fill_in_blanks"]] = None
    options: Optional[Any] = None
    answer: Optional[AnswerEnum] = None
    exam_ids: Optional[List[UUID]] = None
    answer_id: Optional[UUID] = None
    mark: Optional[float] = None
    rules: Optional[str] = None

    @model_validator(mode="after")
    def check_options_update(self):
        # On update, enforce options only when qtype is multiple_choice or fill_in_blanks.
        # If options provided without qtype, allow (service will validate against existing qtype).
        if self.options is not None:
            # if qtype provided, it must allow options
            if self.qtype is not None and self.qtype not in ["multiple_choice", "fill_in_blanks"]:
                raise ValueError("Options are only allowed for multiple_choice or fill_in_blanks questions")
            if isinstance(self.options, str):
                if self.options.strip() == "":
                    raise ValueError("Options cannot be empty")
            elif isinstance(self.options, (list, dict)):
                if isinstance(self.options, list) and len(self.options) == 0:
                    raise ValueError("Options list cannot be empty for multiple_choice/fill_in_blanks questions")
            else:
                raise ValueError("Unsupported options type; must be labeled string, JSON string, list, or dict")
        return self


class QuestionRead(QuestionBase):
    id: UUID
    industry: Optional[Industry]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    # parsed_options provides a structured representation for API responses
    parsed_options: Optional[List[Dict[str, str]]] = None

    @model_validator(mode="after")
    def build_parsed(self):
        raw = getattr(self, "options", None)
        if not raw:
            self.parsed_options = []
            return self
        # If already a list/dict, normalize to list of {label,text}
        if isinstance(raw, list):
            items = []
            for i, v in enumerate(raw, start=1):
                if isinstance(v, str):
                    items.append({"label": str(i), "text": v})
                elif isinstance(v, dict):
                    items.append({"label": v.get("label", str(i)), "text": v.get("text")})
            self.parsed_options = items
            return self
        if isinstance(raw, dict):
            self.parsed_options = [{"label": k, "text": v} for k, v in raw.items()]
            return self

        # raw is a string: try labeled format first, else JSON
        pattern = re.compile(r"\[([^\]]+)\]\-([^\[]+)")
        m = pattern.findall(raw)
        if m:
            self.parsed_options = [{"label": lbl.strip(), "text": txt.strip()} for lbl, txt in m]
            return self
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                items = []
                for i, v in enumerate(parsed, start=1):
                    if isinstance(v, str):
                        items.append({"label": str(i), "text": v})
                    elif isinstance(v, dict):
                        items.append({"label": v.get("label", str(i)), "text": v.get("text")})
                self.parsed_options = items
                return self
            if isinstance(parsed, dict):
                self.parsed_options = [{"label": k, "text": v} for k, v in parsed.items()]
                return self
        except Exception:
            pass
        # fallback: empty
        self.parsed_options = []
        return self


# Response envelope types used by routes/OpenAPI so nested QuestionRead appears
class QuestionResponse(_BaseResponseModel):
    data: Optional[QuestionRead] = None


class QuestionListResponse(_BaseResponseModel):
    data: Optional[List[QuestionRead]] = None
    meta: Optional[_MetaModel] = None
    links: Optional[_LinksModel] = None
