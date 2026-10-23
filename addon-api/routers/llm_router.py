"""
LLM Router - Intelligent routing to multiple LLM providers.

Supports: OpenRouter, Groq, Together AI, Google AI Studio, OpenAI, Anthropic, DeepSeek, Ollama.
Automatic fallback, rate limiting, and task-based provider selection.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Enums & Types
# =============================================================================

class TaskType(str, Enum):
    """Types of tasks for intelligent routing."""
    LORE_RESEARCH = "lore_research"           # Deep knowledge of universes
    ENTITY_DESIGN = "entity_design"           # Minecraft entity JSON
    BEHAVIOR_SCRIPTING = "behavior_scripting" # TypeScript/JS for scripts
    JSON_SCHEMA = "json_schema"               # Strict JSON generation
    CODE_GENERATION = "code_generation"       # General code
    TEXTURE_PROMPTING = "texture_prompting"   # Prompts for image gen
    REASONING = "reasoning"                   # Complex reasoning
    PLANNING = "planning"                     # Task decomposition
    VALIDATION = "validation"                 # Validation/fixing
    DOCUMENTATION = "documentation"           # Writing docs


class ProviderName(str, Enum):
    """Supported LLM providers."""
    OPENROUTER = "openrouter"
    GROQ = "groq"
    TOGETHER = "together"
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"


@dataclass
class LLMMessage:
    """Standard message format."""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """Standard response format."""
    content: str
    provider: ProviderName
    model: str
    usage: dict[str, int] = field(default_factory=dict)  # prompt_tokens, completion_tokens, total_tokens
    latency_ms: int = 0
    finish_reason: str = "stop"


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    name: ProviderName
    base_url: str
    api_key: Optional[str]
    default_model: str
    rate_limit_rpm: int
    enabled: bool = True
    supports_streaming: bool = True
    supports_functions: bool = False
    supports_vision: bool = False
    max_context: int = 32768


# =============================================================================
# Base Provider Class
# =============================================================================

class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._request_times: list[float] = []
        self._lock = asyncio.Lock()

    @property
    @abstractmethod
    def headers(self) -> dict[str, str]:
        """HTTP headers for requests."""
        pass

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=self.headers,
                timeout=httpx.Timeout(120.0, connect=10.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _rate_limit(self):
        """Enforce rate limiting."""
        async with self._lock:
            now = time.time()
            # Remove requests older than 1 minute
            self._request_times = [t for t in self._request_times if now - t < 60]
            if len(self._request_times) >= self.config.rate_limit_rpm:
                # Wait until oldest request is > 60s old
                wait_time = 60 - (now - self._request_times[0]) + 0.1
                logger.debug(f"Rate limit hit for {self.config.name}, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                # Recurse to re-check
                await self._rate_limit()
            self._request_times.append(now)

    @abstractmethod
    def _build_payload(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        stream: bool,
        **kwargs,
    ) -> dict[str, Any]:
        """Build provider-specific request payload."""
        pass

    @abstractmethod
    def _parse_response(self, response: httpx.Response, model: str) -> LLMResponse:
        """Parse provider-specific response."""
        pass

    @abstractmethod
    async def _stream_response(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks."""
        pass

    @retry(
        wait=wait_exponential_jitter(initial=1, max=30),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
    )
    async def complete(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Complete a chat request with retry logic."""
        await self._rate_limit()

        model = model or self.config.default_model
        payload = self._build_payload(messages, model, temperature, max_tokens, False, **kwargs)

        start = time.time()
        response = await self.client.post("/chat/completions", json=payload)
        latency_ms = int((time.time() - start) * 1000)

        response.raise_for_status()
        return self._parse_response(response, model)

    async def stream(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat request."""
        await self._rate_limit()

        model = model or self.config.default_model
        async for chunk in self._stream_response(messages, model, temperature, max_tokens, **kwargs):
            yield chunk


# =============================================================================
# Provider Implementations
# =============================================================================

class OpenRouterProvider(BaseProvider):
    """OpenRouter - Gateway to 100+ models."""

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/addon-generator",
            "X-Title": "Addon Generator",
        }

    def _build_payload(self, messages, model, temperature, max_tokens, stream, **kwargs) -> dict:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        # OpenRouter specific
        if "reasoning" in kwargs:
            payload["reasoning"] = kwargs["reasoning"]
        return payload

    def _parse_response(self, response: httpx.Response, model: str) -> LLMResponse:
        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            provider=ProviderName.OPENROUTER,
            model=model,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def _stream_response(self, messages, model, temperature, max_tokens, **kwargs):
        payload = self._build_payload(messages, model, temperature, max_tokens, True, **kwargs)
        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except Exception:
                        pass


class GroqProvider(BaseProvider):
    """Groq - Ultra-fast inference, generous free tier."""

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, messages, model, temperature, max_tokens, stream, **kwargs) -> dict:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        return payload

    def _parse_response(self, response: httpx.Response, model: str) -> LLMResponse:
        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            provider=ProviderName.GROQ,
            model=model,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def _stream_response(self, messages, model, temperature, max_tokens, **kwargs):
        payload = self._build_payload(messages, model, temperature, max_tokens, True, **kwargs)
        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except Exception:
                        pass


class TogetherProvider(BaseProvider):
    """Together AI - Llama 405B, FLUX images, free tier."""

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, messages, model, temperature, max_tokens, stream, **kwargs) -> dict:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        return payload

    def _parse_response(self, response: httpx.Response, model: str) -> LLMResponse:
        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            provider=ProviderName.TOGETHER,
            model=model,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def _stream_response(self, messages, model, temperature, max_tokens, **kwargs):
        payload = self._build_payload(messages, model, temperature, max_tokens, True, **kwargs)
        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except Exception:
                        pass


class GoogleProvider(BaseProvider):
    """Google AI Studio - Gemini models, 1M context free."""

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.config.api_key or "",
        }

    def _build_payload(self, messages, model, temperature, max_tokens, stream, **kwargs) -> dict:
        # Convert to Gemini format
        system_instruction = None
        contents = []
        for m in messages:
            if m.role == "system":
                system_instruction = {"parts": [{"text": m.content}]}
            else:
                role = "user" if m.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m.content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens or 8192,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        return payload

    def _parse_response(self, response: httpx.Response, model: str) -> LLMResponse:
        data = response.json()
        candidate = data["candidates"][0]
        content = candidate["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        return LLMResponse(
            content=content,
            provider=ProviderName.GOOGLE,
            model=model,
            usage={
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
            finish_reason=candidate.get("finishReason", "STOP").lower(),
        )

    async def _stream_response(self, messages, model, temperature, max_tokens, **kwargs):
        payload = self._build_payload(messages, model, temperature, max_tokens, True, **kwargs)
        # Google uses different streaming endpoint
        async with self.client.stream("POST", f"/models/{model}:streamGenerateContent", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        import json
                        chunk = json.loads(line)
                        if "candidates" in chunk:
                            content = chunk["candidates"][0]["content"]["parts"][0]["text"]
                            yield content
                    except Exception:
                        pass


class OpenAIProvider(BaseProvider):
    """OpenAI Direct - GPT-4o, GPT-4o-mini."""

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, messages, model, temperature, max_tokens, stream, **kwargs) -> dict:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        return payload

    def _parse_response(self, response: httpx.Response, model: str) -> LLMResponse:
        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            provider=ProviderName.OPENAI,
            model=model,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def _stream_response(self, messages, model, temperature, max_tokens, **kwargs):
        payload = self._build_payload(messages, model, temperature, max_tokens, True, **kwargs)
        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except Exception:
                        pass


class AnthropicProvider(BaseProvider):
    """Anthropic Direct - Claude 3.5 Sonnet, Haiku."""

    @property
    def headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.config.api_key or "",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

    def _build_payload(self, messages, model, temperature, max_tokens, stream, **kwargs) -> dict:
        system = None
        msgs = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                msgs.append({"role": m.role, "content": m.content})

        payload = {
            "model": model,
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        return payload

    def _parse_response(self, response: httpx.Response, model: str) -> LLMResponse:
        data = response.json()
        content = "".join(block["text"] for block in data["content"] if block["type"] == "text")
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            provider=ProviderName.ANTHROPIC,
            model=model,
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            },
            finish_reason=data.get("stop_reason", "end_turn"),
        )

    async def _stream_response(self, messages, model, temperature, max_tokens, **kwargs):
        payload = self._build_payload(messages, model, temperature, max_tokens, True, **kwargs)
        async with self.client.stream("POST", "/messages", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    try:
                        import json
                        chunk = json.loads(data)
                        if chunk.get("type") == "content_block_delta":
                            yield chunk["delta"]["text"]
                    except Exception:
                        pass


class DeepSeekProvider(BaseProvider):
    """DeepSeek Direct - Very cheap, OpenAI-compatible."""

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, messages, model, temperature, max_tokens, stream, **kwargs) -> dict:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        return payload

    def _parse_response(self, response: httpx.Response, model: str) -> LLMResponse:
        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            provider=ProviderName.DEEPSEEK,
            model=model,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def _stream_response(self, messages, model, temperature, max_tokens, **kwargs):
        payload = self._build_payload(messages, model, temperature, max_tokens, True, **kwargs)
        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except Exception:
                        pass


class OllamaProvider(BaseProvider):
    """Ollama Local - Privacy-first, no API key needed."""

    @property
    def headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _build_payload(self, messages, model, temperature, max_tokens, stream, **kwargs) -> dict:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        return payload

    def _parse_response(self, response: httpx.Response, model: str) -> LLMResponse:
        data = response.json()
        return LLMResponse(
            content=data["message"]["content"],
            provider=ProviderName.OLLAMA,
            model=model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
            finish_reason=data.get("done_reason", "stop"),
        )

    async def _stream_response(self, messages, model, temperature, max_tokens, **kwargs):
        payload = self._build_payload(messages, model, temperature, max_tokens, True, **kwargs)
        async with self.client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        import json
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]
                        if chunk.get("done"):
                            break
                    except Exception:
                        pass


# =============================================================================
# Provider Factory
# =============================================================================

def create_provider(name: ProviderName) -> BaseProvider:
    """Create a provider instance from settings."""
    s = settings

    configs = {
        ProviderName.OPENROUTER: ProviderConfig(
            name=ProviderName.OPENROUTER,
            base_url=s.OPENROUTER_BASE_URL,
            api_key=s.OPENROUTER_API_KEY,
            default_model=s.OPENROUTER_DEFAULT_MODEL,
            rate_limit_rpm=s.RATE_LIMIT_OPENROUTER,
            enabled=s.ENABLE_OPENROUTER and s.has_openrouter,
            max_context=128000,
        ),
        ProviderName.GROQ: ProviderConfig(
            name=ProviderName.GROQ,
            base_url=s.GROQ_BASE_URL,
            api_key=s.GROQ_API_KEY,
            default_model=s.GROQ_DEFAULT_MODEL,
            rate_limit_rpm=s.RATE_LIMIT_GROQ,
            enabled=s.ENABLE_GROQ and s.has_groq,
            max_context=131072,
        ),
        ProviderName.TOGETHER: ProviderConfig(
            name=ProviderName.TOGETHER,
            base_url=s.TOGETHER_BASE_URL,
            api_key=s.TOGETHER_API_KEY,
            default_model=s.TOGETHER_DEFAULT_MODEL,
            rate_limit_rpm=s.RATE_LIMIT_TOGETHER,
            enabled=s.ENABLE_TOGETHER and s.has_together,
            max_context=128000,
        ),
        ProviderName.GOOGLE: ProviderConfig(
            name=ProviderName.GOOGLE,
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key=s.GOOGLE_API_KEY,
            default_model=s.GOOGLE_DEFAULT_MODEL,
            rate_limit_rpm=s.RATE_LIMIT_GOOGLE,
            enabled=s.ENABLE_GOOGLE and s.has_google,
            max_context=1000000,
        ),
        ProviderName.OPENAI: ProviderConfig(
            name=ProviderName.OPENAI,
            base_url=s.OPENAI_BASE_URL,
            api_key=s.OPENAI_API_KEY,
            default_model=s.OPENAI_DEFAULT_MODEL,
            rate_limit_rpm=s.RATE_LIMIT_OPENAI,
            enabled=s.ENABLE_OPENAI and s.has_openai,
            max_context=128000,
        ),
        ProviderName.ANTHROPIC: ProviderConfig(
            name=ProviderName.ANTHROPIC,
            base_url="https://api.anthropic.com/v1",
            api_key=s.ANTHROPIC_API_KEY,
            default_model=s.ANTHROPIC_DEFAULT_MODEL,
            rate_limit_rpm=s.RATE_LIMIT_ANTHROPIC,
            enabled=s.ENABLE_ANTHROPIC and s.has_anthropic,
            max_context=200000,
        ),
        ProviderName.DEEPSEEK: ProviderConfig(
            name=ProviderName.DEEPSEEK,
            base_url=s.DEEPSEEK_BASE_URL,
            api_key=s.DEEPSEEK_API_KEY,
            default_model=s.DEEPSEEK_DEFAULT_MODEL,
            rate_limit_rpm=s.RATE_LIMIT_DEEPSEEK,
            enabled=s.ENABLE_DEEPSEEK and s.has_deepseek,
            max_context=64000,
        ),
        ProviderName.OLLAMA: ProviderConfig(
            name=ProviderName.OLLAMA,
            base_url=s.OLLAMA_BASE_URL,
            api_key=None,
            default_model=s.OLLAMA_DEFAULT_MODEL,
            rate_limit_rpm=s.RATE_LIMIT_OLLAMA,
            enabled=s.ENABLE_OLLAMA and s.has_ollama,
            max_context=32768,
        ),
    }

    config = configs[name]
    if not config.enabled:
        raise ValueError(f"Provider {name} is not enabled or missing API key")

    providers = {
        ProviderName.OPENROUTER: OpenRouterProvider,
        ProviderName.GROQ: GroqProvider,
        ProviderName.TOGETHER: TogetherProvider,
        ProviderName.GOOGLE: GoogleProvider,
        ProviderName.OPENAI: OpenAIProvider,
        ProviderName.ANTHROPIC: AnthropicProvider,
        ProviderName.DEEPSEEK: DeepSeekProvider,
        ProviderName.OLLAMA: OllamaProvider,
    }

    return providers[name](config)


# =============================================================================
# LLMRouter - Main Entry Point
# =============================================================================

# Task-to-provider routing preferences (ordered by priority)
TASK_ROUTING: dict[TaskType, list[ProviderName]] = {
    TaskType.LORE_RESEARCH: [
        ProviderName.OPENROUTER,      # GPT-4o, Claude 3.5, DeepSeek-R1
        ProviderName.GOOGLE,          # Gemini 1.5 Pro (1M context)
        ProviderName.TOGETHER,        # Llama 405B
        ProviderName.GROQ,            # Llama 3.3 70B
    ],
    TaskType.ENTITY_DESIGN: [
        ProviderName.OPENROUTER,      # Best for structured JSON
        ProviderName.GROQ,            # Fast, good at JSON
        ProviderName.TOGETHER,
    ],
    TaskType.BEHAVIOR_SCRIPTING: [
        ProviderName.OPENROUTER,      # GPT-4o/DeepSeek-Coder best for code
        ProviderName.TOGETHER,        # DeepSeek-Coder, CodeLlama
        ProviderName.GROQ,
    ],
    TaskType.JSON_SCHEMA: [
        ProviderName.GROQ,            # Fast, reliable JSON
        ProviderName.OPENROUTER,
        ProviderName.TOGETHER,
    ],
    TaskType.CODE_GENERATION: [
        ProviderName.OPENROUTER,      # Best code models
        ProviderName.TOGETHER,        # DeepSeek-Coder
        ProviderName.GROQ,
    ],
    TaskType.TEXTURE_PROMPTING: [
        ProviderName.TOGETHER,        # FLUX prompting expertise
        ProviderName.OPENROUTER,
        ProviderName.GROQ,
    ],
    TaskType.REASONING: [
        ProviderName.OPENROUTER,      # o1, DeepSeek-R1, Claude 3.5
        ProviderName.GOOGLE,          # Gemini 1.5 Pro
        ProviderName.TOGETHER,
    ],
    TaskType.PLANNING: [
        ProviderName.OPENROUTER,      # Best planning
        ProviderName.GOOGLE,
        ProviderName.TOGETHER,
    ],
    TaskType.VALIDATION: [
        ProviderName.GROQ,            # Fast validation
        ProviderName.OPENROUTER,
    ],
    TaskType.DOCUMENTATION: [
        ProviderName.OPENROUTER,
        ProviderName.GROQ,
        ProviderName.TOGETHER,
    ],
}


class LLMRouter:
    """Intelligent LLM router with automatic fallback."""

    def __init__(self):
        self._providers: dict[ProviderName, BaseProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all enabled providers."""
        for provider_name in ProviderName:
            try:
                if provider_name in [ProviderName.OPENROUTER, ProviderName.GROQ, ProviderName.TOGETHER,
                                     ProviderName.GOOGLE, ProviderName.OPENAI, ProviderName.ANTHROPIC,
                                     ProviderName.DEEPSEEK, ProviderName.OLLAMA]:
                    provider = create_provider(provider_name)
                    self._providers[provider_name] = provider
                    logger.info(f"Initialized provider: {provider_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_name}: {e}")

    @property
    def available_providers(self) -> list[ProviderName]:
        return list(self._providers.keys())

    def _select_provider(self, task_type: TaskType, preferred: Optional[ProviderName] = None) -> ProviderName:
        """Select best provider for task type."""
        if preferred and preferred in self._providers:
            return preferred

        routing = TASK_ROUTING.get(task_type, [ProviderName.GROQ, ProviderName.OPENROUTER, ProviderName.TOGETHER])
        for provider in routing:
            if provider in self._providers:
                return provider

        # Fallback to any available
        if self._providers:
            return list(self._providers.keys())[0]

        raise RuntimeError("No LLM providers available! Configure at least one in .env")

    async def complete(
        self,
        messages: list[LLMMessage],
        task_type: TaskType = TaskType.CODE_GENERATION,
        preferred_provider: Optional[ProviderName] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Complete with automatic fallback on failure."""
        provider_name = self._select_provider(task_type, preferred_provider)
        provider = self._providers[provider_name]

        try:
            logger.debug(f"Routing {task_type} to {provider_name} ({provider.config.default_model})")
            return await provider.complete(messages, model, temperature, max_tokens, **kwargs)
        except Exception as e:
            logger.warning(f"Provider {provider_name} failed: {e}. Trying fallback...")

            # Try fallbacks
            routing = TASK_ROUTING.get(task_type, [])
            for fallback in routing:
                if fallback != provider_name and fallback in self._providers:
                    try:
                        logger.info(f"Falling back to {fallback}")
                        return await self._providers[fallback].complete(messages, model, temperature, max_tokens, **kwargs)
                    except Exception as fe:
                        logger.warning(f"Fallback {fallback} also failed: {fe}")

            # Last resort: try any remaining provider
            for name, prov in self._providers.items():
                if name not in [provider_name] + routing:
                    try:
                        logger.info(f"Last resort: {name}")
                        return await prov.complete(messages, model, temperature, max_tokens, **kwargs)
                    except Exception:
                        continue

            raise RuntimeError(f"All providers failed for task {task_type}")

    async def stream(
        self,
        messages: list[LLMMessage],
        task_type: TaskType = TaskType.CODE_GENERATION,
        preferred_provider: Optional[ProviderName] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream with automatic fallback."""
        provider_name = self._select_provider(task_type, preferred_provider)
        provider = self._providers[provider_name]

        try:
            async for chunk in provider.stream(messages, model, temperature, max_tokens, **kwargs):
                yield chunk
        except Exception as e:
            logger.warning(f"Stream from {provider_name} failed: {e}. Falling back to non-streaming.")
            # Fallback to non-streaming complete
            response = await self.complete(messages, task_type, preferred_provider, model, temperature, max_tokens, **kwargs)
            yield response.content

    async def close(self):
        """Close all provider connections."""
        for provider in self._providers.values():
            await provider.close()


# Global router instance
_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Get or create global router instance."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


# Convenience functions
async def complete(
    messages: list[LLMMessage] | list[dict[str, str]],
    task_type: TaskType = TaskType.CODE_GENERATION,
    **kwargs,
) -> LLMResponse:
    """Convenience function for simple completion."""
    router = get_router()
    if isinstance(messages[0], dict):
        messages = [LLMMessage(**m) for m in messages]
    return await router.complete(messages, task_type, **kwargs)


async def stream(
    messages: list[LLMMessage] | list[dict[str, str]],
    task_type: TaskType = TaskType.CODE_GENERATION,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """Convenience function for streaming."""
    router = get_router()
    if isinstance(messages[0], dict):
        messages = [LLMMessage(**m) for m in messages]
    async for chunk in router.stream(messages, task_type, **kwargs):
        yield chunk
