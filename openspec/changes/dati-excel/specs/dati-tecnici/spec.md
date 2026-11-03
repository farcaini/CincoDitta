# Spec Delta

## Purpose

Conserva i dati tecnici e di costo mantenuti dal gestore in Excel, su cui si basano pianificazione, controllo dei materiali e costo del pezzo.

## ADDED Requirements

### Requirement: Presse e stampi
Il sistema SHALL conservare per ogni pressa codice, nome, tempo di spurgo e consumo energetico, e per ogni stampo codice, numero di impronte, tempo ciclo e tempo di cambio stampo.

#### Scenario: Nuova pressa
- **WHEN** il gestore aggiunge una pressa con tutti i dati e conferma il caricamento
- **THEN** la pressa è disponibile con quei valori

### Requirement: Compatibilità tra stampi e presse
Il sistema SHALL conservare per ogni stampo le presse su cui può essere montato, come relazione molti a molti.

#### Scenario: Stampo compatibile con due presse
- **WHEN** il foglio Compatibilità ha due righe per lo stesso stampo con presse diverse
- **THEN** il sistema registra entrambe le presse come compatibili

#### Scenario: Coppia duplicata
- **WHEN** la stessa coppia stampo e pressa compare due volte
- **THEN** il sistema segnala un errore

### Requirement: Materiali
Il sistema SHALL conservare per ogni materiale codice, descrizione, tipo (materia prima o componente) e unità di misura (kg o pezzi). Il costo non appartiene al materiale, ma ai singoli flussi in ingresso.

#### Scenario: Tipo non ammesso
- **WHEN** un materiale ha un tipo diverso da materia prima o componente
- **THEN** il sistema segnala un errore

### Requirement: Articoli e distinta
Il sistema SHALL conservare per ogni articolo il codice, la descrizione, lo stampo e il peso del pezzo, e la distinta dei suoi materiali. Il peso della materozza MUST NOT essere richiesto, perché viene rimacinata e riusata.

#### Scenario: Materia prima in distinta
- **WHEN** la distinta indica una materia prima senza quantità per pezzo
- **THEN** il sistema accetta la riga, perché il consumo si ricava dal peso del pezzo

#### Scenario: Componente senza quantità
- **WHEN** la distinta indica un componente senza quantità per pezzo
- **THEN** il sistema lo segnala come dato mancante

### Requirement: Tipi di montaggio
Il sistema SHALL conservare per ogni tipo di montaggio la modalità: a pezzo, con velocità in pezzi all'ora e costo orario, oppure a ordine, con durata in giorni e costo per ordine o per pezzo.

#### Scenario: Montaggio a pezzo
- **WHEN** un montaggio a pezzo indica velocità e costo orario
- **THEN** il sistema lo registra come lavorazione dipendente dalla quantità

#### Scenario: Lavorazione da terzista
- **WHEN** un montaggio a ordine indica durata e costo per ordine
- **THEN** il sistema lo registra come lavorazione dell'intero ordine

#### Scenario: Modalità non ammessa
- **WHEN** un montaggio ha una modalità diversa da a pezzo o a ordine
- **THEN** il sistema segnala un errore

### Requirement: Parametri di costo
Il sistema SHALL conservare i parametri generali, tra cui il costo dell'energia per kWh e il costo orario del personale per macchina, già ripartito dal gestore in base a quante macchine segue un operatore.

#### Scenario: Aggiornamento di un parametro
- **WHEN** il gestore cambia il costo dell'energia e conferma il caricamento
- **THEN** il sistema conserva il nuovo valore

### Requirement: Dati mancanti segnalati
Il sistema SHALL accettare come vuoti tempi, pesi, consumi e costi, elencando i dati mancanti per ogni elemento. Il sistema MUST NOT sostituirli con valori stimati.

#### Scenario: Stampo senza tempo ciclo
- **WHEN** uno stampo ha il tempo ciclo vuoto
- **THEN** il sistema accetta la riga e lo elenca tra i dati mancanti

#### Scenario: Valore non positivo
- **WHEN** un tempo o un peso è zero o negativo
- **THEN** il sistema segnala un errore

### Requirement: Rimozione di elementi in uso
Il sistema SHALL impedire la rimozione di un elemento ancora usato da altri dati o con movimenti di magazzino registrati.

#### Scenario: Materiale con movimenti
- **WHEN** il file non contiene più un materiale con movimenti registrati
- **THEN** il sistema segnala un errore e non applica il file
