"""The Feed — FastAPI daemon entry point."""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI(title="The Feed")

PORT = int(os.getenv("FEED_PORT", "2626"))


@app.get("/")
async def index():
    static_path = Path(__file__).parent.parent.parent / "static" / "index.html"
    return HTMLResponse(content=static_path.read_text())


def run():
    print(f"The Feed is running at http://localhost:{PORT}")
    uvicorn.run("feed.main:app", host="0.0.0.0", port=PORT, reload=False)


if __name__ == "__main__":
    run()
