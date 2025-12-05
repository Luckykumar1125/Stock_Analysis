from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.orm import sessionmaker
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
def get_session(db_path: str):
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


# ---------------------------
# Save JSON Output to Database
# ---------------------------
def save_transactions(transactions_json, session):
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



