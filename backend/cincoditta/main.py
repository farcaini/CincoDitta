"""Applicazione web: API JSON sotto /api, pagine statiche per tutto il resto."""

from contextlib import closing

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cincoditta import importazione, magazzino, validazione
from cincoditta.db import ROOT, connect
from cincoditta.excel import DIMENSIONE_MASSIMA, FileNonValido, genera_file
from cincoditta.fogli import leggi_stato

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

app = FastAPI(title="CincoDitta")


class FlussoAccettato(BaseModel):
    riferimento: str
    codice: str


class Conferma(BaseModel):
    accetta: list[FlussoAccettato] = []


@app.get("/api/health")
def health() -> dict[str, str]:
    with closing(connect()) as conn:
        version = conn.execute("SELECT sqlite_version()").fetchone()[0]
    return {"status": "ok", "sqlite": version}


@app.get("/api/excel")
def scarica_excel() -> Response:
    with closing(connect()) as conn:
        contenuto = genera_file(conn)
    return Response(
        contenuto,
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": 'attachment; filename="cincoditta.xlsx"'},
    )


@app.post("/api/excel/anteprima")
def carica_excel(file: UploadFile) -> dict:
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(400, "Il file deve essere in formato .xlsx")
    contenuto = file.file.read(DIMENSIONE_MASSIMA + 1)
    with closing(connect()) as conn:
        try:
            return importazione.crea_anteprima(conn, contenuto)
        except FileNonValido as e:
            raise HTTPException(400, str(e)) from e


@app.post("/api/excel/anteprima/{identificativo}/conferma")
def conferma_excel(identificativo: str, conferma: Conferma) -> dict[str, bool]:
    accettati = [(voce.riferimento, voce.codice) for voce in conferma.accetta]
    with closing(connect()) as conn:
        try:
            importazione.conferma_anteprima(conn, identificativo, accettati)
        except importazione.AnteprimaNonTrovata as e:
            raise HTTPException(404, "Anteprima non trovata: carica di nuovo il file") from e
        except importazione.DatiCambiati as e:
            raise HTTPException(
                409, "I dati sono cambiati dopo l'anteprima: carica di nuovo il file"
            ) from e
        except importazione.AccettazioneNonValida as e:
            raise HTTPException(400, "Flusso accettato non presente nell'anteprima") from e
    return {"applicato": True}


@app.get("/api/giacenze")
def leggi_giacenze() -> list[dict]:
    with closing(connect()) as conn:
        return magazzino.giacenze(conn)


@app.get("/api/movimenti")
def leggi_movimenti(codice: str) -> list[dict]:
    with closing(connect()) as conn:
        return magazzino.movimenti(conn, codice)


@app.get("/api/arrivi-previsti")
def leggi_arrivi_previsti() -> list[dict]:
    with closing(connect()) as conn:
        return magazzino.arrivi_previsti(conn)


@app.get("/api/dati-mancanti")
def leggi_dati_mancanti() -> list[dict]:
    with closing(connect()) as conn:
        return validazione.dati_mancanti(
            leggi_stato(conn), importazione._flussi_correnti(conn)
        )


# Va montato per ultimo: "/" cattura ogni percorso non gestito dalle API.
app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
