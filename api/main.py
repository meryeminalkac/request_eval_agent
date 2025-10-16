# api/main.py
from __future__ import annotations

from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

app = FastAPI(title="Form Processing API", version="0.2.0")


# ---- Models that match your Power Automate payload ----

class Respondent(BaseModel):
    email: Optional[str] = None

class FormSubmission(BaseModel):
    form_id: Optional[str] = None
    response_id: Optional[str] = None
    submitted_at: Optional[str] = None  # keep as str to match PA exactly
    respondent: Respondent = Field(default_factory=Respondent)
    # PA sends a dict mapping question-title -> value
    answers: Dict[str, Optional[str]] = Field(default_factory=dict)


class FormAnswersResponse(BaseModel):
    question_answer_dict: Dict[str, str]


# ---- Helpers ----

def english_key(full_key: str) -> str:
    """
    Return the English part before ' - ' or ' – '.
    E.g., 'Project-Proje' or 'Project - Proje' or 'Project – Proje' -> 'Project'
    """
    if " - " in full_key:
        return full_key.split(" - ", 1)[0].strip()
    if " – " in full_key:  # en dash
        return full_key.split(" – ", 1)[0].strip()
    # also handle no spaces around dash (rare)
    for sep in ("–", "-"):
        if sep in full_key:
            return full_key.split(sep, 1)[0].strip()
    return full_key.strip()


# ---- Routes ----

@app.get("/")
def root():
    return {"ok": True, "msg": "Form Processing API up"}

@app.post("/form-answers", response_model=FormAnswersResponse)
async def process_form_answers(payload: FormSubmission) -> FormAnswersResponse:
    """
    Accepts Power Automate payload:
    {
      "form_id": "...",
      "response_id": "...",
      "submitted_at": "2025-10-15T06:52:22.7895400Z",
      "respondent": {"email": "..."},
      "answers": {
        "Project-Proje": "...",
        "Company-Kuruluş": "...",
        ...
      }
    }

    Returns:
    {
      "question_answer_dict": {
        "Project": "...",
        "Company": "...",
        ...
      }
    }
    """
    try:
        qa: Dict[str, str] = {}
        for k, v in (payload.answers or {}).items():
            key = english_key(str(k))
            qa[key] = "" if v is None else str(v)
        return FormAnswersResponse(question_answer_dict=qa)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing form answers: {e}")
