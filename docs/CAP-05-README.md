# CAP-05: Case attachments

## Files changed
- `backend/app/api/v1/endpoints/tickets.py`: authenticated list/upload/download API; 10 MB per-file limit and MIME allowlist.
- `backend/app/db/models/ticket_attachment.py`: attachment metadata model.
- `backend/alembic/env.py`: register the model for Alembic metadata.
- `backend/alembic/versions/cap05_ticket_attachments.py`: creates the attachment metadata table.
- `backend/app/static/registry/registry.js`: choose files, paste images with Ctrl+V, drag/drop, mobile camera capture, upload after case creation, and display/download files on case detail.
- `backend/app/static/registry/registry.css`: attachment UI styles.
- `docker-compose.yml`: persistent named volume for private uploaded files (`ticket_attachments`).

## Install in PowerShell
Run from the project root (the folder containing `docker-compose.yml`). Make a backup/commit first and copy the patch files over their matching paths. Do not replace the entire project folder.

```powershell
docker compose config
docker compose build app
docker compose run --rm app python -m alembic upgrade head
docker compose up -d app
docker compose ps
docker compose logs --tail 100 app
```

The migration adds a new table only; it does not drop or reset existing case/customer data. Do not use `docker compose down -v`.

## Acceptance checks
1. Create a case with a JPG/PNG screenshot selected using the file picker.
2. Create another case by pasting a screenshot with Ctrl+V.
3. Test drag/drop and mobile camera capture.
4. Open the created case and verify its file appears and can be opened/downloaded.
5. Restart the app container and verify the attachment remains.
6. Verify unsupported file types and files over 10 MB are rejected.

Uploads are stored in the `ticket_attachments` Docker volume and are served only through authenticated case endpoints, not from a public static directory.
