"""Applicazione web: API JSON sotto /api, pagine statiche per tutto il resto."""

from contextlib import closing

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from cincoditta.db import ROOT, connect

app = FastAPI(title="CincoDitta")


@app.get("/api/health")
def health() -> dict[str, str]:
    with closing(connect()) as conn:
        version = conn.execute("SELECT sqlite_version()").fetchone()[0]
    return {"status": "ok", "sqlite": version}


# Va montato per ultimo: "/" cattura ogni percorso non gestito dalle API.
app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
