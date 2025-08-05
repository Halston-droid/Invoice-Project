from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from sqlalchemy import(Column, String, Integer, Numeric, DateTime)

from sqlalchemy.orm import declarative_base
Base = declarative_base()

class Customer(Base):
    __tablename__="customers"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable = False)
    location = Column(String(120), nullable = False)
    store_count = Column(Integer)
    rate = Column(String(120))
    amount = Column(Numeric(12, 2))
    email = Column(String(120))
    vendornum = Column(String(120))
    currentPurchaseOrderNum = Column(String(120))
    paymentTerm = Column(Integer)
    currentPO = Column(String(120))
    nextPO = Column(String(120))
    unitPrice = Column(Numeric(12, 2))
    totalPrice = Column(Numeric(12, 2))
    fixedPrice = Column(Numeric(12, 2))
    currentPOtotal = Column(Numeric(12, 2))
    currentPOExpDate = Column(DateTime(timezone=True), nullable = True)
    nextPOtotal = Column(Numeric(12, 2))
    nextPOExpDate = Column(DateTime(timezone=True), nullable = True)
    total = Column(Numeric(12, 2))
    multiplier = Column(Numeric(12, 2))
    service_types = Column(String(120))
    service_amounts = Column(String(120))  # Store as CSV string
    other_service_descriptions = Column(String(120))
    other_service_amounts = Column(String(120))