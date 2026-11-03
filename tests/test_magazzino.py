from datetime import date

from conftest import crea_file, errori_di
from test_excel import applica

from cincoditta import importazione, magazzino


def giacenza(conn, codice):
    return next(r["quantita"] for r in magazzino.giacenze(conn) if r["codice"] == codice)


def arrivo(riferimento="DDT-1", quantita=100, costo=2.5, codice="PP-NERO"):
    return [riferimento, "2026-11-01", "arrivo", codice, quantita, costo, None]


def test_giacenza_e_somma_dei_movimenti(conn):
    flussi = [
        arrivo(),
        ["INV-1", "2026-11-02", "rettifica", "PP-NERO", -20, None, None],
    ]
    applica(conn, crea_file(conn, Flussi=flussi))

    assert giacenza(conn, "PP-NERO") == 80
    assert giacenza(conn, "GANCIO") == 0
    assert giacenza(conn, "ART1") == 0


def test_storico_con_origine(conn):
    applica(conn, crea_file(conn, Flussi=[arrivo()]))

    storico = magazzino.movimenti(conn, "PP-NERO")

    assert storico[0]["quantita"] == 100
    assert storico[0]["origine"] == "file"


def test_spedizione_senza_ordine(conn):
    flussi = [["SP-1", "2026-11-01", "spedizione", "ART1", 10, None, None]]

    risultato = importazione.crea_anteprima(conn, crea_file(conn, Flussi=flussi))

    assert "Flussi|2|ordine|La spedizione richiede l'ordine" in errori_di(risultato)


def test_spedizione_diminuisce_la_giacenza(conn):
    flussi = [
        ["INV-1", "2026-11-01", "rettifica", "ART1", 500, None, None],
        ["SP-1", "2026-11-02", "spedizione", "ART1", 200, None, "ORD1"],
    ]
    applica(conn, crea_file(conn, Flussi=flussi))

    assert giacenza(conn, "ART1") == 300


def test_carico_iniziale_con_rettifica(conn):
    flussi = [["INV-1", "2026-11-01", "rettifica", "PP-NERO", 75, 2.5, None]]
    applica(conn, crea_file(conn, Flussi=flussi))

    assert giacenza(conn, "PP-NERO") == 75


def test_vecchia_copia_non_conta_due_volte(conn):
    file = crea_file(conn, Flussi=[arrivo()])
    applica(conn, file)

    risultato = applica(conn, file)

    assert giacenza(conn, "PP-NERO") == 100
    assert len(risultato["flussi"]["ignorati"]) == 1
    assert risultato["flussi"]["nuovi"] == []


def test_bolla_con_piu_materiali(conn):
    flussi = [arrivo(), arrivo(codice="GANCIO", quantita=50, costo=0.1)]
    applica(conn, crea_file(conn, Flussi=flussi))

    assert giacenza(conn, "PP-NERO") == 100
    assert giacenza(conn, "GANCIO") == 50


def test_riga_ripetuta_nello_stesso_file(conn):
    risultato = importazione.crea_anteprima(
        conn, crea_file(conn, Flussi=[arrivo(), arrivo(quantita=5)])
    )

    assert any(e.startswith("Flussi|3|") for e in errori_di(risultato))


def test_differenza_non_confermata_lascia_il_flusso_invariato(conn):
    applica(conn, crea_file(conn, Flussi=[arrivo()]))
    flussi = [arrivo(quantita=120), arrivo("DDT-2", codice="GANCIO", quantita=7, costo=0.1)]

    risultato = applica(conn, crea_file(conn, Flussi=flussi))

    voce = risultato["flussi"]["da_confermare"][0]
    assert voce["prima"]["quantita"] == 100
    assert voce["dopo"]["quantita"] == 120
    assert giacenza(conn, "PP-NERO") == 100
    assert giacenza(conn, "GANCIO") == 7


def test_differenza_confermata_aggiunge_una_correzione(conn):
    applica(conn, crea_file(conn, Flussi=[arrivo()]))

    applica(
        conn,
        crea_file(conn, Flussi=[arrivo(quantita=120)]),
        accetta=[("DDT-1", "PP-NERO")],
    )

    assert giacenza(conn, "PP-NERO") == 120
    storico = magazzino.movimenti(conn, "PP-NERO")
    assert [(m["tipo"], m["quantita"]) for m in storico] == [
        ("arrivo", 100),
        ("correzione", 20),
    ]


def test_vecchia_copia_dopo_una_correzione(conn):
    vecchia = crea_file(conn, Flussi=[arrivo()])
    applica(conn, vecchia)
    applica(
        conn,
        crea_file(conn, Flussi=[arrivo(quantita=120)]),
        accetta=[("DDT-1", "PP-NERO")],
    )

    risultato = applica(conn, vecchia)

    assert risultato["flussi"]["da_confermare"] == []
    assert len(risultato["flussi"]["superati"]) == 1
    assert giacenza(conn, "PP-NERO") == 120


def test_correzione_di_una_spedizione(conn):
    flussi = [["SP-1", "2026-11-02", "spedizione", "ART1", 200, None, "ORD1"]]
    applica(conn, crea_file(conn, Flussi=flussi))
    flussi = [["SP-1", "2026-11-02", "spedizione", "ART1", 150, None, "ORD1"]]

    applica(conn, crea_file(conn, Flussi=flussi), accetta=[("SP-1", "ART1")])

    assert giacenza(conn, "ART1") == -150


def test_prezzi_diversi_conservati_con_il_proprio_movimento(conn):
    flussi = [arrivo("DDT-1", costo=2.5), arrivo("DDT-2", costo=3.0)]
    applica(conn, crea_file(conn, Flussi=flussi))

    costi = [m["costo_unitario"] for m in magazzino.movimenti(conn, "PP-NERO")]
    assert costi == [2.5, 3.0]


def test_arrivo_senza_prezzo_tra_i_dati_mancanti(conn):
    risultato = applica(conn, crea_file(conn, Flussi=[arrivo(costo=None)]))

    assert giacenza(conn, "PP-NERO") == 100
    assert {
        "foglio": "Flussi",
        "elemento": "DDT-1 / PP-NERO",
        "campo": "costo_unitario",
    } in risultato["dati_mancanti"]


def test_costo_su_una_spedizione_non_ammesso(conn):
    flussi = [["SP-1", "2026-11-02", "spedizione", "ART1", 10, 2.0, "ORD1"]]

    risultato = importazione.crea_anteprima(conn, crea_file(conn, Flussi=flussi))

    assert any(e.startswith("Flussi|2|costo_unitario|") for e in errori_di(risultato))


def test_giacenza_negativa_evidenziata(conn):
    flussi = [["INV-1", "2026-11-01", "rettifica", "PP-NERO", -50, None, None]]
    applica(conn, crea_file(conn, Flussi=flussi))

    riga = next(r for r in magazzino.giacenze(conn) if r["codice"] == "PP-NERO")
    assert riga["quantita"] == -50
    assert riga["negativa"]


def test_spedizione_oltre_la_giacenza_avvisa_ma_si_conferma(conn):
    flussi = [["SP-1", "2026-11-02", "spedizione", "ART1", 200, None, "ORD1"]]

    risultato = applica(conn, crea_file(conn, Flussi=flussi))

    assert any("ART1" in avviso and "negativa" in avviso for avviso in risultato["avvisi"])
    assert giacenza(conn, "ART1") == -200


def previsione(riferimento="ODA-1", data="2026-12-01"):
    return [riferimento, "PP-NERO", 500, data]


def test_arrivo_previsto_non_conta_in_giacenza(conn):
    applica(conn, crea_file(conn, Arrivi_previsti=[previsione()]))

    assert giacenza(conn, "PP-NERO") == 0
    stato = magazzino.arrivi_previsti(conn, oggi=date(2026, 11, 3))
    assert stato[0]["stato"] == "aperta"
    assert stato[0]["data"] == "2026-12-01"
    assert stato[0]["quantita"] == 500


def test_arrivo_avvenuto_chiude_la_previsione(conn):
    applica(conn, crea_file(conn, Arrivi_previsti=[previsione()]))

    applica(
        conn,
        crea_file(conn, Arrivi_previsti=[previsione()], Flussi=[arrivo("ODA-1", 500)]),
    )

    assert giacenza(conn, "PP-NERO") == 500
    assert magazzino.arrivi_previsti(conn)[0]["stato"] == "chiusa"


def test_previsione_chiusa_ancora_nel_file_non_si_riapre(conn):
    applica(
        conn,
        crea_file(conn, Arrivi_previsti=[previsione()], Flussi=[arrivo("ODA-1", 500)]),
    )

    risultato = applica(conn, crea_file(conn, Arrivi_previsti=[previsione(data="2027-01-01")]))

    assert any("ODA-1" in avviso for avviso in risultato["avvisi"])
    riga = magazzino.arrivi_previsti(conn)[0]
    assert riga["stato"] == "chiusa"
    assert riga["data"] == "2026-12-01"


def test_previsione_in_ritardo(conn):
    applica(conn, crea_file(conn, Arrivi_previsti=[previsione(data="2026-10-01")]))

    stato = magazzino.arrivi_previsti(conn, oggi=date(2026, 11, 3))

    assert stato[0]["stato"] == "in ritardo"
    assert giacenza(conn, "PP-NERO") == 0
