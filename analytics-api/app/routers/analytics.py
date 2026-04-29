from __future__ import annotations
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session
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


@router.get("/summary")
def summary(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text("""
            SELECT
                t.quantity,
                t.type,
                p.selling_price,
                p.batch_cost,
                p.batch_quantity
            FROM transactions t
            JOIN products p ON p.id = t.product_id
            WHERE t.user_id = :uid
        """),
        {"uid": user_id},
    ).fetchall()

    total_revenue = 0.0
    total_cost = 0.0
    for row in rows:
        if row.type == "sale":
            cost_per_unit = float(row.batch_cost) / float(row.batch_quantity)
            total_revenue += float(row.selling_price) * row.quantity
            total_cost += cost_per_unit * row.quantity

    net_profit = total_revenue - total_cost
    roi = (net_profit / total_cost * 100) if total_cost > 0 else 0.0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_cost": round(total_cost, 2),
        "net_profit": round(net_profit, 2),
        "roi": round(roi, 2),
    }


@router.get("/top-products")
def top_products(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text("""
            SELECT
                p.id,
                p.name,
                p.category,
                p.status,
                p.selling_price,
                p.batch_cost,
                p.batch_quantity,
                COALESCE(SUM(CASE WHEN t.type = 'sale' THEN t.quantity ELSE 0 END), 0) AS units_sold
            FROM products p
            LEFT JOIN transactions t ON t.product_id = p.id AND t.user_id = :uid
            WHERE p.user_id = :uid
            GROUP BY p.id, p.name, p.category, p.status, p.selling_price, p.batch_cost, p.batch_quantity
        """),
        {"uid": user_id},
    ).fetchall()

    results = []
    for row in rows:
        cost_per_unit = float(row.batch_cost) / float(row.batch_quantity)
        revenue = float(row.selling_price) * row.units_sold
        cost = cost_per_unit * row.units_sold
        profit = revenue - cost
        roi = (profit / cost * 100) if cost > 0 else 0.0
        results.append(
            {
                "id": str(row.id),
                "name": row.name,
                "category": row.category,
                "status": row.status,
                "units_sold": row.units_sold,
                "revenue": round(revenue, 2),
                "cost": round(cost, 2),
                "profit": round(profit, 2),
                "roi": round(roi, 2),
            }
        )

    results.sort(key=lambda x: x["profit"], reverse=True)
    return results[:5]


@router.get("/cashflow")
def cashflow(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    six_months_ago = now - relativedelta(months=6)

    rows = db.execute(
        text("""
            SELECT
                DATE_TRUNC('month', t.created_at) AS month,
                t.type,
                t.quantity,
                p.selling_price,
                p.batch_cost,
                p.batch_quantity
            FROM transactions t
            JOIN products p ON p.id = t.product_id
            WHERE t.user_id = :uid
              AND t.created_at >= :since
            ORDER BY month
        """),
        {"uid": user_id, "since": six_months_ago},
    ).fetchall()

    monthly: dict[str, dict] = {}
    for row in rows:
        label = row.month.strftime("%Y-%m")
        if label not in monthly:
            monthly[label] = {"month": label, "earned": 0.0, "spent": 0.0}
        if row.type == "sale":
            monthly[label]["earned"] += float(row.selling_price) * row.quantity
        else:  # restock
            cost_per_unit = float(row.batch_cost) / float(row.batch_quantity)
            monthly[label]["spent"] += cost_per_unit * row.quantity

    result = [
        {
            "month": v["month"],
            "earned": round(v["earned"], 2),
            "spent": round(v["spent"], 2),
            "net": round(v["earned"] - v["spent"], 2),
        }
        for v in sorted(monthly.values(), key=lambda x: x["month"])
    ]
    return result


@router.get("/underperformers")
def underperformers(
    user_id: str = Depends(_get_user_id),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text("""
            SELECT
                p.id,
                p.name,
                p.category,
                p.status,
                p.selling_price,
                p.batch_cost,
                p.batch_quantity,
                COALESCE(SUM(CASE WHEN t.type = 'sale' THEN t.quantity ELSE 0 END), 0) AS units_sold
            FROM products p
            LEFT JOIN transactions t ON t.product_id = p.id AND t.user_id = :uid
            WHERE p.user_id = :uid
            GROUP BY p.id, p.name, p.category, p.status, p.selling_price, p.batch_cost, p.batch_quantity
        """),
        {"uid": user_id},
    ).fetchall()

    results = []
    for row in rows:
        cost_per_unit = float(row.batch_cost) / float(row.batch_quantity)
        revenue = float(row.selling_price) * row.units_sold
        cost = cost_per_unit * row.units_sold
        profit = revenue - cost
        roi = (profit / cost * 100) if cost > 0 else 0.0
        results.append(
            {
                "id": str(row.id),
                "name": row.name,
                "category": row.category,
                "status": row.status,
                "units_sold": row.units_sold,
                "revenue": round(revenue, 2),
                "cost": round(cost, 2),
                "profit": round(profit, 2),
                "roi": round(roi, 2),
            }
        )

    results.sort(key=lambda x: x["roi"])
    return results[:3]
