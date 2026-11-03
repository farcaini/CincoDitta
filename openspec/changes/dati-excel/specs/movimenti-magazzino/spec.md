# Spec Delta

## Purpose

Calcola le giacenze di materie prime, componenti e prodotti finiti da un registro dei movimenti, alimentato dai flussi inseriti dal gestore e dalle operazioni del programma.

## ADDED Requirements

### Requirement: Giacenze calcolate dai movimenti
Il sistema SHALL calcolare la giacenza di ogni codice come somma dei suoi movimenti. La giacenza MUST NOT essere impostabile direttamente.

#### Scenario: Somma dei movimenti
- **WHEN** un materiale ha un arrivo di 100 kg e una rettifica di -20 kg
- **THEN** la sua giacenza è 80 kg

#### Scenario: Consultazione
- **WHEN** il gestore consulta le giacenze
- **THEN** il sistema mostra la quantità per ogni materiale, componente e articolo

### Requirement: Registro con origine dei movimenti
Il sistema SHALL conservare ogni movimento con riferimento, data, tipo, codice, quantità, costo unitario e ordine se presenti, e origine (file o interno). I movimenti registrati MUST NOT essere modificati né cancellati: le correzioni si aggiungono come nuovi movimenti.

#### Scenario: Storico di un codice
- **WHEN** il gestore consulta i movimenti di un codice
- **THEN** il sistema mostra tutti i movimenti che ne spiegano la giacenza

### Requirement: Tipi di flusso ammessi
Il sistema SHALL accettare nel foglio Flussi solo: arrivo di materiale, con quantità positiva; spedizione di articolo, con quantità positiva e ordine obbligatorio; rettifica di qualunque codice, con quantità positiva o negativa, diversa da zero.

#### Scenario: Spedizione senza ordine
- **WHEN** una riga di spedizione non indica l'ordine
- **THEN** il sistema segnala un errore

#### Scenario: Spedizione registrata
- **WHEN** il gestore registra una spedizione di 200 pezzi e conferma il caricamento
- **THEN** la giacenza dell'articolo diminuisce di 200 pezzi

#### Scenario: Carico iniziale
- **WHEN** il gestore inserisce una rettifica positiva per un codice senza movimenti
- **THEN** la giacenza del codice è pari a quella quantità

### Requirement: Flussi non contati due volte
Il sistema SHALL identificare ogni flusso con la coppia riferimento e codice, ignorando le righe identiche già registrate e segnalandole nell'anteprima.

#### Scenario: Vecchia copia ricaricata
- **WHEN** il gestore ricarica un file con flussi già registrati
- **THEN** le giacenze non cambiano e l'anteprima elenca le righe come ignorate

#### Scenario: Bolla con più materiali
- **WHEN** due righe hanno lo stesso riferimento ma codici diversi
- **THEN** il sistema registra entrambi i movimenti

#### Scenario: Riga ripetuta nello stesso file
- **WHEN** due righe del foglio Flussi hanno stesso riferimento e stesso codice
- **THEN** il sistema segnala un errore

### Requirement: Conferma dei flussi già registrati con valori diversi
Il sistema SHALL elencare nell'anteprima le righe con riferimento e codice già registrati ma valori diversi, mostrando valori precedenti e nuovi. Ogni riga SHALL essere ignorata, salvo conferma esplicita del gestore.

#### Scenario: Differenza non confermata
- **WHEN** il gestore conferma l'anteprima senza accettare una riga con valori diversi
- **THEN** il sistema applica il resto del file e lascia invariato quel flusso

#### Scenario: Differenza confermata
- **WHEN** un arrivo registrato di 100 kg compare con 120 kg e il gestore accetta la riga
- **THEN** il flusso vale 120 kg, la giacenza aumenta di 20 kg e un movimento di correzione conserva la storia

#### Scenario: Vecchia copia dopo una correzione
- **WHEN** il file riporta i valori di un flusso già superati da una correzione confermata
- **THEN** il sistema ignora la riga senza chiedere conferma e l'anteprima la elenca come superata

### Requirement: Prezzo sui flussi in ingresso
Il sistema SHALL conservare il costo unitario indicato sugli arrivi e sulle rettifiche positive di materiali. Il costo vuoto SHALL essere accettato ed elencato tra i dati mancanti.

#### Scenario: Prezzi diversi tra due arrivi
- **WHEN** due arrivi dello stesso materiale indicano costi unitari diversi
- **THEN** il sistema conserva ciascun costo con il proprio movimento

#### Scenario: Arrivo senza prezzo
- **WHEN** un arrivo non indica il costo unitario
- **THEN** il sistema registra il movimento e lo elenca tra i dati mancanti

### Requirement: Giacenza negativa ammessa
Il sistema SHALL ammettere giacenze negative, per rappresentare materiale già impegnato oltre la disponibilità, e MUST evidenziarle. Una giacenza negativa di un articolo finito SHALL produrre un avviso nell'anteprima.

#### Scenario: Materiale impegnato oltre la giacenza
- **WHEN** i movimenti di un materiale danno una somma di -50 kg
- **THEN** il sistema mostra -50 kg evidenziati

#### Scenario: Spedizione oltre la giacenza
- **WHEN** una spedizione porterebbe sotto zero la giacenza di un articolo
- **THEN** l'anteprima mostra un avviso e la conferma resta possibile

### Requirement: Arrivi previsti
Il sistema SHALL conservare gli arrivi previsti con riferimento, materiale, quantità e data. Un arrivo previsto MUST NOT contare nella giacenza, e resta aperto finché non viene registrato un arrivo con lo stesso riferimento e materiale.

#### Scenario: Arrivo previsto
- **WHEN** il gestore inserisce un arrivo previsto di 500 kg e conferma il caricamento
- **THEN** la giacenza non cambia e la previsione risulta aperta con la sua data

#### Scenario: Arrivo avvenuto
- **WHEN** il gestore registra nei Flussi un arrivo con lo stesso riferimento e materiale
- **THEN** la giacenza aumenta e la previsione risulta chiusa

#### Scenario: Previsione già chiusa ancora nel file
- **WHEN** il foglio Arrivi previsti contiene una previsione già chiusa
- **THEN** il sistema non la riapre e l'anteprima lo segnala con un avviso

#### Scenario: Arrivo in ritardo
- **WHEN** la data di un arrivo previsto è passata e l'arrivo non è registrato
- **THEN** il sistema la mostra come previsione in ritardo e la giacenza non cambia
