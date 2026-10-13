# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("OmniTwin.LLMProvider")


class ProviderAPIError(Exception):
    """Raised when an upstream LLM provider API returns an error or fails."""
    def __init__(self, provider: str, status_code: int, message: str):
        super().__init__(f"[{provider}] HTTP {status_code}: {message}")
        self.provider = provider
        self.status_code = status_code
        self.message = message


class BaseLLMProvider(ABC):
    """Abstract interface for all LLM providers in the OmniTwin cognitive engine."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g., 'pi-gateway', 'openrouter', 'vertex', 'offline-simulator')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Quick pre-flight check to determine if provider is configured and reachable."""
        pass

    @abstractmethod
    def generate(self, system_prompt: str, user_message: str, **kwargs) -> str:
        """
        Executes a completion turn with the provider.
        Returns the raw response text from the model.
        """
        pass


class PiGatewayProvider(BaseLLMProvider):
    """
    Connects to local/private PI Gateway (https://pi.dev).
    Exposes local and subscription models via OpenAI-compatible /v1/chat/completions.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 20.0,
    ):
        self.base_url = (base_url or os.environ.get("PI_GATEWAY_URL") or "http://127.0.0.1:4000/v1").rstrip("/")
        self.model = model or os.environ.get("PI_GATEWAY_MODEL") or "deepseek/deepseek-v4-flash"
        self.api_key = api_key or os.environ.get("PI_GATEWAY_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "pi-gateway"

    def is_available(self) -> bool:
        """Pings PI Gateway /healthz or /v1/models endpoint."""
        try:
            health_url = self.base_url.replace("/v1", "") + "/healthz"
            req = urllib.request.Request(health_url, headers={"User-Agent": "OmniTwin-Core"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass

        try:
            models_url = f"{self.base_url}/models"
            headers = {"User-Agent": "OmniTwin-Core"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            req = urllib.request.Request(models_url, headers=headers)
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(self, system_prompt: str, user_message: str, **kwargs) -> str:
        endpoint = f"{self.base_url}/chat/completions"
        model_name = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 600)

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OmniTwin-Core",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                choices = body.get("choices", [])
                if not choices:
                    raise ProviderAPIError(self.name, resp.status, "Empty choices array in response")
                return choices[0].get("message", {}).get("content", "").strip()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.warning(f"[PiGatewayProvider] HTTP {e.code} error: {err_body}")
            raise ProviderAPIError(self.name, e.code, err_body)
        except urllib.error.URLError as e:
            logger.warning(f"[PiGatewayProvider] Connection error: {e.reason}")
            raise ProviderAPIError(self.name, 503, str(e.reason))
        except Exception as e:
            logger.warning(f"[PiGatewayProvider] Unexpected error: {e}")
            raise ProviderAPIError(self.name, 500, str(e))


class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter cloud provider (https://openrouter.ai).
    Routes to models from Anthropic, Google, OpenAI, Meta, DeepSeek.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 25.0,
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY") or ""
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = model or os.environ.get("OPENROUTER_MODEL") or "google/gemini-2.5-flash"
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "openrouter"

    def is_available(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("dummy"))

    def generate(self, system_prompt: str, user_message: str, **kwargs) -> str:
        if not self.api_key:
            raise ProviderAPIError(self.name, 401, "OPENROUTER_API_KEY is not configured")

        endpoint = f"{self.base_url}/chat/completions"
        model_name = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 600)

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/imMamdouhaboammar/OmniTwin",
            "X-Title": "OmniTwin Cognitive Engine",
            "User-Agent": "OmniTwin-Core",
        }

        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                choices = body.get("choices", [])
                if not choices:
                    raise ProviderAPIError(self.name, resp.status, "Empty choices array in response")
                return choices[0].get("message", {}).get("content", "").strip()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.warning(f"[OpenRouterProvider] HTTP {e.code} error: {err_body}")
            raise ProviderAPIError(self.name, e.code, err_body)
        except urllib.error.URLError as e:
            logger.warning(f"[OpenRouterProvider] Connection error: {e.reason}")
            raise ProviderAPIError(self.name, 503, str(e.reason))
        except Exception as e:
            logger.warning(f"[OpenRouterProvider] Unexpected error: {e}")
            raise ProviderAPIError(self.name, 500, str(e))


class GoogleVertexGeminiProvider(BaseLLMProvider):
    """
    Google Cloud Vertex AI & Google Gemini REST Provider.
    Supports either GEMINI_API_KEY (direct Gemini API) or VERTEX_PROJECT_ID (Google Cloud).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 25.0,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or ""
        self.project_id = project_id or os.environ.get("VERTEX_PROJECT_ID") or ""
        self.location = location or os.environ.get("VERTEX_LOCATION") or "us-central1"
        self.model = model or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "vertex-gemini"

    def is_available(self) -> bool:
        if self.api_key and not self.api_key.startswith("dummy"):
            return True
        if self.project_id and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            return True
        return False

    def generate(self, system_prompt: str, user_message: str, **kwargs) -> str:
        model_name = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 600)

        if self.api_key:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
        else:
            endpoint = (
                f"https://{self.location}-aiplatform.googleapis.com/v1/projects/"
                f"{self.project_id}/locations/{self.location}/publishers/google/models/{model_name}:generateContent"
            )
            token = os.environ.get("VERTEX_ACCESS_TOKEN", "")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_message}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                candidates = body.get("candidates", [])
                if not candidates:
                    raise ProviderAPIError(self.name, resp.status, "Empty candidates in Gemini response")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    return ""
                return parts[0].get("text", "").strip()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.warning(f"[GoogleVertexGeminiProvider] HTTP {e.code} error: {err_body}")
            raise ProviderAPIError(self.name, e.code, err_body)
        except urllib.error.URLError as e:
            logger.warning(f"[GoogleVertexGeminiProvider] Connection error: {e.reason}")
            raise ProviderAPIError(self.name, 503, str(e.reason))
        except Exception as e:
            logger.warning(f"[GoogleVertexGeminiProvider] Unexpected error: {e}")
            raise ProviderAPIError(self.name, 500, str(e))


class OfflineSimulatorProvider(BaseLLMProvider):
    """
    Deterministic in-character fallback generator.
    Produces grounded responses from delivered EPs when no cloud provider is configured.
    Supports English and Arabic naturally.
    """

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "offline-simulator"

    def is_available(self) -> bool:
        return True

    def generate(self, system_prompt: str, user_message: str, **kwargs) -> str:
        ep_matches = re.findall(r'<point id="([^"]+)">([^<]+)</point>', system_prompt)
        primary_id = ep_matches[0][0] if ep_matches else None
        primary_text = ep_matches[0][1] if ep_matches else ""

        move_match = re.search(r'<assigned_social_move>([^<]+)</assigned_social_move>', system_prompt)
        social_move = move_match.group(1) if move_match else "answer"

        is_ar = bool(re.search(r"[\u0600-\u06FF]", user_message) or re.search(r"[\u0600-\u06FF]", primary_text))
        tag = f" [{primary_id}]" if primary_id else ""

        if is_ar:
            if social_move == "check_in":
                return f"أهلاً، أخبارك إيه؟ لعلك بخير.{tag}"
            elif social_move == "tease":
                return "شايفك بتهزر! ماشي يا سيدي."
            elif social_move == "minimal_presence":
                return "طاقتي منخفضة شوية دلوقتي، هكلمك أول ما أفضى."
            elif social_move == "give_opinion":
                if primary_text:
                    return f"رأيي في الموضوع ده: {primary_text}.{tag}"
                return "شايف إنك تفكر فيها بهدوء الأول."
            elif social_move == "practical_help":
                if primary_text:
                    return f"الحل العملي للجزئية دي: {primary_text}.{tag}"
                return "قولي التفاصيل ونرتبها سوا خطوة بخطوة."
            else:
                if primary_text:
                    return f"تمام، {primary_text}.{tag}"
                return "تمام، سامعك ومعاك."
        else:
            if social_move == "check_in":
                return f"Hey there, good to hear from you.{tag}"
            elif social_move == "tease":
                return "Look who decided to check in!"
            elif social_move == "minimal_presence":
                return "A bit drained right now, let's catch up shortly."
            elif social_move == "give_opinion":
                if primary_text:
                    return f"From my perspective: {primary_text}.{tag}"
                return "I suggest taking a beat and considering the long-term impact."
            elif social_move == "practical_help":
                if primary_text:
                    return f"Here is how I approach this: {primary_text}.{tag}"
                return "Share the exact details and let's work through it step by step."
            else:
                if primary_text:
                    return f"Understood. {primary_text}.{tag}"
                return "Understood, I am with you."


class MultiProviderRouter(BaseLLMProvider):
    """
    Smart Multi-Provider Router with priority chaining and automatic failover:
    1. PI Gateway (Preferred local/edge gateway)
    2. OpenRouter (Cloud multi-model router)
    3. Google Vertex / Gemini (Direct cloud provider)
    4. Offline Simulator (Deterministic grounded safety net)
    """

    def __init__(
        self,
        providers: Optional[List[BaseLLMProvider]] = None,
        allow_fallback: bool = True,
    ):
        if providers:
            self.providers = providers
        else:
            self.providers = [
                PiGatewayProvider(),
                OpenRouterProvider(),
                GoogleVertexGeminiProvider(),
                OfflineSimulatorProvider(),
            ]
        self.allow_fallback = allow_fallback
        self.last_used_provider: Optional[str] = None

    @property
    def name(self) -> str:
        return "multi-provider-router"

    def is_available(self) -> bool:
        return any(p.is_available() for p in self.providers)

    def get_provider_status(self) -> List[Dict[str, Any]]:
        return [{"provider": p.name, "available": p.is_available()} for p in self.providers]

    def generate(self, system_prompt: str, user_message: str, **kwargs) -> str:
        errors = []
        for p in self.providers:
            if not p.is_available() and p.name != "offline-simulator":
                continue

            try:
                response = p.generate(system_prompt, user_message, **kwargs)
                if response:
                    self.last_used_provider = p.name
                    return response
            except Exception as e:
                errors.append(f"{p.name}: {e}")
                if not self.allow_fallback and p.name != "offline-simulator":
                    raise

        fallback = OfflineSimulatorProvider()
        self.last_used_provider = fallback.name
        return fallback.generate(system_prompt, user_message, **kwargs)


def get_default_provider() -> BaseLLMProvider:
    """Factory creating the configured LLM provider."""
    explicit_provider = os.environ.get("LLM_PROVIDER", "auto").lower()

    if explicit_provider in ("pi-gateway", "pi"):
        return PiGatewayProvider()
    elif explicit_provider == "openrouter":
        return OpenRouterProvider()
    elif explicit_provider in ("vertex", "gemini"):
        return GoogleVertexGeminiProvider()
    elif explicit_provider in ("simulator", "offline"):
        return OfflineSimulatorProvider()
    else:
        return MultiProviderRouter()
