const messaggio = document.getElementById("messaggio");
const sezioneAnteprima = document.getElementById("anteprima");
const contenutoAnteprima = document.getElementById("contenuto-anteprima");
const pulsanteConferma = document.getElementById("conferma");

let idAnteprima = null;

function elemento(tag, testo, classe) {
  const nodo = document.createElement(tag);
  if (testo !== undefined && testo !== null) nodo.textContent = testo;
  if (classe) nodo.className = classe;
  return nodo;
}

function tabella(intestazioni, righe) {
  const contenitore = elemento("div", null, "scorrevole");
  const tab = elemento("table");
  const testa = tab.createTHead().insertRow();
  for (const titolo of intestazioni) testa.append(elemento("th", titolo));
  const corpo = tab.createTBody();
  for (const riga of righe) {
    const tr = corpo.insertRow();
    for (const cella of riga) {
      const td = tr.insertCell();
      if (cella instanceof Node) td.append(cella);
      else td.textContent = cella ?? "";
    }
  }
  contenitore.append(tab);
  return contenitore;
}

function gruppo(titolo, ...contenuti) {
  const blocco = elemento("div");
  blocco.append(elemento("h3", titolo), ...contenuti);
  return blocco;
}

function elenco(voci) {
  const lista = elemento("ul");
  for (const voce of voci) lista.append(elemento("li", voce));
  return lista;
}

function descriviValori(valori) {
  return Object.entries(valori)
    .map(([campo, valore]) => `${campo}: ${valore ?? "vuoto"}`)
    .join(", ");
}

function descriviFlusso(flusso) {
  return descriviValori({
    data: flusso.data,
    tipo: flusso.tipo,
    quantità: flusso.quantita,
    costo: flusso.costo_unitario,
    ordine: flusso.ordine,
  });
}

function tabellaGiacenze(righe) {
  return tabella(
    ["Codice", "Descrizione", "Categoria", "Quantità", "Unità"],
    righe.map((riga) => [
      riga.codice,
      riga.descrizione,
      riga.categoria,
      elemento("span", riga.quantita, riga.negativa ? "negativa" : ""),
      riga.unita,
    ]),
  );
}

function tabellaMancanti(righe) {
  return tabella(
    ["Foglio", "Elemento", "Dato"],
    righe.map((riga) => [riga.foglio, riga.elemento, riga.campo]),
  );
}

function mostraErrori(errori) {
  contenutoAnteprima.replaceChildren();
  sezioneAnteprima.hidden = true;
  idAnteprima = null;
  const quanti = errori.length === 1 ? "1 errore" : `${errori.length} errori`;
  messaggio.textContent = `Il file contiene ${quanti}: non è stato applicato nulla.`;
  messaggio.className = "errore";
  messaggio.after(
    Object.assign(
      tabella(
        ["Foglio", "Riga", "Colonna", "Problema"],
        errori.map((e) => [e.foglio, e.riga, e.colonna, e.messaggio]),
      ),
      { id: "errori" },
    ),
  );
}

function bloccoCambiamenti(cambiamenti) {
  const fogli = Object.entries(cambiamenti);
  if (fogli.length === 0) return elemento("p", "Nessun cambiamento nei dati.");
  const blocco = elemento("div");
  for (const [foglio, differenze] of fogli) {
    const voci = [
      ...differenze.aggiunti.map((chiave) => `Aggiunto: ${chiave}`),
      ...differenze.modificati.map(
        (voce) =>
          `Modificato ${voce.chiave}: ${descriviValori(voce.prima)} → ${descriviValori(voce.dopo)}`,
      ),
      ...differenze.rimossi.map((chiave) =>
        foglio === "Ordini"
          ? `Non più nel file (viene conservato): ${chiave}`
          : `Rimosso: ${chiave}`,
      ),
    ];
    blocco.append(gruppo(foglio, elenco(voci)));
  }
  return blocco;
}

function bloccoDaConfermare(voci) {
  return tabella(
    ["Accetta", "Flusso", "Valori registrati", "Valori nel file"],
    voci.map((voce) => {
      const casella = elemento("input");
      casella.type = "checkbox";
      casella.dataset.riferimento = voce.riferimento;
      casella.dataset.codice = voce.codice;
      casella.setAttribute("aria-label", `Accetta ${voce.riferimento} ${voce.codice}`);
      return [
        casella,
        `${voce.riferimento} / ${voce.codice}`,
        descriviFlusso(voce.prima),
        descriviFlusso(voce.dopo),
      ];
    }),
  );
}

function mostraAnteprima(risultato) {
  idAnteprima = risultato.id;
  const { flussi } = risultato;
  const parti = [gruppo("Cambiamenti", bloccoCambiamenti(risultato.cambiamenti))];

  if (risultato.avvisi.length > 0) {
    parti.push(gruppo("Avvisi", elenco(risultato.avvisi)));
  }
  parti.push(
    gruppo(
      `Nuovi flussi (${flussi.nuovi.length})`,
      ...(flussi.nuovi.length > 0
        ? [elenco(flussi.nuovi.map((f) => `${f.riferimento} / ${f.codice}: ${descriviFlusso(f)}`))]
        : []),
    ),
  );
  if (flussi.da_confermare.length > 0) {
    parti.push(
      gruppo(
        `Flussi già registrati con valori diversi (${flussi.da_confermare.length})`,
        elemento("p", "Le righe non selezionate vengono ignorate."),
        bloccoDaConfermare(flussi.da_confermare),
      ),
    );
  }
  const ignorati = [
    ...flussi.ignorati.map((f) => `${f.riferimento} / ${f.codice}: già registrato`),
    ...flussi.superati.map((f) => `${f.riferimento} / ${f.codice}: superato da una correzione`),
  ];
  if (ignorati.length > 0) parti.push(gruppo("Righe ignorate", elenco(ignorati)));
  if (risultato.dati_mancanti.length > 0) {
    parti.push(
      gruppo(
        `Dati mancanti (${risultato.dati_mancanti.length})`,
        tabellaMancanti(risultato.dati_mancanti),
      ),
    );
  }
  parti.push(gruppo("Giacenze risultanti", tabellaGiacenze(risultato.giacenze)));

  contenutoAnteprima.replaceChildren(...parti);
  sezioneAnteprima.hidden = false;
  messaggio.textContent = "Il file è valido. Nulla è stato ancora applicato.";
  messaggio.className = "";
}

async function testoErrore(risposta) {
  try {
    return (await risposta.json()).detail ?? risposta.statusText;
  } catch {
    return risposta.statusText;
  }
}

function pulisci() {
  document.getElementById("errori")?.remove();
  sezioneAnteprima.hidden = true;
  idAnteprima = null;
}

document.getElementById("caricamento").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  pulisci();
  const dati = new FormData();
  dati.append("file", document.getElementById("file").files[0]);
  messaggio.textContent = "Controllo in corso…";
  messaggio.className = "";
  try {
    const risposta = await fetch("/api/excel/anteprima", { method: "POST", body: dati });
    if (!risposta.ok) {
      messaggio.textContent = await testoErrore(risposta);
      messaggio.className = "errore";
      return;
    }
    const risultato = await risposta.json();
    if (risultato.valido) mostraAnteprima(risultato);
    else mostraErrori(risultato.errori);
  } catch {
    messaggio.textContent = "Backend non raggiungibile.";
    messaggio.className = "errore";
  }
});

pulsanteConferma.addEventListener("click", async () => {
  const accetta = [...contenutoAnteprima.querySelectorAll("input[type=checkbox]:checked")].map(
    (casella) => ({
      riferimento: casella.dataset.riferimento,
      codice: casella.dataset.codice,
    }),
  );
  try {
    const risposta = await fetch(`/api/excel/anteprima/${idAnteprima}/conferma`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accetta }),
    });
    if (!risposta.ok) {
      messaggio.textContent = await testoErrore(risposta);
      messaggio.className = "errore";
      pulisci();
      return;
    }
    pulisci();
    messaggio.textContent =
      "Dati applicati. Scarica il file aggiornato per avere il foglio Flussi vuoto.";
    messaggio.className = "riuscito";
    document.getElementById("caricamento").reset();
    await aggiornaRiepilogo();
  } catch {
    messaggio.textContent = "Backend non raggiungibile.";
    messaggio.className = "errore";
  }
});

async function mostraMovimenti(codice) {
  const righe = await (await fetch(`/api/movimenti?codice=${encodeURIComponent(codice)}`)).json();
  document.getElementById("movimenti").replaceChildren(
    gruppo(
      `Movimenti di ${codice}`,
      tabella(
        ["Data", "Tipo", "Riferimento", "Quantità", "Costo", "Ordine", "Origine"],
        righe.map((r) => [
          r.data,
          r.tipo,
          r.riferimento,
          r.quantita,
          r.costo_unitario,
          r.ordine,
          r.origine,
        ]),
      ),
    ),
  );
}

async function aggiornaRiepilogo() {
  const [giacenze, arrivi, mancanti] = await Promise.all(
    ["/api/giacenze", "/api/arrivi-previsti", "/api/dati-mancanti"].map(async (percorso) =>
      (await fetch(percorso)).json(),
    ),
  );

  const zonaGiacenze = document.getElementById("giacenze");
  if (giacenze.length === 0) {
    zonaGiacenze.replaceChildren(elemento("p", "Nessun materiale o articolo registrato."));
  } else {
    zonaGiacenze.replaceChildren(
      tabella(
        ["Codice", "Descrizione", "Categoria", "Quantità", "Unità"],
        giacenze.map((riga) => {
          const collegamento = elemento("button", riga.codice, "collegamento");
          collegamento.type = "button";
          collegamento.addEventListener("click", () => mostraMovimenti(riga.codice));
          return [
            collegamento,
            riga.descrizione,
            riga.categoria,
            elemento("span", riga.quantita, riga.negativa ? "negativa" : ""),
            riga.unita,
          ];
        }),
      ),
    );
  }

  document.getElementById("arrivi").replaceChildren(
    arrivi.length === 0
      ? elemento("p", "Nessun arrivo previsto.")
      : tabella(
          ["Riferimento", "Materiale", "Quantità", "Data", "Stato"],
          arrivi.map((r) => [
            r.riferimento,
            r.materiale,
            r.quantita,
            r.data,
            elemento("span", r.stato, r.stato === "in ritardo" ? "negativa" : ""),
          ]),
        ),
  );

  document.getElementById("mancanti").replaceChildren(
    mancanti.length === 0 ? elemento("p", "Nessun dato mancante.") : tabellaMancanti(mancanti),
  );
}

aggiornaRiepilogo().catch(() => {
  messaggio.textContent = "Backend non raggiungibile.";
  messaggio.className = "errore";
});
