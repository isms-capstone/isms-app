"""Read-only row fingerprints used before/after the additive CAT migration."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import MetaData, Table, inspect, select
from app.db.session import engine


def fingerprint(connection, table_name, columns):
    table = Table(table_name, MetaData(), autoload_with=connection)
    rows = connection.execute(select(*(table.c[name] for name in columns))).mappings()
    encoded = sorted(json.dumps(dict(row), sort_keys=True, ensure_ascii=False, default=str) for row in rows)
    return {'count': len(encoded), 'sha256': hashlib.sha256('\n'.join(encoded).encode()).hexdigest()}


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['snapshot', 'verify'])
    parser.add_argument('--file', required=True)
    args = parser.parse_args()
    path = Path(args.file)
    with engine.connect() as connection:
        if args.operation == 'snapshot':
            if path.exists():
                raise RuntimeError('Refusing to replace an existing snapshot')
            inspector = inspect(connection)
            result = {}
            for name in inspector.get_table_names():
                if name == 'alembic_version':
                    continue
                columns = [column['name'] for column in inspector.get_columns(name)]
                result[name] = {'columns': columns, **fingerprint(connection, name, columns)}
            path.write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(f'Captured fingerprints for {len(result)} existing tables; no row contents exported.')
        else:
            result = json.loads(path.read_text(encoding='utf-8'))
            for name, expected in result.items():
                actual = fingerprint(connection, name, expected['columns'])
                if actual != {key: expected[key] for key in ('count', 'sha256')}:
                    raise RuntimeError(f'Existing rows changed in {name}')
            print(f'Verified: all pre-existing columns and rows in {len(result)} tables are unchanged.')


if __name__ == '__main__':
    run()
