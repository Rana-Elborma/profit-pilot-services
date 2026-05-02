import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from app.database import get_db
from app.schemas import ProductCreate, ProductUpdate, ProductResponse
from app.deps import get_current_user

router = APIRouter()


def _doc_to_product(doc) -> dict:
    data = doc.to_dict()
    data["id"] = doc.id
    return data


@router.get("", response_model=list[ProductResponse])
def list_products(
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    docs = db.collection("products").where("user_id", "==", current_user["id"]).get()
    return [_doc_to_product(d) for d in docs]


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    body: ProductCreate,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    product_id = str(uuid.uuid4())
    data = body.model_dump()
    data["user_id"] = current_user["id"]
    data["created_at"] = datetime.now(timezone.utc)
    db.collection("products").document(product_id).set(data)
    data["id"] = product_id
    return data


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    body: ProductUpdate,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    ref = db.collection("products").document(product_id)
    doc = ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    updates = body.model_dump(exclude_none=True)
    if updates:
        ref.update(updates)
    updated = ref.get().to_dict()
    updated["id"] = product_id
    return updated


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    ref = db.collection("products").document(product_id)
    doc = ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    ref.delete()
