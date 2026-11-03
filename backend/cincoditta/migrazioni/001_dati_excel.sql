CREATE TABLE presse (
    codice TEXT PRIMARY KEY,
    nome TEXT,
    spurgo_minuti REAL,
    consumo_kw REAL
);

CREATE TABLE stampi (
    codice TEXT PRIMARY KEY,
    impronte INTEGER,
    tempo_ciclo_secondi REAL,
    cambio_stampo_minuti REAL
);

CREATE TABLE compatibilita (
    stampo TEXT NOT NULL REFERENCES stampi (codice),
    pressa TEXT NOT NULL REFERENCES presse (codice),
    PRIMARY KEY (stampo, pressa)
);

CREATE TABLE materiali (
    codice TEXT PRIMARY KEY,
    descrizione TEXT,
    tipo TEXT NOT NULL,
    unita TEXT NOT NULL
);

CREATE TABLE articoli (
    codice TEXT PRIMARY KEY,
    descrizione TEXT,
    stampo TEXT NOT NULL REFERENCES stampi (codice),
    peso_pezzo_grammi REAL
);

CREATE TABLE distinta (
    articolo TEXT NOT NULL REFERENCES articoli (codice),
    materiale TEXT NOT NULL REFERENCES materiali (codice),
    quantita_per_pezzo REAL,
    PRIMARY KEY (articolo, materiale)
);

CREATE TABLE montaggi (
    tipo TEXT PRIMARY KEY,
    modalita TEXT NOT NULL,
    pezzi_ora REAL,
    durata_giorni REAL,
    costo_orario REAL,
    costo_ordine REAL,
    costo_pezzo REAL
);

CREATE TABLE parametri (
    nome TEXT PRIMARY KEY,
    valore REAL
);

CREATE TABLE ordini (
    codice TEXT PRIMARY KEY,
    articolo TEXT NOT NULL REFERENCES articoli (codice),
    quantita INTEGER NOT NULL,
    data_spedizione TEXT NOT NULL,
    presente_nel_file INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE fasi_montaggio (
    ordine TEXT NOT NULL REFERENCES ordini (codice),
    sequenza INTEGER NOT NULL,
    tipo TEXT NOT NULL REFERENCES montaggi (tipo),
    PRIMARY KEY (ordine, sequenza)
);

CREATE TABLE arrivi_previsti (
    riferimento TEXT NOT NULL,
    materiale TEXT NOT NULL REFERENCES materiali (codice),
    quantita INTEGER NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (riferimento, materiale)
);

-- Unica fonte delle giacenze: quantita in millesimi, con il segno dell'effetto.
CREATE TABLE movimenti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    riferimento TEXT NOT NULL,
    data TEXT NOT NULL,
    tipo TEXT NOT NULL,
    codice TEXT NOT NULL,
    quantita INTEGER NOT NULL,
    costo_unitario REAL,
    ordine TEXT,
    origine TEXT NOT NULL CHECK (origine IN ('file', 'interno'))
);

CREATE INDEX movimenti_codice ON movimenti (codice);

-- Valori dei flussi come scritti nel file, per riconoscere righe note o superate.
CREATE TABLE flussi_versioni (
    riferimento TEXT NOT NULL,
    codice TEXT NOT NULL,
    versione INTEGER NOT NULL,
    data TEXT NOT NULL,
    tipo TEXT NOT NULL,
    quantita INTEGER NOT NULL,
    costo_unitario REAL,
    ordine TEXT,
    PRIMARY KEY (riferimento, codice, versione)
);

CREATE TABLE anteprime (
    id TEXT PRIMARY KEY,
    impronta TEXT NOT NULL,
    piano TEXT NOT NULL
);
