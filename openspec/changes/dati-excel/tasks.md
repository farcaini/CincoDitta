# Tasks

## 1. Preparazione

- [x] 1.1 Aggiungere `openpyxl` e `python-multipart` alle dipendenze e verificare con `uv run pytest` che i test esistenti passino
- [x] 1.2 Aggiungere `*.xlsx` a `.gitignore` e verificare con `git check-ignore` che un file di prova sia escluso

## 2. Database

- [x] 2.1 Aggiungere le migrazioni numerate con `PRAGMA user_version` e verificare con un test che vengano applicate una sola volta
- [x] 2.2 Creare le tabelle di dati tecnici, ordini, fasi, arrivi previsti, movimenti e anteprime, e verificare con un test che le chiavi esterne siano rispettate

## 3. Definizione dei fogli e generazione del file

- [x] 3.1 Definire in un unico modulo fogli, colonne, tipi e obbligatorietà, come da `design.md`, e verificare con un test che tutti i fogli siano presenti
- [x] 3.2 Generare il file `.xlsx` dalla definizione e dai dati correnti, con Flussi vuoto e Giacenze calcolate, e verificare con test i due scenari di scaricamento

## 4. Lettura e validazione

- [x] 4.1 Leggere un file caricato con limiti di formato e dimensione, e verificare con test il rifiuto di file non `.xlsx` o oltre 10 MB
- [x] 4.2 Validare intestazioni, tipi e valori ammessi riportando foglio, riga e colonna, e verificare con test gli scenari di `scambio-excel`
- [x] 4.3 Validare i dati tecnici, compresi riferimenti tra fogli, valori non positivi ed elementi in uso, e verificare con test gli scenari di `dati-tecnici`
- [x] 4.4 Elencare i dati mancanti per ogni elemento senza sostituirli, e verificare con un test lo scenario dello stampo senza tempo ciclo
- [x] 4.5 Validare ordini e fasi di montaggio, e verificare con test gli scenari di `ordini`

## 5. Movimenti e giacenze

- [x] 5.1 Registrare i movimenti con origine e calcolare le giacenze come somma, e verificare con test lo scenario della somma
- [x] 5.2 Validare i tipi di flusso e l'identità riferimento e codice, e verificare con test le righe ignorate e quelle ripetute nel file
- [x] 5.3 Gestire i flussi con valori diversi con correzione e versioni superate, e verificare con test gli scenari di differenza confermata, non confermata e vecchia copia
- [x] 5.4 Conservare il costo unitario sui flussi in ingresso e verificare con test che due arrivi conservino prezzi diversi e che un prezzo vuoto sia elencato tra i dati mancanti
- [x] 5.5 Ammettere ed evidenziare le giacenze negative, con l'avviso sugli articoli, e verificare con test i due scenari
- [x] 5.6 Gestire gli arrivi previsti aperti, chiusi e in ritardo, e verificare con test che non contino mai nella giacenza

## 6. Anteprima e conferma

- [x] 6.1 Calcolare e salvare l'anteprima senza modificare i dati, e verificare con un test che i dati restino invariati
- [x] 6.2 Applicare l'anteprima in un'unica transazione, rifiutandola se i dati sono cambiati, e verificare con test la conferma, il file con un errore e i dati cambiati
- [x] 6.3 Ignorare il foglio Giacenze con un avviso, e verificare con un test che una quantità modificata non cambi la giacenza
- [x] 6.4 Marcare gli ordini assenti come non più presenti nel file, e verificare con un test che l'ordine resti conservato

## 7. API e pagina

- [x] 7.1 Esporre scaricamento, anteprima, conferma, giacenze e movimenti sotto `/api`, e verificare con test `TestClient` il percorso completo
- [x] 7.2 Creare `frontend/dati.html` con caricamento, anteprima, errori, accettazione riga per riga dei flussi diversi, conferma e giacenze, e verificare il percorso nel browser con un file di prova
- [x] 7.3 Documentare nel `README.md` come usare il file, e riportare in `openspec/config.yaml` il flusso confermato al posto delle ipotesi di dominio; verificare con `openspec validate --all`

## 8. Verifica d'insieme

- [x] 8.1 Eseguire dall'inizio il percorso scarica, compila, carica, conferma, ricarica la stessa copia, e verificare che le giacenze non cambino al secondo caricamento

## Workflow follow-up

- Archiviare la modifica dopo la revisione, poi proseguire con `verifica-materiali`.
