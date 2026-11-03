# Design

## Context

Vedi `proposal.md` per le motivazioni. Il backend oggi è uno scheletro: `backend/cincoditta/db.py` apre la connessione SQLite (chiavi esterne e WAL attivi), `main.py` espone `/api/health` e serve `frontend/`. Non esistono tabelle né migrazioni. Il file è gestito da una sola persona, ma il programma genera a sua volta movimenti di magazzino, quindi file e database non devono mai sovrascriversi a vicenda.

## Goals / Non-Goals

**Goals:**

- Un'unica definizione dei fogli, da cui derivano sia il file generato sia la validazione.
- Nessun dato parziale o doppio, anche ricaricando un file vecchio.
- Giacenze sempre spiegabili a partire dai movimenti.

**Non-Goals:**

- Autenticazione: il server resta in ascolto solo su `127.0.0.1` finché non verrà definita.
- Leggere il file direttamente da una cartella condivisa: si passa sempre dal caricamento.
- Calcolare nell'anteprima gli effetti sulle date di spedizione: arriverà con `code-di-stampa`, che estenderà l'anteprima.

## Decisions

### I fogli sono definiti una sola volta nel codice

Un modulo dichiara fogli, colonne, tipi e obbligatorietà. Il generatore e il validatore leggono la stessa definizione, così il file non può divergere dal programma. Il file viene generato a richiesta: nel repository non si versiona alcun modello binario. Alternativa scartata: un `.xlsx` modello versionato, che andrebbe aggiornato a mano a ogni cambio.

| Foglio | Colonne | Natura |
| --- | --- | --- |
| Presse | codice, nome, spurgo_minuti, consumo_kw | Stato completo |
| Stampi | codice, impronte, tempo_ciclo_secondi, cambio_stampo_minuti | Stato completo |
| Compatibilità | stampo, pressa | Stato completo |
| Materiali | codice, descrizione, tipo, unità | Stato completo |
| Articoli | codice, descrizione, stampo, peso_pezzo_grammi | Stato completo |
| Distinta | articolo, materiale, quantità_per_pezzo | Stato completo |
| Montaggi | tipo, modalità, pezzi_ora, durata_giorni, costo_orario, costo_ordine, costo_pezzo | Stato completo |
| Parametri | nome, valore | Stato completo |
| Ordini | codice, articolo, quantità, data_spedizione | Stato completo |
| Fasi montaggio | ordine, sequenza, tipo | Stato completo |
| Arrivi previsti | riferimento, materiale, quantità, data | Stato completo |
| Flussi | riferimento, data, tipo, codice, quantità, costo_unitario, ordine | Solo eventi nuovi |
| Giacenze | codice, quantità | Sola lettura, ignorato al caricamento |

Nella Distinta, la materia prima ha `quantità_per_pezzo` vuota, perché il consumo si ricava dal peso del pezzo; i componenti la indicano.

### Due tipi di foglio: stato e flussi

I fogli di stato descrivono com'è la realtà ora: si confrontano con il database e si applicano le differenze. Il foglio Flussi descrive eventi: ogni riga aggiunge un movimento. Alternativa scartata: giacenze in Excel con confronto tra versioni, più fragile e superata dalla scelta del gestore.

### Identità dei flussi: riferimento e codice

La chiave è la coppia `(riferimento, codice)`, perché una bolla può avere più righe. Una riga già registrata e identica viene ignorata. Alternativa scartata: "un file si applica una sola volta" con un identificativo nascosto, che costringerebbe a riscaricare il file dopo ogni conferma.

### Flussi con valori diversi: conferma riga per riga

Una riga con la stessa chiave ma valori diversi compare nell'anteprima con valori precedenti e nuovi, e resta ignorata salvo conferma del gestore. La pagina invia le righe accettate insieme alla conferma dell'anteprima. Se accettata, il flusso assume i nuovi valori, ma il movimento originale resta: si aggiunge un movimento di correzione pari alla differenza, così il registro continua a spiegare la giacenza. Alternativa scartata: riscrivere il movimento, che cancellerebbe la storia.

Il sistema conserva ogni versione dei valori di un flusso. Una riga uguale a una versione già superata viene ignorata come "superata": altrimenti ricaricare una vecchia copia riproporrebbe ogni volta la correzione all'indietro.

### Prezzo sui flussi, non sul materiale

Il costo unitario sta sulle righe di arrivo e di rettifica positiva. Serve a `costo-pezzo`, che userà il prezzo più alto, e un solo prezzo nel foglio Materiali non basterebbe a calcolarlo. Il costo resta facoltativo: se manca, viene elencato tra i dati mancanti.

### Giacenza calcolata, mai salvata

Una tabella `movimenti` è l'unica fonte: la giacenza è la somma delle sue righe, con un campo origine (`file` o `interno`) che le modifiche successive useranno per scarichi e carichi automatici. Le quantità si salvano come interi in millesimi, per evitare errori di arrotondamento nelle somme. Alternativa scartata: una colonna saldo, che può disallinearsi dallo storico.

### Anteprima salvata e conferma separata

Il caricamento valida il file e salva in database il risultato, con un'impronta dello stato dei dati e dell'ultimo movimento. La conferma applica tutto in un'unica transazione. Se nel frattempo i dati sono cambiati, la conferma viene rifiutata e serve una nuova anteprima. Così ciò che il gestore ha visto è esattamente ciò che viene applicato. Resta valida solo l'ultima anteprima.

### Ordini rimossi dal file

Un ordine assente dal foglio viene marcato come "non più nel file" e mai cancellato, e l'anteprima lo elenca. Che cosa comporti se è già in coda lo stabilirà `code-di-stampa`, che potrà bloccare la conferma.

### Migrazioni minime

File SQL numerati in `backend/cincoditta/migrazioni/`, applicati all'avvio in ordine usando `PRAGMA user_version`. Alternativa scartata: Alembic, sproporzionato senza un ORM.

### Interfaccia

`GET /api/excel` restituisce il file, unica risposta non JSON. `POST /api/excel/anteprima` riceve il file e restituisce l'anteprima; `POST /api/excel/anteprima/{id}/conferma` la applica, ricevendo le righe in conflitto accettate; `GET /api/giacenze` restituisce le giacenze. La pagina statica `frontend/dati.html` guida il gestore in questi passaggi con JavaScript puro.

## Risks / Trade-offs

- [Il file scaricato contiene dati aziendali e il repository è pubblico] → `.gitignore` esclude `*.xlsx`; il server ascolta solo in locale.
- [File anomalo o molto grande] → si accettano solo `.xlsx`, fino a 10 MB, in sola lettura e senza eseguire macro.
- [Celle con formule senza valore salvato] → vengono lette come vuote e quindi segnalate, mai interpretate.
- [Il gestore cambia i nomi delle colonne] → intestazioni mancanti o rinominate bloccano il caricamento e vengono indicate.
- [Le giacenze teoriche si allontanano da quelle reali] → la rettifica è un'operazione normale; il registro ne conserva la storia.
- [Il foglio Flussi cresce se non viene svuotato] → dopo la conferma la pagina propone il file aggiornato, con il foglio vuoto.

## Migration Plan

Non ci sono dati da migrare. La partenza si fa inserendo nei Flussi una rettifica per ogni codice, con il risultato di un inventario. Per tornare indietro basta rimuovere le nuove pagine: il database è locale e può essere ricreato dal file e dai movimenti.

## Decisioni per le modifiche successive

Confermate dal gestore, da applicare quando verranno scritte quelle modifiche:

- **`costo-pezzo`:** il prezzo si valuta sul singolo ordine: se il prezzo di un materiale cambia tra l'inizio e la fine della stampa, si usa per tutti i pezzi il più alto di quel periodo. I prezzi precedenti all'ultimo in vigore all'inizio della stampa non contano.
- **`costo-pezzo`:** il costo orario del personale nei Parametri tiene già conto di quante macchine segue un operatore, quindi il programma non lo ripartisce.
- **`avanzamento-e-magazzino`:** i componenti vengono scalati all'ingresso in montaggio.
