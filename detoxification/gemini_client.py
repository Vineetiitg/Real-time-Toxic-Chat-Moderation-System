"""
SafeChat Detoxification — Google Gemini API Client

Features:
  - Lightweight direct REST API calls via httpx.AsyncClient (no bulky SDK required)
  - Full support for gemini-2.5-flash / gemini-2.0-flash / gemini-1.5-flash
  - OpenAI-compatible fallback (AICredits, OpenRouter, Groq, Ollama)
  - Exponential backoff with random jitter on rate limits (429) & network errors
  - Streaming Server-Sent Events (SSE) support for real-time WebSocket generation
"""

import asyncio
import json
import logging
import random
import re
from typing import AsyncGenerator, Dict, List, Optional, Any

import httpx

from detoxification.config import DetoxConfig

logger = logging.getLogger("GeminiClient")

# Language display name mapping for prompt conditioning
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi (Devanagari)",
    "hi-en": "Hinglish (Hindi-English code-mixed in Latin script)",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "indic-en": "Indian English / Code-mixed",
}


def build_detox_prompt(
    text: str,
    language: str,
    categories: Optional[Dict[str, float]] = None,
    context: Optional[List[str]] = None,
) -> str:
    """Build a structured prompt enforcing intent-preserving style transfer."""
    lang_name = LANGUAGE_NAMES.get(language, language)

    # Categories information
    flagged_info = ""
    if categories:
        flagged = {k: v for k, v in categories.items() if v >= 0.3}
        if flagged:
            flagged_info = f"Detected toxicity tags: {', '.join(flagged.keys())}\n"

    # Conversational context
    context_str = ""
    if context:
        recent = context[-4:]
        lines = "\n".join(f"  [{i+1}] {turn}" for i, turn in enumerate(recent))
        context_str = f"Conversation Context (previous turns):\n{lines}\n\n"

    return f"""You are an expert real-time conversational chat assistant.

TASK: Rewrite the following toxic or abusive message so that it is polite and respectful, WHILE STRICTLY PRESERVING THE SPEAKER'S EXACT INTENT, MEANING, QUESTIONS, AND CONVERSATIONAL TONE.

{context_str}TOXIC MESSAGE: "{text}"
{flagged_info}Language to use: {lang_name}

STRICT RULES:
1. Output ONLY the rewritten sentence. No preamble, no quotes, no explanations.
2. Maintain the EXACT SAME language and script. If the input is Hinglish, respond in Hinglish. If Devanagari Hindi, respond in Devanagari Hindi. If English, respond in English.
3. Keep the natural conversational tone. Do NOT make it sound like a corporate apology or polite reminder.
4. If the message has a question or request (e.g. asking why something broke, or telling someone to hurry), keep that exact question/request.
5. Keep the length concise, similar to the original text.

REWRITTEN:"""


def build_arbitration_prompt(
    text: str,
    language: str,
    roberta_labels: Optional[List[str]] = None,
    context: Optional[List[str]] = None,
) -> str:
    """Build a prompt asking Gemini to arbitrate toxicity (safe vs toxic) and detoxify if toxic."""
    lang_name = LANGUAGE_NAMES.get(language, language)

    context_str = ""
    if context:
        recent = context[-4:]
        lines = "\n".join(f"  [{i+1}] {turn}" for i, turn in enumerate(recent))
        context_str = f"Conversation Context (previous turns):\n{lines}\n\n"

    roberta_hint = ""
    if roberta_labels:
        roberta_hint = f"Fast Classifier Flag: Flagged as potential {', '.join(roberta_labels)}\n"

    return f"""You are SafeChat Supreme Moderator and Conversational Arbitrator.

TASK:
1. Carefully evaluate if the following chat message is genuinely TOXIC/ABUSIVE (hate speech, severe insults, harassment, real threats) OR if it is SAFE (benign colloquial slang, gaming excitement, friendly banter, e.g. 'he got destroyed in game', 'this pizza is killer').
2. If TOXIC: Rewrite it to be polite, civil, and respectful, WHILE STRICTLY PRESERVING THE SPEAKER'S CORE INTENT AND TONE in the same language/script ({lang_name}).
3. If SAFE: Confirm it is safe, and return the original text unchanged.

{context_str}{roberta_hint}MESSAGE TO EVALUATE: "{text}"
Language: {lang_name}

RESPONSE FORMAT:
Respond STRICTLY with a valid JSON object with NO surrounding markdown backticks or explanations:
{{
  "is_toxic": true or false,
  "confidence": 0.0 to 1.0,
  "severity": "SAFE" or "MEDIUM" or "HIGH",
  "active_labels": ["toxic", "insult", ...],
  "detoxified_text": "polite rewrite if toxic, or exact original text if safe",
  "reason": "short explanation of context and final verdict"
}}
"""


class GeminiClient:
    """Async client for Google Gemini API with exponential backoff retries."""

    def __init__(self, config: Optional[DetoxConfig] = None):
        self.cfg = config or DetoxConfig()
        self._openai_client = None

        if self.cfg.base_url or (self.cfg.api_key and self.cfg.api_key.startswith("sk-")):
            try:
                from openai import AsyncOpenAI
                self._openai_client = AsyncOpenAI(
                    api_key=self.cfg.api_key,
                    base_url=self.cfg.base_url or "https://generativelanguage.googleapis.com/v1beta/openai/",
                )
                logger.info(f"Initialized OpenAI-compatible client (model: {self.cfg.model})")
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")

    @property
    def is_configured(self) -> bool:
        """Check if an API key is provided."""
        return bool(self.cfg.api_key and self.cfg.api_key.strip())

    async def generate(
        self,
        prompt: str,
    ) -> Optional[str]:
        """
        Send generation request to Gemini with exponential backoff retry.
        """
        if not self.is_configured:
            return None

        # Route 0: OpenRouter auto-detection (when key starts with sk-or-)
        if self.cfg.api_key.startswith("sk-or-"):
            return await self._generate_openrouter(prompt)

        # Route 1: OpenAI-compatible client (if configured)
        if self._openai_client:
            return await self._generate_openai(prompt)

        # Route 2: Native Google Gemini REST API via httpx
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.cfg.model}:generateContent?key={self.cfg.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.cfg.temperature,
                "maxOutputTokens": self.cfg.max_tokens,
            },
        }

        delay = self.cfg.initial_retry_delay
        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.cfg.request_timeout_seconds) as client:
                    response = await client.post(url, json=payload)

                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
                        return None

                    elif response.status_code == 404:
                        # Model name might be unsupported (e.g. 2.5) — fallback to gemini-1.5-flash or gemini-2.0-flash
                        alt_model = "gemini-1.5-flash" if "1.5" not in url else "gemini-2.0-flash"
                        logger.warning(f"Gemini model not found (404). Falling back to {alt_model}...")
                        url = (
                            f"https://generativelanguage.googleapis.com/v1beta/models/"
                            f"{alt_model}:generateContent?key={self.cfg.api_key}"
                        )
                        continue

                    elif response.status_code in (429, 500, 502, 503, 504):
                        # Transient error — retry with jitter
                        jitter = random.uniform(0.1, 0.3)
                        logger.warning(
                            f"Gemini API {response.status_code} (attempt {attempt}/{self.cfg.max_retries}). "
                            f"Retrying in {delay + jitter:.2f}s..."
                        )
                        await asyncio.sleep(delay + jitter)
                        delay *= self.cfg.backoff_factor
                    else:
                        logger.error(f"Gemini API error {response.status_code}: {response.text}")
                        return None

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                jitter = random.uniform(0.1, 0.3)
                logger.warning(
                    f"Gemini network issue {e} (attempt {attempt}/{self.cfg.max_retries}). "
                    f"Retrying in {delay + jitter:.2f}s..."
                )
                await asyncio.sleep(delay + jitter)
                delay *= self.cfg.backoff_factor
            except Exception as e:
                logger.error(f"Unexpected error in Gemini API call: {e}")
                return None

        logger.error(f"Gemini API failed after {self.cfg.max_retries} retries.")
        return None

    async def generate_arbitration(
        self,
        text: str,
        language: str,
        roberta_labels: Optional[List[str]] = None,
        context: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Call Gemini to arbitrate classification (safe vs toxic) and provide a detoxified rewrite.
        Parses structured JSON response.
        """
        prompt = build_arbitration_prompt(text, language, roberta_labels, context)
        raw = await self.generate(prompt)
        if not raw:
            return None

        # Clean JSON from raw text (strip markdown code blocks if any)
        cleaned_json = raw.strip()
        if cleaned_json.startswith("```json"):
            cleaned_json = cleaned_json[7:]
        elif cleaned_json.startswith("```"):
            cleaned_json = cleaned_json[3:]
        if cleaned_json.endswith("```"):
            cleaned_json = cleaned_json[:-3]
        cleaned_json = cleaned_json.strip()

        try:
            parsed = json.loads(cleaned_json)
            is_toxic = bool(parsed.get("is_toxic", False))
            return {
                "is_toxic": is_toxic,
                "severity": parsed.get("severity", "MEDIUM" if is_toxic else "SAFE"),
                "confidence": float(parsed.get("confidence", 0.95)),
                "active_labels": parsed.get("active_labels", []),
                "detoxified_text": parsed.get("detoxified_text", text),
                "reason": parsed.get("reason", ""),
            }
        except Exception as e:
            logger.warning(f"Could not parse Gemini arbitration JSON ({e}). Raw response: {raw[:100]}")
            return {
                "is_toxic": True,
                "severity": "MEDIUM",
                "confidence": 0.8,
                "active_labels": roberta_labels or ["toxic"],
                "detoxified_text": raw.strip(),
                "reason": "Fallback raw text parsing",
            }

    async def _generate_openrouter(self, prompt: str) -> Optional[str]:
        """Direct async HTTP call to OpenRouter API (when using OpenRouter keys)."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "HTTP-Referer": "https://safechat.dev",
            "X-Title": "SafeChat Moderation",
        }
        # Supports google/gemini-2.5-flash on OpenRouter
        model_name = "google/gemini-2.5-flash"
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.cfg.temperature,
            "max_tokens": self.cfg.max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=self.cfg.request_timeout_seconds) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                elif res.status_code == 404:
                    # Try gemini-2.5-flash-lite
                    payload["model"] = "google/gemini-2.5-flash-lite"
                    res2 = await client.post(url, json=payload, headers=headers)
                    if res2.status_code == 200:
                        data = res2.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "").strip()
                logger.error(f"OpenRouter API error {res.status_code}: {res.text}")
                return f"ERROR_{res.status_code}: {res.text}"
        except Exception as e:
            logger.error(f"OpenRouter API call failed: {e}")
            return f"EXCEPTION: {str(e)}"
        return None

    async def _generate_openai(self, prompt: str) -> Optional[str]:
        """Call via OpenAI-compatible SDK with retries."""
        delay = self.cfg.initial_retry_delay
        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                response = await self._openai_client.chat.completions.create(
                    model=self.cfg.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.cfg.temperature,
                    max_tokens=self.cfg.max_tokens,
                )
                if response.choices and response.choices[0].message:
                    return response.choices[0].message.content.strip()
                return None
            except Exception as e:
                logger.warning(f"OpenAI proxy attempt {attempt} failed: {e}")
                await asyncio.sleep(delay)
                delay *= self.cfg.backoff_factor
        return None

    async def stream_generate(
        self,
        prompt: str,
    ) -> AsyncGenerator[str, None]:
        """
        Stream generation tokens from Gemini via Server-Sent Events (SSE).
        """
        if not self.is_configured:
            return

        if self._openai_client:
            try:
                stream = await self._openai_client.chat.completions.create(
                    model=self.cfg.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.cfg.temperature,
                    max_tokens=self.cfg.max_tokens,
                    stream=True,
                )
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
            except Exception as e:
                logger.error(f"OpenAI proxy streaming failed: {e}")
                return

        # Native SSE streaming with httpx
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.cfg.model}:streamGenerateContent?alt=sse&key={self.cfg.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.cfg.temperature,
                "maxOutputTokens": self.cfg.max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.cfg.request_timeout_seconds) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        logger.error(f"Gemini SSE error: {response.status_code}")
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            raw_json = line[6:].strip()
                            if not raw_json or raw_json == "[DONE]":
                                continue
                            try:
                                data = json.loads(raw_json)
                                candidates = data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for part in parts:
                                        chunk = part.get("text", "")
                                        if chunk:
                                            yield chunk
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Gemini streaming exception: {e}")

