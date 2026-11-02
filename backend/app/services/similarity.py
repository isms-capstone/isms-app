"""SIM v1 (SRS 8.4): PyThaiNLP word segmentation + MariaDB FULLTEXT candidate search.

Importing this module registers the Ticket listeners that keep ticket.search_text
up to date, so every code path that creates/edits a case is covered automatically.
"""
import logging
import os
from functools import lru_cache

from pythainlp.corpus import thai_stopwords
from pythainlp.tokenize import word_tokenize
from sqlalchemy import event, inspect, or_, select, text
from sqlalchemy.orm import Session

from app.db.models.customer import Organization
from app.db.models.master_data import Product
from app.db.models.product import ProductInstance
from app.db.models.ticket import Ticket
from app.db.models.user import User

log = logging.getLogger(__name__)

EXCLUDED_STATUSES = ('DRAFT', 'DUPLICATE', 'CANCELLED')
MIN_QUERY_CHARS = 10        # SIM-01
MIN_COVERAGE = 0.2          # ต้องมีคำค้นตรงอย่างน้อย 20% ถึงจะแสดง
CANDIDATE_POOL = 50
# ตั้ง SIM_USE_FULLTEXT=false ใน .env เพื่อสลับไปใช้ LIKE (ใช้กับ SQLite หรือถ้า FULLTEXT ไทยไม่ทำงาน)
USE_FULLTEXT = os.getenv('SIM_USE_FULLTEXT', 'true').lower() == 'true'


def tokenize(value: str | None) -> list[str]:
    """ตัดคำไทย/อังกฤษ ทิ้งช่องว่างและเครื่องหมายล้วน"""
    if not value:
        return []
    tokens = []
    for raw in word_tokenize(value.lower(), engine='newmm', keep_whitespace=False):
        token = raw.strip()
        if token and any(ch.isalnum() or '\u0e00' <= ch <= '\u0e7f' for ch in token):
            tokens.append(token)
    return tokens


def build_search_text(subject: str | None, description: str | None) -> str:
    return ' '.join(tokenize(f'{subject or ""} {description or ""}'))[:30000]


@event.listens_for(Ticket, 'before_insert')
def _index_on_insert(mapper, connection, target):
    target.search_text = build_search_text(target.subject, target.description)


@event.listens_for(Ticket, 'before_update')
def _index_on_update(mapper, connection, target):
    state = inspect(target)
    if state.attrs.subject.history.has_changes() or state.attrs.description.history.has_changes():
        target.search_text = build_search_text(target.subject, target.description)


@lru_cache(maxsize=1)
def _stopwords() -> frozenset:
    return frozenset(thai_stopwords())


def _candidates(db: Session, tokens: list[str]) -> list[Ticket]:
    if USE_FULLTEXT and db.bind.dialect.name == 'mysql':
        rows = db.execute(text(
            "SELECT id, MATCH(search_text) AGAINST (:q IN NATURAL LANGUAGE MODE) AS ft "
            "FROM ticket "
            "WHERE status NOT IN ('DRAFT','DUPLICATE','CANCELLED') "
            "AND MATCH(search_text) AGAINST (:q IN NATURAL LANGUAGE MODE) "
            "ORDER BY ft DESC LIMIT :pool"),
            {'q': ' '.join(tokens), 'pool': CANDIDATE_POOL}).all()
        ids = [row.id for row in rows]
        return db.scalars(select(Ticket).where(Ticket.id.in_(ids))).all() if ids else []
    conditions = [Ticket.search_text.contains(token, autoescape=True) for token in tokens[:8]]
    return db.scalars(select(Ticket)
                      .where(Ticket.status.not_in(EXCLUDED_STATUSES), or_(*conditions))
                      .order_by(Ticket.created_at.desc()).limit(CANDIDATE_POOL * 4)).all()


def _hint(ticket: Ticket, assignee_name: str | None) -> str:
    if ticket.status in ('RESOLVED', 'CLOSED'):
        return 'เคยแก้แล้ว มีวิธีแก้' if (ticket.resolution_detail or '').strip() else 'ปิดแล้ว (ยังไม่มีบันทึกวิธีแก้)'
    return f'กำลังแก้อยู่โดย {assignee_name}' if assignee_name else 'เปิดอยู่ ยังไม่มีผู้รับผิดชอบ'


def similar_cases(db: Session, q: str, organization_id: int | None = None,
                  product_instance_id: int | None = None, limit: int = 5) -> list[dict]:
    tokens = list(dict.fromkeys(tokenize(q)))
    stop = _stopwords()
    content = [t for t in tokens if len(t) >= 2 and t not in stop] or [t for t in tokens if len(t) >= 2]
    if not content:
        return []
    wanted = set(content)
    candidates = _candidates(db, content)
    if not candidates:
        return []

    instance_ids = {t.product_instance_id for t in candidates if t.product_instance_id}
    if product_instance_id:
        instance_ids.add(product_instance_id)
    product_of = {i.id: i.product_id for i in db.scalars(
        select(ProductInstance).where(ProductInstance.id.in_(instance_ids))).all()} if instance_ids else {}
    query_product = product_of.get(product_instance_id)

    scored = []
    for ticket in candidates:
        coverage = len(wanted & set((ticket.search_text or '').split())) / len(wanted)
        if coverage < MIN_COVERAGE:
            continue
        score = coverage
        if organization_id and ticket.organization_id == organization_id:
            score += 0.10   # ลูกค้าเดียวกัน
        if query_product and product_of.get(ticket.product_instance_id) == query_product:
            score += 0.05   # ผลิตภัณฑ์เดียวกัน
        scored.append((min(score, 1.0), ticket))
    scored.sort(key=lambda pair: (pair[0], pair[1].created_at), reverse=True)
    top = scored[:limit]
    if not top:
        return []

    org_ids = {t.organization_id for _, t in top if t.organization_id}
    user_ids = {t.assignee_id for _, t in top if t.assignee_id}
    product_ids = {product_of.get(t.product_instance_id) for _, t in top} - {None}
    orgs = {o.id: o.name for o in db.scalars(select(Organization).where(Organization.id.in_(org_ids))).all()}
    users = {u.id: getattr(u, 'name', None) or u.username
             for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()}
    products = {p.id: p.name for p in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()}

    return [{
        'id': t.id,
        'ticket_no': t.ticket_no,
        'subject': t.subject,
        'status': t.status,
        'hint': _hint(t, users.get(t.assignee_id)),
        'score': round(score * 100),
        'customer': orgs.get(t.organization_id, 'ยังไม่ระบุลูกค้า'),
        'product': products.get(product_of.get(t.product_instance_id), 'ยังไม่ระบุ'),
        'assignee': users.get(t.assignee_id),
        'last_activity': (t.closed_at or t.resolved_at or t.created_at).isoformat(),
        'channel': t.channel,
'category_id': t.category_id,
'product_instance_id': t.product_instance_id,
'severity': t.severity,
'resolution_code_id': t.resolution_code_id,
'resolution_detail': t.resolution_detail,
    } for score, t in top]
