"""ConfBadge API - the deliberately buggy service used in the talk
"Break My API: Can AI Find the Bugs I Forgot to Test?"

Four endpoints:
    POST /auth/login       - exchange email+password for a bearer token
    GET  /tickets          - search the published ticket catalogue
    POST /orders           - buy tickets, paying from your credit balance
    GET  /orders/{id}      - fetch a single order
    POST /_reset           - test-only: rebuild the database

Every bug is intentional and marked with `# BUG-Bn`. Read the markers before
the talk; do NOT show this file to the audience until after the demo.
"""

import base64
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.db import execute, init_db, query_all, query_one

MAX_PER_ORDER = 10          # documented limit: "up to 10 tickets per order"
LOYALTY_RATE = 0.10         # 10% of ticket value comes back as credits

COUPONS = {
    "EARLYBIRD": 20,        # 20% off, unlimited use, expires at launch
    "SPEAKER100": 100,      # 100% off, SINGLE USE, speakers only
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ConfBadge API",
    version="0.9.0",
    description=(
        "Internal ticket shop. Attendees buy tickets from a prepaid credit "
        "balance and earn 10% of the ticket value back as credits. "
        "Maximum 10 tickets per order."
    ),
    lifespan=lifespan,
)


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------

def make_token(user_id: int, role: str) -> str:
    # BUG-B7: the token is base64, not a signature. Anyone can mint one.
    #         There is also no expiry and no revocation.
    return base64.urlsafe_b64encode(f"{user_id}:{role}".encode()).decode()


def current_user(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        raw = base64.urlsafe_b64decode(authorization[7:] + "===").decode()
        user_id, role = raw.split(":")
    except Exception as exc:
        # BUG-B9: a malformed token is a client error, but this returns 500 and
        #         hands the caller the internal exception text.
        raise HTTPException(status_code=500, detail=f"token decode failed: {exc}")
    return {"id": int(user_id), "role": role}


class LoginIn(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
def login(body: LoginIn):
    row = query_one("SELECT id, role, password FROM users WHERE email = ?", (body.email,))
    if row is None or row["password"] != body.password:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {
        "access_token": make_token(row["id"], row["role"]),
        "token_type": "bearer",
        "role": row["role"],
    }


# --------------------------------------------------------------------------
# catalogue
# --------------------------------------------------------------------------

@app.get("/tickets")
def search_tickets(q: str = ""):
    # BUG-B3: the search term is concatenated straight into SQL.
    #         `?q=' OR '1'='1` leaks unpublished internal tickets.
    sql = (
        "SELECT id, name, price, stock, audience FROM tickets "
        f"WHERE published = 1 AND name LIKE '%{q}%'"
    )
    rows = query_all(sql)
    return {"count": len(rows), "results": [dict(r) for r in rows]}


# --------------------------------------------------------------------------
# orders
# --------------------------------------------------------------------------

class OrderIn(BaseModel):
    ticket_id: int
    quantity: int
    coupon: Optional[str] = None


@app.post("/orders", status_code=201)
def create_order(body: OrderIn, authorization: Optional[str] = Header(default=None)):
    user = current_user(authorization)

    ticket = query_one("SELECT * FROM tickets WHERE id = ?", (body.ticket_id,))
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    # BUG-B3b: no `published` check here either, so an unpublished ticket id
    #          discovered via the search injection can be ordered directly.

    # BUG-B2: the docs promise "up to 10 per order" but >= rejects exactly 10.
    if body.quantity >= MAX_PER_ORDER:
        raise HTTPException(status_code=400, detail=f"max {MAX_PER_ORDER} tickets per order")
    # BUG-B1: there is no lower bound. quantity = 0 or -5 sails straight through.

    discount = 0
    if body.coupon:
        discount = COUPONS.get(body.coupon.upper(), 0)
        # BUG-B5: SPEAKER100 is documented as single use, but nothing is ever
        #         written down about which coupons have been redeemed.

    total = round(ticket["price"] * body.quantity * (100 - discount) / 100, 2)

    # BUG-B6: read -> decide -> sleep -> write. Each statement is locked, the
    #         sequence is not. Two concurrent orders both read the same stock.
    stock = query_one("SELECT stock FROM tickets WHERE id = ?", (body.ticket_id,))["stock"]
    if stock < body.quantity:
        raise HTTPException(status_code=409, detail="sold out")
    time.sleep(0.05)  # stands in for payment-gateway latency
    execute("UPDATE tickets SET stock = ? WHERE id = ?", (stock - body.quantity, body.ticket_id))

    # BUG-B8: loyalty credits are calculated from the LIST price, not from the
    #         amount actually paid. Combined with BUG-B5 this is a money loop.
    credits_earned = round(ticket["price"] * body.quantity * LOYALTY_RATE, 2)

    # BUG-B1b: the balance is never checked before charging it.
    execute(
        "UPDATE users SET credits = credits - ? + ? WHERE id = ?",
        (total, credits_earned, user["id"]),
    )

    order_id = execute(
        "INSERT INTO orders (user_id, ticket_id, quantity, coupon, total, credits_earned) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user["id"], body.ticket_id, body.quantity, body.coupon, total, credits_earned),
    )
    balance = query_one("SELECT credits FROM users WHERE id = ?", (user["id"],))["credits"]

    return {
        "order_id": order_id,
        "ticket": ticket["name"],
        "quantity": body.quantity,
        "total_charged": total,
        "credits_earned": credits_earned,
        "credit_balance": round(balance, 2),
    }


@app.get("/orders/{order_id}")
def get_order(order_id: int, authorization: Optional[str] = Header(default=None)):
    current_user(authorization)
    row = query_one("SELECT * FROM orders WHERE id = ?", (order_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="order not found")
    # BUG-B4: authenticated, but not authorised. Any valid token reads any
    #         order, including other people's.
    return dict(row)


@app.post("/_reset")
def reset():
    """Test-only hook so every demo run starts from identical state."""
    init_db()
    return {"status": "reset"}


@app.get("/me")
def me(authorization: Optional[str] = Header(default=None)):
    user = current_user(authorization)
    row = query_one("SELECT id, email, role, credits FROM users WHERE id = ?", (user["id"],))
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return dict(row)
