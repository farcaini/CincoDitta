const stato = document.getElementById("stato");

fetch("/api/health")
  .then((response) => {
    if (!response.ok) throw new Error(response.statusText);
    return response.json();
  })
  .then((dati) => {
    stato.textContent = `${dati.status} (SQLite ${dati.sqlite})`;
  })
  .catch(() => {
    stato.textContent = "non raggiungibile";
  });
