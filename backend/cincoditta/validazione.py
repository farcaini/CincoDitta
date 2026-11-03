"""Controlli di coerenza tra i fogli e segnalazione dei dati mancanti."""

from cincoditta.excel import errore
from cincoditta.fogli import (
    ARTICOLI,
    DISTINTA,
    FLUSSI,
    FOGLI_STATO,
    MATERIALI,
    MONTAGGI,
    ORDINI,
    PARAMETRI,
    PARAMETRI_ATTESI,
    RIFERIMENTI,
)


def valida(righe: dict[str, list[dict]], conn) -> list[dict]:
    """Restituisce gli errori di contenuto; le celle già illeggibili valgono None."""
    errori = []
    for foglio in (*FOGLI_STATO, FLUSSI):
        _chiavi_duplicate(foglio, righe.get(foglio.nome, []), errori)
    _riferimenti(righe, errori)
    _codici_ambigui(righe, errori)
    _montaggi(righe.get(MONTAGGI.nome, []), errori)
    _flussi(righe, conn, errori)
    _elementi_in_uso(righe, conn, errori)
    return errori


def _chiavi_duplicate(foglio, righe, errori) -> None:
    viste = set()
    for riga in righe:
        chiave = tuple(riga[campo] for campo in foglio.chiave)
        if None in chiave:
            continue
        if chiave in viste:
            errori.append(
                errore(
                    foglio.nome,
                    riga["_riga"],
                    None,
                    f"Riga ripetuta: {' / '.join(map(str, chiave))}",
                )
            )
        viste.add(chiave)


def _riferimenti(righe, errori) -> None:
    for foglio, campo, destinazione, campo_destinazione in RIFERIMENTI:
        if foglio.nome not in righe or destinazione.nome not in righe:
            continue
        validi = {riga[campo_destinazione] for riga in righe[destinazione.nome]}
        for riga in righe[foglio.nome]:
            valore = riga[campo]
            if valore is not None and valore not in validi:
                errori.append(
                    errore(
                        foglio.nome,
                        riga["_riga"],
                        campo,
                        f"{valore} non è presente nel foglio {destinazione.nome}",
                    )
                )


def _codici_ambigui(righe, errori) -> None:
    articoli = {riga["codice"] for riga in righe.get(ARTICOLI.nome, [])}
    for riga in righe.get(MATERIALI.nome, []):
        if riga["codice"] in articoli:
            errori.append(
                errore(
                    MATERIALI.nome,
                    riga["_riga"],
                    "codice",
                    f"{riga['codice']} è usato anche da un articolo",
                )
            )


def _montaggi(righe, errori) -> None:
    for riga in righe:
        if riga["costo_ordine"] is not None and riga["costo_pezzo"] is not None:
            errori.append(
                errore(
                    MONTAGGI.nome,
                    riga["_riga"],
                    "costo_ordine",
                    "Indica il costo per ordine oppure per pezzo, non entrambi",
                )
            )


def _flussi(righe, conn, errori) -> None:
    materiali = {riga["codice"] for riga in righe.get(MATERIALI.nome, [])}
    articoli = {riga["codice"] for riga in righe.get(ARTICOLI.nome, [])}
    ordini = {riga["codice"] for riga in righe.get(ORDINI.nome, [])}
    ordini |= {
        riga["codice"]
        for riga in conn.execute("SELECT codice FROM ordini WHERE presente_nel_file = 0")
    }

    def segnala(riga, colonna, messaggio):
        errori.append(errore(FLUSSI.nome, riga["_riga"], colonna, messaggio))

    for riga in righe.get(FLUSSI.nome, []):
        tipo, codice, quantita = riga["tipo"], riga["codice"], riga["quantita"]
        if codice is not None and codice not in materiali | articoli:
            segnala(riga, "codice", f"{codice} non è un materiale né un articolo")
        if tipo == "arrivo" and codice in articoli:
            segnala(riga, "codice", "L'arrivo riguarda solo i materiali")
        if tipo == "spedizione":
            if codice in materiali:
                segnala(riga, "codice", "La spedizione riguarda solo gli articoli")
            if riga["ordine"] is None:
                segnala(riga, "ordine", "La spedizione richiede l'ordine")
        if quantita is not None:
            if tipo in ("arrivo", "spedizione") and quantita <= 0:
                segnala(riga, "quantità", "La quantità deve essere maggiore di zero")
            if tipo == "rettifica" and quantita == 0:
                segnala(riga, "quantità", "La rettifica non può essere zero")
        if riga["ordine"] is not None and riga["ordine"] not in ordini:
            segnala(riga, "ordine", f"L'ordine {riga['ordine']} non esiste")
        if riga["costo_unitario"] is not None and not ingresso_di_materiale(
            riga, materiali
        ):
            segnala(
                riga,
                "costo_unitario",
                "Il costo si indica solo per arrivi e rettifiche positive di materiali",
            )


def ingresso_di_materiale(riga: dict, materiali: set[str]) -> bool:
    return (
        riga["codice"] in materiali
        and riga["tipo"] in ("arrivo", "rettifica")
        and (riga["quantita"] or 0) > 0
    )


def _elementi_in_uso(righe, conn, errori) -> None:
    def controlla(foglio, campo, usati):
        if foglio.nome not in righe:
            return
        presenti = {riga[campo] for riga in righe[foglio.nome]}
        for codice, motivo in sorted(usati.items()):
            if codice not in presenti:
                errori.append(
                    errore(foglio.nome, None, campo, f"{codice} non si può rimuovere: {motivo}")
                )

    con_movimenti = {
        riga["codice"]: "ha movimenti registrati"
        for riga in conn.execute("SELECT DISTINCT codice FROM movimenti")
    }
    codici_materiali = {
        riga["codice"] for riga in conn.execute("SELECT codice FROM materiali")
    }
    codici_articoli = {
        riga["codice"] for riga in conn.execute("SELECT codice FROM articoli")
    }
    articoli_in_uso = {
        riga["articolo"]: "è usato da un ordine non più nel file"
        for riga in conn.execute(
            "SELECT DISTINCT articolo FROM ordini WHERE presente_nel_file = 0"
        )
    }
    articoli_in_uso |= {c: m for c, m in con_movimenti.items() if c in codici_articoli}
    montaggi_in_uso = {
        riga["tipo"]: "è usato da un ordine non più nel file"
        for riga in conn.execute(
            """
            SELECT DISTINCT tipo FROM fasi_montaggio
            WHERE ordine IN (SELECT codice FROM ordini WHERE presente_nel_file = 0)
            """
        )
    }
    controlla(
        MATERIALI,
        "codice",
        {c: m for c, m in con_movimenti.items() if c in codici_materiali},
    )
    controlla(ARTICOLI, "codice", articoli_in_uso)
    controlla(MONTAGGI, "tipo", montaggi_in_uso)


def dati_mancanti(righe: dict[str, list[dict]], flussi: list[dict]) -> list[dict]:
    """Elenca i dati vuoti necessari ai calcoli, senza mai stimarli."""
    mancanti = []

    def aggiungi(foglio, elemento, campo):
        mancanti.append({"foglio": foglio, "elemento": elemento, "campo": campo})

    for foglio in FOGLI_STATO:
        for riga in righe.get(foglio.nome, []):
            elemento = " / ".join(str(riga[campo]) for campo in foglio.chiave)
            for colonna in foglio.colonne:
                if colonna.segnala and riga[colonna.campo] is None:
                    aggiungi(foglio.nome, elemento, colonna.nome)

    nomi_parametri = {riga["nome"] for riga in righe.get(PARAMETRI.nome, [])}
    for nome in PARAMETRI_ATTESI:
        if nome not in nomi_parametri:
            aggiungi(PARAMETRI.nome, nome, "valore")

    tipi = {riga["codice"]: riga["tipo"] for riga in righe.get(MATERIALI.nome, [])}
    for riga in righe.get(DISTINTA.nome, []):
        if tipi.get(riga["materiale"]) == "componente" and riga["quantita_per_pezzo"] is None:
            aggiungi(
                DISTINTA.nome,
                f"{riga['articolo']} / {riga['materiale']}",
                "quantità_per_pezzo",
            )

    for riga in righe.get(MONTAGGI.nome, []):
        if riga["modalita"] == "a pezzo":
            vuoti = [c for c in ("pezzi_ora", "costo_orario") if riga[c] is None]
        else:
            vuoti = ["durata_giorni"] if riga["durata_giorni"] is None else []
            if riga["costo_ordine"] is None and riga["costo_pezzo"] is None:
                vuoti.append("costo_ordine o costo_pezzo")
        for campo in vuoti:
            aggiungi(MONTAGGI.nome, riga["tipo"], campo)

    materiali = set(tipi)
    for riga in flussi:
        if riga["costo_unitario"] is None and ingresso_di_materiale(riga, materiali):
            aggiungi(
                FLUSSI.nome,
                f"{riga['riferimento']} / {riga['codice']}",
                "costo_unitario",
            )
    return mancanti
