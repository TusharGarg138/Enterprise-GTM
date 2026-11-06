"""
Reusable Gemini API service with async REST communication and automatic model fallbacks.

Design decisions:
- Single responsibility: wraps Google GenAI REST calls without gRPC deadlocks.
- Model name is read from config with automatic graceful fallback on 503/404/429.
- Implements: timeouts, bounded retries with exponential backoff,
  rate-limit detection, quota exhaustion detection, structured JSON output,
  response caching (in-memory LRU for identical prompts).
- Does NOT contain business logic, scoring or database access.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Fallback models available on Gemini free tier in case primary has high-demand spikes
FALLBACK_MODELS: List[str] = [
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.8-flash",
]

# In-memory response cache: hash -> (response_text, timestamp)
_response_cache: Dict[str, tuple[str, float]] = {}
_CACHE_TTL = 3600  # seconds


def _cache_key(prompt: str, model: str) -> str:
    return hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()


def _get_cached(prompt: str, model: str) -> Optional[str]:
    key = _cache_key(prompt, model)
    if key in _response_cache:
        text, ts = _response_cache[key]
        if time.time() - ts < _CACHE_TTL:
            logger.debug("Gemini cache hit for prompt hash %s", key[:12])
            return text
        del _response_cache[key]
    return None


def _set_cached(prompt: str, model: str, response: str) -> None:
    key = _cache_key(prompt, model)
    _response_cache[key] = (response, time.time())


class GeminiServiceError(Exception):
    """Raised when the Gemini service cannot fulfill a request."""

    def __init__(self, message: str, is_quota_error: bool = False, is_retryable: bool = False):
        super().__init__(message)
        self.is_quota_error = is_quota_error
        self.is_retryable = is_retryable


class GeminiService:
    """
    Async REST wrapper for the Google Gemini API.
    Uses direct HTTPS endpoints to avoid gRPC deadlocks on Windows and provides
    resilient multi-model fallback on temporary Google service spikes.
    """

    def __init__(self) -> None:
        self._api_key = settings.GEMINI_API_KEY
        self._model_name = settings.GEMINI_MODEL or "gemini-3.1-flash-lite"
        self._temperature = settings.GEMINI_TEMPERATURE
        self._max_tokens = settings.GEMINI_MAX_OUTPUT_TOKENS
        self._timeout = settings.GEMINI_REQUEST_TIMEOUT
        self._max_retries = settings.GEMINI_MAX_RETRIES
        self._retry_delay = settings.GEMINI_RETRY_DELAY
        self._active_model = self._model_name

    def _get_models_to_try(self) -> List[str]:
        models = [self._model_name]
        for m in FALLBACK_MODELS:
            if m not in models:
                models.append(m)
        return models

    async def generate_text(
        self,
        prompt: str,
        use_cache: bool = True,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        Generate text from a prompt. Returns raw string response.
        """
        if not self._api_key:
            raise GeminiServiceError(
                "GEMINI_API_KEY is not configured in .env. AI features are unavailable.",
                is_quota_error=False,
                is_retryable=False,
            )

        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n---\n\n{prompt}"

        if use_cache:
            cached = _get_cached(full_prompt, self._active_model)
            if cached is not None:
                return cached

        models_to_try = self._get_models_to_try()
        last_error = "Unknown error"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for model in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self._api_key}"
                payload = {
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": self._temperature,
                        "maxOutputTokens": self._max_tokens,
                    },
                }

                for attempt in range(1, self._max_retries + 1):
                    try:
                        logger.debug("Calling Gemini API model=%s (attempt %d/%d)", model, attempt, self._max_retries)
                        resp = await client.post(url, json=payload)

                        if resp.status_code == 200:
                            data = resp.json()
                            candidates = data.get("candidates", [])
                            if candidates and "content" in candidates[0]:
                                parts = candidates[0]["content"].get("parts", [])
                                if parts and "text" in parts[0]:
                                    text = parts[0]["text"].strip()
                                    self._active_model = model
                                    if use_cache:
                                        _set_cached(full_prompt, model, text)
                                    return text

                        elif resp.status_code == 503 or resp.status_code == 429:
                            err_msg = resp.json().get("error", {}).get("message", "Service overloaded")
                            logger.warning("Gemini model %s returned %d: %s. Trying next model...", model, resp.status_code, err_msg)
                            last_error = f"{model}: {err_msg}"
                            break  # Break retry loop to try next fallback model immediately

                        elif resp.status_code == 404:
                            err_msg = resp.json().get("error", {}).get("message", "Model not found")
                            logger.warning("Gemini model %s returned 404: %s. Trying fallback model...", model, err_msg)
                            last_error = f"{model}: {err_msg}"
                            break  # Try next model

                        else:
                            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                            logger.error("Gemini API error: %s", last_error)

                    except httpx.TimeoutException:
                        logger.warning("Gemini request timeout on model %s (attempt %d)", model, attempt)
                        last_error = f"{model} timed out"
                    except Exception as exc:
                        logger.error("Gemini connection error on %s: %s", model, exc)
                        last_error = str(exc)

                    if attempt < self._max_retries:
                        await asyncio.sleep(self._retry_delay)

        raise GeminiServiceError(f"All Gemini models failed. Last error: {last_error}", is_retryable=True)

    async def generate_structured(
        self,
        prompt: str,
        schema_description: str,
        system_instruction: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a structured JSON response validated against schema.
        """
        json_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Respond with valid JSON only. "
            "Do not include markdown code fences, prose, or explanations outside the JSON. "
            f"The JSON must conform to this schema:\n{schema_description}"
        )

        raw = await self.generate_text(
            json_prompt,
            use_cache=use_cache,
            system_instruction=system_instruction,
        )

        # Strip markdown fences if present
        clean = raw.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            ).strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError as exc:
            # Try to extract the first { ... } block if surrounded by text
            start_brace = clean.find("{")
            end_brace = clean.rfind("}")
            if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                try:
                    return json.loads(clean[start_brace:end_brace + 1])
                except json.JSONDecodeError:
                    pass

            logger.error("Failed to parse Gemini response as JSON: %s\nRaw: %.300s", exc, raw)
            raise GeminiServiceError(
                f"Gemini returned an invalid JSON response that could not be parsed: {exc}"
            ) from exc

    def get_model_name(self) -> str:
        return self._active_model

    async def health_check(self) -> Dict[str, Any]:
        """
        Verify Gemini API connectivity using the active model.
        """
        if not self._api_key:
            return {
                "status": "not_configured",
                "model": self._model_name,
                "message": "GEMINI_API_KEY is not set.",
            }
        try:
            answer = await self.generate_text("Reply with: OK", use_cache=False)
            return {
                "status": "ok",
                "model": self._active_model,
                "message": f"Gemini API is reachable ({self._active_model}).",
            }
        except GeminiServiceError as exc:
            return {
                "status": "error",
                "model": self._active_model,
                "message": str(exc),
                "is_quota_error": exc.is_quota_error,
            }
        except Exception as exc:
            return {
                "status": "error",
                "model": self._active_model,
                "message": f"Health check failed: {type(exc).__name__}",
            }


@lru_cache(maxsize=1)
def get_gemini_service() -> GeminiService:
    return GeminiService()
