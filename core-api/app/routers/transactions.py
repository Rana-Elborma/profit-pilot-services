from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Product, Transaction
from app.schemas import TransactionCreate, TransactionResponse
from app.deps import get_current_user

router = APIRouter()


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Transaction).filter(Transaction.user_id == current_user.id).all()


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    body: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.type not in ("sale", "restock"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="type must be 'sale' or 'restock'",
        )

    product = db.query(Product).filter(
        Product.id == body.product_id, Product.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if body.type == "sale":
        if product.remaining_quantity < body.quantity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Insufficient remaining quantity",
            )
        product.remaining_quantity -= body.quantity
    else:  # restock
        product.remaining_quantity += body.quantity
        product.batch_quantity += body.quantity

    transaction = Transaction(
        user_id=current_user.id,
        product_id=body.product_id,
        quantity=body.quantity,
        type=body.type,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction
