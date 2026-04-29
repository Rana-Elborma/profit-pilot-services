from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProductCreate(BaseModel):
    name: str
    image: Optional[str] = None
    batch_quantity: int
    remaining_quantity: int
    batch_cost: float
    selling_price: float
    category: Optional[str] = None
    status: str = "stable"


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    image: Optional[str] = None
    batch_quantity: Optional[int] = None
    remaining_quantity: Optional[int] = None
    batch_cost: Optional[float] = None
    selling_price: Optional[float] = None
    category: Optional[str] = None
    status: Optional[str] = None


class ProductResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    image: Optional[str] = None
    batch_quantity: int
    remaining_quantity: int
    batch_cost: float
    selling_price: float
    category: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    product_id: UUID
    quantity: int
    type: str  # "sale" or "restock"


class TransactionResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    type: str
    created_at: datetime

    model_config = {"from_attributes": True}
