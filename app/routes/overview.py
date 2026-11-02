"""Panoramica: la prima pagina dopo il login."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.insights import (
    BIRTHDAY_WINDOW_DAYS,
    DORMANT_AFTER_DAYS,
    dormant_customers,
    month_totals,
    upcoming_birthdays,
)
from app.models import Customer
from app.routes.agenda import appointments_between
from app.templating import templates

router = APIRouter()


@router.get("/panoramica")
def overview(request: Request, db: DbSession, user: CurrentUser):
    today = date.today()
    midnight = datetime.combine(today, datetime.min.time())
    visits_this_month, cents_this_month = month_totals(db, user.business_id, today)
    customer_count = db.scalar(
        select(func.count(Customer.id)).where(Customer.business_id == user.business_id)
    )
    context = {
        "user": user,
        "today": today,
        "now": datetime.now(),
        "appointments_today": appointments_between(
            db, user.business_id, midnight, midnight + timedelta(days=1)
        ),
        "customer_count": customer_count,
        "visits_this_month": visits_this_month,
        "cents_this_month": cents_this_month,
        "dormant": dormant_customers(db, user.business_id, today),
        "birthdays": upcoming_birthdays(db, user.business_id, today),
        "dormant_days": DORMANT_AFTER_DAYS,
        "birthday_days": BIRTHDAY_WINDOW_DAYS,
    }
    return templates.TemplateResponse(request, "overview.html", context)
