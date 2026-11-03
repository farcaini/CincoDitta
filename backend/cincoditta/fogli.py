"""Struttura del file Excel: unica definizione per generazione e validazione."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Colonna:
    nome: str
    campo: str
    # testo, numero, intero, data, quantita (salvata in millesimi), scelta
    tipo: str = "testo"
    obbligatoria: bool = False
    positivo: bool = False
    scelte: tuple[str, ...] = ()
    # Se vuota compare tra i dati mancanti.
    segnala: bool = False


@dataclass(frozen=True)
class Foglio:
    nome: str
    tabella: str
    colonne: tuple[Colonna, ...]
    chiave: tuple[str, ...]
    # Condizione per le sole righe che il file rappresenta.
    filtro: str = ""

    @property
    def campi(self) -> tuple[str, ...]:
        return tuple(colonna.campo for colonna in self.colonne)


def _testo(nome, campo=None, **opzioni):
    return Colonna(nome, campo or nome, **opzioni)


def _dato(nome, tipo="numero"):
    return Colonna(nome, nome, tipo=tipo, positivo=True, segnala=True)


def _costo(nome):
    return Colonna(nome, nome, tipo="numero", positivo=True)


PRESSE = Foglio(
    "Presse",
    "presse",
    (
        _testo("codice", obbligatoria=True),
        _testo("nome"),
        _dato("spurgo_minuti"),
        _dato("consumo_kw"),
    ),
    ("codice",),
)
STAMPI = Foglio(
    "Stampi",
    "stampi",
    (
        _testo("codice", obbligatoria=True),
        _dato("impronte", "intero"),
        _dato("tempo_ciclo_secondi"),
        _dato("cambio_stampo_minuti"),
    ),
    ("codice",),
)
COMPATIBILITA = Foglio(
    "Compatibilità",
    "compatibilita",
    (_testo("stampo", obbligatoria=True), _testo("pressa", obbligatoria=True)),
    ("stampo", "pressa"),
)
MATERIALI = Foglio(
    "Materiali",
    "materiali",
    (
        _testo("codice", obbligatoria=True),
        _testo("descrizione"),
        _testo(
            "tipo",
            tipo="scelta",
            obbligatoria=True,
            scelte=("materia prima", "componente"),
        ),
        _testo("unità", "unita", tipo="scelta", obbligatoria=True, scelte=("kg", "pezzi")),
    ),
    ("codice",),
)
ARTICOLI = Foglio(
    "Articoli",
    "articoli",
    (
        _testo("codice", obbligatoria=True),
        _testo("descrizione"),
        _testo("stampo", obbligatoria=True),
        _dato("peso_pezzo_grammi"),
    ),
    ("codice",),
)
DISTINTA = Foglio(
    "Distinta",
    "distinta",
    (
        _testo("articolo", obbligatoria=True),
        _testo("materiale", obbligatoria=True),
        Colonna("quantità_per_pezzo", "quantita_per_pezzo", tipo="numero", positivo=True),
    ),
    ("articolo", "materiale"),
)
MONTAGGI = Foglio(
    "Montaggi",
    "montaggi",
    (
        _testo("tipo", obbligatoria=True),
        _testo(
            "modalità",
            "modalita",
            tipo="scelta",
            obbligatoria=True,
            scelte=("a pezzo", "a ordine"),
        ),
        _costo("pezzi_ora"),
        _costo("durata_giorni"),
        _costo("costo_orario"),
        _costo("costo_ordine"),
        _costo("costo_pezzo"),
    ),
    ("tipo",),
)
PARAMETRI = Foglio(
    "Parametri",
    "parametri",
    (_testo("nome", obbligatoria=True), _dato("valore")),
    ("nome",),
)
ORDINI = Foglio(
    "Ordini",
    "ordini",
    (
        _testo("codice", obbligatoria=True),
        _testo("articolo", obbligatoria=True),
        Colonna("quantità", "quantita", tipo="intero", obbligatoria=True, positivo=True),
        Colonna("data_spedizione", "data_spedizione", tipo="data", obbligatoria=True),
    ),
    ("codice",),
    "presente_nel_file = 1",
)
FASI = Foglio(
    "Fasi montaggio",
    "fasi_montaggio",
    (
        _testo("ordine", obbligatoria=True),
        Colonna("sequenza", "sequenza", tipo="intero", obbligatoria=True, positivo=True),
        _testo("tipo", obbligatoria=True),
    ),
    ("ordine", "sequenza"),
    "ordine IN (SELECT codice FROM ordini WHERE presente_nel_file = 1)",
)
ARRIVI = Foglio(
    "Arrivi previsti",
    "arrivi_previsti",
    (
        _testo("riferimento", obbligatoria=True),
        _testo("materiale", obbligatoria=True),
        Colonna("quantità", "quantita", tipo="quantita", obbligatoria=True, positivo=True),
        Colonna("data", "data", tipo="data", obbligatoria=True),
    ),
    ("riferimento", "materiale"),
    """NOT EXISTS (
        SELECT 1 FROM movimenti m
        WHERE m.tipo = 'arrivo'
          AND m.riferimento = arrivi_previsti.riferimento
          AND m.codice = arrivi_previsti.materiale
    )""",
)
FLUSSI = Foglio(
    "Flussi",
    "flussi_versioni",
    (
        _testo("riferimento", obbligatoria=True),
        Colonna("data", "data", tipo="data", obbligatoria=True),
        _testo(
            "tipo",
            tipo="scelta",
            obbligatoria=True,
            scelte=("arrivo", "spedizione", "rettifica"),
        ),
        _testo("codice", obbligatoria=True),
        Colonna("quantità", "quantita", tipo="quantita", obbligatoria=True),
        _costo("costo_unitario"),
        _testo("ordine"),
    ),
    ("riferimento", "codice"),
)

# Fogli che descrivono lo stato attuale, in ordine di dipendenza.
FOGLI_STATO = (
    PRESSE,
    STAMPI,
    COMPATIBILITA,
    MATERIALI,
    ARTICOLI,
    DISTINTA,
    MONTAGGI,
    PARAMETRI,
    ORDINI,
    FASI,
    ARRIVI,
)
GIACENZE = "Giacenze"
PARAMETRI_ATTESI = ("costo_energia_kwh", "costo_orario_personale")

RIFERIMENTI = (
    (COMPATIBILITA, "stampo", STAMPI, "codice"),
    (COMPATIBILITA, "pressa", PRESSE, "codice"),
    (ARTICOLI, "stampo", STAMPI, "codice"),
    (DISTINTA, "articolo", ARTICOLI, "codice"),
    (DISTINTA, "materiale", MATERIALI, "codice"),
    (ORDINI, "articolo", ARTICOLI, "codice"),
    (FASI, "ordine", ORDINI, "codice"),
    (FASI, "tipo", MONTAGGI, "tipo"),
    (ARRIVI, "materiale", MATERIALI, "codice"),
)


def leggi_stato(conn) -> dict[str, list[dict]]:
    """Restituisce le righe del database come il file le rappresenta."""
    stato = {}
    for foglio in FOGLI_STATO:
        condizione = f"WHERE {foglio.filtro}" if foglio.filtro else ""
        righe = conn.execute(
            f"SELECT {', '.join(foglio.campi)} FROM {foglio.tabella} {condizione} "
            f"ORDER BY {', '.join(foglio.chiave)}"
        )
        stato[foglio.nome] = [dict(riga) for riga in righe]
    return stato
