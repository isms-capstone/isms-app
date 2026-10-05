#!/usr/bin/env bash
# Metadata-only inspection. No migration, stamp, credential output or container restart.
set -euo pipefail
cd "$(dirname "$0")/.."
printf 'Checkout: '
git rev-parse HEAD
git status --short
docker compose version --short
if [[ -f .env.staging ]]; then echo 'Staging env file: present (values not printed)';
else echo 'Staging env file: missing'; fi
docker ps --filter label=com.docker.compose.project=isms-staging --format '{{.Names}} {{.Image}} {{.Status}}'
docker inspect isms-db-staging --format '{{range .Mounts}}{{.Name}} {{.Destination}}{{println}}{{end}}'
docker exec isms-db-staging sh -c '
  export MYSQL_PWD="$MARIADB_PASSWORD"
  mariadb --user="$MARIADB_USER" "$MARIADB_DATABASE" -N -e "SELECT VERSION(); SHOW TABLES;"
  has_history=$(mariadb --user="$MARIADB_USER" "$MARIADB_DATABASE" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=\"alembic_version\";")
  if [ "$has_history" = 1 ]; then
    mariadb --user="$MARIADB_USER" "$MARIADB_DATABASE" -N -e "SELECT version_num FROM alembic_version;"
  else
    echo "No Alembic history table: schema reconciliation review required."
  fi
'
