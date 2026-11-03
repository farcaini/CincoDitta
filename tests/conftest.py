from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from cincoditta.db import connect
from cincoditta.excel import genera_file
from cincoditta.main import app


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setenv("CINCODITTA_DB", str(tmp_path / "test.db"))


@pytest.fixture
def conn():
    connessione = connect()
    yield connessione
    connessione.close()


@pytest.fixture
def client():
    return TestClient(app)


# Colonne di ciascun foglio, nell'ordine del file generato.
DATI_BASE = {
    "Presse": [["P1", "Pressa 1", 10, 45]],
    "Stampi": [["S1", 4, 30, 90]],
    "Compatibilità": [["S1", "P1"]],
    "Materiali": [
        ["PP-NERO", "Polipropilene nero", "materia prima", "kg"],
        ["GANCIO", "Gancio", "componente", "pezzi"],
    ],
    "Articoli": [["ART1", "Articolo 1", "S1", 25]],
    "Distinta": [["ART1", "PP-NERO", None], ["ART1", "GANCIO", 1]],
    "Montaggi": [
        ["gancio", "a pezzo", 200, None, 20, None, None],
        ["floccatura", "a ordine", None, 10, None, 500, None],
    ],
    "Parametri": [["costo_energia_kwh", 0.3], ["costo_orario_personale", 25]],
    "Ordini": [["ORD1", "ART1", 1000, "2026-12-15"]],
    "Fasi montaggio": [["ORD1", 1, "gancio"]],
}


def crea_file(conn, **sostituzioni) -> bytes:
    """File generato dal programma, con i dati base e i fogli indicati sostituiti."""
    libro = load_workbook(BytesIO(genera_file(conn)))
    dati = dict(DATI_BASE)
    dati.update({nome.replace("_", " "): righe for nome, righe in sostituzioni.items()})
    for nome, righe in dati.items():
        foglio = libro[nome]
        foglio.delete_rows(2, foglio.max_row)
        for riga in righe:
            foglio.append(riga)
    uscita = BytesIO()
    libro.save(uscita)
    return uscita.getvalue()


def errori_di(risultato: dict) -> list[str]:
    return [
        f"{e['foglio']}|{e['riga']}|{e['colonna']}|{e['messaggio']}"
        for e in risultato.get("errori", [])
    ]
