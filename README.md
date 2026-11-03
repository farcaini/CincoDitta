# CincoDitta

Software per l'organizzazione del lavoro in una ditta di stampaggio plastica.

- **Backend:** Python (FastAPI) con SQLite
- **Frontend:** pagine web statiche (HTML, CSS, JavaScript), senza fase di build
- **Metodo:** sviluppo guidato dalle specifiche con [OpenSpec](https://github.com/Fission-AI/OpenSpec)

## Avvio

Serve [uv](https://docs.astral.sh/uv/).

```bash
uv run uvicorn cincoditta.main:app --reload
```

L'applicazione risponde su <http://127.0.0.1:8000>. Il database viene creato in
`data/cincoditta.db` e non viene versionato; per usare un altro percorso, imposta
`CINCODITTA_DB`.

## Dati e magazzino

I dati tecnici, gli ordini e i flussi di magazzino si gestiscono con un file Excel, dalla
pagina <http://127.0.0.1:8000/dati.html>:

1. Scarica il file: contiene i dati attuali, con il foglio Flussi vuoto.
2. Modifica i fogli e registra nei Flussi arrivi, spedizioni e rettifiche.
3. Carica il file: viene controllato e mostra un'anteprima, senza applicare nulla.
4. Conferma: i cambiamenti vengono applicati tutti insieme.

Regole principali:

- Le giacenze non si inseriscono: il programma le calcola dai movimenti. Il foglio Giacenze è
  in sola lettura. La situazione iniziale si carica con una rettifica per ogni codice.
- Riferimento e codice identificano un flusso: ricaricare una vecchia copia non lo conta due
  volte. Se i valori sono diversi, nell'anteprima scegli se aggiornarlo.
- Gli arrivi previsti non contano nella giacenza finché nei Flussi non c'è un arrivo con lo
  stesso riferimento e materiale.
- I dati tecnici vuoti sono ammessi e vengono elencati tra i dati mancanti, mai stimati.

Il file compilato contiene dati aziendali: non versionarlo (`*.xlsx` è escluso da git).

## Test

```bash
uv run pytest
```

## Struttura

| Percorso | Contenuto |
| --- | --- |
| `backend/cincoditta/` | API e accesso ai dati |
| `frontend/` | Pagine statiche servite dal backend |
| `tests/` | Test automatici |
| `openspec/specs/` | Specifiche correnti del sistema |
| `openspec/changes/` | Modifiche proposte o in corso |
| `data/` | Database locale, escluso da git |

## Sviluppo con OpenSpec

Ogni funzionalità parte da una proposta, in Claude Code:

1. `/opsx:explore`: chiarire l'idea, se serve
2. `/opsx:propose <idea>`: creare proposta, design, specifiche e attività
3. `/opsx:apply`: implementare le attività
4. `/opsx:archive`: archiviare la modifica e aggiornare le specifiche
