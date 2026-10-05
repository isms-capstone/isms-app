"""Registry aliases use the canonical ADM catalogue; instances belong to customers."""
from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base
from app.db.models.master_data import Product, Module as ProductModule


class ProductInstance(Base):
    __tablename__ = "product_instance"
    __table_args__ = (
        UniqueConstraint("organization_id", "product_id", "code", name="uq_org_product_instance_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
