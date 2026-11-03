"""Accesso al database SQLite."""

import os
import sqlite3
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "cincoditta.db"
MIGRAZIONI = Path(__file__).parent / "migrazioni"

_blocco_migrazioni = threading.Lock()


def connect() -> sqlite3.Connection:
    """Apre una connessione; il percorso si può cambiare con CINCODITTA_DB."""
    path = Path(os.environ.get("CINCODITTA_DB", DEFAULT_DB))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    with _blocco_migrazioni:
        migra(conn)
    return conn


def migra(conn: sqlite3.Connection) -> None:
    """Applica in ordine i file NNN_*.sql non ancora eseguiti su questo database."""
    versione = conn.execute("PRAGMA user_version").fetchone()[0]
    for file in sorted(MIGRAZIONI.glob("*.sql")):
        numero = int(file.name.split("_")[0])
        if numero > versione:
            conn.executescript(
                f"BEGIN;\n{file.read_text()}\nPRAGMA user_version = {numero};\nCOMMIT;"
            )
