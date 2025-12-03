import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# ----------------------------------------------------------------
# 1. CONFIGURATION & CREDENTIALS
# ----------------------------------------------------------------
# Get credentials from Environment Variables (or default to root/empty)
username = os.getenv("db_username", "root")
password = os.getenv("db_pass", "")
host = os.getenv("db_host", "localhost")
db_name = "judgemenot_db"

# Construct Connection Strings
if password.strip() == "":
    # For connecting to the Server only (to create DB)
    SERVER_URL = f"mysql+pymysql://{username}@{host}"
    # For connecting to the specific Database
    DATABASE_URL = f"mysql+pymysql://{username}@{host}/{db_name}"
else:
    SERVER_URL = f"mysql+pymysql://{username}:{password}@{host}"
    DATABASE_URL = f"mysql+pymysql://{username}:{password}@{host}/{db_name}"

# ----------------------------------------------------------------
# 2. AUTO-CREATE DATABASE LOGIC
# ----------------------------------------------------------------
def create_database_if_not_exists():
    """
    Connects to MySQL server and creates the database if it doesn't exist.
    This runs automatically when the app starts.
    """
    try:
        # We need isolation_level="AUTOCOMMIT" because CREATE DATABASE 
        # cannot run inside a standard transaction block.
        temp_engine = create_engine(SERVER_URL, isolation_level="AUTOCOMMIT")
        
        with temp_engine.connect() as conn:
            # Safe command that only creates if missing
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
            print(f"✅ Database check: '{db_name}' is ready.")
            
    except Exception as e:
        print(f"⚠️  Database Warning: Could not auto-create '{db_name}'.")
        print(f"   Error details: {e}")
        print("   Please ensure MySQL is running and the user has CREATE permissions.")
    finally:
        # Close the temp connection immediately
        if 'temp_engine' in locals():
            temp_engine.dispose()

# Run this immediately when the module is imported
create_database_if_not_exists()

# ----------------------------------------------------------------
# 3. FINAL ENGINE SETUP
# ----------------------------------------------------------------
# Now we connect to the actual database
engine = create_engine(DATABASE_URL, pool_recycle=3600)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency function to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()