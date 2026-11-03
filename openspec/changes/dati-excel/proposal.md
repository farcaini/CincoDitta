# Proposal

## Why

Pianificazione, controllo dei materiali e costo del pezzo hanno tutti bisogno di dati che oggi non sono raccolti in un unico posto: tempi e pesi degli stampi non esistono ancora in forma utilizzabile. Il gestore, che è una sola persona, vuole mantenerli in un foglio Excel facile da modificare, e il programma deve poterli leggere in modo affidabile prima di poter calcolare qualunque coda.

## What Changes

- Il programma genera un file Excel con la sua struttura e con i dati correnti, da scaricare e modificare.
- Il gestore carica il file: il programma lo valida, mostra un'anteprima dei cambiamenti e applica tutto solo dopo la conferma, oppure non applica nulla.
- Il file contiene i dati tecnici: presse, stampi, compatibilità stampo-pressa, materiali, articoli, distinta, tipi di montaggio e parametri di costo.
- Il file contiene gli ordini e le loro fasi di montaggio, in sequenza. Il tipo di montaggio appartiene all'ordine, perché lo stesso articolo può essere lavorato in modi diversi.
- I dati mancanti sono ammessi e segnalati: il programma non inventa valori.
- Le giacenze non si inseriscono in Excel. Il gestore registra solo i flussi (arrivi, spedizioni, rettifiche), e il programma calcola le giacenze da un registro dei movimenti interno.
- Ogni flusso ha un riferimento, così ricaricare una vecchia copia del file non conta due volte lo stesso movimento. Se un flusso già registrato arriva con valori diversi, il gestore decide nell'anteprima se aggiornarlo.
- Il costo unitario dei materiali si indica sui flussi in ingresso, perché può cambiare da un arrivo all'altro.
- Gli arrivi previsti si registrano a parte e non contano come giacenza finché l'arrivo non è avvenuto.

Restano fuori da questa modifica, e sono affidati alle successive:

- `verifica-materiali`: calcolo del fabbisogno, controllo della materia prima e coda d'attesa.
- `code-di-stampa`: calcolo dei tempi, accorpamento, conferma del responsabile, scarico e reintegro della materia prima.
- `avanzamento-e-magazzino`: produzione, lista d'attesa montaggio, controllo qualità, carico automatico dei prodotti finiti.
- `costo-pezzo`: calcolo del costo. Qui si raccolgono solo i dati che gli serviranno.

## Capabilities

### New Capabilities

- `scambio-excel`: scaricamento del file, caricamento, validazione, anteprima e applicazione "tutto o niente".
- `dati-tecnici`: presse, stampi, compatibilità, materiali, articoli, distinta, montaggi, parametri e segnalazione dei dati mancanti.
- `ordini`: ordini con codice stabile e relative fasi di montaggio in sequenza.
- `movimenti-magazzino`: flussi con riferimento, registro dei movimenti, giacenze calcolate e arrivi previsti.

### Modified Capabilities

Nessuna: non esistono ancora specifiche.

## Impact

- **Codice:** nuovi moduli in `backend/cincoditta/`, prime tabelle SQLite con un meccanismo di migrazione, nuova pagina in `frontend/`.
- **API:** nuovi endpoint sotto `/api` per scaricare il file, caricarlo, confermare l'anteprima e leggere le giacenze.
- **Dipendenze:** `openpyxl` per i file Excel e `python-multipart` per il caricamento.
- **Dati:** il file compilato contiene dati aziendali e non va versionato; il repository è pubblico.
