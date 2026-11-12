"""Accès au LLM local (Ollama) — gratuit, sans compte, aucune donnée envoyée sur internet.

Ollama fait tourner un modèle open source sur ton PC et l'expose à l'adresse
http://localhost:11434. Ce module est utilisé par toutes les briques d'IA du projet
(réclamations, note de crédit, agent SQL, RAG).

Réglages possibles dans .env :
    LLM_MODEL=qwen2.5:3b            # modèle de chat (plus gros = meilleur mais plus lent)
    EMBED_MODEL=nomic-embed-text    # modèle d'« embeddings » pour le RAG
    OLLAMA_URL=http://localhost:11434
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv

from creditlens.config import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


def _post(path: str, payload: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        f"{OLLAMA_URL}{path}", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        if "not found" in detail:
            model = payload.get("model")
            raise RuntimeError(f"Modèle {model} absent. Lance : ollama pull {model}") from exc
        raise RuntimeError(f"Erreur Ollama {exc.code} : {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Ollama ne répond pas sur " + OLLAMA_URL +
                           " : ouvre l'application Ollama (ou lance `ollama serve`).") from exc


def chat(prompt: str, system: str | None = None, json_mode: bool = False,
         temperature: float = 0.0, max_tokens: int = 400, model: str | None = None) -> LLMResponse:
    """Envoie un message au LLM et renvoie sa réponse."""
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    payload = {"model": model or LLM_MODEL, "messages": messages, "stream": False,
               "options": {"temperature": temperature, "num_predict": max_tokens}}
    if json_mode:
        payload["format"] = "json"          # Ollama force une réponse JSON valide
    data = _post("/api/chat", payload)
    return LLMResponse(text=data["message"]["content"],
                       input_tokens=int(data.get("prompt_eval_count", 0)),
                       output_tokens=int(data.get("eval_count", 0)),
                       model=payload["model"])


def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Transforme des textes en vecteurs (utilisé par le RAG)."""
    data = _post("/api/embed", {"model": model or EMBED_MODEL, "input": texts})
    return data["embeddings"]


def check() -> None:
    """Vérifie qu'Ollama tourne et affiche les modèles installés."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
            models = [m["name"] for m in json.loads(resp.read())["models"]]
    except urllib.error.URLError as exc:
        raise SystemExit("Ollama ne répond pas : ouvre l'application Ollama.") from exc
    print("Ollama OK. Modèles installés :", ", ".join(models) or "aucun")
    for needed in (LLM_MODEL, EMBED_MODEL):
        if not any(m == needed or m.startswith(needed + ":") for m in models):
            print(f"  -> manquant : {needed}   (installe-le avec : ollama pull {needed})")
    reply = chat("Réponds seulement : OK", max_tokens=5)
    print(f"Test du modèle {reply.model} : {reply.text.strip()!r}")


if __name__ == "__main__":
    check()
