-- E-Sbírka PostgreSQL Extensions
-- Run this first before restoring the backup

-- pgvector for embedding storage and similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify extensions
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pg_trgm');
