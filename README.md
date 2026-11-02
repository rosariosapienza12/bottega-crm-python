# Bottega

A small CRM for hairdressers, beauticians, gyms, shops and B&Bs that still
keep track of their customers on paper or in WhatsApp chats.

The goal is simple: help the owner notice when a regular customer stops
coming, and make it easy to get back in touch.

Bottega is a learning project, built step by step.

## What it does

- **Accounts per business.** Each owner registers their business and only
  ever sees their own customers, visits and appointments.
- **Customers.** Records with phone, email, birthday and notes. The list has
  live search and can be sorted by name, last visit or loyalty.
- **Visits.** Date, amount and what was done, added without reloading the page.
- **Agenda.** A weekly view of appointments. When an appointment is over,
  you type what the customer paid and press "Fatto": it becomes a visit.
- **Overview.** Today's appointments, customers who haven't come back in
  60 days and birthdays in the next two weeks, each with a pre-filled
  WhatsApp message (wa.me link).
- **Loyalty score** from 0 to 100, based on visits and spending in the last
  year.

The interface is in Italian, since that's who it's for.

Still to do: an AI-generated summary of a customer's history, deployment
with Docker and PostgreSQL.

## Tech stack

Python, FastAPI, SQLAlchemy and Alembic. SQLite in development, PostgreSQL
planned for production. Server-rendered Jinja2 templates with HTMX for the
interactive parts and Tailwind CSS. Passwords hashed with Argon2. Tests with
pytest.

## Running it locally (Windows / PowerShell)

```powershell
git clone https://github.com/rosariosapienza12/bottega-crm-python.git
cd bottega-crm-python

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Create your local config, then set a real SECRET_KEY in .env
Copy-Item .env.example .env

# Create the database tables
alembic upgrade head

uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000> and register a business.

To run the tests:

```powershell
pytest
```

The tests use an in-memory database and a fake configuration, so they never
touch your `.env` or `bottega.db`.

## Project structure

```
app/
  main.py         FastAPI app, middleware, security headers
  config.py       settings loaded from .env
  database.py     engine and sessions
  deps.py         shared dependencies (db session, logged-in user)
  routes/         auth, overview, customers, agenda
  models/         Business, User, Customer, Visit, Appointment
  insights.py     dormant customers, birthdays, loyalty score
  money.py        euro amounts stored as integer cents
  phone.py        phone numbers and WhatsApp links
  templates/      Jinja2 templates (files starting with _ are HTMX fragments)
  static/         stylesheet
alembic/          database migrations
tests/            pytest tests
```
