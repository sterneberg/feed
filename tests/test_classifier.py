"""Tests for TF-IDF content-based classification."""

from feed.classifier import (
    CONFIDENCE_THRESHOLD,
    classify,
    load_corpus,
    score,
    tokenize,
)


def test_tokenize_lowercases_and_drops_stopwords():
    tokens = tokenize("The quick Brown fox and a lazy dog.")
    assert "quick" in tokens
    assert "brown" in tokens
    assert "fox" in tokens
    assert "the" not in tokens
    assert "and" not in tokens


def test_tokenize_drops_single_character_tokens():
    assert "a" not in tokenize("a b c word")
    assert "word" in tokenize("a b c word")


def test_classify_routes_fastapi_to_python(tmp_path):
    corpus = load_corpus(tmp_path)  # empty knowledge_root — seeds only
    body = "When wiring up a FastAPI service, use Pydantic models and async def handlers."
    assert classify(body, corpus) == "python"


def test_classify_routes_semantic_python_without_literal_python_token(tmp_path):
    corpus = load_corpus(tmp_path)
    body = "Use async def with await for I/O-bound handlers; pytest-asyncio for coroutines."
    assert classify(body, corpus) == "python"


def test_classify_routes_spring_boot_to_java(tmp_path):
    corpus = load_corpus(tmp_path)
    body = "In Spring Boot, prefer constructor injection so beans stay testable with JUnit and Mockito."
    assert classify(body, corpus) == "java"


def test_classify_routes_goroutines_to_golang(tmp_path):
    corpus = load_corpus(tmp_path)
    body = "Always pass context.Context first; use errgroup for fan-out goroutines."
    assert classify(body, corpus) == "golang"


def test_classify_routes_otel_to_observability(tmp_path):
    corpus = load_corpus(tmp_path)
    body = "Instrument with OpenTelemetry and attach correlation ids to structured logs."
    assert classify(body, corpus) == "observability"


def test_classify_routes_openapi_to_api(tmp_path):
    corpus = load_corpus(tmp_path)
    body = "Document REST endpoints in OpenAPI and return RFC 7807 problem details."
    assert classify(body, corpus) == "api"


def test_classify_ambiguous_falls_back_to_general(tmp_path):
    corpus = load_corpus(tmp_path)
    body = "Be kind. Ask questions."
    assert classify(body, corpus) == "general"


def test_classify_zero_overlap_falls_back_to_general(tmp_path):
    corpus = load_corpus(tmp_path)
    body = "Xylophone marmalade quibble."
    assert classify(body, corpus) == "general"


def test_score_returns_sorted_descending(tmp_path):
    corpus = load_corpus(tmp_path)
    scored = score("FastAPI Pydantic uvicorn", corpus)
    scores = [s for _, s in scored]
    assert scores == sorted(scores, reverse=True)


def test_load_corpus_incorporates_live_file_content(tmp_path):
    # Drop a file under the python target path and verify its content
    # leaks into the python corpus entry.
    python_path = tmp_path / "language-guidelines" / "python.md"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("This file mentions a very unique token: zqxwce.")

    corpus = load_corpus(tmp_path)
    assert "zqxwce" in corpus["python"]


def test_live_content_can_outweigh_seeds(tmp_path):
    """A novel term sitting in a target file should pull matching packets to it."""
    java_path = tmp_path / "language-guidelines" / "java.md"
    java_path.parent.mkdir(parents=True)
    # Stuff the java file with a distinctive made-up term.
    java_path.write_text("flibbercrumble " * 20)

    corpus = load_corpus(tmp_path)
    assert classify("Notes on flibbercrumble and how to use it.", corpus) == "java"


def test_confidence_threshold_is_reasonable():
    # Sanity check: the threshold is a small positive number. If this
    # ever changes dramatically it's worth re-tuning against real data.
    assert 0.0 < CONFIDENCE_THRESHOLD < 0.2
