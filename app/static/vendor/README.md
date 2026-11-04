# Librerie esterne

Copiate qui invece che caricate da un CDN: il sito non dipende da un server
esterno e la Content-Security-Policy può permettere script solo dal sito.

| File | Origine | Licenza |
|---|---|---|
| `tailwindcss-browser-4.1.11.js` | npm `@tailwindcss/browser@4.1.11`, `dist/index.global.js` | MIT |
| `htmx-2.0.4.min.js` | npm `htmx.org@2.0.4`, `dist/htmx.min.js` | 0BSD |

Per aggiornarle: `npm pack <pacchetto>@<versione>`, estrarre il file indicato
e cambiare il nome qui e in `app/templates/base.html`.
