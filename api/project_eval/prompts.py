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

# Business Impact
SUBMETRIC_PROMPTS[("business_impact", "Strategic Fit")] = SubmetricPrompt(
	key="strategic_fit",
	name="Strategic Fit",
	description="Alignment to strategy and core objectives.",
	template=(
		"Proje:\n{project_text}\n\n"
		"Yukarıdaki projenin Stratejik Uyumunu (1–5) değerlendirin. Dikkate alın:\n"
		"- Şirket stratejisi ve temel hedeflerle uyum\n"
		"**Geçmiş Proje Örneği:**\n"
		"Proje: {past_project_name}\n"
		"Şirket: {past_project_company}\n"
		"Kapsam ve Hedefler: {past_project_scope_and_objectives}\n"
		"**Geçmiş Değerlendirme (Stratejik Uyum):** {past_metric_evaluation}\n"
		"Puan: {past_metric_score}\n"
		'Sadece JSON döndürün: {{"score_1_to_5": float, "reason": str}}'
	),
)

SUBMETRIC_PROMPTS[("business_impact", "Business Value Contribution")] = SubmetricPrompt(
	key="business_value",
	name="Business Value Contribution",
	description="Expected measurable benefits and stakeholder impact.",
	template=(
		"Proje:\n{project_text}\n\n"
		"Yukarıdaki projenin İş Değeri Katkısını (1–5) değerlendirin. Dikkate alın:\n"
		"- Beklenen ölçülebilir faydalar\n"
		"- Paydaş etkisi ve sonuçları\n"
		"**Geçmiş Proje Örneği:**\nProje: {past_project_name}\nİş Değeri Katkısı: {past_project_business_value_contribution}\n"
		"**Geçmiş Değerlendirme (İş Değeri Katkısı):** {past_metric_evaluation}\nPuan: {past_metric_score}\n"
		'Sadece JSON döndürün: {{"score_1_to_5": float, "reason": str}}'
	),
)
SUBMETRIC_PROMPTS[("business_impact", "Scalability & Replicability Potential")] = SubmetricPrompt(
	key="scalability",
	name="Scalability",
	description="Ease of replication and scale.",
	template=(
		"Proje:\n{project_text}\n\n"
		"Yukarıdaki projenin Ölçeklenebilirlik Potansiyelini (1–5) değerlendirin. Dikkate alın:\n"
        "**Geçmiş Proje Örneği:**\nProje: {past_project_name}\nÖlçeklenebilirlik ve Tekrarlanabilirlik Potansiyeli: {past_project_scalability_data_scope}\n"
        "**Geçmiş Değerlendirme (Ölçeklenebilirlik ve Tekrarlanabilirlik Potansiyeli):** {past_metric_evaluation}\nPuan: {past_metric_score}\n"
		"- Ölçek için operasyonel hazırlık\n"
		'Sadece JSON döndürün: {{"score_1_to_5": float, "reason": str}}'
	),
)

# Resource Investment
SUBMETRIC_PROMPTS[("resource_investment", "Projected Timeline")] = SubmetricPrompt(
	key="duration_complexity",
	name="Projected Timeline",
	description="Realism of the estimated duration and schedule.",
	template=(
		"Proje:\n{project_text}\n\n"
		"Yukarıdaki projenin Tahmini Zaman Çizelgesi gerçekçiliğini (1–5) değerlendirin. Dikkate alın:\n"
		"- Tahmini süre vs kapsam ve kısıtlar\n"
        "- Milestone'lar / kritik yol netliği\n"
		"- Dış bağımlılıklar ve sıralama\n"
        "**Geçmiş Proje Örneği:**\nProje: {past_project_name}\nTahmini Zaman Çizelgesi: {past_project_data_scope}\n"
		"**Geçmiş Değerlendirme (Tahmini Zaman Çizelgesi):** {past_metric_evaluation}\nPuan: {past_metric_score}\n"
		'Sadece JSON döndürün: {{"score_1_to_5": float, "reason": str}}'
	),
)
#This part is a bit complicated we need past project assignment and duration data 
SUBMETRIC_PROMPTS[("resource_investment", "Estimated Person-Day Effort")] = SubmetricPrompt(
	key="team_footprint",
	name="Team Footprint",
	description="Size/skills needed for delivery.",
	template=(
		"Proje:\n{project_text}\n\n"
		"Yukarıdaki projenin Ekip Ayak İzini (1–5) değerlendirin. Dikkate alın:\n"
		"- Gerekli roller ve kıdem seviyeleri\n"
		"- Fonksiyonlar arası çaba yoğunluğu\n" 
		"Mevcut durum: {current_stuff}\n"
		'Sadece JSON döndürün: {{"score_1_to_5": float, "reason": str}}'
	),
)

#Execution Risk
SUBMETRIC_PROMPTS[("execution_risk", "External Resource Dependency")] = SubmetricPrompt(
	key="external_dependence",
	name="External Dependence",
	description="Reliance on vendors/external inputs.",
	template=(
		"Proje:\n{project_text}\n\n"
		"Yukarıdaki projenin Dış Bağımlılığını (1–5) değerlendirin. Dikkate alın:\n"
		"- Tedarikçi bağımlılığı ve kısıtlar\n"
		"- Dış engeller ve riskler\n"
        "**Geçmiş Proje Örneği:**\nProje: {past_project_name}\nVeri Kapsamı: {past_project_data_scope}\nPaydaşlar: {past_project_stakeholders}\n"
		"**Geçmiş Değerlendirme (Dış Kaynak Bağımlılığı):** {past_metric_evaluation}\nPuan: {past_metric_score}\n"
		'Sadece JSON döndürün: {{"score_1_to_5": float, "reason": str}}'
	),
)

# Risk
SUBMETRIC_PROMPTS[("execution_risk", "Scope Definition Risk")] = SubmetricPrompt(
	key="scope_definition",
	name="Scope Definition",
	description="Clarity of scope, goals, and acceptance.",
	template=(
		"Proje:\n{project_text}\n\n"
		"Yukarıdaki projenin Kapsam Tanımını (1–5) değerlendirin. Dikkate alın:\n"
		"- Net kapsam ve başarı kriterleri\n"
		"- Kesin problem tanımı\n"
        "**Geçmiş Proje Örneği:**\nProje: {past_project_name}\nVeri Kapsamı: {past_project_data_scope}\nKapsam ve Hedefler: {past_project_scope_and_objectives}\n"
		"**Geçmiş Değerlendirme (Kapsam Tanımı):** {past_metric_evaluation}\nPuan: {past_metric_score}\n"
		'Sadece JSON döndürün: {{"score_1_to_5": float, "reason": str}}'
	),
)
SUBMETRIC_PROMPTS[("execution_risk", "Critical Talent Dependency")] = SubmetricPrompt(
	key="critical_talent",
	name="Critical Talent",
	description="Availability of key skills/ownership.",
	template=(
		"Proje:\n{project_text}\n\n"
		"Yukarıdaki projenin Kritik Yetenek Bağımlılığını (1–5) değerlendirin. Dikkate alın:\n"
		"- Nadir yetenekler ve darboğazlar\n"
		"- Sahiplik netliği\n"
        "Mevcut Durum: {current_stuff}\n"
        "**Geçmiş Proje Örneği:**\nProje: {past_project_name}\nKapsam ve Hedefler: {past_project_scope_and_objectives}\n"
		"**Geçmiş Değerlendirme (Kritik Yetenek):** {past_metric_evaluation}\nPuan: {past_metric_score}\n"
		'Sadece JSON döndürün: {{"score_1_to_5": float, "reason": str}}'
	),
)
SUBMETRIC_PROMPTS[("execution_risk", "Solution Complexity & Innovation Risk")] = SubmetricPrompt(
	key="innovation_complexity",
	name="Innovation Complexity",
	description="Novelty/uncertainty of approach.",
	template=(
		"Proje:\n{project_text}\n\n"
		"Yukarıdaki projenin İnovasyon Karmaşıklığını (1–5) değerlendirin. Dikkate alın:\n"
		"- Teknik bilinmeyenler/Ar-Ge ihtiyaçları\n"
		"- Uygulanabilirlik belirsizliği\n"
        "**Geçmiş Proje Örneği:**\nProje: {past_project_name}\nKapsam ve Hedefler: {past_project_scope_and_objectives}\n"
		"**Geçmiş Değerlendirme (İnovasyon Karmaşıklığı):** {past_metric_evaluation}\nPuan: {past_metric_score}\n"
		'Sadece JSON döndürün: {{"score_1_to_5": float, "reason": str}}'
	),
)
SUBMETRIC_PROMPTS[("execution_risk", "Implementation Failure Risk")] = SubmetricPrompt(
	key="implementation_failure",
	name="Implementation Failure",
	description="Likelihood of delivery/adoption failure.",
	template=(
		"Proje:\n{project_text}\n\n"
		"Yukarıdaki projenin Uygulama Başarısızlığı riskini (1–5) değerlendirin. Dikkate alın:\n"
		"- Uygulama boşlukları ve değişim riskleri\n"
		"- Benimsenme ve yaygınlaştırma engelleri\n"
        "**Geçmiş Proje Örneği:**\nProje: {past_project_name}\nKapsam ve Hedefler: {past_project_scope_and_objectives}\n"
		"**Geçmiş Değerlendirme (Uygulama Başarısızlığı):** {past_metric_evaluation}\nPuan: {past_metric_score}\n"
		'Sadece JSON döndürün: {{"score_1_to_5": float, "reason": str}}'
	),
)


