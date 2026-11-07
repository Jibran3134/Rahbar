"""OpenAI-compatible hosted provider (section 3.5).

Targets any OpenAI-compatible endpoint: Groq, OpenAI, Together, Mistral, etc.
Set LLM_PROVIDER=hosted, HOSTED_BASE_URL, LLM_MODEL and LLM_API_KEY.

Wire format used by this provider:
  POST {HOSTED_BASE_URL}/chat/completions
  Authorization: Bearer {LLM_API_KEY}
  Content-Type: application/json
  Body: OpenAI chat-completions JSON with response_format={type:"json_object"}

The provider reuses the same SYSTEM_PROMPT and arithmetic helpers as the
Ollama provider so both paths produce identical grounding behaviour.
"""

from __future__ import annotations

import json
import logging

import httpx
from pydantic import ValidationError

from ...config import Settings
from ...schemas import Answer, Passage
from .base import ProviderError, ProviderFailureKind
from .citations import normalize_inline_citations
from ...routes import metrics
from ...services.arithmetic import comparison_hints
from .ollama import SYSTEM_PROMPT  # shared prompt keeps both paths aligned

log = logging.getLogger("rahbar.hosted")

# Groq's JSON-object mode does not accept a full JSON Schema in response_format
# (unlike Ollama's format field).  We rely on the prompt + response_format
# type="json_object" to get parseable output, then validate with Pydantic.
_FIELD_HINT = (
    "\nReturn a JSON object with exactly these keys: "
    "reasoning (string), answer (string), "
    "citations (array of {source, section, page}), "
    "answered_from_context (boolean), "
    "confidence (one of: high, medium, low)."
)


class HostedProvider:
    """OpenAI-compatible hosted LLM provider."""

    name = "hosted"

    def __init__(self, settings: Settings, *, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client
        if not settings.hosted_base_url:
            raise ValueError("HOSTED_BASE_URL must be set for the hosted provider")
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY must be set for the hosted provider")

    def generate(
        self, question: str, passages: list[Passage], *, feedback: str | None = None
    ) -> Answer:
        evidence = [
            {
                "number": i,
                "source": p.source,
                "section": p.section,
                "page": p.page,
                "text": p.text,
                "inline_citation": f"[{p.source} / {p.section}]",
            }
            for i, p in enumerate(passages, 1)
        ]

        instructions = SYSTEM_PROMPT + _FIELD_HINT
        arithmetic = comparison_hints(question, passages)
        if arithmetic:
            instructions += (
                "\nComputed arithmetic for literal numbers only; not cited policy evidence, "
                "not proof of matching units, rule applicability or official standing:\n"
                + arithmetic
            )
        if feedback:
            instructions += "\nPrevious attempt failed validation: " + feedback[:200]

        body = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": instructions},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"evidence": evidence, "question": question}, ensure_ascii=False
                    ),
                },
            ],
            "max_tokens": 768,
            "temperature": self.settings.temperature,
            "response_format": {"type": "json_object"},
        }

        base_url = self.settings.hosted_base_url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        connection = self.client or httpx.Client()
        try:
            response = connection.post(
                f"{base_url}/chat/completions",
                json=body,
                headers=headers,
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            outer = response.json()

            # Validate the OpenAI-compatible envelope
            if (
                not isinstance(outer, dict)
                or not isinstance(outer.get("choices"), list)
                or not outer["choices"]
                or not isinstance(outer["choices"][0].get("message"), dict)
            ):
                raise ProviderError(ProviderFailureKind.INVALID_SCHEMA)

            finish_reason = outer["choices"][0].get("finish_reason", "stop")
            if finish_reason == "length":
                raise ProviderError(ProviderFailureKind.INVALID_SCHEMA)

            content = outer["choices"][0]["message"].get("content", "")

            # Token accounting
            usage = outer.get("usage", {})
            incoming = usage.get("prompt_tokens")
            outgoing = usage.get("completion_tokens")
            if (
                type(incoming) is int and incoming >= 0
                and type(outgoing) is int and outgoing >= 0
            ):
                metrics.tokens(incoming, outgoing, "actual")
            else:
                metrics.tokens(
                    (len(json.dumps(body["messages"])) + 3) // 4,
                    (len(content) + 3) // 4,
                    "estimated",
                )

            parsed = json.loads(content)
            answer = Answer.model_validate(parsed, strict=True)

            return normalize_inline_citations(answer,passages)

        except httpx.TimeoutException:
            raise ProviderError(ProviderFailureKind.TIMEOUT) from None
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            log.warning(
                "hosted provider HTTP error",
                extra={"status": status},
            )
            raise ProviderError(ProviderFailureKind.TRANSPORT) from None
        except httpx.HTTPError:
            raise ProviderError(ProviderFailureKind.TRANSPORT) from None
        except ValidationError:
            raise ProviderError(ProviderFailureKind.INVALID_SCHEMA) from None
        except (KeyError, TypeError):
            raise ProviderError(ProviderFailureKind.INVALID_SCHEMA) from None
        except ValueError:
            raise ProviderError(ProviderFailureKind.INVALID_JSON) from None
        finally:
            if self.client is None:
                connection.close()

