"""
TF-IDF routing prototype for the memory feed.

Self-contained — no external deps. Seeds each DOMAIN_MAP target file with
a short, realistic "topics covered" blurb (what the 'dreamer' would leave
behind over time), then scores several candidate memories against the
corpus and prints the winning route plus the full score table.

Run:  python tfidf_prototype.py
"""

from __future__ import annotations

import math
import re
from collections import Counter

# Mirror of feed.writer.DOMAIN_MAP, but with seed content inline so the
# prototype runs against realistic text instead of empty files.
SEED_CORPUS: dict[str, str] = {
    "java": """
        Java and the JVM. Spring Boot, Spring Framework, Maven, Gradle.
        Hibernate and JPA for persistence. JUnit and Mockito for tests.
        Checked exceptions, streams, records, sealed classes, virtual threads.
        Kotlin interop notes live here too.
    """,
    "python": """
        Python 3 idioms. FastAPI, Flask, Django for web. Pydantic models,
        dataclasses, type hints, asyncio and async/await. uv and pip for
        packaging, pytest for tests, ruff for linting. Pandas and numpy
        for data work. ASGI servers like uvicorn and hypercorn.
    """,
    "golang": """
        Go and goroutines. Channels, context, errgroup. Standard library
        net/http, chi and gin routers. Table-driven tests with the testing
        package. Go modules, go vet, golangci-lint. gRPC with protobuf.
    """,
    "api": """
        API design, specs, and plans. REST conventions, resource modeling,
        pagination, idempotency keys, versioning. OpenAPI and JSON schema.
        GraphQL schema design. Request validation and error envelopes.
        Writing RFCs and design docs before implementation.
    """,
    "testing": """
        Testing philosophy and practice. Unit tests, integration tests,
        contract tests, end-to-end tests. Fixtures, factories, golden files.
        Flaky test triage. Property-based testing with hypothesis. Mocking
        boundaries, not internals. Coverage as a smell, not a goal.
    """,
    "observability": """
        Observability: logs, metrics, traces. OpenTelemetry instrumentation,
        Prometheus metrics, Grafana dashboards. Structured logging with
        correlation ids. SLOs, SLIs, error budgets. Distributed tracing
        across service boundaries. Alerting hygiene and runbooks.
    """,
    "general": """
        Catch-all for cross-cutting notes that do not fit a specific
        language or topic. Team process, communication norms, review
        etiquette, onboarding notes.
    """,
}


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")

# Minimal stopword list — just the worst offenders. Kept small on purpose
# so you can see the effect of IDF doing the real filtering.
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "over",
    "a", "an", "of", "to", "in", "on", "is", "are", "be", "it", "as", "or",
    "by", "at", "we", "you", "our", "but", "not", "if", "so", "do", "does",
}


def tokenize(text: str) -> list[str]:
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text)
        if t.lower() not in _STOPWORDS and len(t) > 1
    ]


def compute_idf(docs: dict[str, list[str]]) -> dict[str, float]:
    """Smoothed IDF, matching sklearn's default formula: log((1+N)/(1+df)) + 1."""
    n = len(docs)
    df: Counter[str] = Counter()
    for tokens in docs.values():
        for term in set(tokens):
            df[term] += 1
    return {term: math.log((1 + n) / (1 + d)) + 1 for term, d in df.items()}


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    vec = {term: count * idf.get(term, 0.0) for term, count in tf.items()}
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {term: v / norm for term, v in vec.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    # Both already L2-normalized, so dot product == cosine similarity.
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(term, 0.0) for term, v in a.items())


def route(query: str, corpus: dict[str, str]) -> list[tuple[str, float]]:
    """Return [(domain, score), ...] sorted by descending score."""
    doc_tokens = {name: tokenize(text) for name, text in corpus.items()}

    # Fit IDF on corpus + query so query-only terms still get weight.
    # (We give the query a synthetic doc name so it contributes to df.)
    fit_docs = dict(doc_tokens)
    fit_docs["__query__"] = tokenize(query)
    idf = compute_idf(fit_docs)

    doc_vecs = {name: tfidf_vector(toks, idf) for name, toks in doc_tokens.items()}
    query_vec = tfidf_vector(tokenize(query), idf)

    scored = [(name, cosine(query_vec, vec)) for name, vec in doc_vecs.items()]
    scored.sort(key=lambda p: p[1], reverse=True)
    return scored


def print_report(label: str, query: str, corpus: dict[str, str]) -> None:
    scored = route(query, corpus)
    winner, top_score = scored[0]
    runner_up_score = scored[1][1] if len(scored) > 1 else 0.0
    margin = top_score - runner_up_score

    print(f"\n=== {label} ===")
    print(f"Query: {query.strip()[:120]}{'...' if len(query.strip()) > 120 else ''}")
    print(f"Winner: {winner}  (score={top_score:.4f}, margin over #2={margin:.4f})")
    print("All scores:")
    for name, score in scored:
        bar = "#" * int(score * 40)
        print(f"  {name:<14} {score:.4f}  {bar}")


QUERIES: list[tuple[str, str]] = [
    (
        "The canonical FastAPI case",
        "When wiring up a FastAPI service, prefer Pydantic v2 models for "
        "request validation and use async def handlers so uvicorn can "
        "multiplex connections.",
    ),
    (
        "Semantic-only Python (no literal 'python' token)",
        "Use async def with await for I/O-bound handlers; pytest-asyncio "
        "lets you test coroutines without a custom event loop fixture.",
    ),
    (
        "Spring Boot note — should land in java",
        "In Spring Boot, prefer constructor injection over field injection "
        "so beans stay testable with plain JUnit and Mockito.",
    ),
    (
        "Go concurrency note",
        "Always pass context.Context as the first argument to functions "
        "that may block on I/O; use errgroup for fan-out goroutines.",
    ),
    (
        "Testing philosophy note",
        "Mock at module boundaries, not internal helpers. Prefer fixtures "
        "over setUp/tearDown. Treat flaky tests as bugs, not noise.",
    ),
    (
        "Observability note",
        "Instrument with OpenTelemetry and export traces to the collector; "
        "attach correlation ids to structured logs for cross-service joins.",
    ),
    (
        "API design note",
        "Version REST endpoints in the URL, return RFC 7807 problem "
        "details for errors, and document everything in OpenAPI.",
    ),
    (
        "Ambiguous / should fall back to general",
        "Be kind in code reviews. Ask questions before proposing rewrites.",
    ),
    (
        "Novel term with zero corpus overlap",
        "Prefer Bazel remote cache with BuildBuddy for hermetic builds.",
    ),
]


if __name__ == "__main__":
    print("TF-IDF routing prototype")
    print(f"Corpus: {len(SEED_CORPUS)} documents")
    for label, query in QUERIES:
        print_report(label, query, SEED_CORPUS)
