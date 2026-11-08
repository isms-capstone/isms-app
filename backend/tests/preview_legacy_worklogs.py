"""Disposable WRK browser fixture matching the observed merged backend contract.

No real database, accounts, or ticket records are used by this server.
"""
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title='Legacy worklog compatibility QA')
token = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')
rows = []
fail_next = False
created_at = datetime.now(timezone.utc).isoformat()


def authenticated(value: str = Depends(token)):
    if value != 'qa-worklog-token':
        raise HTTPException(401, 'Invalid QA token')


@app.post('/api/v1/auth/login')
def login(username: str = Form(), password: str = Form()):
    if username != 'qa-admin' or password != 'test-only-password':
        raise HTTPException(401, 'Invalid QA login')
    return {'access_token': 'qa-worklog-token', 'token_type': 'bearer'}


@app.get('/api/v1/registry/session', dependencies=[Depends(authenticated)])
def session():
    return {'id': 20, 'username': 'qa-admin', 'role': 'Admin', 'can_create_cases': True,
            'can_edit_customers': True, 'can_edit_products': True}


@app.get('/api/v1/tickets/1', dependencies=[Depends(authenticated)])
def ticket():
    return {'id': 1, 'ticket_no': 'DVHT-QA-00001', 'subject': 'WRK compatibility QA',
            'description': 'Disposable test case', 'status': 'NEW', 'organization_id': 1,
            'created_by_id': 20, 'owner_id': 20, 'assignee_id': 20, 'channel': 'phone',
            'reported_at': created_at, 'created_at': created_at, 'severity': None,
            'contact_id': None, 'product_instance_id': None, 'department_id': None,
            'course_or_exam_id': None, 'module_id': None, 'category_id': None,
            'symptom_id': None, 'service_stage_id': None, 'ticket_type_id': None,
            'current_tier': None, 'sla_policy_id': None, 'is_exam_window': False}


@app.get('/api/v1/customers/organizations/1', dependencies=[Depends(authenticated)])
def organization():
    return {'id': 1, 'name': 'WRK QA organization', 'is_active': True}


@app.get('/api/v1/tickets/1/lifecycle-options', dependencies=[Depends(authenticated)])
def lifecycle():
    return {'actions': [], 'assignees': [], 'causes': [], 'solutions': [], 'categories': [], 'instances': []}


class WorklogCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=1, max_length=20000)
    is_internal: bool = True
    channel: str | None = None


@app.get('/api/v1/tickets/{ticket_id}/worklogs', dependencies=[Depends(authenticated)])
def worklogs(ticket_id: int):
    if ticket_id != 1:
        raise HTTPException(404, 'Case not found')
    return rows


@app.post('/api/v1/tickets/{ticket_id}/worklogs', status_code=201, dependencies=[Depends(authenticated)])
def add_worklog(ticket_id: int, body: WorklogCreate):
    global fail_next
    if fail_next:
        fail_next = False
        return PlainTextResponse('Internal Server Error: private traceback must not reach browser', status_code=500)
    if ticket_id != 1:
        raise HTTPException(404, 'Case not found')
    row = {'id': len(rows) + 1, 'ticket_id': 1, 'author_id': 20,
           'message': body.message, 'is_internal': body.is_internal,
           'channel': body.channel or 'phone', 'created_at': datetime.now(timezone.utc).isoformat()}
    rows.append(row)
    return row


@app.post('/api/v1/qa/reset', dependencies=[Depends(authenticated)])
def reset():
    rows.clear()
    return {'ok': True}


@app.post('/api/v1/qa/seed', dependencies=[Depends(authenticated)])
def seed():
    rows.clear()
    for index in range(105):
        rows.append({'id': index + 1, 'ticket_id': 1, 'author_id': 20,
                     'message': f'Seed {index}', 'is_internal': True,
                     'channel': 'phone', 'created_at': created_at})
    return {'count': len(rows)}


@app.post('/api/v1/qa/fail-next', dependencies=[Depends(authenticated)])
def fail_once():
    global fail_next
    fail_next = True
    return {'ok': True}
