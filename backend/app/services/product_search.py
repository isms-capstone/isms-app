"""SIM/KB integration hook: preserve cross-product candidates, prefer same product."""
from dataclasses import dataclass

from sqlalchemy import case, literal
from sqlalchemy.orm import Session

from app.db.models.product import ProductInstance


@dataclass(frozen=True)
class ProductSearchContext:
    product_instance_id: int | None
    preferred_product_id: int | None


def resolve_search_context(db: Session, product_instance_id: int | None):
    if product_instance_id is None:
        return ProductSearchContext(None, None)
    instance = db.get(ProductInstance, product_instance_id)
    if instance is None:
        raise ValueError("Unknown product_instance_id")
    return ProductSearchContext(instance.id, instance.product_id)


def product_preference_order(candidate_product_id, context: ProductSearchContext):
    """Use first in ORDER BY, then relevance DESC, then stable candidate ID.

    candidate_product_id is a SQLAlchemy column/expression, not user SQL.
    Matching is by product, including other instances of that same product.
    This expression never filters away cross-product candidates.
    """
    if context.preferred_product_id is None:
        return literal(0)
    return case((candidate_product_id == context.preferred_product_id, 0), else_=1)
