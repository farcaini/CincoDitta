"""Accesso al database SQLite."""

import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "cincoditta.db"


def connect() -> sqlite3.Connection:
    """Apre una connessione; il percorso si può cambiare con CINCODITTA_DB."""
    path = Path(os.environ.get("CINCODITTA_DB", DEFAULT_DB))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn
