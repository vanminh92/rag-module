"""One injectable Ollama JSON client, reused by rewriting, generation and checks."""

import json

from ollama import Client

from .settings import RAGSettings


class OllamaJSON:
    def __init__(self, settings: RAGSettings):
        self.settings = settings
        self.client = Client(host=settings.ollama_host, timeout=settings.timeout)
        self.calls: list[dict] = []

    def __call__(self, task: str, system: str, payload: dict, schema: dict, *, max_tokens=768) -> str:
        response = self.client.chat(
            model=self.settings.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            format=schema,
            options={"temperature": 0, "num_ctx": 8192, "num_predict": max_tokens, "seed": 0},
            keep_alive="10m",
        )
        content = response.message.content or ""
        self.calls.append({"task": task, "response": content,
                           "prompt_tokens": response.prompt_eval_count,
                           "output_tokens": response.eval_count,
                           "total_duration_ns": response.total_duration})
        return content
