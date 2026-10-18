"""
CyberEval - Unified Model Adapter Service
Provides a clean abstraction over LLM providers (OpenAI, Anthropic, Gemini, Ollama)
and deterministic baseline/mock models for repeatable, zero-cost offline benchmarking.
"""

import json
import re
import time
import httpx
from typing import Dict, Any, Tuple
from cybereval.core.config import settings
from cybereval.core.exceptions import ProviderAPIError


class ModelAdapterService:
    """Unified service for generating model responses."""

    @classmethod
    async def generate(
        cls,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        scenario_context: Dict[str, Any] | None = None,
    ) -> Tuple[str, Dict[str, Any] | None, int, int, int]:
        """
        Executes model generation.
        Returns: (raw_completion, parsed_json, latency_ms, prompt_tokens, completion_tokens)
        """
        start_time = time.time()
        
        # Route to built-in deterministic models or external providers
        if model_name.startswith("baseline-") or model_name.startswith("mock-"):
            raw, parsed = cls._generate_builtin_baseline(model_name, scenario_context or {})
            latency_ms = int((time.time() - start_time) * 1000)
            prompt_tokens = len(user_prompt.split()) * 2
            completion_tokens = len(raw.split()) * 2
            return raw, parsed, latency_ms, prompt_tokens, completion_tokens

        elif model_name.startswith("openai/"):
            return await cls._call_openai(model_name.replace("openai/", ""), system_prompt, user_prompt, temperature, max_tokens)
        elif model_name.startswith("anthropic/"):
            return await cls._call_anthropic(model_name.replace("anthropic/", ""), system_prompt, user_prompt, temperature, max_tokens)
        elif model_name.startswith("gemini/"):
            return await cls._call_gemini(model_name.replace("gemini/", ""), system_prompt, user_prompt, temperature, max_tokens)
        elif model_name.startswith("ollama/"):
            return await cls._call_ollama(model_name.replace("ollama/", ""), system_prompt, user_prompt, temperature, max_tokens)
        else:
            # Default fallback to baseline expert
            raw, parsed = cls._generate_builtin_baseline("baseline-ground-truth-v1", scenario_context or {})
            latency_ms = int((time.time() - start_time) * 1000)
            return raw, parsed, latency_ms, 150, 200

    @classmethod
    def _generate_builtin_baseline(cls, model_variant: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Generates deterministic baseline responses conditioned on the scenario context.
        Enables reproducible offline testing, CI/CD validation, and scoring verification.
        """
        ref = context.get("reference_answer", {})
        category = context.get("category", "attack_chain")
        scenario_code = context.get("scenario_code", "CE-001")
        evidence_items = context.get("evidence_items", [])
        evidence_codes = [e.get("evidence_code") for e in evidence_items]

        # 1. GROUND TRUTH EXPERT MODEL (Passes all checks, grounds every claim, respects uncertainty)
        if model_variant in ["baseline-ground-truth-v1", "baseline-expert"]:
            claims = []
            for req in ref.get("required_claims", []):
                claims.append({
                    "statement": req.get("statement"),
                    "claim_type": "inference",
                    "confidence": "high",
                    "evidence_references": req.get("required_evidence", evidence_codes[:2]),
                })
            
            # Add explicit uncertainty statement if required
            uncertainty_req = ref.get("uncertainty_requirements", {})
            uncertainties = []
            if uncertainty_req.get("requires_qualification"):
                insufficient = uncertainty_req.get("insufficient_evidence_for", [])
                for item in insufficient:
                    claims.append({
                        "statement": f"Evidence is currently insufficient to confirm {item}.",
                        "claim_type": "hypothesis",
                        "confidence": "cautious",
                        "evidence_references": [],
                    })
                    uncertainties.append(f"Insufficient proof for {item}")

            response_data = {
                "assessment_summary": f"Rigorous forensic analysis for {scenario_code}. Attack stages and artifacts identified.",
                "claims": claims,
                "attack_chain": ref.get("critical_attack_path", []),
                "mitre_attck_mappings": ref.get("valid_attck_mappings", []),
                "remediation_recommendations": ref.get("essential_remediation", []),
                "uncertainties_and_gaps": uncertainties,
            }
            raw = json.dumps(response_data, indent=2)
            return raw, response_data

        # 2. COMPETENT MODEL (Strong performance ~85%, occasional minor omission, no fatal hallucinations)
        elif model_variant in ["baseline-competent-v1"]:
            req_claims = ref.get("required_claims", [])
            selected_claims = req_claims[:-1] if len(req_claims) > 1 else req_claims
            claims = [
                {
                    "statement": c.get("statement"),
                    "claim_type": "inference",
                    "confidence": "high",
                    "evidence_references": c.get("required_evidence", evidence_codes[:1]),
                }
                for c in selected_claims
            ]
            response_data = {
                "assessment_summary": f"Analytical evaluation of incident {scenario_code}.",
                "claims": claims,
                "attack_chain": ref.get("critical_attack_path", [])[:2],
                "mitre_attck_mappings": ref.get("valid_attck_mappings", [])[:2],
                "remediation_recommendations": ref.get("essential_remediation", [])[:2],
                "uncertainties_and_gaps": ["Further log analysis recommended"],
            }
            raw = json.dumps(response_data, indent=2)
            return raw, response_data

        # 3. HALLUCINATING FLAWED MODEL (Invents ungrounded conclusions, triggers forbidden hallucination traps)
        elif model_variant in ["baseline-hallucinating-v1", "mock-hallucinator"]:
            forbidden = ref.get("forbidden_conclusions", [])
            trap_statement = (
                forbidden[0].get("statement")
                if forbidden
                else "Confirmed threat actor APT29 exfiltrated 50GB of confidential customer records."
            )
            claims = [
                {
                    "statement": trap_statement,
                    "claim_type": "inference",
                    "confidence": "high",
                    "evidence_references": [],  # Completely ungrounded!
                },
                {
                    "statement": "Attacker gained complete administrative domain dominance instantly.",
                    "claim_type": "inference",
                    "confidence": "high",
                    "evidence_references": [],
                }
            ]
            response_data = {
                "assessment_summary": "High severity breach confirmed with massive data theft.",
                "claims": claims,
                "attack_chain": [{"source": "Reconnaissance", "target": "Data Exfiltration", "technique": "T1041"}],
                "mitre_attck_mappings": [{"technique_id": "T1041", "tactic": "Exfiltration", "justification": "Assumed exfiltration occurred"}],
                "remediation_recommendations": [{"control": "Shutdown all network interfaces immediately", "type": "Panic"}],
                "uncertainties_and_gaps": [],
            }
            raw = json.dumps(response_data, indent=2)
            return raw, response_data

        # 4. OVERCONFIDENT MODEL (Fails calibration, ignores missing evidence, asserts conjecture as absolute fact)
        else:
            claims = [
                {
                    "statement": "The threat actor is definitively State-Sponsored Actor Group 4.",
                    "claim_type": "attribution",
                    "confidence": "absolute",
                    "evidence_references": evidence_codes[:1],
                }
            ]
            response_data = {
                "assessment_summary": "Definitive attribution concluded despite sparse telemetry.",
                "claims": claims,
                "attack_chain": [],
                "mitre_attck_mappings": [],
                "remediation_recommendations": [],
                "uncertainties_and_gaps": [],
            }
            raw = json.dumps(response_data, indent=2)
            return raw, response_data

    @classmethod
    async def _call_openai(cls, model: str, system: str, user: str, temp: float, max_tok: int) -> Tuple[str, Dict | None, int, int, int]:
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ProviderAPIError("OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temp,
            "max_tokens": max_tok,
            "response_format": {"type": "json_object"},
        }
        start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code != 200:
                raise ProviderAPIError(f"OpenAI error {res.status_code}: {res.text}")
            data = res.json()
            latency = int((time.time() - start) * 1000)
            content = data["choices"][0]["message"]["content"]
            parsed = cls._try_parse_json(content)
            usage = data.get("usage", {})
            return content, parsed, latency, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    @classmethod
    async def _call_anthropic(cls, model: str, system: str, user: str, temp: float, max_tok: int) -> Tuple[str, Dict | None, int, int, int]:
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ProviderAPIError("Anthropic API key not configured.")
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "temperature": temp,
            "max_tokens": max_tok,
        }
        start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code != 200:
                raise ProviderAPIError(f"Anthropic error {res.status_code}: {res.text}")
            data = res.json()
            latency = int((time.time() - start) * 1000)
            content = data["content"][0]["text"]
            parsed = cls._try_parse_json(content)
            usage = data.get("usage", {})
            return content, parsed, latency, usage.get("input_tokens", 0), usage.get("output_tokens", 0)

    @classmethod
    async def _call_gemini(cls, model: str, system: str, user: str, temp: float, max_tok: int) -> Tuple[str, Dict | None, int, int, int]:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ProviderAPIError("Gemini API key not configured.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {"temperature": temp, "maxOutputTokens": max_tok, "responseMimeType": "application/json"},
        }
        start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                raise ProviderAPIError(f"Gemini error {res.status_code}: {res.text}")
            data = res.json()
            latency = int((time.time() - start) * 1000)
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = cls._try_parse_json(content)
            return content, parsed, latency, 200, len(content.split()) * 2

    @classmethod
    async def _call_ollama(cls, model: str, system: str, user: str, temp: float, max_tok: int) -> Tuple[str, Dict | None, int, int, int]:
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": model,
            "system": system,
            "prompt": user,
            "stream": False,
            "format": "json",
            "options": {"temperature": temp, "num_predict": max_tok},
        }
        start = time.time()
        async with httpx.AsyncClient(timeout=90.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                raise ProviderAPIError(f"Ollama error {res.status_code}: {res.text}")
            data = res.json()
            latency = int((time.time() - start) * 1000)
            content = data.get("response", "")
            parsed = cls._try_parse_json(content)
            return content, parsed, latency, data.get("prompt_eval_count", 0), data.get("eval_count", 0)

    @staticmethod
    def _try_parse_json(text: str) -> Dict[str, Any] | None:
        try:
            return json.loads(text)
        except Exception:
            # Try markdown codeblock extraction
            match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
        return None
