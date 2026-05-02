import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from app.database import get_db
from app.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.deps import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: firestore.Client = Depends(get_db)):
    existing = db.collection("users").where("email", "==", body.email).limit(1).get()
    if len(existing) > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user_id = str(uuid.uuid4())
    db.collection("users").document(user_id).set({
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "created_at": datetime.now(timezone.utc),
    })
    return TokenResponse(access_token=create_access_token(user_id))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: firestore.Client = Depends(get_db)):
    docs = db.collection("users").where("email", "==", body.email).limit(1).get()
    if not docs:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    doc = docs[0]
    user = doc.to_dict()
    if not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(doc.id))
