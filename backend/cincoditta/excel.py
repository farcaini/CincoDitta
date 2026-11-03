"""Generazione e lettura del file Excel."""

import math
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.worksheet.datavalidation import DataValidation

from cincoditta import magazzino
from cincoditta.fogli import (
    FLUSSI,
    FOGLI_STATO,
    GIACENZE,
    PARAMETRI,
    PARAMETRI_ATTESI,
    Colonna,
    Foglio,
    leggi_stato,
)

DIMENSIONE_MASSIMA = 10 * 1024 * 1024
DIMENSIONE_ESTRATTA_MASSIMA = 200 * 1024 * 1024
RIGHE_CON_MENU = 1000
VALORE_MASSIMO = 10**12


class FileNonValido(Exception):
    """Il file non è un .xlsx leggibile."""


@dataclass
class Lettura:
    righe: dict[str, list[dict]] = field(default_factory=dict)
    errori: list[dict] = field(default_factory=list)
    # Quantità del foglio Giacenze, in millesimi; None se non è un numero.
    giacenze: dict[str, int | None] = field(default_factory=dict)


def errore(foglio: str, riga: int | None, colonna: str | None, messaggio: str) -> dict:
    return {"foglio": foglio, "riga": riga, "colonna": colonna, "messaggio": messaggio}


def genera_file(conn) -> bytes:
    stato = leggi_stato(conn)
    nomi_presenti = {riga["nome"] for riga in stato[PARAMETRI.nome]}
    stato[PARAMETRI.nome] += [
        {"nome": nome, "valore": None}
        for nome in PARAMETRI_ATTESI
        if nome not in nomi_presenti
    ]

    libro = Workbook()
    libro.remove(libro.active)
    for foglio in FOGLI_STATO:
        _scrivi_foglio(libro, foglio, stato[foglio.nome])
    _scrivi_foglio(libro, FLUSSI, [])

    giacenze = libro.create_sheet(GIACENZE)
    _intestazioni(giacenze, ["codice", "quantità"])
    for riga in magazzino.giacenze(conn):
        giacenze.append([riga["codice"], riga["quantita"]])
    giacenze.protection.sheet = True

    uscita = BytesIO()
    libro.save(uscita)
    return uscita.getvalue()


def _intestazioni(foglio_excel, nomi: list[str]) -> None:
    foglio_excel.append(nomi)
    for cella in foglio_excel[1]:
        cella.font = Font(bold=True)
    foglio_excel.freeze_panes = "A2"


def _scrivi_foglio(libro, foglio: Foglio, righe: list[dict]) -> None:
    foglio_excel = libro.create_sheet(foglio.nome)
    _intestazioni(foglio_excel, [colonna.nome for colonna in foglio.colonne])
    for riga in righe:
        foglio_excel.append(
            [_valore_per_file(colonna, riga[colonna.campo]) for colonna in foglio.colonne]
        )
    for indice, colonna in enumerate(foglio.colonne, start=1):
        lettera = foglio_excel.cell(row=1, column=indice).column_letter
        foglio_excel.column_dimensions[lettera].width = max(12, len(colonna.nome) + 2)
        if colonna.tipo == "scelta":
            menu = DataValidation(
                type="list", formula1=f'"{",".join(colonna.scelte)}"', allow_blank=True
            )
            foglio_excel.add_data_validation(menu)
            menu.add(f"{lettera}2:{lettera}{RIGHE_CON_MENU}")
        elif colonna.tipo == "data":
            for cella in foglio_excel[lettera][1:]:
                cella.number_format = "DD/MM/YYYY"


def _valore_per_file(colonna: Colonna, valore):
    if valore is None:
        return None
    if colonna.tipo == "quantita":
        return magazzino.da_millesimi(valore)
    if colonna.tipo == "data":
        return date.fromisoformat(valore)
    return valore


def leggi_file(contenuto: bytes) -> Lettura:
    """Legge tutti i fogli raccogliendo gli errori di formato, senza fermarsi al primo."""
    libro = _apri(contenuto)
    lettura = Lettura()
    try:
        for foglio in (*FOGLI_STATO, FLUSSI):
            if foglio.nome not in libro.sheetnames:
                lettura.errori.append(errore(foglio.nome, None, None, "Foglio mancante"))
                continue
            lettura.righe[foglio.nome] = _leggi_foglio(
                libro[foglio.nome], foglio, lettura.errori
            )
        if GIACENZE in libro.sheetnames:
            lettura.giacenze = _leggi_giacenze(libro[GIACENZE])
    finally:
        libro.close()
    return lettura


def _apri(contenuto: bytes):
    if len(contenuto) > DIMENSIONE_MASSIMA:
        raise FileNonValido("Il file supera i 10 MB")
    try:
        with zipfile.ZipFile(BytesIO(contenuto)) as archivio:
            estratto = sum(voce.file_size for voce in archivio.infolist())
        if estratto > DIMENSIONE_ESTRATTA_MASSIMA:
            raise FileNonValido("Il contenuto del file è troppo grande")
        return load_workbook(BytesIO(contenuto), read_only=True, data_only=True)
    except (zipfile.BadZipFile, InvalidFileException, KeyError, OSError, ValueError) as e:
        raise FileNonValido("Il file non è un .xlsx leggibile") from e


def _leggi_foglio(foglio_excel, foglio: Foglio, errori: list[dict]) -> list[dict]:
    righe = foglio_excel.iter_rows(values_only=True)
    intestazione = next(righe, ())
    posizioni = {
        str(nome).strip().lower(): indice
        for indice, nome in enumerate(intestazione)
        if nome is not None
    }
    mancanti = [c for c in foglio.colonne if c.nome.lower() not in posizioni]
    for colonna in mancanti:
        errori.append(errore(foglio.nome, 1, colonna.nome, "Colonna mancante"))
    if mancanti:
        return []

    risultato = []
    for numero, valori in enumerate(righe, start=2):
        if all(_vuota(valore) for valore in valori):
            continue
        riga = {"_riga": numero}
        for colonna in foglio.colonne:
            posizione = posizioni[colonna.nome.lower()]
            grezzo = valori[posizione] if posizione < len(valori) else None
            try:
                riga[colonna.campo] = converti(colonna, grezzo)
            except ValueError as e:
                riga[colonna.campo] = None
                errori.append(errore(foglio.nome, numero, colonna.nome, str(e)))
        risultato.append(riga)
    return risultato


def _vuota(valore) -> bool:
    return valore is None or (isinstance(valore, str) and not valore.strip())


def _leggi_giacenze(foglio_excel) -> dict[str, int | None]:
    colonna = Colonna("quantità", "quantita", tipo="quantita")
    righe = foglio_excel.iter_rows(values_only=True)
    next(righe, None)
    giacenze = {}
    for valori in righe:
        if len(valori) < 2 or _vuota(valori[0]):
            continue
        try:
            giacenze[_testo(valori[0])] = converti(colonna, valori[1])
        except ValueError:
            giacenze[_testo(valori[0])] = None
    return giacenze


def converti(colonna: Colonna, valore):
    """Normalizza una cella secondo il tipo della colonna; ValueError se non è valida."""
    if _vuota(valore):
        if colonna.obbligatoria:
            raise ValueError("Valore obbligatorio mancante")
        return None
    match colonna.tipo:
        case "testo":
            return _testo(valore)
        case "scelta":
            scelta = _testo(valore).lower()
            if scelta not in colonna.scelte:
                raise ValueError(f"Valore non ammesso: usa {', '.join(colonna.scelte)}")
            return scelta
        case "data":
            return _data(valore)
        case "numero":
            numero = float(_decimale(valore))
        case "intero":
            numero = _decimale(valore)
            if numero != numero.to_integral_value():
                raise ValueError("Serve un numero intero")
            numero = int(numero)
        case "quantita":
            numero = int(
                (_decimale(valore) * 1000).quantize(Decimal(1), rounding=ROUND_HALF_UP)
            )
    if colonna.positivo and numero <= 0:
        raise ValueError("Il valore deve essere maggiore di zero")
    return numero


def _testo(valore) -> str:
    if isinstance(valore, float) and valore.is_integer():
        valore = int(valore)
    return str(valore).strip()


def _decimale(valore) -> Decimal:
    if isinstance(valore, bool) or isinstance(valore, (date, datetime)):
        raise ValueError("Serve un numero")
    try:
        numero = Decimal(str(valore).strip().replace(",", "."))
    except InvalidOperation as e:
        raise ValueError("Serve un numero") from e
    if not math.isfinite(numero) or abs(numero) > VALORE_MASSIMO:
        raise ValueError("Serve un numero")
    return numero


def _data(valore) -> str:
    if isinstance(valore, datetime):
        return valore.date().isoformat()
    if isinstance(valore, date):
        return valore.isoformat()
    testo = str(valore).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(testo, formato).date().isoformat()
        except ValueError:
            pass
    raise ValueError("Serve una data valida (GG/MM/AAAA)")
