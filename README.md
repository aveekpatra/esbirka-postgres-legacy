# E-Sbírka PostgreSQL for Railway

PostgreSQL database deployment for E-Sbírka legal document system with pgvector embeddings.

## Quick Start

### 1. Create Railway PostgreSQL

1. Go to [Railway.app](https://railway.app)
2. Create a new project
3. Add **PostgreSQL** plugin (not MySQL!)
4. Copy the `DATABASE_URL` from the plugin settings

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and paste your Railway DATABASE_URL
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Restore Backup

```bash
# Ensure psql is installed and in PATH
python scripts/restore_backup.py
```

This will:
- Enable pgvector and pg_trgm extensions
- Stream the compressed backup to Railway
- Show progress during restore

### 5. Verify Restore

```bash
python scripts/verify_restore.py
```

## Database Schema

The database contains:

| Table | Description |
|-------|-------------|
| `laws` | Legal acts metadata |
| `versions` | Law version history |
| `sections` | Law sections/paragraphs |
| `section_chunks` | Chunked text with embeddings |
| `judgments` | Court judgment metadata |
| `judgment_chunks` | Judgment text chunks with embeddings |
| `judgment_contents` | Full judgment text |
| `judgment_law_references` | Links between judgments and laws |
| `definitions` | Legal term definitions |
| `query_cache` | Search result caching |

## Required Extensions

- **pgvector** - Vector similarity search for embeddings
- **pg_trgm** - Trigram fuzzy text search

Railway's PostgreSQL plugin supports both extensions.

## Environment Variables

```bash
# Railway PostgreSQL (required)
DATABASE_URL=postgresql://postgres:xxx@host.railway.internal:5432/railway

# For Backend connection
POSTGRES_HOST=roundhouse.proxy.rlwy.net
POSTGRES_PORT=12345
POSTGRES_USER=postgres
POSTGRES_PASSWORD=xxx
POSTGRES_DB=railway
```

## Backup Information

- **Format**: gzip-compressed SQL
- **Location**: `../E-sbirka integration/database/backups/`
- **Size**: ~27 GB compressed

## Troubleshooting

### psql not found
Install PostgreSQL client:
- **Windows**: Install PostgreSQL, add `bin` folder to PATH
- **Mac**: `brew install postgresql`
- **Linux**: `apt install postgresql-client`

### Connection timeout
- Check your Railway DATABASE_URL is correct
- Ensure your IP is not blocked by Railway firewall
- Try using the external proxy URL instead of internal

### Extension errors
If pgvector fails to create, your Railway PostgreSQL version may not support it.
Contact Railway support or use a higher tier plan.
