from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


INSTRUCTIONS = """You answer questions using only the supplied DD-KB excerpts.
If the excerpts do not support an answer, say that the knowledge base does not contain enough information.
Cite factual claims using the excerpt labels exactly, for example [S1]. Be concise and do not invent sources."""


class GenerationError(RuntimeError):
    pass


def _output_text(response: dict) -> str:
    parts: list[str] = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def answer(question: str, sources: list[dict]) -> tuple[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise GenerationError("Set OPENAI_API_KEY to enable generated answers. Retrieval is still available below.")
    model = os.environ.get("OPENAI_MODEL", "gpt-5.6")
    context = "\n\n".join(
        f"[S{index}] {source['path']} — {source['section']} (line {source['line']})\n{source['text']}"
        for index, source in enumerate(sources, 1)
    )
    payload = json.dumps({
        "model": model,
        "instructions": INSTRUCTIONS,
        "input": f"Question:\n{question}\n\nKnowledge-base excerpts:\n{context}",
        "store": False,
    }).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses", data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read()).get("error", {}).get("message")
        except (json.JSONDecodeError, AttributeError):
            detail = None
        raise GenerationError(detail or f"OpenAI request failed ({error.code}).") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise GenerationError("Could not reach OpenAI. Check your connection and try again.") from error
    text = _output_text(data)
    if not text:
        raise GenerationError("The model returned no text.")
    return text, model

