from io import BytesIO

import pytest
from conftest import crea_file, errori_di
from openpyxl import Workbook, load_workbook

from cincoditta import importazione
from cincoditta.excel import DIMENSIONE_MASSIMA, FileNonValido, genera_file, leggi_file
from cincoditta.fogli import FLUSSI, FOGLI_STATO, GIACENZE


def applica(conn, contenuto, accetta=()):
    risultato = importazione.crea_anteprima(conn, contenuto)
    assert risultato["valido"], risultato["errori"]
    importazione.conferma_anteprima(conn, risultato["id"], list(accetta))
    return risultato


def test_tutti_i_fogli_previsti_senza_dati(conn):
    libro = load_workbook(BytesIO(genera_file(conn)))

    attesi = [foglio.nome for foglio in FOGLI_STATO] + [FLUSSI.nome, GIACENZE]
    assert libro.sheetnames == attesi
    assert libro["Presse"].max_row == 1
    assert libro["Flussi"].max_row == 1


def test_scaricamento_con_dati_ha_flussi_vuoti_e_giacenze(conn):
    flussi = [["DDT-1", "2026-11-01", "arrivo", "PP-NERO", 100, 2.5, None]]
    applica(conn, crea_file(conn, Flussi=flussi))

    libro = load_workbook(BytesIO(genera_file(conn)))

    assert libro["Presse"]["A2"].value == "P1"
    assert libro["Flussi"].max_row == 1
    giacenze = {riga[0]: riga[1] for riga in libro["Giacenze"].iter_rows(min_row=2, values_only=True)}
    assert giacenze["PP-NERO"] == 100


def test_file_non_xlsx_rifiutato():
    with pytest.raises(FileNonValido):
        leggi_file(b"questo non e' un file excel")


def test_file_troppo_grande_rifiutato():
    with pytest.raises(FileNonValido, match="10 MB"):
        leggi_file(b"0" * (DIMENSIONE_MASSIMA + 1))


def test_testo_al_posto_di_un_numero(conn):
    risultato = importazione.crea_anteprima(
        conn, crea_file(conn, Stampi=[["S1", "quattro", 30, 90]])
    )

    assert not risultato["valido"]
    assert "Stampi|2|impronte|Serve un numero" in errori_di(risultato)


def test_riferimento_inesistente(conn):
    risultato = importazione.crea_anteprima(
        conn, crea_file(conn, Articoli=[["ART1", "x", "NON-ESISTE", 25]])
    )

    assert any(e.startswith("Articoli|2|stampo|") for e in errori_di(risultato))


def test_colonna_rinominata(conn):
    libro = load_workbook(BytesIO(crea_file(conn)))
    libro["Presse"]["D1"].value = "kw"
    uscita = BytesIO()
    libro.save(uscita)

    risultato = importazione.crea_anteprima(conn, uscita.getvalue())

    assert "Presse|1|consumo_kw|Colonna mancante" in errori_di(risultato)


def test_foglio_mancante(conn):
    uscita = BytesIO()
    Workbook().save(uscita)

    risultato = importazione.crea_anteprima(conn, uscita.getvalue())

    assert "Presse|None|None|Foglio mancante" in errori_di(risultato)


def test_numeri_con_virgola_e_date_italiane(conn):
    flussi = [["DDT-1", "01/11/2026", "arrivo", "PP-NERO", "12,5", None, None]]
    applica(conn, crea_file(conn, Flussi=flussi))

    riga = conn.execute("SELECT data, quantita FROM movimenti").fetchone()
    assert riga["data"] == "2026-11-01"
    assert riga["quantita"] == 12500
