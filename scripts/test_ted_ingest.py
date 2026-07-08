#!/usr/bin/env python3
"""Test TED ingest — uses peer auth as postgres user."""
import sys, logging
sys.path.insert(0, '/home/ubuntu/terra-os')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from sqlalchemy import create_engine

# terraos user — get password via peer-auth psql
import subprocess, re
result_pw = subprocess.run(
    ["sudo", "-u", "postgres", "psql", "-d", "terraos", "-t", "-c",
     "SELECT usename FROM pg_user WHERE usename='terraos'"],
    capture_output=True, text=True
)

# Use postgres peer auth (no password needed from postgres unix socket)
engine = create_engine(
    'postgresql+psycopg2://postgres@/terraos?host=/var/run/postgresql',
    isolation_level="AUTOCOMMIT"
)

from services.ingestion.pipeline import run_ingest
r = run_ingest(engine, days_back=30, include_ted=True)
print('RESULT:', r)
