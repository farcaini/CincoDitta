"""Giacenze calcolate dal registro dei movimenti."""

from datetime import date


def effetto(tipo: str, quantita: int) -> int:
    """Variazione di giacenza di un flusso, in millesimi."""
    return -quantita if tipo == "spedizione" else quantita


def da_millesimi(valore: int | None) -> float | None:
    return None if valore is None else valore / 1000


def totali(conn) -> dict[str, int]:
    righe = conn.execute(
        "SELECT codice, SUM(quantita) AS totale FROM movimenti GROUP BY codice"
    )
    return {riga["codice"]: riga["totale"] for riga in righe}


def componi_giacenze(
    importi: dict[str, int], materiali: list[dict], articoli: list[dict]
) -> list[dict]:
    """Una riga per ogni materiale e articolo, anche se a zero."""
    elenco = [
        (riga["codice"], riga["descrizione"], riga["tipo"], riga["unita"])
        for riga in materiali
    ]
    elenco += [
        (riga["codice"], riga["descrizione"], "articolo", "pezzi") for riga in articoli
    ]
    return [
        {
            "codice": codice,
            "descrizione": descrizione,
            "categoria": categoria,
            "unita": unita,
            "quantita": da_millesimi(importi.get(codice, 0)),
            "negativa": importi.get(codice, 0) < 0,
        }
        for codice, descrizione, categoria, unita in elenco
    ]


def giacenze(conn) -> list[dict]:
    materiali = conn.execute(
        "SELECT codice, descrizione, tipo, unita FROM materiali ORDER BY codice"
    )
    articoli = conn.execute(
        "SELECT codice, descrizione FROM articoli ORDER BY codice"
    )
    return componi_giacenze(
        totali(conn), [dict(r) for r in materiali], [dict(r) for r in articoli]
    )


def movimenti(conn, codice: str) -> list[dict]:
    righe = conn.execute(
        "SELECT * FROM movimenti WHERE codice = ? ORDER BY id", (codice,)
    )
    return [
        {**dict(riga), "quantita": da_millesimi(riga["quantita"])} for riga in righe
    ]


def arrivi_previsti(conn, oggi: date | None = None) -> list[dict]:
    """Previsioni con stato: chiusa, in ritardo oppure aperta."""
    oggi = (oggi or date.today()).isoformat()
    righe = conn.execute(
        """
        SELECT a.*, EXISTS (
            SELECT 1 FROM movimenti m
            WHERE m.tipo = 'arrivo'
              AND m.riferimento = a.riferimento
              AND m.codice = a.materiale
        ) AS chiusa
        FROM arrivi_previsti a
        ORDER BY a.data, a.riferimento
        """
    )
    risultato = []
    for riga in righe:
        if riga["chiusa"]:
            stato = "chiusa"
        elif riga["data"] < oggi:
            stato = "in ritardo"
        else:
            stato = "aperta"
        risultato.append(
            {
                "riferimento": riga["riferimento"],
                "materiale": riga["materiale"],
                "quantita": da_millesimi(riga["quantita"]),
                "data": riga["data"],
                "stato": stato,
            }
        )
    return risultato
