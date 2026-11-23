"""Transactional outbox for notifications about external portal replies."""
from email.message import EmailMessage
from email.utils import formataddr
import os
import smtplib
import ssl

from sqlalchemy import select

from app.db.models.customer import ChannelIdentity
from app.core.config import settings
from app.db.models.portal import PortalEmail, PortalOutbox
from app.db.models.ticket import Ticket
from app.db.models.work_category import TicketWorklog


def queue_reply(db, ticket, worklog):
    # Cases opened by customers (product button or self-service portal) use the
    # portal channel; a public reply delivered there also notifies by e-mail (POR-06).
    if ticket.channel != "portal" or worklog.channel != "portal" or worklog.is_internal:
        return
    addresses = db.scalars(select(ChannelIdentity.value).where(
        ChannelIdentity.contact_id == ticket.contact_id,
        ChannelIdentity.channel_type == "email",
    ).distinct().limit(2)).all()
    if len(addresses) == 1:
        db.add(PortalEmail(worklog_id=worklog.id, recipient=addresses[0]))


def _message(sender, recipient, subject, body, message_id):
    message = EmailMessage()
    message["From"] = formataddr(("ISMS Support", sender))
    message["To"] = recipient
    message["Subject"] = subject
    message["Message-ID"] = f"<{message_id}@{sender.rsplit('@', 1)[-1]}>"
    message.set_content(body)
    return message


def deliver_replies(db, batch=25):
    """Send queued portal e-mails. Each message is removed and committed right
    after it is sent, so a crash can repeat at most the one message in flight."""
    host = os.getenv("POR_SMTP_HOST")
    sender = os.getenv("POR_SMTP_FROM")
    if not host or not sender:
        return 0
    replies = db.scalars(select(PortalEmail).order_by(PortalEmail.worklog_id)
                         .limit(batch).with_for_update(skip_locked=True)).all()
    notices = db.scalars(select(PortalOutbox).order_by(PortalOutbox.id)
                         .limit(batch).with_for_update(skip_locked=True)).all()
    if not replies and not notices:
        db.rollback()
        return 0
    base = settings.PORTAL_BASE_URL.rstrip("/")
    sent = 0
    with smtplib.SMTP(host, int(os.getenv("POR_SMTP_PORT") or "587"), timeout=10) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if username := os.getenv("POR_SMTP_USER"):
            smtp.login(username, os.environ["POR_SMTP_PASSWORD"])
        for row in replies:
            ticket_no = db.scalar(select(Ticket.ticket_no).join(TicketWorklog, TicketWorklog.ticket_id == Ticket.id)
                                  .where(TicketWorklog.id == row.worklog_id))
            body = (f"ทีมสนับสนุนตอบเคส {ticket_no} ของคุณแล้ว\n\n"
                    f"อ่านข้อความได้ที่ {base}/portal/cases/{ticket_no}\n"
                    "(ถ้ายังไม่ได้เข้าสู่ระบบ ให้กรอกอีเมลนี้เพื่อรับลิงก์ หรือกดปุ่มแจ้งปัญหาในผลิตภัณฑ์)")
            smtp.send_message(_message(sender, row.recipient, f"ISMS: มีข้อความตอบกลับเคส {ticket_no}",
                                       body, f"portal-reply-{row.worklog_id}"))
            db.delete(row)
            db.commit()
            sent += 1
        for row in notices:
            smtp.send_message(_message(sender, row.recipient, row.subject, row.body, f"portal-notice-{row.id}"))
            db.delete(row)
            db.commit()
            sent += 1
    return sent
