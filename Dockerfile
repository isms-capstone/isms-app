FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HOME=/home/isms PYTHAINLP_DATA_DIR=/var/lib/pythainlp
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Run as an unprivileged user. The legacy attachment directory is created here
# so a new named volume mounted on it inherits this ownership.
RUN useradd --system --uid 10001 --create-home --home-dir /home/isms isms \
    && mkdir -p /app/uploads/ticket-attachments /var/lib/pythainlp \
    && chown -R isms /app/uploads /var/lib/pythainlp
COPY --chown=isms backend ./backend

WORKDIR /app/backend
USER isms

EXPOSE 3000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000", "--proxy-headers"]
