# CodeAlpha Restaurant Management

A REST API for restaurant menus, orders, stock, tables, reservations, and daily reports. It uses Django, Django REST Framework, token authentication for staff APIs, and the default SQLite database.

## Setup

From the project directory, create and activate a virtual environment and install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Apply database migrations and optionally create the sample data:

```powershell
python manage.py migrate
python manage.py seed_restaurant
```

Create a Django admin/staff account:

```powershell
python manage.py createsuperuser
```

Start the development server:

```powershell
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/api/` and Django admin is at `http://127.0.0.1:8000/admin/`.

Run tests with:

```powershell
python manage.py test
```

## Authentication

Public endpoints are menu listing, table availability, order placement, and reservation creation/cancellation. Order listing/detail/status, inventory, and reports require a signed-in Django staff user. Obtain a DRF token using the username and password of a staff account:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_STAFF_USERNAME","password":"YOUR_PASSWORD"}'
```

Use the returned token as `Authorization: Token YOUR_TOKEN` on protected requests. Authenticated non-staff accounts receive `403`; unauthenticated protected requests receive `401`.

Customers can create a regular (non-staff) account and receive a token:

```bash
curl -X POST http://127.0.0.1:8000/api/register-user/ \
  -H "Content-Type: application/json" \
  -d '{"username":"new-customer","password":"StrongPass!927"}'
```

Log in an existing account to receive its token:

```bash
curl -X POST http://127.0.0.1:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"new-customer","password":"StrongPass!927"}'
```

Registration applies Django's configured password validators. Staff accounts should be created with `createsuperuser` or through Django admin, not public registration.

## API examples

Examples use `curl`; replace `YOUR_TOKEN` with a staff token where indicated. Run `python manage.py seed_restaurant` for the sample menu and table IDs.

### Menu

List available menu items (public):

```bash
curl http://127.0.0.1:8000/api/menu/
```

### Orders

Place an order (public). The API checks availability and recipe inventory and deducts stock atomically:

```bash
curl -X POST http://127.0.0.1:8000/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{"customer_name":"Alex","table":1,"items":[{"menu_item":1,"quantity":2}]}'
```

List orders (staff only):

```bash
curl http://127.0.0.1:8000/api/orders/ -H "Authorization: Token YOUR_TOKEN"
```

Get one order (staff only):

```bash
curl http://127.0.0.1:8000/api/orders/1/ -H "Authorization: Token YOUR_TOKEN"
```

Update order status (staff only). Setting `cancelled` restores the recipe stock once:

```bash
curl -X PATCH http://127.0.0.1:8000/api/orders/1/status/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"cancelled"}'
```

### Tables and reservations

List tables that fit and have no overlapping two-hour reservation (public):

```bash
curl "http://127.0.0.1:8000/api/tables/available/?date=2026-12-01&time=19:00&party_size=3"
```

Create a reservation (public):

```bash
curl -X POST http://127.0.0.1:8000/api/reservations/ \
  -H "Content-Type: application/json" \
  -d '{"table":3,"customer_name":"Taylor","phone":"555-0101","date":"2026-12-01","start_time":"19:00","party_size":3}'
```

Cancel a reservation by deleting it (public; its status is retained as `cancelled`):

```bash
curl -X DELETE http://127.0.0.1:8000/api/reservations/1/
```

### Inventory

List inventory (staff only):

```bash
curl http://127.0.0.1:8000/api/inventory/ -H "Authorization: Token YOUR_TOKEN"
```

Update inventory fields (staff only):

```bash
curl -X PATCH http://127.0.0.1:8000/api/inventory/1/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quantity":"12.500"}'
```

### Reports

Get daily sales for a date (staff only; cancelled orders are excluded):

```bash
curl "http://127.0.0.1:8000/api/reports/daily-sales/?date=2026-12-01" \
  -H "Authorization: Token YOUR_TOKEN"
```

List inventory below its low-stock threshold (staff only):

```bash
curl http://127.0.0.1:8000/api/reports/low-stock/ \
  -H "Authorization: Token YOUR_TOKEN"
```

## Notes

- An order menu item without a recipe does not consume stock.
- A reservation occupies its table for two hours from its start time. Cancelled reservations do not block availability.
- A cancelled order cannot be reopened; this prevents stock from being re-added without being deducted again.
- Validation and business-rule failures return JSON responses with HTTP `400`; missing records return `404`.
