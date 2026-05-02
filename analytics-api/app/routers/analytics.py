from __future__ import annotations
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from google.cloud import firestore
from app import config
from app.database import get_db

router = APIRouter()
_bearer = HTTPBearer()


def _get_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise JWTError("missing sub")
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _load_products(db: firestore.Client, user_id: str) -> dict[str, dict]:
    docs = db.collection("products").where("user_id", "==", user_id).get()
    return {d.id: d.to_dict() for d in docs}


def _load_transactions(db: firestore.Client, user_id: str) -> list[dict]:
    docs = db.collection("transactions").where("user_id", "==", user_id).get()
    return [d.to_dict() for d in docs]


@router.get("/summary")
def summary(
    user_id: str = Depends(_get_user_id),
    db: firestore.Client = Depends(get_db),
):
    products = _load_products(db, user_id)
    transactions = _load_transactions(db, user_id)

    total_revenue = 0.0
    total_cost = 0.0
    for txn in transactions:
        if txn["type"] == "sale":
            product = products.get(txn["product_id"])
            if product:
                cost_per_unit = float(product["batch_cost"]) / float(product["batch_quantity"])
                total_revenue += float(product["selling_price"]) * txn["quantity"]
                total_cost += cost_per_unit * txn["quantity"]

    net_profit = total_revenue - total_cost
    roi = (net_profit / total_cost * 100) if total_cost > 0 else 0.0
    return {
        "total_revenue": round(total_revenue, 2),
        "total_cost": round(total_cost, 2),
        "net_profit": round(net_profit, 2),
        "roi": round(roi, 2),
    }


def _aggregate_products(products: dict, transactions: list) -> list[dict]:
    aggregated: dict[str, dict] = {}
    for pid, p in products.items():
        aggregated[pid] = {
            "id": pid,
            "name": p["name"],
            "category": p.get("category"),
            "status": p.get("status", "stable"),
            "units_sold": 0,
            "revenue": 0.0,
            "cost": 0.0,
        }
    for txn in transactions:
        if txn["type"] != "sale":
            continue
        pid = txn["product_id"]
        product = products.get(pid)
        if not product or pid not in aggregated:
            continue
        cost_per_unit = float(product["batch_cost"]) / float(product["batch_quantity"])
        aggregated[pid]["units_sold"] += txn["quantity"]
        aggregated[pid]["revenue"] += float(product["selling_price"]) * txn["quantity"]
        aggregated[pid]["cost"] += cost_per_unit * txn["quantity"]

    results = []
    for agg in aggregated.values():
        profit = agg["revenue"] - agg["cost"]
        roi = (profit / agg["cost"] * 100) if agg["cost"] > 0 else 0.0
        results.append({
            "id": agg["id"],
            "name": agg["name"],
            "category": agg["category"],
            "status": agg["status"],
            "units_sold": agg["units_sold"],
            "revenue": round(agg["revenue"], 2),
            "cost": round(agg["cost"], 2),
            "profit": round(profit, 2),
            "roi": round(roi, 2),
        })
    return results


@router.get("/top-products")
def top_products(
    user_id: str = Depends(_get_user_id),
    db: firestore.Client = Depends(get_db),
):
    results = _aggregate_products(_load_products(db, user_id), _load_transactions(db, user_id))
    results.sort(key=lambda x: x["profit"], reverse=True)
    return results[:5]


@router.get("/cashflow")
def cashflow(
    user_id: str = Depends(_get_user_id),
    db: firestore.Client = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    six_months_ago = now - relativedelta(months=6)
    products = _load_products(db, user_id)
    transactions = _load_transactions(db, user_id)

    monthly: dict[str, dict] = {}
    for txn in transactions:
        created_at = txn.get("created_at")
        if created_at is None:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at < six_months_ago:
            continue
        product = products.get(txn["product_id"])
        if not product:
            continue
        label = created_at.strftime("%Y-%m")
        if label not in monthly:
            monthly[label] = {"month": label, "earned": 0.0, "spent": 0.0}
        if txn["type"] == "sale":
            monthly[label]["earned"] += float(product["selling_price"]) * txn["quantity"]
        else:
            cost_per_unit = float(product["batch_cost"]) / float(product["batch_quantity"])
            monthly[label]["spent"] += cost_per_unit * txn["quantity"]

    return [
        {
            "month": v["month"],
            "earned": round(v["earned"], 2),
            "spent": round(v["spent"], 2),
            "net": round(v["earned"] - v["spent"], 2),
        }
        for v in sorted(monthly.values(), key=lambda x: x["month"])
    ]


@router.get("/underperformers")
def underperformers(
    user_id: str = Depends(_get_user_id),
    db: firestore.Client = Depends(get_db),
):
    results = _aggregate_products(_load_products(db, user_id), _load_transactions(db, user_id))
    results.sort(key=lambda x: x["roi"])
    return results[:3]
