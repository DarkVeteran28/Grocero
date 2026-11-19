#!/bin/sh
set -eu

chown app:app /data

if [ ! -s /data/grocery.db ]; then
    echo "No database found; loading the bundled sample data."
    gosu app python scripts/seed.py
else
    chown app:app /data/grocery.db
fi

exec gosu app "$@"
