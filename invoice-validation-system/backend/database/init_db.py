import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.core import engine, Base
from database.models import Project, Document, ValidationResult

def init_db():
    print(f"Creating tables in database...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()
