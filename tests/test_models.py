import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Business, Customer, User


def add_business(db, name):
    business = Business(name=name)
    db.add(business)
    db.commit()
    return business


def test_customer_is_linked_to_its_business(db):
    salon = add_business(db, "Salone Anna")
    salon.customers.append(
        Customer(first_name="Maria", last_name="Rossi", phone="+393331234567")
    )
    db.commit()

    customer = db.scalars(select(Customer)).one()
    assert customer.business_id == salon.id


def test_two_users_cannot_share_an_email(db):
    salon = add_business(db, "Salone Anna")
    db.add(User(business=salon, email="anna@example.com", password_hash="hash1"))
    db.commit()

    db.add(User(business=salon, email="anna@example.com", password_hash="hash2"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_deleting_a_business_keeps_other_businesses_customers(db):
    salon = add_business(db, "Salone Anna")
    gym = add_business(db, "Palestra Fit")
    salon.customers.append(Customer(first_name="Maria", last_name="Rossi", phone="+393331111111"))
    gym.customers.append(Customer(first_name="Luca", last_name="Bianchi", phone="+393332222222"))
    db.commit()

    db.delete(salon)
    db.commit()

    remaining = db.scalars(select(Customer.first_name)).all()
    assert remaining == ["Luca"]
