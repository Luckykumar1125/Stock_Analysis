from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# ---------------------------
# Database Model
# ---------------------------
class TransactionDB(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String)
    time = Column(String)
    transaction_type = Column(String)
    name = Column(String)
    amount = Column(Float)


# ---------------------------
# Database Setup
# ---------------------------
engine = create_engine("sqlite:///bank_statements.db", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


# ---------------------------
# Save JSON Output to Database
# ---------------------------
def save_transactions(transactions_json):
    """
    transactions_json should be a list of dicts:
    [
        {"date": "...", "time": "...", "transaction_type": "...", "name": "...", "amount": 1234.56},
        ...
    ]
    """
    session = SessionLocal()

    for t in transactions_json:
        entry = TransactionDB(
            date=t["date"],
            time=t["time"],
            transaction_type=t["transaction_type"],
            name=t["name"],
            amount=t["amount"]
        )
        session.add(entry)

    session.commit()
    session.close()



