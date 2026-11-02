// Le due cose che htmx da solo non fa: cambiare tema e trascinare le richieste.

// ---------- Tema chiaro / scuro ----------

function isDark() {
  var chosen = document.documentElement.dataset.theme;
  if (chosen) return chosen === "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function updateThemeButton() {
  var button = document.querySelector("[data-theme-toggle]");
  if (button) button.textContent = isDark() ? "Tema chiaro" : "Tema scuro";
}

document.addEventListener("click", function (event) {
  if (!event.target.closest("[data-theme-toggle]")) return;
  var next = isDark() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("tema", next); } catch (e) { /* va bene lo stesso */ }
  updateThemeButton();
});

document.addEventListener("DOMContentLoaded", updateThemeButton);

// ---------- Pipeline: trascinamento delle richieste ----------
// Al rilascio mandiamo al server la colonna di arrivo e l'ordine delle schede;
// il server risponde con la pipeline aggiornata (totali compresi).
// Su telefono e da tastiera c'è il menu a tendina in ogni scheda.

var dragged = null;

function cardBelow(list, y) {
  var cards = list.querySelectorAll(".card[data-id]:not(.dragging)");
  for (var i = 0; i < cards.length; i++) {
    var box = cards[i].getBoundingClientRect();
    if (y < box.top + box.height / 2) return cards[i];
  }
  return null;
}

document.addEventListener("dragstart", function (event) {
  var card = event.target.closest && event.target.closest(".card[data-id]");
  if (!card) return;
  dragged = card;
  card.classList.add("dragging");
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", card.dataset.id);
});

document.addEventListener("dragover", function (event) {
  var column = dragged && event.target.closest(".column");
  if (!column) return;
  event.preventDefault();
  document.querySelectorAll(".column.over").forEach(function (c) {
    if (c !== column) c.classList.remove("over");
  });
  column.classList.add("over");
  var list = column.querySelector(".cards");
  var below = cardBelow(list, event.clientY);
  if (below) list.insertBefore(dragged, below);
  else list.appendChild(dragged);
});

document.addEventListener("drop", function (event) {
  var column = dragged && event.target.closest(".column");
  if (!column) return;
  event.preventDefault();
  var order = Array.prototype.map
    .call(column.querySelectorAll(".card[data-id]"), function (c) { return c.dataset.id; })
    .join(",");
  htmx.ajax("POST", "/richieste/" + dragged.dataset.id + "/sposta", {
    target: "#board",
    swap: "outerHTML",
    values: { stage: column.dataset.stage, order: order },
  });
});

document.addEventListener("dragend", function () {
  if (dragged) dragged.classList.remove("dragging");
  dragged = null;
  document.querySelectorAll(".column.over").forEach(function (c) { c.classList.remove("over"); });
});
