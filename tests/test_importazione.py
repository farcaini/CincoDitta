from io import BytesIO

import pytest
from conftest import crea_file, errori_di
from openpyxl import load_workbook
from test_excel import applica

from cincoditta import importazione, magazzino
from cincoditta.excel import genera_file


def conta(conn, tabella):
    return conn.execute(f"SELECT COUNT(*) FROM {tabella}").fetchone()[0]


def test_anteprima_non_modifica_i_dati(conn):
    risultato = importazione.crea_anteprima(conn, crea_file(conn))

    assert risultato["valido"]
    assert risultato["cambiamenti"]["Presse"]["aggiunti"] == ["P1"]
    assert conta(conn, "presse") == 0
    assert conta(conn, "ordini") == 0


def test_file_con_un_errore_non_applica_nulla(conn):
    risultato = importazione.crea_anteprima(
        conn, crea_file(conn, Presse=[["P1", "ok", 10, 45], ["P2", "no", "x", 45]])
    )

    assert not risultato["valido"]
    assert "id" not in risultato
    assert conta(conn, "presse") == 0
    assert conta(conn, "anteprime") == 0


def test_conferma_applica_tutti_i_cambiamenti(conn):
    applica(conn, crea_file(conn))

    assert conta(conn, "presse") == 1
    assert conta(conn, "ordini") == 1
    assert conta(conn, "fasi_montaggio") == 1
    assert conta(conn, "anteprime") == 0


def test_dati_cambiati_dopo_anteprima(conn):
    risultato = importazione.crea_anteprima(conn, crea_file(conn))
    with conn:
        conn.execute("INSERT INTO presse (codice) VALUES ('NUOVA')")

    with pytest.raises(importazione.DatiCambiati):
        importazione.conferma_anteprima(conn, risultato["id"], [])

    assert conta(conn, "ordini") == 0


def test_resta_valida_solo_ultima_anteprima(conn):
    prima = importazione.crea_anteprima(conn, crea_file(conn))
    importazione.crea_anteprima(conn, crea_file(conn))

    with pytest.raises(importazione.AnteprimaNonTrovata):
        importazione.conferma_anteprima(conn, prima["id"], [])


def test_flusso_accettato_non_in_anteprima(conn):
    risultato = importazione.crea_anteprima(conn, crea_file(conn))

    with pytest.raises(importazione.AccettazioneNonValida):
        importazione.conferma_anteprima(conn, risultato["id"], [("X", "Y")])


def test_foglio_giacenze_ignorato_con_avviso(conn):
    flussi = [["DDT-1", "2026-11-01", "arrivo", "PP-NERO", 100, 2.5, None]]
    applica(conn, crea_file(conn, Flussi=flussi))

    libro = load_workbook(BytesIO(crea_file(conn)))
    for riga in libro["Giacenze"].iter_rows(min_row=2):
        if riga[0].value == "PP-NERO":
            riga[1].value = 999
    uscita = BytesIO()
    libro.save(uscita)

    risultato = applica(conn, uscita.getvalue())

    assert any("Giacenze" in avviso and "PP-NERO" in avviso for avviso in risultato["avvisi"])
    giacenza = next(r for r in magazzino.giacenze(conn) if r["codice"] == "PP-NERO")
    assert giacenza["quantita"] == 100


def test_giacenze_risultanti_in_anteprima(conn):
    flussi = [["DDT-1", "2026-11-01", "arrivo", "PP-NERO", 100, 2.5, None]]

    risultato = importazione.crea_anteprima(conn, crea_file(conn, Flussi=flussi))

    giacenza = next(r for r in risultato["giacenze"] if r["codice"] == "PP-NERO")
    assert giacenza["quantita"] == 100


def test_ordine_assente_non_riproposto_nel_file(conn):
    applica(conn, crea_file(conn))
    applica(conn, crea_file(conn, Ordini=[], Fasi_montaggio=[]))

    libro = load_workbook(BytesIO(genera_file(conn)))

    assert libro["Ordini"].max_row == 1
    assert libro["Fasi montaggio"].max_row == 1


def test_file_riscaricato_e_ricaricato_non_cambia_nulla(conn):
    flussi = [["DDT-1", "2026-11-01", "arrivo", "PP-NERO", 12.345, 2.5, None]]
    previsioni = [["ODA-1", "PP-NERO", 500.5, "2026-12-01"]]
    applica(conn, crea_file(conn, Flussi=flussi, Arrivi_previsti=previsioni))

    risultato = importazione.crea_anteprima(conn, genera_file(conn))

    assert risultato["valido"], risultato["errori"]
    assert risultato["cambiamenti"] == {}
    assert risultato["flussi"]["nuovi"] == []
    assert risultato["avvisi"] == []


def test_percorso_completo_via_api(client, conn):
    assert client.get("/api/excel").status_code == 200

    flussi = [["DDT-1", "2026-11-01", "arrivo", "PP-NERO", 100, 2.5, None]]
    file = crea_file(conn, Flussi=flussi)
    risposta = client.post("/api/excel/anteprima", files={"file": ("dati.xlsx", file)})
    anteprima = risposta.json()
    assert anteprima["valido"]

    risposta = client.post(f"/api/excel/anteprima/{anteprima['id']}/conferma", json={})
    assert risposta.json() == {"applicato": True}

    giacenze = client.get("/api/giacenze").json()
    assert next(r for r in giacenze if r["codice"] == "PP-NERO")["quantita"] == 100
    assert client.get("/api/movimenti", params={"codice": "PP-NERO"}).json()[0]["tipo"] == "arrivo"

    # La stessa copia ricaricata non cambia le giacenze.
    anteprima = client.post("/api/excel/anteprima", files={"file": ("dati.xlsx", file)}).json()
    client.post(f"/api/excel/anteprima/{anteprima['id']}/conferma", json={})
    giacenze = client.get("/api/giacenze").json()
    assert next(r for r in giacenze if r["codice"] == "PP-NERO")["quantita"] == 100

    assert client.get("/api/arrivi-previsti").json() == []
    assert client.get("/api/dati-mancanti").json() == []


def test_api_rifiuta_formato_e_conferme_errate(client):
    risposta = client.post("/api/excel/anteprima", files={"file": ("dati.csv", b"a,b")})
    assert risposta.status_code == 400

    risposta = client.post("/api/excel/anteprima", files={"file": ("dati.xlsx", b"nonzip")})
    assert risposta.status_code == 400

    assert client.post("/api/excel/anteprima/inesistente/conferma", json={}).status_code == 404


def test_api_conferma_con_dati_cambiati(client, conn):
    file = crea_file(conn)
    anteprima = client.post("/api/excel/anteprima", files={"file": ("dati.xlsx", file)}).json()
    with conn:
        conn.execute("INSERT INTO presse (codice) VALUES ('NUOVA')")

    risposta = client.post(f"/api/excel/anteprima/{anteprima['id']}/conferma", json={})

    assert risposta.status_code == 409


def test_errori_indicano_foglio_riga_e_colonna(client, conn):
    file = crea_file(conn, Stampi=[["S1", "x", 30, 90]])

    risultato = client.post("/api/excel/anteprima", files={"file": ("dati.xlsx", file)}).json()

    assert errori_di(risultato) == ["Stampi|2|impronte|Serve un numero"]
