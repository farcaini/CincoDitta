from conftest import DATI_BASE, crea_file, errori_di
from test_excel import applica

from cincoditta import importazione


def mancanti_di(risultato):
    return {(m["foglio"], m["elemento"], m["campo"]) for m in risultato["dati_mancanti"]}


def test_nuova_pressa_registrata(conn):
    applica(conn, crea_file(conn))

    riga = conn.execute("SELECT * FROM presse WHERE codice = 'P1'").fetchone()
    assert riga["consumo_kw"] == 45
    assert riga["spurgo_minuti"] == 10


def test_stampo_compatibile_con_due_presse(conn):
    presse = DATI_BASE["Presse"] + [["P2", "Pressa 2", 10, 60]]
    applica(
        conn,
        crea_file(conn, Presse=presse, Compatibilità=[["S1", "P1"], ["S1", "P2"]]),
    )

    assert conn.execute("SELECT COUNT(*) FROM compatibilita").fetchone()[0] == 2


def test_coppia_compatibilita_duplicata(conn):
    risultato = importazione.crea_anteprima(
        conn, crea_file(conn, Compatibilità=[["S1", "P1"], ["S1", "P1"]])
    )

    assert any(e.startswith("Compatibilità|3|") for e in errori_di(risultato))


def test_tipo_materiale_non_ammesso(conn):
    risultato = importazione.crea_anteprima(
        conn, crea_file(conn, Materiali=[["PP-NERO", "x", "plastica", "kg"]])
    )

    assert any(e.startswith("Materiali|2|tipo|") for e in errori_di(risultato))


def test_materia_prima_senza_quantita_accettata_componente_segnalato(conn):
    distinta = [["ART1", "PP-NERO", None], ["ART1", "GANCIO", None]]
    risultato = importazione.crea_anteprima(conn, crea_file(conn, Distinta=distinta))

    assert risultato["valido"]
    assert mancanti_di(risultato) == {
        ("Distinta", "ART1 / GANCIO", "quantità_per_pezzo")
    }


def test_montaggi_a_pezzo_e_a_ordine(conn):
    applica(conn, crea_file(conn))

    righe = {r["tipo"]: r for r in conn.execute("SELECT * FROM montaggi")}
    assert righe["gancio"]["modalita"] == "a pezzo"
    assert righe["gancio"]["pezzi_ora"] == 200
    assert righe["floccatura"]["modalita"] == "a ordine"
    assert righe["floccatura"]["costo_ordine"] == 500


def test_modalita_montaggio_non_ammessa(conn):
    risultato = importazione.crea_anteprima(
        conn,
        crea_file(conn, Montaggi=[["gancio", "a mano", 200, None, 20, None, None]]),
    )

    assert any(e.startswith("Montaggi|2|modalità|") for e in errori_di(risultato))


def test_parametro_aggiornato(conn):
    applica(conn, crea_file(conn))
    parametri = [["costo_energia_kwh", 0.4], ["costo_orario_personale", 25]]

    applica(conn, crea_file(conn, Parametri=parametri))

    valore = conn.execute(
        "SELECT valore FROM parametri WHERE nome = 'costo_energia_kwh'"
    ).fetchone()[0]
    assert valore == 0.4


def test_stampo_senza_tempo_ciclo_accettato_e_segnalato(conn):
    risultato = importazione.crea_anteprima(
        conn, crea_file(conn, Stampi=[["S1", 4, None, 90]])
    )

    assert risultato["valido"]
    assert ("Stampi", "S1", "tempo_ciclo_secondi") in mancanti_di(risultato)
    importazione.conferma_anteprima(conn, risultato["id"], [])
    valore = conn.execute("SELECT tempo_ciclo_secondi FROM stampi").fetchone()[0]
    assert valore is None


def test_valore_non_positivo(conn):
    risultato = importazione.crea_anteprima(
        conn, crea_file(conn, Stampi=[["S1", 4, 0, 90]])
    )

    assert "Stampi|2|tempo_ciclo_secondi|Il valore deve essere maggiore di zero" in errori_di(
        risultato
    )


def test_materiale_con_movimenti_non_rimovibile(conn):
    flussi = [["DDT-1", "2026-11-01", "arrivo", "GANCIO", 100, 0.1, None]]
    applica(conn, crea_file(conn, Flussi=flussi))

    risultato = importazione.crea_anteprima(
        conn,
        crea_file(
            conn,
            Materiali=[["PP-NERO", "x", "materia prima", "kg"]],
            Distinta=[["ART1", "PP-NERO", None]],
        ),
    )

    assert not risultato["valido"]
    assert any("GANCIO non si può rimuovere" in e for e in errori_di(risultato))


def test_nuovo_ordine_con_fasi_in_sequenza(conn):
    fasi = [["ORD1", 2, "floccatura"], ["ORD1", 1, "gancio"]]
    applica(conn, crea_file(conn, Fasi_montaggio=fasi))

    assert conn.execute("SELECT articolo FROM ordini").fetchone()[0] == "ART1"
    sequenza = [
        r["tipo"]
        for r in conn.execute("SELECT tipo FROM fasi_montaggio ORDER BY sequenza")
    ]
    assert sequenza == ["gancio", "floccatura"]


def test_ordine_ricaricato_non_cambia(conn):
    applica(conn, crea_file(conn))

    risultato = applica(conn, crea_file(conn))

    assert "Ordini" not in risultato["cambiamenti"]
    assert conn.execute("SELECT COUNT(*) FROM ordini").fetchone()[0] == 1


def test_codice_ordine_ripetuto(conn):
    ordini = DATI_BASE["Ordini"] * 2

    risultato = importazione.crea_anteprima(conn, crea_file(conn, Ordini=ordini))

    assert any(e.startswith("Ordini|3|") for e in errori_di(risultato))


def test_ordine_con_dati_non_validi(conn):
    risultato = importazione.crea_anteprima(
        conn,
        crea_file(
            conn,
            Ordini=[["ORD1", "ART1", 0, "2026-12-15"], ["ORD2", "ART1", 5, "domani"]],
            Fasi_montaggio=[],
        ),
    )

    assert any(e.startswith("Ordini|2|quantità|") for e in errori_di(risultato))
    assert any(e.startswith("Ordini|3|data_spedizione|") for e in errori_di(risultato))


def test_ordine_modificato_mostra_prima_e_dopo(conn):
    applica(conn, crea_file(conn))

    risultato = importazione.crea_anteprima(
        conn, crea_file(conn, Ordini=[["ORD1", "ART1", 1500, "2026-12-15"]])
    )

    modifica = risultato["cambiamenti"]["Ordini"]["modificati"][0]
    assert modifica["prima"] == {"quantita": 1000}
    assert modifica["dopo"] == {"quantita": 1500}


def test_ordine_tolto_conservato(conn):
    applica(conn, crea_file(conn))

    risultato = applica(conn, crea_file(conn, Ordini=[], Fasi_montaggio=[]))

    assert risultato["cambiamenti"]["Ordini"]["rimossi"] == ["ORD1"]
    riga = conn.execute("SELECT presente_nel_file FROM ordini").fetchone()
    assert riga["presente_nel_file"] == 0
    assert conn.execute("SELECT COUNT(*) FROM fasi_montaggio").fetchone()[0] == 1


def test_ordine_senza_montaggio(conn):
    applica(conn, crea_file(conn, Fasi_montaggio=[]))

    assert conn.execute("SELECT COUNT(*) FROM fasi_montaggio").fetchone()[0] == 0


def test_sequenza_ripetuta(conn):
    fasi = [["ORD1", 1, "gancio"], ["ORD1", 1, "floccatura"]]

    risultato = importazione.crea_anteprima(conn, crea_file(conn, Fasi_montaggio=fasi))

    assert any(e.startswith("Fasi montaggio|3|") for e in errori_di(risultato))


def test_tipo_montaggio_inesistente(conn):
    risultato = importazione.crea_anteprima(
        conn, crea_file(conn, Fasi_montaggio=[["ORD1", 1, "saldatura"]])
    )

    assert any(e.startswith("Fasi montaggio|2|tipo|") for e in errori_di(risultato))
