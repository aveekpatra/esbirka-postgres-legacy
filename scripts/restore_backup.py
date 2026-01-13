"""
Memory-efficient PostgreSQL backup restore script for Railway.
Streams compressed backup directly to Railway PostgreSQL.
"""

import subprocess
import sys
import os
import gzip
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BACKUP_DIR = Path(__file__).parent.parent.parent / "E-sbirka integration" / "database" / "backups"
CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming


def format_size(bytes_count: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.2f} TB"


def format_time(seconds: float) -> str:
    """Format seconds to human-readable time."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def find_latest_backup() -> Path:
    """Find the most recent backup file."""
    backups = list(BACKUP_DIR.glob("esbirka_laws_*.sql.gz"))
    if not backups:
        print(f"❌ No backup files found in {BACKUP_DIR}")
        sys.exit(1)
    
    latest = max(backups, key=lambda p: p.stat().st_mtime)
    size = latest.stat().st_size
    print(f"📦 Found backup: {latest.name}")
    print(f"   Size: {format_size(size)}")
    return latest


def get_database_url() -> str:
    """Get Railway PostgreSQL connection URL."""
    url = os.getenv("DATABASE_URL")
    if not url:
        print("❌ DATABASE_URL not set in environment")
        print("   Set it to your Railway PostgreSQL connection string")
        print("   Example: postgresql://postgres:pass@host.railway.internal:5432/railway")
        sys.exit(1)
    
    # Mask password for display
    masked = url.split("@")[0].rsplit(":", 1)[0] + ":***@" + url.split("@")[1]
    print(f"🔗 Connecting to: {masked}")
    return url


def enable_extensions(db_url: str) -> bool:
    """Enable required PostgreSQL extensions."""
    print("\n📦 Enabling extensions...")
    
    schema_file = Path(__file__).parent.parent / "schema" / "01_extensions.sql"
    if not schema_file.exists():
        print(f"⚠️ Schema file not found: {schema_file}")
        return False
    
    try:
        result = subprocess.run(
            ["psql", db_url, "-f", str(schema_file)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ Extensions enabled successfully")
            return True
        else:
            print(f"⚠️ Extension setup had issues: {result.stderr}")
            return True  # Continue anyway, extensions might already exist
            
    except FileNotFoundError:
        print("❌ psql not found. Please install PostgreSQL client.")
        return False
    except Exception as e:
        print(f"❌ Failed to enable extensions: {e}")
        return False


def stream_restore(backup_path: Path, db_url: str) -> bool:
    """
    Stream compressed backup to PostgreSQL.
    Memory-efficient: reads in chunks, never loads full backup into RAM.
    """
    print("\n🚀 Starting restore...")
    print(f"   This may take several hours for large databases.")
    print(f"   Press Ctrl+C to cancel.\n")
    
    start_time = time.time()
    bytes_read = 0
    total_size = backup_path.stat().st_size
    last_report_time = start_time
    
    try:
        # Start psql process
        psql_process = subprocess.Popen(
            ["psql", db_url, "-q"],  # -q for quiet mode
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        
        # Stream decompressed data to psql
        with gzip.open(backup_path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                
                psql_process.stdin.write(chunk)
                bytes_read += len(chunk)
                
                # Progress report every 10 seconds
                current_time = time.time()
                if current_time - last_report_time >= 10:
                    elapsed = current_time - start_time
                    # Estimate based on compressed size ratio
                    progress = (f.tell() / total_size) * 100
                    speed = bytes_read / elapsed
                    eta = (total_size - f.tell()) / (f.tell() / elapsed) if f.tell() > 0 else 0
                    
                    print(f"\r⏳ Progress: {progress:.1f}% | "
                          f"Read: {format_size(bytes_read)} | "
                          f"Speed: {format_size(speed)}/s | "
                          f"ETA: {format_time(eta)}", end="", flush=True)
                    
                    last_report_time = current_time
        
        # Close stdin and wait for completion
        psql_process.stdin.close()
        psql_process.wait()
        
        elapsed = time.time() - start_time
        print()  # New line after progress
        
        if psql_process.returncode == 0:
            print(f"\n✅ Restore completed successfully!")
            print(f"⏱️ Total time: {format_time(elapsed)}")
            print(f"📊 Data processed: {format_size(bytes_read)}")
            return True
        else:
            stderr = psql_process.stderr.read().decode('utf-8', errors='replace')
            print(f"\n❌ Restore failed with code {psql_process.returncode}")
            if stderr:
                print(f"Error: {stderr[:500]}")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Restore interrupted by user")
        psql_process.terminate()
        return False
    except FileNotFoundError:
        print("❌ psql not found. Please install PostgreSQL client.")
        print("   On Windows: Install PostgreSQL and add bin folder to PATH")
        print("   On Mac: brew install postgresql")
        print("   On Linux: apt install postgresql-client")
        return False
    except Exception as e:
        print(f"\n❌ Restore failed: {e}")
        return False


def main():
    print("=" * 60)
    print("🚀 E-Sbírka PostgreSQL Restore Tool")
    print("   Railway.com Database Import")
    print("=" * 60)
    print()
    
    # Get database URL
    db_url = get_database_url()
    
    # Find latest backup
    backup_path = find_latest_backup()
    
    # Confirm before proceeding
    print()
    print("⚠️  WARNING: This will REPLACE all data in the target database!")
    response = input("   Continue? [y/N]: ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    # Enable extensions first
    if not enable_extensions(db_url):
        print("⚠️ Continuing without extension setup...")
    
    # Stream restore
    success = stream_restore(backup_path, db_url)
    
    print()
    if success:
        print("=" * 60)
        print("✅ DATABASE RESTORE COMPLETE")
        print("=" * 60)
        print()
        print("📋 Next steps:")
        print("   1. Run verify_restore.py to check data integrity")
        print("   2. Update your Backend .env with the Railway DATABASE_URL")
        print()
    else:
        print("=" * 60)
        print("❌ DATABASE RESTORE FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
