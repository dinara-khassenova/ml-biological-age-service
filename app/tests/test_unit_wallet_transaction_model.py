from sqlmodel import Session, select

from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
from models.enum import TransactionType


def test_create_wallet_and_transaction(session: Session):
    user = User(id=1, email="w1@mail.ru", password="password123")
    session.add(user)
    session.commit()

    wallet = Wallet(user_id=1, balance=0)
    session.add(wallet)
    session.commit()

    tx = Transaction(user_id=1, amount=100, tx_type=TransactionType.TOPUP)
    session.add(tx)
    session.commit()

    items = session.exec(select(Transaction).where(Transaction.user_id == 1)).all()
    assert len(items) == 1
    assert items[0].amount == 100
    assert items[0].tx_type == TransactionType.TOPUP
