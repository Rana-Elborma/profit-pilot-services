import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from app.database import get_db
from app.schemas import TransactionCreate, TransactionResponse
from app.deps import get_current_user

router = APIRouter()


@firestore.transactional
def _execute_transaction(
    transaction,
    product_ref,
    txn_ref,
    user_id: str,
    quantity: int,
    txn_type: str,
    txn_data: dict,
):
    snapshot = product_ref.get(transaction=transaction)
    if not snapshot.exists or snapshot.to_dict().get("user_id") != user_id:
        raise ValueError("not_found")
    product = snapshot.to_dict()
    if txn_type == "sale":
        if product["remaining_quantity"] < quantity:
            raise ValueError("insufficient")
        transaction.update(product_ref, {
            "remaining_quantity": product["remaining_quantity"] - quantity,
        })
    else:
        transaction.update(product_ref, {
            "remaining_quantity": product["remaining_quantity"] + quantity,
            "batch_quantity": product["batch_quantity"] + quantity,
        })
    transaction.set(txn_ref, txn_data)


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    docs = db.collection("transactions").where("user_id", "==", current_user["id"]).get()
    result = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        result.append(data)
    return result


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    body: TransactionCreate,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    if body.type not in ("sale", "restock"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="type must be 'sale' or 'restock'",
        )
    txn_id = str(uuid.uuid4())
    txn_data = {
        "user_id": current_user["id"],
        "product_id": str(body.product_id),
        "quantity": body.quantity,
        "type": body.type,
        "created_at": datetime.now(timezone.utc),
    }
    product_ref = db.collection("products").document(str(body.product_id))
    txn_ref = db.collection("transactions").document(txn_id)
    t = db.transaction()
    try:
        _execute_transaction(t, product_ref, txn_ref, current_user["id"], body.quantity, body.type, txn_data)
    except ValueError as e:
        msg = str(e)
        if msg == "not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        if msg == "insufficient":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Insufficient remaining quantity",
            )
        raise
    txn_data["id"] = txn_id
    return txn_data
