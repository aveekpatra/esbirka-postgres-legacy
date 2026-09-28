# E-Sbirka Postgres restore

> Legacy: this was part of an earlier version of the Aturno (Lexio) stack and is no longer in use. It is kept for reference.

Scripts to load a gzip-compressed SQL backup of the E-Sbirka legal database (Czech laws and court judgments with pgvector embeddings) into a PostgreSQL instance on Railway, then check that the restore is complete.

## Stack

- Python 3
- PostgreSQL with the `vector` (pgvector) and `pg_trgm` extensions
- `psql` client, asyncpg, python-dotenv

## Getting started

Install the PostgreSQL client so `psql` is on your PATH (for example `brew install postgresql` or `apt install postgresql-client`), then:

```bash
pip install -r requirements.txt
cp .env.example .env    # set DATABASE_URL
python scripts/restore_backup.py
python scripts/verify_restore.py
```

Environment variables (see `.env.example`):

- `DATABASE_URL`: connection string of the target PostgreSQL database
- `LOCAL_DATABASE_URL`: listed in the example file but not read by the scripts

## How it works

`scripts/restore_backup.py`:

1. Looks for the newest `esbirka_laws_*.sql.gz` in `../E-sbirka integration/database/backups/` (a folder outside this repo, about 27 GB compressed).
2. Runs `schema/01_extensions.sql` to enable `vector` and `pg_trgm`.
3. Asks for confirmation, then streams the decompressed backup into `psql` in 64 KB chunks, printing progress and ETA every 10 seconds.

`scripts/verify_restore.py` connects with asyncpg, prints the server version and installed extensions, counts rows in each expected table and checks how many `section_chunks` have embeddings.

## Database tables

| Table | Contents |
| --- | --- |
| `laws` | Legal act metadata |
| `versions` | Version history of each act |
| `sections` | Sections and paragraphs |
| `section_chunks` | Chunked section text with embeddings |
| `judgments` | Court judgment metadata |
| `judgment_contents` | Full judgment text |
| `judgment_chunks` | Judgment text chunks with embeddings |
| `judgment_law_references` | Links from judgments to laws |
| `definitions` | Legal term definitions |
| `query_cache` | Cached search results |

## Project structure

```
schema/01_extensions.sql   Extensions to enable before the restore
scripts/restore_backup.py  Streams the backup into PostgreSQL
scripts/verify_restore.py  Checks tables, row counts and embeddings
railway.json               Railway service config
```

## Deployment

The database itself is a Railway PostgreSQL service. `railway.json` only starts a placeholder `python -m http.server $PORT` so the repo can be deployed as a service; the restore is run from a local machine.
