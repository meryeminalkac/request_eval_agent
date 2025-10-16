# api/main.py
from __future__ import annotations
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import json

# ---- your evaluator imports (must be importable on Render) ----
from project_eval.llm import Generator, StubLLMClient
from project_eval.evaluators import ImpactEvaluator, EffortEvaluator, RiskEvaluator

app = FastAPI(title="Form Processing API (Minimal Sync)", version="0.5.0")

# ----- Payload matching your Power Automate Compose -----
class Respondent(BaseModel):
    email: Optional[str] = None

class FormSubmission(BaseModel):
    form_id: Optional[str] = None
    response_id: Optional[str] = None
    submitted_at: Optional[str] = None
    respondent: Respondent = Field(default_factory=Respondent)
    answers: Dict[str, Optional[str]] = Field(default_factory=dict)

# ----- Helpers -----
def english_key(full_key: str) -> str:
    for sep in (" - ", " – ", "–", "-"):
        if sep in full_key:
            return full_key.split(sep, 1)[0].strip()
    return full_key.strip()

def normalize_to_dict(sub: FormSubmission) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in (sub.answers or {}).items():
        out[english_key(str(k))] = "" if v is None else str(v)
    return out

def build_project_text(normalized: Dict[str, str]) -> str:
    project_name = normalized.get("Project", "Unknown Project")
    key_map = {
        "Company": "Company",
        "Project Scope & Objectives": "Scope and Objectives",
        "Business Value Contribution": "Business Value",
        "Project Stakeholders & Sponsorship": "Stakeholders",
        "Data Scope": "Data Sources",
    }
    parts = [f"Project: {project_name}"]
    for k, v in normalized.items():
        label = key_map.get(k, k)
        parts.append(f"{label}: {v}")
    return "\n".join(parts)

async def run_evaluations(normalized: Dict[str, str]):
    # Try Azure; fall back to stub (keeps things working on Render free)
    try:
        llm = Generator()
    except Exception:
        llm = StubLLMClient()

    project_name = normalized.get("Project", "Unknown Project")
    project_text = build_project_text(normalized)

    with open("evaulations.json", "r", encoding="utf-8") as f:
        evaulations_cfg = json.load(f)
    with open("prf_answers.json", "r", encoding="utf-8") as f:
        prf_answers = json.load(f)
    with open("staff_info.json", "r", encoding="utf-8") as f:
        staff_info = json.load(f)

    impact = ImpactEvaluator(llm)
    effort = EffortEvaluator(llm)
    risk   = RiskEvaluator(llm)

    impact_res = await impact.evaluate_with_sources(
        project_name=project_name,
        project_text=project_text,
        evaulations=evaulations_cfg,
        prf_answers=prf_answers,
        staff_info=staff_info,
    )
    effort_res = await effort.evaluate_with_sources(
        project_name=project_name,
        project_text=project_text,
        evaulations=evaulations_cfg,
        prf_answers=prf_answers,
        staff_info=staff_info,
    )
    risk_res = await risk.evaluate_with_sources(
        project_name=project_name,
        project_text=project_text,
        evaulations=evaulations_cfg,
        prf_answers=prf_answers,
        staff_info=staff_info,
    )

    return {"impact": impact_res, "effort": effort_res, "risk": risk_res}

# ----- Routes -----
@app.get("/")
def ping():
    return {"ok": True, "msg": "Minimal evaluator up"}

@app.post("/form-answers")
async def form_answers(payload: FormSubmission):
    """
    Minimal: normalize -> evaluate synchronously -> return results.
    Power Automate HTTP action should POST here.
    """
    try:
        normalized = normalize_to_dict(payload)
        results = await run_evaluations(normalized)
        return {
            "question_answer_dict": normalized,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Evaluation failed: {e}")
