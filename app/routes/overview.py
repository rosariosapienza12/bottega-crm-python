"""Panoramica: la prima pagina dopo il login."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Request
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.cash import change_percent, last_months
from app.deps import CurrentUser, DbSession
from app.insights import (
    BIRTHDAY_WINDOW_DAYS,
    DORMANT_AFTER_DAYS,
    dormant_customers,
    upcoming_birthdays,
)
from app.models import Customer, Product, Request as PipelineRequest
from app.routes.agenda import appointments_between
from app.routes.pipeline import OPEN_STAGES, open_requests
from app.templating import templates

router = APIRouter()


@router.get("/panoramica")
def overview(request: Request, db: DbSession, user: CurrentUser):
    today = date.today()
    midnight = datetime.combine(today, datetime.min.time())
    business_id = user.business_id

    months = last_months(db, business_id, today)
    this_month, last_month = months[-1], months[-2]
    open_count, open_cents = open_requests(db, business_id)
    to_reorder = db.scalars(
        select(Product)
        .where(Product.business_id == business_id, Product.to_reorder)
        .order_by(Product.quantity)
    ).all()
    hot_requests = db.scalars(
        select(PipelineRequest)
        .options(joinedload(PipelineRequest.customer))
        .where(PipelineRequest.business_id == business_id, PipelineRequest.stage.in_(OPEN_STAGES))
        .order_by(PipelineRequest.value_cents.desc())
        .limit(5)
    ).all()

    context = {
        "user": user,
        "today": today,
        "now": datetime.now(),
        "this_month": this_month,
        "income_change": change_percent(this_month.income_cents, last_month.income_cents),
        "months": months,
        "open_count": open_count,
        "open_cents": open_cents,
        "hot_requests": hot_requests,
        "to_reorder": to_reorder,
        "customer_count": db.scalar(
            select(func.count(Customer.id)).where(Customer.business_id == business_id)
        ),
        "appointments_today": appointments_between(
            db, business_id, midnight, midnight + timedelta(days=1)
        ),
        "dormant": dormant_customers(db, business_id, today),
        "birthdays": upcoming_birthdays(db, business_id, today),
        "dormant_days": DORMANT_AFTER_DAYS,
        "birthday_days": BIRTHDAY_WINDOW_DAYS,
    }
    return templates.TemplateResponse(request, "overview.html", context)
