"""Transactional outbox for notifications about external portal replies."""
from email.message import EmailMessage
from email.utils import formataddr
import os
import smtplib
import ssl

from sqlalchemy import select

from app.db.models.customer import ChannelIdentity
from app.db.models.portal import PortalEmail, PortalSubmission


def queue_reply(db, ticket, worklog):
    if ticket.channel != "portal" or worklog.channel != "portal" or worklog.is_internal:
        return
    if not db.scalar(select(PortalSubmission.grant_key)
                     .where(PortalSubmission.ticket_id == ticket.id).limit(1)):
        return
    addresses = db.scalars(select(ChannelIdentity.value).where(
        ChannelIdentity.contact_id == ticket.contact_id,
        ChannelIdentity.channel_type == "email",
    ).distinct().limit(2)).all()
    if len(addresses) == 1:
        db.add(PortalEmail(worklog_id=worklog.id, recipient=addresses[0]))


def deliver_replies(db):
    host = os.getenv("POR_SMTP_HOST")
    sender = os.getenv("POR_SMTP_FROM")
    if not host or not sender:
        return
    rows = db.scalars(select(PortalEmail).order_by(PortalEmail.worklog_id)
                      .limit(25).with_for_update(skip_locked=True)).all()
    if not rows:
        return
    with smtplib.SMTP(host, int(os.getenv("POR_SMTP_PORT") or "587"), timeout=10) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if username := os.getenv("POR_SMTP_USER"):
            smtp.login(username, os.environ["POR_SMTP_PASSWORD"])
        for row in rows:
            message = EmailMessage()
            message["From"] = formataddr(("ISMS Support", sender))
            message["To"] = row.recipient
            message["Subject"] = "ISMS: มีข้อความตอบกลับจากทีมสนับสนุน"
            message["Message-ID"] = f"<portal-reply-{row.worklog_id}@{sender.rsplit('@', 1)[-1]}>"
            message.set_content("ทีมสนับสนุนตอบเคสของคุณแล้ว กรุณาเปิดเมนูแจ้งปัญหาจากผลิตภัณฑ์เพื่ออ่านข้อความ")
            smtp.send_message(message)
            db.delete(row)
        db.commit()
