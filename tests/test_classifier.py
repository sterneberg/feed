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


def test_classify_routes_nodejs_to_nodejs(tmp_path):
    corpus = load_corpus(tmp_path)
    body = "Register Express middleware with app.use(); prefer named functions over anonymous callbacks."
    assert classify(body, corpus) == "nodejs"


def test_classify_nodejs_async_does_not_bleed_into_python(tmp_path):
    """async/await/callback tokens should not pull nodejs packets into python."""
    corpus = load_corpus(tmp_path)
    body = "Prefer async/await over raw Promise chains in Node.js; wrap callbacks with util.promisify."
    assert classify(body, corpus) == "nodejs"


def test_load_corpus_discovers_extra_language_file(tmp_path):
    """A file in language-guidelines/ not in DOMAIN_MAP is included as a domain."""
    nodejs_path = tmp_path / "language-guidelines" / "nodejs.md"
    nodejs_path.parent.mkdir(parents=True)
    nodejs_path.write_text("Node.js Express npm async callbacks.")

    corpus = load_corpus(tmp_path)
    assert "nodejs" in corpus
    assert "Express" in corpus["nodejs"]


def test_load_corpus_discovers_extra_general_file(tmp_path):
    """A file in general-guidelines/ not in DOMAIN_MAP is included as a domain."""
    ops_path = tmp_path / "general-guidelines" / "ops.md"
    ops_path.parent.mkdir(parents=True)
    ops_path.write_text("Docker Kubernetes Helm deployment manifests.")

    corpus = load_corpus(tmp_path)
    assert "ops" in corpus
    assert "Docker" in corpus["ops"]


def test_classify_routes_to_dynamically_discovered_domain(tmp_path):
    """classify() routes to a domain discovered from the filesystem, not just DOMAIN_MAP."""
    nodejs_path = tmp_path / "language-guidelines" / "nodejs.md"
    nodejs_path.parent.mkdir(parents=True)
    nodejs_path.write_text(
        "Node.js Express npm async callbacks Promise middleware "
        "require module exports webpack babel eslint "
        "Node.js Node.js Node.js Express Express Express"
    )

    corpus = load_corpus(tmp_path)
    body = "Use Express middleware for request validation in Node.js APIs."
    assert classify(body, corpus) == "nodejs"


def test_discovered_domains_do_not_displace_builtin_seeds(tmp_path):
    """Built-in seeds still work when extra files are present."""
    nodejs_path = tmp_path / "language-guidelines" / "nodejs.md"
    nodejs_path.parent.mkdir(parents=True)
    nodejs_path.write_text("Node.js Express npm.")

    corpus = load_corpus(tmp_path)
    body = "Use async def with await for I/O-bound handlers; pytest-asyncio for coroutines."
    assert classify(body, corpus) == "python"
