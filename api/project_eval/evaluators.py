from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple
import json
import os
import logging

from .llm import LLMClient
from .prompts import SUBMETRIC_PROMPTS, SubmetricPrompt


def _coerce_score(value: Any) -> float:
	try:
		f = float(value)
		if 1.0 <= f <= 5.0:
			return float(f"{f:.2f}")
	except Exception:
		pass
	return 3.0


def _band(score: float) -> str:
	if score < 2.5:
		return "low"
	if score < 3.67:
		return "mid"
	return "high"


class Evaluator:
	"""
	Base evaluator for a main metric.

	- Equal-weight simple mean across submetrics
	- Bands: <2.5 low, <3.77 mid, else high
	"""

	def __init__(self, metric_id: str, submetric_keys: List[str], llm: LLMClient) -> None:
		self.metric_id = metric_id
		self.submetric_keys = submetric_keys
		self.llm = llm

	def _normalize_llm_response(self, resp: Any) -> dict:
		"""Normalize possibly malformed LLM outputs into a dict with expected keys.

		- If resp is a JSON string, parse it.
		- If keys come quoted (e.g., '"score_1_to_5"'), strip quotes/spaces.
		- Default score to 3.0 and provide a fallback reason when missing/invalid.
		"""
		# If bytes → decode first
		if isinstance(resp, (bytes, bytearray)):
			try:
				resp = resp.decode("utf-8", errors="ignore")
			except Exception:
				pass
		if isinstance(resp, str):
			try:
				resp = json.loads(resp)
			except Exception:
				return {"score_1_to_5": 3.0, "reason": "Unparseable LLM output; defaulted."}
		# Some providers return a list with a single dict
		if isinstance(resp, list) and resp and isinstance(resp[0], dict):
			resp = resp[0]
		if not isinstance(resp, dict):
			return {"score_1_to_5": 3.0, "reason": "Non-dict LLM output; defaulted."}
		cleaned = {str(k).strip(" '\""): v for k, v in resp.items()}
		try:
			score = float(cleaned.get("score_1_to_5", 3.0))
			if not (1.0 <= score <= 5.0):
				raise ValueError
		except Exception:
			score = 3.0
		reason = cleaned.get("reason")
		if not isinstance(reason, str) or not reason.strip():
			reason = "No reason; defaulted."
		return {"score_1_to_5": float(f"{score:.2f}"), "reason": reason.strip()}

	def _index_by_project_name(self, obj: Any) -> Dict[str, dict]:
		"""Accept dict (single project), list of dicts, or dict keyed by name."""
		if isinstance(obj, dict) and "project_name" in obj:
			return {obj.get("project_name", ""): obj}
		if isinstance(obj, list):
			out: Dict[str, dict] = {}
			for item in obj:
				if isinstance(item, dict) and "project_name" in item:
					out[item["project_name"]] = item
			return out
		if isinstance(obj, dict):
			return {k: v for k, v in obj.items() if isinstance(v, dict)}
		return {}

	def _build_prompt_kwargs(
		self,
		project_name: str,
		submetric_label: str,
		evaulations: Any,
		prf_answers: Any,
		staff_info: Any,
	) -> Dict[str, Any]:
		eva_by = self._index_by_project_name(evaulations)
		prf_by = self._index_by_project_name(prf_answers)
		staff = staff_info if isinstance(staff_info, dict) else {"raw": staff_info}

		# Use past project data as examples (not matching by project name)
		# Get the first available project as an example
		if eva_by:
			example_project = list(eva_by.keys())[0]
			eva = eva_by[example_project].get("metrics", {})
		else:
			eva = {}

		metric_entry = eva.get(submetric_label) or {}
		past_metric_evaluation = metric_entry.get("evaluation", "")
		past_metric_score = metric_entry.get("score", "")

		# Use past project data as examples (not matching by project name)
		if prf_by:
			example_project = list(prf_by.keys())[0]
			prf = prf_by[example_project]
		else:
			prf = {}
		past_project_company = prf.get("company") or prf.get("business_unit") or ""
		past_project_scope_and_objectives = (
			prf.get("Project Scope & Objectives") or prf.get("scope") or prf.get("objectives") or ""
		)
		past_project_business_value_contribution = (
			eva.get("Business Value Contribution", {}).get("evaluation", "")
		)
		past_project_scalability_data_scope = (
			eva.get("Scalability & Replicability Potential", {}).get("evaluation", "")
		)
		past_project_data_scope = prf.get("data_scope") or prf.get("data_sources") or ""
		past_project_stakeholders = prf.get("Project Stakeholders & Sponsorship") or prf.get("team") or ""
		current_stuff = staff.get("current_stuff") or staff.get("staff") or staff

		# Get the example project name for display
		example_project_name = list(eva_by.keys())[0] if eva_by else "Example Project"
		
		return {
			"past_project_name": example_project_name,  # Use example project name, not current project
			"past_project_company": past_project_company,
			"past_project_scope_and_objectives": past_project_scope_and_objectives,
			"past_project_business_value_contribution": past_project_business_value_contribution,
			"past_project_scalability_data_scope": past_project_scalability_data_scope,
			"past_project_data_scope": past_project_data_scope,
			"past_project_stakeholders": past_project_stakeholders,
			"past_metric_evaluation": past_metric_evaluation,
			"past_metric_score": past_metric_score,
			"current_stuff": current_stuff,
		}

	async def _score_one(
		self,
		prompt: SubmetricPrompt,
		project_text: str,
		project_name: str | None = None,
		evaulations: Any | None = None,
		prf_answers: Any | None = None,
		staff_info: Any | None = None,
		submetric_label: str | None = None,
	) -> dict:
		kwargs: Dict[str, Any] = {}
		if project_name is not None and (evaulations is not None or prf_answers is not None or staff_info is not None):
			kwargs = self._build_prompt_kwargs(
				project_name,
				submetric_label or prompt.name,
				evaulations or {},
				prf_answers or {},
				staff_info or {},
			)
		rendered = prompt.render(project_text, **kwargs)
		# Optional prompt logging
		if os.environ.get("LOG_PROMPTS", "").lower() in {"1", "true", "yes"}:
			try:
				logging.getLogger("uvicorn.access").info(
					"[LLM PROMPT] metric=%s sub=%s prompt=%s",
					self.metric_id,
					prompt.name,
					rendered[:1000],
				)
			except Exception:
				pass
		try:
			raw = await self.llm.complete(rendered)
			resp = self._normalize_llm_response(raw)
		except Exception as e:
			resp = {"score_1_to_5": 3.0, "reason": f"LLM error: {e}; defaulted to 3.0."}
		score = _coerce_score(resp.get("score_1_to_5"))
		reason = resp.get("reason")
		if not isinstance(reason, str) or not reason.strip():
			reason = "No reason; defaulted."

		# Optional debugging
		if os.environ.get("LOG_LLM", "").lower() in {"1", "true", "yes"}:
			try:
				print(f"[LLM DEBUG] metric={self.metric_id} sub={prompt.name} score={score} reason={reason[:120]}")
			except Exception:
				pass
		return {
			"key": prompt.key,
			"name": prompt.name,
			"score": score,
			"reason": reason.strip(),
		}

	async def evaluate(self, project_text: str) -> dict:
		# Back-compat: use only internal keys (may not match prompts with display labels)
		prompts: List[Tuple[str, SubmetricPrompt]] = []
		for key in self.submetric_keys:
			pmpt = SUBMETRIC_PROMPTS.get((self.metric_id, key))
			if pmpt is None:
				pmpt = SubmetricPrompt(
					key=key,
					name=key.replace("_", " ").title(),
					description="Auto placeholder",
					template="Project:\n{project_text}\n\nReturn JSON only: {{\"score_1_to_5\": 3.0, \"reason\": \"placeholder\"}}",
				)
			prompts.append((key, pmpt))

		sub_results = await asyncio.gather(*(self._score_one(p, project_text) for _, p in prompts))
		overall = float(f"{(sum(s['score'] for s in sub_results) / len(sub_results)) if sub_results else 3.0:.2f}")
		band = _band(overall)

		reasons = [s["reason"] for s in sub_results if isinstance(s.get("reason"), str)]
		overall_reason = " ".join(r.strip() for r in reasons[:2]) or "Balanced across submetrics."

		return {
			"metric": self.metric_id,
			"overall_score": overall,
			"band": band,
			"overall_reason": overall_reason[:240],
			"submetrics": sub_results,
		}

	async def evaluate_with_sources(
		self,
		project_name: str,
		project_text: str,
		evaulations: Any,
		prf_answers: Any,
		staff_info: Any,
	) -> dict:
		# Use the prompts exactly as defined in prompts.py for this metric (by display label)
		prompts_for_metric: List[Tuple[str, SubmetricPrompt]] = [
			(label, pmpt)
			for (metric, label), pmpt in SUBMETRIC_PROMPTS.items()
			if metric == self.metric_id
		]
		if not prompts_for_metric:
			# Fallback to the generic method
			return await self.evaluate(project_text)

		sub_results = await asyncio.gather(
			*(
				self._score_one(
					pmpt,
					project_text,
					project_name=project_name,
					evaulations=evaulations,
					prf_answers=prf_answers,
					staff_info=staff_info,
					submetric_label=label,
				)
				for label, pmpt in prompts_for_metric
			)
		)

		overall = float(f"{(sum(s['score'] for s in sub_results) / len(sub_results)) if sub_results else 3.0:.2f}")
		band = _band(overall)
		reasons = [s["reason"] for s in sub_results if isinstance(s.get("reason"), str)]
		overall_reason = " ".join(r.strip() for r in reasons[:2]) or "Balanced across submetrics."

		return {
			"metric": self.metric_id,
			"overall_score": overall,
			"band": band,
			"overall_reason": overall_reason[:240],
			"submetrics": sub_results,
		}


class ImpactEvaluator(Evaluator):
	def __init__(self, llm: LLMClient) -> None:
		super().__init__(
			metric_id="business_impact",
			submetric_keys=[
				"Strategic Fit",
				"Business Value Contribution",
				"Scalability & Replicability Potential",
			],
			llm=llm,
		)


class EffortEvaluator(Evaluator):
	def __init__(self, llm: LLMClient) -> None:
		super().__init__(
			metric_id="resource_investment",
			submetric_keys=[
				"Projected Timeline",
				"Estimated Person-Day Effort",
				"External Resource Dependency",
			],
			llm=llm,
		)


class RiskEvaluator(Evaluator):
	def __init__(self, llm: LLMClient) -> None:
		super().__init__(
			metric_id="execution_risk",
			submetric_keys=[
				"Scope Definition Risk",
				"Critical Talent Dependency",
				"Solution Complexity & Innovation Risk",
				"Implementation Failure Risk",
			],
			llm=llm,
		)


