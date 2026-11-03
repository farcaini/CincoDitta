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
