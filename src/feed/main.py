"""The Feed — FastAPI daemon entry point."""

import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

from feed.github import fetch_issues, add_label, RateLimitError
from feed.governor import get_ruleset
from feed.models import build_packets, Packet
from feed.storage import load_state, save_state, advance_cursor, increment_stat
from feed.writer import incorporate

PORT = int(os.getenv("FEED_PORT", "2626"))
GITHUB_TOKEN = os.getenv("FEED_GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("FEED_GITHUB_REPO", "")
GITHUB_ORG = os.getenv("FEED_GITHUB_ORG", "")
KNOWLEDGE_ROOT = os.getenv("FEED_KNOWLEDGE_ROOT", str(Path.home() / "team-brain"))

# In-memory packet cache for the current session
_packet_cache: dict[int, Packet] = {}
_state = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _state
    _state = load_state()
    print(f"The Feed is running at http://localhost:{PORT}")
    yield
    if _state:
        save_state(_state)


app = FastAPI(title="The Feed", lifespan=lifespan)


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/")
async def index():
    static_path = Path(__file__).parent.parent.parent / "static" / "index.html"
    return HTMLResponse(content=static_path.read_text())


@app.get("/api/packets")
async def get_packets():
    global _packet_cache
    try:
        raw = await fetch_issues(GITHUB_REPO, _state.cursor, GITHUB_TOKEN)
        packets = await build_packets(raw, GITHUB_ORG, GITHUB_TOKEN)
        _packet_cache = {p.id: p for p in packets}
        return [p.model_dump() for p in packets]
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/incorporate/{packet_id}")
async def incorporate_packet(packet_id: int):
    packet = _packet_cache.get(packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Packet not found")
    if packet.risk_level == "threat":
        raise HTTPException(status_code=400, detail="Cannot incorporate threat packet")
    try:
        file_path = incorporate(
            KNOWLEDGE_ROOT,
            packet.sequence_number,
            packet.sender_login,
            packet.created_at,
            packet.domain,
            packet.body,
        )
        increment_stat(_state, "incorporated")
        advance_cursor(_state, packet.created_at)
        save_state(_state)
        await add_label(GITHUB_REPO, packet.sequence_number, "incorporated", GITHUB_TOKEN)
        return {"status": "incorporated", "file": str(file_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/filter/{packet_id}")
async def filter_packet(packet_id: int):
    packet = _packet_cache.get(packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Packet not found")
    try:
        increment_stat(_state, "filtered")
        advance_cursor(_state, packet.created_at)
        save_state(_state)
        await add_label(GITHUB_REPO, packet.sequence_number, "filtered", GITHUB_TOKEN)
        return {"status": "filtered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quarantine/{packet_id}")
async def quarantine_packet(packet_id: int):
    packet = _packet_cache.get(packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Packet not found")
    try:
        increment_stat(_state, "quarantined")
        # Quarantine does NOT advance cursor
        save_state(_state)
        await add_label(GITHUB_REPO, packet.sequence_number, "quarantined", GITHUB_TOKEN)
        return {"status": "quarantined"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    return {
        "incorporated": _state.session_stats.incorporated,
        "filtered": _state.session_stats.filtered,
        "quarantined": _state.session_stats.quarantined,
        "cursor": _state.cursor,
    }


@app.get("/api/governor")
async def get_governor():
    return {"rules": get_ruleset()}


def run():
    uvicorn.run("feed.main:app", host="0.0.0.0", port=PORT, reload=False)


if __name__ == "__main__":
    run()
