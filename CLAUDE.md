# CincoDitta

Software per l'organizzazione del lavoro in una ditta di stampaggio plastica.
Contesto e vincoli del progetto: `openspec/config.yaml`.

## Comandi

- Avvio: `uv run uvicorn cincoditta.main:app --reload`
- Test: `uv run pytest`
- Stato delle specifiche: `openspec list`, `openspec validate --all`

## Regole

- Le nuove funzionalità passano da una modifica OpenSpec (`/opsx:propose`) prima del codice.
- Specifiche, documentazione e interfaccia sono in italiano.
- Non versionare mai database o file con dati aziendali.
