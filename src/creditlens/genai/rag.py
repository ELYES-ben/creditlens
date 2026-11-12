"""RAG réglementaire : répond aux questions de réglementation bancaire en citant la source.

RAG = Retrieval-Augmented Generation. Le LLM ne connaît pas forcément la réglementation ;
on lui fournit les passages utiles d'une base documentaire avant qu'il réponde, et il cite
d'où vient l'information.

Base documentaire : data/regulations/ (fichiers .md, .txt et .pdf).
Tout tourne en local et gratuitement via Ollama (embeddings + rédaction).

Déroulé :
  1. build   : découpe les documents en morceaux, calcule leurs « embeddings » (vecteurs),
               et les stocke dans data/regulations/_index.npz
  2. ask     : transforme la question en vecteur, retrouve les morceaux les plus proches,
               et fait rédiger la réponse par le LLM en citant les sources
  3. evaluate: vérifie, sur quelques questions, que le bon document est bien retrouvé

Utilisation :
    python -m creditlens.genai.rag build
    python -m creditlens.genai.rag ask "Que dit l'AI Act sur le scoring de crédit ?"
    python -m creditlens.genai.rag evaluate
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from creditlens.config import DOCS_DIR, PROJECT_ROOT
from creditlens.genai import llm

REG_DIR = PROJECT_ROOT / "data" / "regulations"
INDEX = REG_DIR / "_index.npz"
CHUNKS = REG_DIR / "_chunks.json"
TOP_K = 4
CHUNK_WORDS = 180         # taille d'un morceau, en mots
OVERLAP_WORDS = 40        # chevauchement entre morceaux (pour ne pas couper une idée)

ANSWER_PROMPT = """Tu es un assistant spécialisé en réglementation bancaire. Réponds à la question
en français, en t'appuyant UNIQUEMENT sur les extraits ci-dessous. Si les extraits ne
contiennent pas la réponse, dis-le clairement. Cite tes sources entre crochets, par exemple [1].

Extraits :
{context}

Question : {question}

Réponse (avec les numéros de source entre crochets) :"""


# --------------------------------------------------------------------------- lecture des documents
def read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit("Pour lire des PDF : pip install pypdf")
    return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return read_pdf(path)
    return path.read_text(encoding="utf-8", errors="replace")


def split_into_chunks(text: str) -> list[str]:
    """Découpe un texte en morceaux de CHUNK_WORDS mots, avec chevauchement."""
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        chunk = " ".join(words[start:start + CHUNK_WORDS]).strip()
        if chunk:
            chunks.append(chunk)
        start += CHUNK_WORDS - OVERLAP_WORDS
    return chunks


# --------------------------------------------------------------------------- 1. build
def build() -> None:
    docs = sorted(p for p in REG_DIR.glob("*") if p.suffix.lower() in (".md", ".txt", ".pdf"))
    if not docs:
        raise SystemExit(f"Aucun document dans {REG_DIR} (.md, .txt ou .pdf)")
    chunks, sources = [], []
    for doc in docs:
        for i, chunk in enumerate(split_into_chunks(read_document(doc))):
            chunks.append(chunk)
            sources.append({"document": doc.name, "morceau": i})
    print(f"    {len(docs)} documents -> {len(chunks)} morceaux. Calcul des embeddings...")

    vectors = []
    for start in range(0, len(chunks), 32):                 # par lots de 32
        vectors.extend(llm.embed(chunks[start:start + 32]))
        print(f"\r    {min(start + 32, len(chunks))}/{len(chunks)}", end="", flush=True)
    print()
    matrix = np.array(vectors, dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9   # normalise (pour le cosinus)
    np.savez_compressed(INDEX, vectors=matrix)
    CHUNKS.write_text(json.dumps({"chunks": chunks, "sources": sources}, ensure_ascii=False),
                      encoding="utf-8")
    print(f"    Index écrit dans {INDEX.name} et {CHUNKS.name}")


# --------------------------------------------------------------------------- recherche
def load_index():
    if not INDEX.exists():
        raise SystemExit("Index absent. Lance d'abord : python -m creditlens.genai.rag build")
    data = json.loads(CHUNKS.read_text(encoding="utf-8"))
    return np.load(INDEX)["vectors"], data["chunks"], data["sources"]


def search(question: str, vectors, chunks, sources, k: int = TOP_K) -> list[dict]:
    q = np.array(llm.embed([question])[0], dtype=np.float32)
    q /= np.linalg.norm(q) + 1e-9
    scores = vectors @ q                                    # similarité cosinus
    best = np.argsort(-scores)[:k]
    return [{"rang": r + 1, "score": float(scores[i]), "texte": chunks[i], **sources[i]}
            for r, i in enumerate(best)]


# --------------------------------------------------------------------------- 2. ask
def ask(question: str, show: bool = True) -> dict:
    vectors, chunks, sources = load_index()
    hits = search(question, vectors, chunks, sources)
    context = "\n\n".join(f"[{h['rang']}] (source : {h['document']})\n{h['texte']}" for h in hits)
    reply = llm.chat(ANSWER_PROMPT.format(context=context, question=question),
                     temperature=0.2, max_tokens=500)
    result = {"question": question, "answer": reply.text.strip(),
              "sources": [{"rang": h["rang"], "document": h["document"], "score": round(h["score"], 3)}
                          for h in hits]}
    if show:
        print(f"\n{reply.text.strip()}\n")
        print("Sources utilisées :")
        for h in hits:
            print(f"  [{h['rang']}] {h['document']} (proximité {h['score']:.2f})")
    return result


# --------------------------------------------------------------------------- 3. evaluate
EVAL_QUESTIONS = [
    ("Que dit l'AI Act sur le scoring de crédit ?", "03_ai_act"),
    ("Qu'est-ce que la LGD et quelle est sa valeur de référence ?", "04_pd_lgd_ead"),
    ("Quels sont les trois stages d'IFRS 9 ?", "02_ifrs9"),
    ("Comment calcule-t-on la perte attendue ?", "04_pd_lgd_ead"),
    ("Qu'est-ce que l'approche IRB de Bâle III ?", "01_bale_iii"),
    ("Comment vérifier qu'un modèle de scoring est équitable ?", "05_equite_discrimination"),
    ("Quelle est la différence entre discrimination directe et indirecte ?", "05_equite_discrimination"),
    ("Que couvrent les fonds propres et que couvrent les provisions ?", "01_bale_iii"),
]


def evaluate() -> None:
    vectors, chunks, sources = load_index()
    rows, hits_top1 = [], 0
    for question, expected_doc in EVAL_QUESTIONS:
        found = search(question, vectors, chunks, sources, k=3)
        docs = [h["document"] for h in found]
        top1 = expected_doc in docs[0]
        top3 = any(expected_doc in d for d in docs)
        hits_top1 += top1
        rows.append({"question": question, "attendu": expected_doc,
                     "trouve_top1": top1, "trouve_top3": top3, "documents": docs})
        print(f"  {'OK ' if top1 else ('top3' if top3 else 'RATE')} — {question[:55]}")

    top1 = 100 * hits_top1 / len(EVAL_QUESTIONS)
    top3 = 100 * sum(r["trouve_top3"] for r in rows) / len(EVAL_QUESTIONS)
    print(f"\n=== Bon document trouvé en 1er : {top1:.0f} % | dans le top 3 : {top3:.0f} % ===")
    DOCS_DIR.mkdir(exist_ok=True)
    report = [
        "# Évaluation du RAG réglementaire", "",
        f"Sur {len(EVAL_QUESTIONS)} questions, le bon document est retrouvé "
        f"**en 1re position dans {top1:.0f} %** des cas et **dans le top 3 dans {top3:.0f} %**.", "",
        "| Question | Document attendu | 1er | Top 3 |", "|---|---|---|---|",
        *[f"| {r['question']} | {r['attendu']} | {'✅' if r['trouve_top1'] else '❌'} | "
          f"{'✅' if r['trouve_top3'] else '❌'} |" for r in rows], "",
    ]
    (DOCS_DIR / "rag_eval_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Rapport : docs/rag_eval_report.md")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage : build | ask \"question\" | evaluate")
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "ask":
        ask(" ".join(sys.argv[2:]) or "Que dit l'AI Act sur le scoring de crédit ?")
    elif cmd == "evaluate":
        evaluate()
    else:
        raise SystemExit(f"Commande inconnue : {cmd}")


if __name__ == "__main__":
    main()
