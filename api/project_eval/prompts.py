from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class SubmetricPrompt:
	"""
	Submetric prompt definition.

	template must include "{project_text}" placeholder.
	You can also add any extra placeholders (e.g., {context}, {sources}, {language}).
	LLM must return JSON only:
	  {"score_1_to_5": float, "reason": str}
	"""
	key: str
	name: str
	description: str
	template: str

	def render(self, project_text: str, **kwargs) -> str:
		"""
		Render the prompt as a formatted string.

		Parameters
		- project_text: required base description
		- **kwargs: any additional placeholders referenced by the template
		  (e.g., context retrieved from a vector DB)
		"""
		return self.template.format(project_text=project_text, **kwargs)


SUBMETRIC_PROMPTS: Dict[Tuple[str, str], SubmetricPrompt] = {}

# Impact
SUBMETRIC_PROMPTS[("business_impact", "Strategic Fit")] = SubmetricPrompt(
	key="strategic_fit",
	name="Strategic Fit",
	description="Alignment to strategy and core objectives.",
	template=(
		"Project:\n{project_text}\n\n"
		"Evaluate Strategic Fit (1–5) of the project above. Consider:\n"
		"- Alignment to company strategy and core objectives\n"
		"**Past Project Example:**\n"
		"Project: {past_project_name}\n"
		"Company: {past_project_company}\n"
		"Scope & Objectives: {past_project_scope_and_objectives}\n"
		"**Past Evaluation (Strategic Fit):** {past_metric_evaluation}\n"
		"Score: {past_metric_score}\n"
		'Return JSON only: {"score_1_to_5": float, "reason": str}'
	),
)

SUBMETRIC_PROMPTS[("business_impact", "Business Value Contribution")] = SubmetricPrompt(
	key="business_value",
	name="Business Value Contribution",
	description="Expected measurable benefits and stakeholder impact.",
	template=(
		"Project:\n{project_text}\n\n"
		"Evaluate Business Value (1–5) of the project above. Consider:\n"
		"- Expected measurable benefits\n"
		"- Stakeholder impact and outcomes\n"
		"**Past Project Example:**\nProject: {past_project_name}\nBusiness Value Contribution: {past_project_business_value_contribution}\n"
		"**Past Evaluation (Business Value Contribution):** {past_metric_evaluation}\nScore: {past_metric_score}\n"
		'Return JSON only: {"score_1_to_5": float, "reason": str}'
	),
)
SUBMETRIC_PROMPTS[("business_impact", "Scalability & Replicability Potential")] = SubmetricPrompt(
	key="scalability",
	name="Scalability",
	description="Ease of replication and scale.",
	template=(
		"Project:\n{project_text}\n\n"
		"Evaluate Scalability (1–5) of the project above. Consider:\n"
        "**Past Project Example:**\nProject: {past_project_name}\nScalability & Replicability Potential: {past_project_scalability_data_scope}\n"
        "**Past Evaluation (Scalability & Replicability Potential):** {past_metric_evaluation}\nScore: {past_metric_score}\n"
		"- Operational readiness for scale\n"
		'Return JSON only: {"score_1_to_5": float, "reason": str}'
	),
)

# Effort
SUBMETRIC_PROMPTS[("resource_investment", "Projected Timeline")] = SubmetricPrompt(
	key="duration_complexity",
	name="Projected Timeline",
	description="Realism of the estimated duration and schedule.",
	template=(
		"Project:\n{project_text}\n\n"
		"Evaluate Projected Timeline realism (1–5) of the project above. Consider:\n"
		"- Estimated duration vs scope and constraints\n"
        "- Milestones / critical path clarity\n"
		"- External dependencies and sequencing\n"
        "**Past Project Example:**\nProject: {past_project_name}\nProjected Timeline: {past_project_data_scope}\n"
        "**Past Evaluation (Projected Timeline):** {past_metric_evaluation}\nScore: {past_metric_score}\n"
		'Return JSON only: {"score_1_to_5": float, "reason": str}'
	),
)
#This part is a bit complicated we need past project assignment and duration data 
SUBMETRIC_PROMPTS[("resource_investment", "Estimated Person-Day Effort")] = SubmetricPrompt(
	key="team_footprint",
	name="Team Footprint",
	description="Size/skills needed for delivery.",
	template=(
		"Project:\n{project_text}\n\n"
		"Evaluate Team Footprint (1–5) of the project above. Consider:\n"
		"- Required roles and seniority\n"
		"- Effort intensity across functions\n" 
		"Here is current stuff: {current_stuff}\n"
		'Return JSON only: {"score_1_to_5": float, "reason": str}'
	),
)
SUBMETRIC_PROMPTS[("execution_risk", "External Resource Dependency")] = SubmetricPrompt(
	key="external_dependence",
	name="External Dependence",
	description="Reliance on vendors/external inputs.",
	template=(
		"Project:\n{project_text}\n\n"
		"Evaluate External Dependence (1–5) of the project above. Consider:\n"
		"- Vendor reliance and constraints\n"
		"- External blockers and risks\n"
        "**Past Project Example:**\nProject: {past_project_name}\nData Scope: {past_project_data_scope}\nStakeholders: {past_project_stakeholders}\n"
        "**Past Evaluation (External Resource Dependency):** {past_metric_evaluation}\nScore: {past_metric_score}\n"
		'Return JSON only: {"score_1_to_5": float, "reason": str}'
	),
)

# Risk
SUBMETRIC_PROMPTS[("execution_risk", "Scope Definition Risk")] = SubmetricPrompt(
	key="scope_definition",
	name="Scope Definition",
	description="Clarity of scope, goals, and acceptance.",
	template=(
		"Project:\n{project_text}\n\n"
		"Evaluate Scope Definition (1–5) of the project above. Consider:\n"
		"- Clear scope and success criteria\n"
		"- Crisp problem statement\n"
        "**Past Project Example:**\nProject: {past_project_name}\nData Scope: {past_project_data_scope}\nScope & Objectives: {past_project_scope_and_objectives}\n"
        "**Past Evaluation (Scope Definition):** {past_metric_evaluation}\nScore: {past_metric_score}\n"
		'Return JSON only: {"score_1_to_5": float, "reason": str}'
	),
)
SUBMETRIC_PROMPTS[("execution_risk", "Critical Talent Dependency")] = SubmetricPrompt(
	key="critical_talent",
	name="Critical Talent",
	description="Availability of key skills/ownership.",
	template=(
		"Project:\n{project_text}\n\n"
		"Evaluate Critical Talent (1–5) of the project above. Consider:\n"
		"- Scarce skills and bottlenecks\n"
		"- Ownership clarity\n"
        "Current Stuff:{current_stuff}\n"
        "**Past Project Example:**\nProject: {past_project_name}\nScope & Objectives: {past_project_scope_and_objectives}\n"
        "**Past Evaluation (Critical Talent):** {past_metric_evaluation}\nScore: {past_metric_score}\n"
		'Return JSON only: {"score_1_to_5": float, "reason": str}'
	),
)
SUBMETRIC_PROMPTS[("execution_risk", "Solution Complexity & Innovation Risk")] = SubmetricPrompt(
	key="innovation_complexity",
	name="Innovation Complexity",
	description="Novelty/uncertainty of approach.",
	template=(
		"Project:\n{project_text}\n\n"
		"Evaluate Innovation Complexity (1–5) of the project above. Consider:\n"
		"- Technical unknowns/R&D needs\n"
		"- Feasibility uncertainty\n"
        "**Past Project Example:**\nProject: {past_project_name}\nScope & Objectives: {past_project_scope_and_objectives}\n"
        "**Past Evaluation (Innovation Complexity):** {past_metric_evaluation}\nScore: {past_metric_score}\n"
		'Return JSON only: {"score_1_to_5": float, "reason": str}'
	),
)
SUBMETRIC_PROMPTS[("execution_risk", "Implementation Failure Risk")] = SubmetricPrompt(
	key="implementation_failure",
	name="Implementation Failure",
	description="Likelihood of delivery/adoption failure.",
	template=(
		"Project:\n{project_text}\n\n"
		"Evaluate Implementation Failure (1–5) of the project above. Consider:\n"
		"- Execution gaps and change risks\n"
		"- Adoption and rollout barriers\n"
        "**Past Project Example:**\nProject: {past_project_name}\nScope & Objectives: {past_project_scope_and_objectives}\n"
        "**Past Evaluation (Implementation Failure):** {past_metric_evaluation}\nScore: {past_metric_score}\n"
		'Return JSON only: {"score_1_to_5": float, "reason": str}'
	),
)


