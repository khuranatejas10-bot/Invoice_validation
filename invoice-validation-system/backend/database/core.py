import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Use a default Postgres URL, or read from env.
# Falling back to sqlite for local testing since Postgres is not running.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./invoice_db.sqlite"
)

# SQLite needs connect_args={"check_same_thread": False}
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
