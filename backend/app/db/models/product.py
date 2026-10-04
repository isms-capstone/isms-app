"""Product catalogue and customer installations (P1-CUSPRD-02)."""
from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    modules: Mapped[list["ProductModule"]] = relationship(back_populates="product")


class ProductModule(Base):
    __tablename__ = "product_module"
    __table_args__ = (UniqueConstraint("product_id", "code", name="uq_product_module_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    product: Mapped[Product] = relationship(back_populates="modules")


class ProductInstance(Base):
    __tablename__ = "product_instance"
    __table_args__ = (
        UniqueConstraint("organization_id", "product_id", "code", name="uq_org_product_instance_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
