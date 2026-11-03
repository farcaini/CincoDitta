# Spec Delta

## Purpose

Conserva gli ordini inseriti dal gestore in Excel e la sequenza di montaggi richiesta da ciascuno, come punto di partenza della pianificazione.

## ADDED Requirements

### Requirement: Ordini con codice stabile
Il sistema SHALL identificare ogni ordine con un codice univoco e conservarne articolo, quantità e data di spedizione. Ricaricare un ordine con lo stesso codice MUST NOT creare un duplicato.

#### Scenario: Nuovo ordine
- **WHEN** il gestore aggiunge una riga con un codice nuovo e conferma il caricamento
- **THEN** il sistema registra un nuovo ordine

#### Scenario: Ordine ricaricato
- **WHEN** il file contiene un ordine già registrato con gli stessi valori
- **THEN** l'ordine non cambia e l'anteprima non lo elenca tra i cambiamenti

#### Scenario: Codice ripetuto nel file
- **WHEN** lo stesso codice ordine compare su due righe
- **THEN** il sistema segnala un errore

#### Scenario: Dati dell'ordine non validi
- **WHEN** un ordine non ha una data di spedizione valida o ha una quantità non positiva
- **THEN** il sistema segnala un errore

### Requirement: Ordini modificati o tolti
Il sistema SHALL elencare nell'anteprima gli ordini modificati o assenti dal file. Un ordine assente MUST NOT essere cancellato: il sistema lo conserva e lo marca come non più presente nel file.

#### Scenario: Quantità modificata
- **WHEN** il gestore cambia la quantità di un ordine esistente e carica il file
- **THEN** l'anteprima mostra il valore precedente e quello nuovo

#### Scenario: Ordine tolto dal file
- **WHEN** il gestore toglie un ordine dal file e conferma il caricamento
- **THEN** il sistema conserva l'ordine e lo marca come non più presente nel file

### Requirement: Fasi di montaggio in sequenza
Il sistema SHALL conservare per ogni ordine zero o più fasi di montaggio, ordinate per sequenza. Lo stesso articolo MAY avere fasi diverse in ordini diversi.

#### Scenario: Più montaggi
- **WHEN** un ordine ha le fasi 1 montaggio gancio e 2 montaggio molla
- **THEN** il sistema conserva entrambe le fasi in quest'ordine

#### Scenario: Ordine senza montaggio
- **WHEN** un ordine non ha righe nel foglio Fasi montaggio
- **THEN** il sistema lo registra come ordine senza montaggio

#### Scenario: Sequenza ripetuta
- **WHEN** due fasi dello stesso ordine hanno la stessa sequenza
- **THEN** il sistema segnala un errore

#### Scenario: Tipo di montaggio inesistente
- **WHEN** una fase indica un tipo assente dal foglio Montaggi
- **THEN** il sistema segnala un errore
