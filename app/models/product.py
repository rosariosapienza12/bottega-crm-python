"""Un prodotto in magazzino (tinte, shampoo, integratori...)."""

from sqlalchemy import ForeignKey, String, and_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(20), default="pz")
    quantity: Mapped[int] = mapped_column(default=0)
    # Arrivati a questa quantità il prodotto finisce in "da riordinare".
    # 0 vuol dire "non avvisarmi".
    min_quantity: Mapped[int] = mapped_column(default=0)
    unit_cost_cents: Mapped[int] = mapped_column(default=0)

    # hybrid_property: la stessa regola vale in Python (product.to_reorder)
    # e dentro le query (select(Product).where(Product.to_reorder))
    @hybrid_property
    def to_reorder(self) -> bool:
        return self.min_quantity > 0 and self.quantity <= self.min_quantity

    @to_reorder.inplace.expression
    @classmethod
    def _to_reorder_expression(cls):
        return and_(cls.min_quantity > 0, cls.quantity <= cls.min_quantity)
