"""
Content-based routing for incoming memory packets.

Each target file in `writer.DOMAIN_MAP` is treated as one document in a
small corpus. On classification we tokenize the candidate packet body,
compute a TF-IDF vector over the same vocabulary as the corpus, and
route to the document with the highest cosine similarity. If the top
score is below `CONFIDENCE_THRESHOLD` we fall back to `general` — the
idea being that a separate "dreamer" agent will later re-sort anything
that landed in general (or that landed in the wrong place).

The corpus for each domain is the concatenation of:

  1. A short seed blurb baked in below (gives cold-start behaviour when
     the real file is empty or missing).
  2. The live contents of the target file under `knowledge_root`, if it
     exists.

As real packets accumulate, (2) dominates and the seed's influence
fades naturally.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from feed.writer import DOMAIN_MAP

# Below this cosine score, classification is considered unreliable and
# the packet falls back to `general`. Tuned against the prototype
# dataset: real winners scored 0.07+ and pure noise stayed under 0.05.
CONFIDENCE_THRESHOLD = 0.05

# Seed descriptions — a short "topics covered" blurb per domain. These
# give TF-IDF something to work with before any real content has
# accumulated. Keep them lean: a dense list of distinctive vocabulary
# beats prose.
SEED_DESCRIPTIONS: dict[str, str] = {
    "java": (
        "Java JVM Spring Boot Spring Framework Maven Gradle Hibernate JPA "
        "JUnit Mockito checked exceptions streams records sealed classes "
        "virtual threads Kotlin interop."
    ),
    "python": (
        "Python FastAPI Flask Django Pydantic dataclasses type hints "
        "asyncio async await uv pip pytest ruff pandas numpy ASGI uvicorn "
        "hypercorn coroutines."
    ),
    "golang": (
        "Go golang goroutines channels context errgroup net http chi gin "
        "table driven tests testing package go modules go vet golangci "
        "lint gRPC protobuf."
    ),
    "api": (
        "API design specs plans REST conventions resource modeling "
        "pagination idempotency versioning OpenAPI JSON schema GraphQL "
        "request validation error envelopes RFC design docs."
    ),
    "testing": (
        "Testing unit integration contract end to end fixtures factories "
        "golden files flaky triage property based hypothesis mocking "
        "boundaries coverage."
    ),
    "observability": (
        "Observability logs metrics traces OpenTelemetry Prometheus "
        "Grafana dashboards structured logging correlation ids SLO SLI "
        "error budgets distributed tracing alerting runbooks."
    ),
    "general": (
        "Team process communication review etiquette onboarding "
        "cross cutting notes."
    ),
}


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")

# Minimal stopword list. Kept small on purpose — IDF does the real
# filtering. Only the most frequent English function words are listed
# here to keep vectors compact.
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "that", "this", "from", "into", "over",
        "a", "an", "of", "to", "in", "on", "is", "are", "be", "it", "as", "or",
        "by", "at", "we", "you", "our", "but", "not", "if", "so", "do", "does",
        "was", "were", "has", "have", "had", "will", "can", "should", "would",
    }
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, stopwords removed, single-char tokens dropped."""
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text)
        if t.lower() not in _STOPWORDS and len(t) > 1
    ]


def _compute_idf(docs: dict[str, list[str]]) -> dict[str, float]:
    """Smoothed IDF: log((1 + N) / (1 + df)) + 1 (matches sklearn default)."""
    n = len(docs)
    df: Counter[str] = Counter()
    for tokens in docs.values():
        for term in set(tokens):
            df[term] += 1
    return {term: math.log((1 + n) / (1 + d)) + 1 for term, d in df.items()}


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """Raw-count TF times IDF, L2-normalized."""
    tf = Counter(tokens)
    vec = {term: count * idf.get(term, 0.0) for term, count in tf.items()}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {term: v / norm for term, v in vec.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    # Both vectors are already L2-normalized, so the dot product *is*
    # the cosine similarity.
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(term, 0.0) for term, v in a.items())


def load_corpus(knowledge_root: str | Path) -> dict[str, str]:
    """
    Build the per-domain corpus by concatenating the seed blurb with the
    live contents of each target file under `knowledge_root`. Missing
    files are fine — the seed alone is enough to classify against.
    """
    root = Path(knowledge_root).expanduser()
    corpus: dict[str, str] = {}
    for domain, relative in DOMAIN_MAP.items():
        seed = SEED_DESCRIPTIONS.get(domain, "")
        target = root / relative
        try:
            live = target.read_text(encoding="utf-8") if target.exists() else ""
        except OSError:
            live = ""
        corpus[domain] = f"{seed}\n{live}"
    return corpus


def score(body: str, corpus: dict[str, str]) -> list[tuple[str, float]]:
    """Return [(domain, cosine_score), ...] sorted by descending score."""
    doc_tokens = {name: tokenize(text) for name, text in corpus.items()}

    # Fit IDF on corpus + query so that terms appearing only in the
    # query still receive a meaningful weight.
    fit_docs = dict(doc_tokens)
    fit_docs["__query__"] = tokenize(body)
    idf = _compute_idf(fit_docs)

    doc_vectors = {name: _tfidf_vector(toks, idf) for name, toks in doc_tokens.items()}
    query_vector = _tfidf_vector(tokenize(body), idf)

    scored = [(name, _cosine(query_vector, vec)) for name, vec in doc_vectors.items()]
    scored.sort(key=lambda p: p[1], reverse=True)
    return scored


def classify(body: str, corpus: dict[str, str]) -> str:
    """
    Route a packet body to a domain key. Returns `general` when the top
    match falls below `CONFIDENCE_THRESHOLD` — the dreamer can re-sort
    those later with richer context.
    """
    scored = score(body, corpus)
    if not scored:
        return "general"
    winner, top_score = scored[0]
    if top_score < CONFIDENCE_THRESHOLD:
        return "general"
    return winner
