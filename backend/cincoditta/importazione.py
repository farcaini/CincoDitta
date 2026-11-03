"""Anteprima di un file caricato e sua applicazione in un'unica transazione."""

import hashlib
import json
import uuid

from cincoditta import magazzino
from cincoditta.excel import leggi_file
from cincoditta.fogli import (
    ARRIVI,
    ARTICOLI,
    FASI,
    FLUSSI,
    FOGLI_STATO,
    MATERIALI,
    ORDINI,
    Foglio,
    leggi_stato,
)
from cincoditta.validazione import dati_mancanti, valida

CAMPI_VERSIONE = ("data", "tipo", "quantita", "costo_unitario", "ordine")
TABELLE_IMPRONTA = (
    *(foglio.tabella for foglio in FOGLI_STATO),
    "movimenti",
    "flussi_versioni",
)


class AnteprimaNonTrovata(Exception):
    pass


class DatiCambiati(Exception):
    pass


class AccettazioneNonValida(Exception):
    pass


def impronta(conn) -> str:
    """Identifica lo stato dei dati, per riconoscere un'anteprima superata."""
    hash_stato = hashlib.sha256()
    for tabella in TABELLE_IMPRONTA:
        righe = sorted(repr(tuple(riga)) for riga in conn.execute(f"SELECT * FROM {tabella}"))
        hash_stato.update(repr((tabella, righe)).encode())
    return hash_stato.hexdigest()


def crea_anteprima(conn, contenuto: bytes) -> dict:
    """Valida il file e calcola i cambiamenti, senza toccare i dati."""
    lettura = leggi_file(contenuto)
    errori = lettura.errori + valida(lettura.righe, conn)
    if errori:
        return {"valido": False, "errori": errori}

    righe = {
        nome: [{k: v for k, v in riga.items() if k != "_riga"} for riga in elenco]
        for nome, elenco in lettura.righe.items()
    }
    flussi = righe.pop(FLUSSI.nome)
    avvisi = []
    righe[ARRIVI.nome] = _togli_previsioni_chiuse(conn, righe[ARRIVI.nome], avvisi)
    classificati = _classifica_flussi(conn, flussi)

    stato = leggi_stato(conn)
    importi = _importi_risultanti(conn, classificati["nuovi"])
    giacenze = magazzino.componi_giacenze(
        importi, righe[MATERIALI.nome], righe[ARTICOLI.nome]
    )
    avvisi += _avvisi_giacenze(lettura.giacenze, magazzino.totali(conn), giacenze)

    risultato = {
        "valido": True,
        "id": uuid.uuid4().hex,
        "cambiamenti": _cambiamenti(stato, righe),
        "flussi": {
            gruppo: [_flusso_per_utente(riga) for riga in elenco]
            for gruppo, elenco in classificati.items()
            if gruppo != "da_confermare"
        }
        | {
            "da_confermare": [
                {
                    "riferimento": voce["nuovo"]["riferimento"],
                    "codice": voce["nuovo"]["codice"],
                    "prima": _flusso_per_utente(voce["precedente"]),
                    "dopo": _flusso_per_utente(voce["nuovo"]),
                }
                for voce in classificati["da_confermare"]
            ]
        },
        "avvisi": avvisi,
        "dati_mancanti": dati_mancanti(
            righe, _flussi_correnti(conn) + classificati["nuovi"]
        ),
        "giacenze": giacenze,
    }
    piano = {
        "righe": righe,
        "nuovi": classificati["nuovi"],
        "da_confermare": classificati["da_confermare"],
    }
    with conn:
        conn.execute("DELETE FROM anteprime")
        conn.execute(
            "INSERT INTO anteprime (id, impronta, piano) VALUES (?, ?, ?)",
            (risultato["id"], impronta(conn), json.dumps(piano)),
        )
    return risultato


def conferma_anteprima(conn, identificativo: str, accettati: list[tuple[str, str]]) -> None:
    """Applica tutto o niente; accettati sono i flussi diversi approvati dal gestore."""
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        salvata = conn.execute(
            "SELECT impronta, piano FROM anteprime WHERE id = ?", (identificativo,)
        ).fetchone()
        if salvata is None:
            raise AnteprimaNonTrovata
        if salvata["impronta"] != impronta(conn):
            raise DatiCambiati

        piano = json.loads(salvata["piano"])
        da_confermare = {
            (voce["nuovo"]["riferimento"], voce["nuovo"]["codice"]): voce
            for voce in piano["da_confermare"]
        }
        if not set(accettati) <= set(da_confermare):
            raise AccettazioneNonValida

        conn.execute("PRAGMA defer_foreign_keys = ON")
        _applica_stato(conn, piano["righe"])
        for riga in piano["nuovi"]:
            _registra_nuovo(conn, riga)
        for chiave in accettati:
            _registra_correzione(conn, da_confermare[chiave])
        conn.execute("DELETE FROM anteprime")


def _togli_previsioni_chiuse(conn, righe, avvisi) -> list[dict]:
    chiuse = {
        (riga["riferimento"], riga["codice"])
        for riga in conn.execute(
            "SELECT DISTINCT riferimento, codice FROM movimenti WHERE tipo = 'arrivo'"
        )
    }
    aperte = []
    for riga in righe:
        if (riga["riferimento"], riga["materiale"]) in chiuse:
            avvisi.append(
                f"Arrivo previsto {riga['riferimento']} / {riga['materiale']}: "
                "già arrivato, la riga viene ignorata"
            )
        else:
            aperte.append(riga)
    return aperte


def _classifica_flussi(conn, flussi: list[dict]) -> dict[str, list]:
    gruppi = {"nuovi": [], "ignorati": [], "superati": [], "da_confermare": []}
    for riga in flussi:
        versioni = [
            dict(versione)
            for versione in conn.execute(
                """
                SELECT riferimento, codice, data, tipo, quantita, costo_unitario, ordine
                FROM flussi_versioni
                WHERE riferimento = ? AND codice = ?
                ORDER BY versione
                """,
                (riga["riferimento"], riga["codice"]),
            )
        ]
        if not versioni:
            gruppi["nuovi"].append(riga)
        elif _uguali(riga, versioni[-1]):
            gruppi["ignorati"].append(riga)
        elif any(_uguali(riga, versione) for versione in versioni):
            gruppi["superati"].append(riga)
        else:
            gruppi["da_confermare"].append({"nuovo": riga, "precedente": versioni[-1]})
    return gruppi


def _uguali(prima: dict, seconda: dict) -> bool:
    return all(prima[campo] == seconda[campo] for campo in CAMPI_VERSIONE)


def _flussi_correnti(conn) -> list[dict]:
    righe = conn.execute(
        """
        SELECT riferimento, codice, tipo, quantita, costo_unitario
        FROM flussi_versioni v
        WHERE versione = (
            SELECT MAX(versione) FROM flussi_versioni
            WHERE riferimento = v.riferimento AND codice = v.codice
        )
        """
    )
    return [dict(riga) for riga in righe]


def _importi_risultanti(conn, nuovi: list[dict]) -> dict[str, int]:
    importi = magazzino.totali(conn)
    for riga in nuovi:
        importi[riga["codice"]] = importi.get(riga["codice"], 0) + magazzino.effetto(
            riga["tipo"], riga["quantita"]
        )
    return importi


def _avvisi_giacenze(nel_file, attuali, giacenze) -> list[str]:
    avvisi = []
    diverse = sorted(
        codice for codice, valore in nel_file.items() if valore != attuali.get(codice, 0)
    )
    if diverse:
        avvisi.append(
            "Il foglio Giacenze è in sola lettura: ignorati i valori diversi per "
            + ", ".join(diverse)
        )
    for riga in giacenze:
        if riga["categoria"] == "articolo" and riga["negativa"]:
            avvisi.append(
                f"La giacenza dell'articolo {riga['codice']} diventerebbe negativa "
                f"({riga['quantita']:g})"
            )
    return avvisi


def _cambiamenti(stato, nuove) -> dict[str, dict]:
    cambiamenti = {}
    for foglio in FOGLI_STATO:
        differenze = _differenze(foglio, stato[foglio.nome], nuove[foglio.nome])
        if any(differenze.values()):
            cambiamenti[foglio.nome] = differenze
    return cambiamenti


def _differenze(foglio: Foglio, attuali, nuove) -> dict[str, list]:
    def per_chiave(righe):
        return {tuple(riga[campo] for campo in foglio.chiave): riga for riga in righe}

    prima, dopo = per_chiave(attuali), per_chiave(nuove)
    modificati = []
    for chiave in prima.keys() & dopo.keys():
        campi = [c for c in foglio.campi if prima[chiave][c] != dopo[chiave][c]]
        if campi:
            modificati.append(
                {
                    "chiave": " / ".join(map(str, chiave)),
                    "prima": {c: _per_utente(foglio, c, prima[chiave][c]) for c in campi},
                    "dopo": {c: _per_utente(foglio, c, dopo[chiave][c]) for c in campi},
                }
            )
    return {
        "aggiunti": [
            " / ".join(map(str, chiave)) for chiave in sorted(dopo.keys() - prima.keys())
        ],
        "modificati": sorted(modificati, key=lambda voce: voce["chiave"]),
        "rimossi": [
            " / ".join(map(str, chiave)) for chiave in sorted(prima.keys() - dopo.keys())
        ],
    }


def _per_utente(foglio: Foglio, campo: str, valore):
    tipo = next(colonna.tipo for colonna in foglio.colonne if colonna.campo == campo)
    return magazzino.da_millesimi(valore) if tipo == "quantita" else valore


def _flusso_per_utente(riga: dict) -> dict:
    return {**riga, "quantita": magazzino.da_millesimi(riga["quantita"])}


def _applica_stato(conn, righe) -> None:
    for foglio in FOGLI_STATO:
        if foglio in (ORDINI, FASI, ARRIVI):
            continue
        conn.execute(f"DELETE FROM {foglio.tabella}")
        _inserisci(conn, foglio, righe[foglio.nome])

    # Gli ordini assenti dal file e le previsioni chiuse restano nel database.
    conn.execute("UPDATE ordini SET presente_nel_file = 0")
    conn.executemany(
        """
        INSERT INTO ordini (codice, articolo, quantita, data_spedizione, presente_nel_file)
        VALUES (:codice, :articolo, :quantita, :data_spedizione, 1)
        ON CONFLICT (codice) DO UPDATE SET
            articolo = excluded.articolo,
            quantita = excluded.quantita,
            data_spedizione = excluded.data_spedizione,
            presente_nel_file = 1
        """,
        righe[ORDINI.nome],
    )
    conn.execute(f"DELETE FROM {FASI.tabella} WHERE {FASI.filtro}")
    _inserisci(conn, FASI, righe[FASI.nome])
    conn.execute(f"DELETE FROM {ARRIVI.tabella} WHERE {ARRIVI.filtro}")
    _inserisci(conn, ARRIVI, righe[ARRIVI.nome])


def _inserisci(conn, foglio: Foglio, righe: list[dict]) -> None:
    segnaposto = ", ".join(f":{campo}" for campo in foglio.campi)
    conn.executemany(
        f"INSERT INTO {foglio.tabella} ({', '.join(foglio.campi)}) VALUES ({segnaposto})",
        righe,
    )


def _registra_versione(conn, riga: dict, versione: int) -> None:
    conn.execute(
        """
        INSERT INTO flussi_versioni
            (riferimento, codice, versione, data, tipo, quantita, costo_unitario, ordine)
        VALUES (:riferimento, :codice, :versione, :data, :tipo, :quantita,
                :costo_unitario, :ordine)
        """,
        {**riga, "versione": versione},
    )


def _registra_movimento(conn, riga: dict, tipo: str, quantita: int) -> None:
    conn.execute(
        """
        INSERT INTO movimenti
            (riferimento, data, tipo, codice, quantita, costo_unitario, ordine, origine)
        VALUES (:riferimento, :data, :tipo_movimento, :codice, :variazione,
                :costo_unitario, :ordine, 'file')
        """,
        {**riga, "tipo_movimento": tipo, "variazione": quantita},
    )


def _registra_nuovo(conn, riga: dict) -> None:
    _registra_versione(conn, riga, 1)
    _registra_movimento(
        conn, riga, riga["tipo"], magazzino.effetto(riga["tipo"], riga["quantita"])
    )


def _registra_correzione(conn, voce: dict) -> None:
    """Il movimento originale resta: si aggiunge solo la differenza."""
    nuovo, precedente = voce["nuovo"], voce["precedente"]
    versione = conn.execute(
        "SELECT MAX(versione) FROM flussi_versioni WHERE riferimento = ? AND codice = ?",
        (nuovo["riferimento"], nuovo["codice"]),
    ).fetchone()[0]
    _registra_versione(conn, nuovo, versione + 1)
    differenza = magazzino.effetto(nuovo["tipo"], nuovo["quantita"]) - magazzino.effetto(
        precedente["tipo"], precedente["quantita"]
    )
    _registra_movimento(conn, nuovo, "correzione", differenza)
