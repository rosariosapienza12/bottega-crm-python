from sqlalchemy import select

from app.models import Request as PipelineRequest
from tests.test_customers import add_customer


def add_request(client, title, **extra):
    data = {"title": title, "contact_name": "Sara", "value": "100", **extra}
    return client.post("/richieste", data=data, headers={"HX-Request": "true"})


def test_new_request_goes_in_the_first_column(logged_in, db):
    response = add_request(logged_in, "Trucco sposa", value="250,00")

    assert 'id="board"' in response.text
    item = db.scalars(select(PipelineRequest)).one()
    assert item.stage == "nuova"
    assert item.value_cents == 250_00
    assert item.who == "Sara"


def test_request_needs_a_title_and_a_person(logged_in, db):
    assert "Scrivi cosa chiede" in add_request(logged_in, " ").text
    assert "Scegli un cliente" in add_request(logged_in, "Taglio", contact_name="").text
    assert db.scalars(select(PipelineRequest)).first() is None


def test_request_linked_to_a_customer(logged_in, db):
    url = add_customer(logged_in)
    add_request(logged_in, "Colore", customer_id=url.rsplit("/", 1)[1], contact_name="")

    assert db.scalars(select(PipelineRequest)).one().who == "Maria Rossi"


def test_drag_to_another_column_with_order(logged_in, db):
    for title in ["A", "B", "C"]:
        add_request(logged_in, title)
    a, b, c = db.scalars(select(PipelineRequest).order_by(PipelineRequest.id)).all()
    logged_in.post(f"/richieste/{a.id}/sposta", data={"stage": "contattata"})

    # C viene trascinata sopra A nella colonna "contattata"
    logged_in.post(f"/richieste/{c.id}/sposta", data={"stage": "contattata", "order": f"{c.id},{a.id}"})

    db.expire_all()
    column = db.scalars(
        select(PipelineRequest)
        .where(PipelineRequest.stage == "contattata")
        .order_by(PipelineRequest.position)
    ).all()
    assert [r.title for r in column] == ["C", "A"]
    assert db.get(PipelineRequest, b.id).stage == "nuova"


def test_unknown_stage_is_rejected(logged_in, db):
    add_request(logged_in, "A")
    item = db.scalars(select(PipelineRequest)).one()

    response = logged_in.post(f"/richieste/{item.id}/sposta", data={"stage": "vinta-alla-lotteria"})

    assert response.status_code == 400


def test_edit_and_delete_request(logged_in, db):
    add_request(logged_in, "A")
    item_id = db.scalars(select(PipelineRequest.id)).one()

    logged_in.post(
        f"/richieste/{item_id}",
        data={"title": "A modificata", "contact_name": "Sara", "value": "80", "stage": "confermata", "notes": "ok"},
    )
    item = db.get(PipelineRequest, item_id)
    db.refresh(item)
    assert (item.title, item.stage, item.value_cents) == ("A modificata", "confermata", 80_00)

    logged_in.post(f"/richieste/{item_id}/elimina")
    db.expire_all()
    assert db.scalars(select(PipelineRequest)).first() is None


def test_deleting_a_customer_keeps_the_request_with_the_name(logged_in, db):
    url = add_customer(logged_in)
    add_request(logged_in, "Colore", customer_id=url.rsplit("/", 1)[1], contact_name="")

    logged_in.post(f"{url}/elimina")

    item = db.scalars(select(PipelineRequest)).one()
    db.refresh(item)
    assert item.customer_id is None
    assert item.who == "Maria Rossi"
