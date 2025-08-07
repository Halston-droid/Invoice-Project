# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import NoResultFound
from models import Base 
from models import InvoiceNumberTracker

DATABASE_URL = "sqlite:///customers.sqlite"# relative file in project root
# ↓ echo=False unless you want SQL statements printed for debugging
engine = create_engine(DATABASE_URL, echo=False, future=True)

# expire_on_commit=False lets you keep attributes usable after commit
SessionLocal = sessionmaker(bind=engine,
                            autoflush=False,
                            autocommit=False,
                            expire_on_commit=False,
                            future=True)

def init_db() -> None:
    """Create all tables once at app startup or for a migration."""
    Base.metadata.create_all(engine)  
  
def initialize_invoice_tracker():
    with SessionLocal() as db:
        if not db.query(InvoiceNumberTracker).first():
            db.add(InvoiceNumberTracker(last_number=1394711))  # Set your base
            db.commit()