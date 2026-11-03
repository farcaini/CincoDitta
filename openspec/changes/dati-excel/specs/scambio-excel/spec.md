# Spec Delta

## Purpose

Permette al gestore di scambiare dati con il programma tramite un unico file Excel, con controllo preventivo degli errori e applicazione solo dopo conferma.

## ADDED Requirements

### Requirement: Scaricamento del file aggiornato
Il sistema SHALL generare a richiesta un file `.xlsx` con tutti i fogli previsti, i dati correnti, il foglio Flussi senza righe e il foglio Giacenze calcolato al momento.

#### Scenario: Primo scaricamento senza dati
- **WHEN** il gestore scarica il file e il database è vuoto
- **THEN** il file contiene tutti i fogli con le sole intestazioni

#### Scenario: Scaricamento con dati esistenti
- **WHEN** il gestore scarica il file e sono presenti dati e movimenti
- **THEN** i fogli riportano i dati correnti, Flussi non ha righe e Giacenze mostra le quantità attuali

### Requirement: Validazione del file caricato
Il sistema SHALL controllare intestazioni, tipi di dato, valori ammessi, chiavi duplicate e riferimenti tra fogli, indicando per ogni errore foglio, riga e problema.

#### Scenario: Valore non valido
- **WHEN** il file contiene testo al posto di un numero in una colonna numerica
- **THEN** il sistema segnala foglio, riga e colonna dell'errore

#### Scenario: Riferimento inesistente
- **WHEN** un articolo indica uno stampo assente dal foglio Stampi
- **THEN** il sistema segnala un errore su quella riga

#### Scenario: Colonna rinominata
- **WHEN** a un foglio manca un'intestazione prevista
- **THEN** il sistema segnala il foglio e la colonna mancante

#### Scenario: File non accettato
- **WHEN** il file caricato non è un `.xlsx` o supera i 10 MB
- **THEN** il sistema lo rifiuta senza elaborarlo

### Requirement: Anteprima prima dell'applicazione
Il sistema SHALL mostrare, prima di applicare un file valido, elementi aggiunti, modificati e rimossi per foglio, nuovi flussi, righe ignorate, flussi da confermare, avvisi e giacenze risultanti.

#### Scenario: Anteprima di un file valido
- **WHEN** il gestore carica un file senza errori
- **THEN** il sistema mostra l'anteprima e i dati restano invariati

### Requirement: Applicazione tutto o niente
Il sistema SHALL applicare un file soltanto dopo la conferma dell'anteprima e per intero. Un file con errori MUST NOT modificare alcun dato.

#### Scenario: File con un solo errore
- **WHEN** il file contiene una sola riga non valida tra molte corrette
- **THEN** il sistema non applica nessuna riga e non permette la conferma

#### Scenario: Conferma
- **WHEN** il gestore conferma un'anteprima valida
- **THEN** il sistema applica tutti i cambiamenti mostrati

#### Scenario: Dati cambiati dopo l'anteprima
- **WHEN** il gestore conferma un'anteprima ma i dati sono cambiati dopo la sua creazione
- **THEN** il sistema rifiuta la conferma e chiede un nuovo caricamento

### Requirement: Foglio Giacenze in sola lettura
Il sistema SHALL ignorare al caricamento il contenuto del foglio Giacenze.

#### Scenario: Giacenza modificata nel file
- **WHEN** il gestore cambia una quantità nel foglio Giacenze e carica il file
- **THEN** la giacenza non cambia e l'anteprima lo segnala con un avviso
