"""Keep the Thai token index in sync with case and worklog writes."""
import unicodedata

from sqlalchemy import event, inspect

from app.db.models.case_search import CaseSearchToken
from app.db.models.ticket import Ticket
from app.db.models.work_category import TicketWorklog
from app.services.similarity import tokenize


def search_tokens(value):
    normalized = unicodedata.normalize('NFC', value or '').casefold()
    return sorted({token[:191] for token in tokenize(normalized)})


def token_rows(ticket_id, source_id, value):
    return [{'ticket_id': ticket_id, 'source_id': source_id, 'token': token}
            for token in search_tokens(value)]


def replace_tokens(connection, ticket_id, source_id, value):
    table = CaseSearchToken.__table__
    connection.execute(table.delete().where(
        table.c.ticket_id == ticket_id, table.c.source_id == source_id))
    rows = token_rows(ticket_id, source_id, value)
    if rows:
        connection.execute(table.insert(), rows)


@event.listens_for(Ticket, 'after_insert')
def index_ticket(_mapper, connection, ticket):
    replace_tokens(connection, ticket.id, 0, f'{ticket.subject or ""} {ticket.description or ""}')


@event.listens_for(Ticket, 'after_update')
def reindex_ticket(mapper, connection, ticket):
    attributes = inspect(ticket).attrs
    if attributes.subject.history.has_changes() or attributes.description.history.has_changes():
        index_ticket(mapper, connection, ticket)


@event.listens_for(TicketWorklog, 'after_insert')
def index_worklog(_mapper, connection, row):
    replace_tokens(connection, row.ticket_id, row.id, row.message)


@event.listens_for(TicketWorklog, 'after_update')
def reindex_worklog(mapper, connection, row):
    if inspect(row).attrs.message.history.has_changes():
        index_worklog(mapper, connection, row)


@event.listens_for(TicketWorklog, 'after_delete')
def remove_worklog_index(_mapper, connection, row):
    replace_tokens(connection, row.ticket_id, row.id, '')
