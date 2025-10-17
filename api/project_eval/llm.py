from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Protocol, Any

try:
	from openai import AsyncAzureOpenAI
except ImportError:
	AsyncAzureOpenAI = None


class LLMClient(Protocol):
	"""
	Async LLM interface that returns parsed dict:
	  {"score_1_to_5": float, "reason": str}
	"""

	async def complete(self, prompt: str) -> dict[str, Any]:
		...


class Generator:
	"""
	Azure OpenAI client that loads API keys from JSON and calls Azure OpenAI API.
	"""

	def __init__(self, config_path: str | Path = "config.json"):
		self.config_path = Path(config_path)
		self.client = None
		self._config = None

	def load_api_key(self) -> dict[str, Any]:
		"""
		Load API configuration from JSON file.
		Expected format:
		{
			"azure_endpoint": "https://your-resource.openai.azure.com/",
			"api_key": "your-api-key",
			"api_version": "2024-02-15-preview",
			"deployment_name": "your-deployment-name"
		}
		"""
		if not self.config_path.exists():
			raise FileNotFoundError(f"Config file not found: {self.config_path}")
		
		with self.config_path.open("r", encoding="utf-8") as f:
			self._config = json.load(f)
		
		required_keys = ["azure_endpoint", "api_key", "api_version", "deployment_name"]
		missing_keys = [key for key in required_keys if key not in self._config]
		if missing_keys:
			raise ValueError(f"Missing required config keys: {missing_keys}")
		
		return self._config

	async def complete(self, prompt: str) -> dict[str, Any]:
		"""
		Call Azure OpenAI API with the given prompt.
		Returns parsed JSON response with score_1_to_5 and reason.
		"""
		if AsyncAzureOpenAI is None:
			raise ImportError("openai package not installed. Install with: pip install openai")
		
		if self._config is None:
			self.load_api_key()
		
		if self.client is None:
			self.client = AsyncAzureOpenAI(
				azure_endpoint=self._config["azure_endpoint"],
				api_key=self._config["api_key"],
				api_version=self._config["api_version"]
			)
		
		try:
			response = await self.client.chat.completions.create(
				model=self._config["deployment_name"],
				messages=[
					{"role": "system", "content": "You are an expert project evaluator. You must respond with ONLY valid JSON in this exact format: {\"score_1_to_5\": number, \"reason\": \"text\"}. Do not include any markdown formatting, code blocks, or additional text."},
					{"role": "user", "content": prompt}
				],
				temperature=0.1,
				max_tokens=500
			)
			
			content = response.choices[0].message.content.strip()
			
			# Try to parse JSON response
			try:
				# Clean the content - remove markdown code blocks if present
				cleaned_content = content.strip()
				if cleaned_content.startswith("```json"):
					cleaned_content = cleaned_content[7:]  # Remove ```json
				if cleaned_content.startswith("```"):
					cleaned_content = cleaned_content[3:]   # Remove ```
				if cleaned_content.endswith("```"):
					cleaned_content = cleaned_content[:-3]  # Remove trailing ```
				cleaned_content = cleaned_content.strip()
				
				result = json.loads(cleaned_content)
				if "score_1_to_5" not in result or "reason" not in result:
					raise ValueError("Missing required fields in response")
				return result
			except (json.JSONDecodeError, ValueError) as e:
				# Fallback if JSON parsing fails
				return {
					"score_1_to_5": 3.0,
					"reason": f"Failed to parse response: {str(e)}. Raw response: {content[:100]}..."
				}
		
		except Exception as e:
			return {
				"score_1_to_5": 3.0,
				"reason": f"API call failed: {str(e)}"
			}


class StubLLMClient:
	"""
	Deterministic stub. No external deps. Produces mid-ish scores with a tiny, stable tweak.
	"""

	async def complete(self, prompt: str) -> dict[str, Any]:
		await asyncio.sleep(0.01)
		tweak = (sum(ord(c) for c in prompt[:128]) % 9) * 0.05  # 0.0..0.4
		score = 3.0 + (tweak - 0.2)  # 2.8..3.2
		return {
			"score_1_to_5": float(f"{score:.2f}"),
			"reason": "Deterministic stub based on prompt content.",
		}


