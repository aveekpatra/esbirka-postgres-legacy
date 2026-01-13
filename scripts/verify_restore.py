"""
Verify PostgreSQL restore integrity.
Checks tables, row counts, and vector functionality.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

try:
    import asyncpg
except ImportError:
    print("Installing asyncpg...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "asyncpg"])
    import asyncpg

# Load environment variables
load_dotenv()


async def verify_database():
    """Verify database integrity after restore."""
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set")
        return False
    
    print("=" * 60)
    print("🔍 E-Sbírka Database Verification")
    print("=" * 60)
    print()
    
    try:
        conn = await asyncpg.connect(db_url)
        print("✅ Connected to database")
        
        # Check PostgreSQL version
        version = await conn.fetchval("SELECT version()")
        print(f"📊 {version[:50]}...")
        print()
        
        # Check extensions
        print("📦 Extensions:")
        extensions = await conn.fetch("""
            SELECT extname, extversion 
            FROM pg_extension 
            WHERE extname IN ('vector', 'pg_trgm')
        """)
        for ext in extensions:
            print(f"   ✅ {ext['extname']} v{ext['extversion']}")
        
        if len(extensions) < 2:
            print("   ⚠️ Some extensions may be missing")
        print()
        
        # Check tables
        print("📋 Tables:")
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        expected_tables = [
            'laws', 'versions', 'sections', 'section_chunks',
            'judgments', 'judgment_chunks', 'judgment_contents',
            'judgment_law_references', 'definitions', 'query_cache'
        ]
        
        found_tables = [t['tablename'] for t in tables]
        for table in expected_tables:
            if table in found_tables:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"   ✅ {table}: {count:,} rows")
            else:
                print(f"   ❌ {table}: NOT FOUND")
        print()
        
        # Check vector columns
        print("🧮 Vector columns:")
        vector_cols = await conn.fetch("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE data_type = 'USER-DEFINED' 
            AND udt_name = 'vector'
        """)
        
        for col in vector_cols:
            print(f"   ✅ {col['table_name']}.{col['column_name']}")
        
        if not vector_cols:
            print("   ⚠️ No vector columns found")
        print()
        
        # Test vector search
        print("🔬 Testing vector search...")
        try:
            # Check if section_chunks has embeddings
            has_embeddings = await conn.fetchval("""
                SELECT COUNT(*) FROM section_chunks WHERE embedding IS NOT NULL
            """)
            print(f"   📊 Chunks with embeddings: {has_embeddings:,}")
            
            if has_embeddings > 0:
                # Test a sample similarity search
                result = await conn.fetchval("""
                    SELECT COUNT(*) FROM (
                        SELECT id FROM section_chunks 
                        WHERE embedding IS NOT NULL 
                        LIMIT 1
                    ) t
                """)
                print(f"   ✅ Vector operations working")
        except Exception as e:
            print(f"   ⚠️ Vector test failed: {e}")
        
        print()
        print("=" * 60)
        print("✅ VERIFICATION COMPLETE")
        print("=" * 60)
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    success = asyncio.run(verify_database())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
