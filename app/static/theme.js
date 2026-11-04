// Caricato nell'<head>: applica il tema scelto prima che la pagina venga
// disegnata, altrimenti si vedrebbe un lampo del tema sbagliato.
try {
  var savedTheme = localStorage.getItem("tema");
  if (savedTheme === "light" || savedTheme === "dark") {
    document.documentElement.dataset.theme = savedTheme;
  }
} catch (e) {
  // localStorage può essere bloccato (navigazione privata): resta il tema chiaro
}
