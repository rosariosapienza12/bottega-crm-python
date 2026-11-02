# Bottega

A small CRM for hairdressers, beauticians, gyms, shops and B&Bs that still
keep track of their customers on paper or in WhatsApp chats.

The goal is simple: help the owner notice when a regular customer stops
coming, and make it easy to get back in touch.

Bottega is a learning project and is still at an early stage.

## Status

Done:
- FastAPI app with a placeholder home page
- Configuration from a `.env` file
- Database models for businesses, users and customers, with Alembic migrations
- Tests for the home page and the models

Next:
- Login, with each business seeing only its own customers
- Customer records, appointments, visit history and notes
- A list of customers who haven't come back in a while
- A loyalty score based on how often customers come and how much they spend
- Pre-filled WhatsApp messages (wa.me links) and birthday reminders
- A short AI-generated summary of a customer's history

## Tech stack

Python, FastAPI, SQLAlchemy and Alembic. SQLite in development, PostgreSQL in
production. Jinja2 templates with HTMX and Tailwind CSS. Tests with pytest,
deployment with Docker.

## Running it locally (Windows / PowerShell)

```powershell
git clone https://github.com/rosariosapienza12/Bottega-crm.git
cd Bottega-crm

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Create your local config, then set a real SECRET_KEY in .env
Copy-Item .env.example .env

# Create the database tables
alembic upgrade head

uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000>.

To run the tests:

```powershell
pytest
```

## Project structure

```
app/
  main.py         FastAPI app and routes
  config.py       settings loaded from .env
  database.py     engine and sessions
  models/         SQLAlchemy models (Business, User, Customer)
  templates/      Jinja2 templates
alembic/          database migrations
tests/            pytest tests
```
