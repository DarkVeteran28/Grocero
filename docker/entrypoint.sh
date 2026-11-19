#!/bin/sh
set -eu

if [ ! -s /data/grocery.db ]; then
    echo "No database found; loading the bundled sample data."
    python scripts/seed.py
fi

exec "$@"
