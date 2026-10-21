# Bottega — CRM for small businesses

Bottega is a simple CRM for hairdressers, beauticians, gyms, shops and B&Bs
that still track their customers on paper or WhatsApp.

It helps owners **keep their regular customers coming back**: it shows who
hasn't visited in a while, who the best customers are, and lets the owner
reach them with a pre-filled WhatsApp message.

> 🚧 Work in progress — built step by step as a learning project.

## Planned features

- Customer records, appointments, visit and purchase history, notes
- **Dormant customers**: who hasn't come back in too long
- **Loyalty score** based on visit frequency and spending
- One-click **WhatsApp message** (wa.me link)
- **Birthday reminders**
- **Multi-business**: each owner only sees their own customers
- **AI summary** of a customer's history

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** SQLite (development), PostgreSQL (production)
- **Frontend:** Jinja2 templates, HTMX, Tailwind CSS
- **Testing:** pytest
- **Deployment:** Docker

## Getting started (Windows / PowerShell)

```powershell
# 1. Clone the repository
git clone https://github.com/rosariosapienza12/Bottega-crm.git
cd Bottega-crm

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your local configuration
Copy-Item .env.example .env

# 5. Start the development server
uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000> in your browser.

## Project structure

```
app/
  main.py        # application entry point and routes
  templates/     # Jinja2 HTML templates
```
