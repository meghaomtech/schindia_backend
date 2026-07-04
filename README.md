# Shichida India — Backend

## Quick Start (Local Development)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations (creates local SQLite database)
python manage.py migrate

# 3. Create a superuser for Django admin
python manage.py createsuperuser

# 4. Start the server
python manage.py runserver
```

Server runs at: `http://localhost:8000`  
Django Admin: `http://localhost:8000/admin/`

---

## Environments

| Environment | `.env` setting | Database | Tables |
|-------------|---------------|----------|--------|
| **Local** | `DJANGO_ENV=local` | SQLite (`db.sqlite3`) | Django ORM |
| **Dev** | `DJANGO_ENV=dev` | AWS DynamoDB | `Shichida-dev-*` |
| **Production** | `DJANGO_ENV=production` | AWS DynamoDB | `Shichida-production-*` |

---

## `.env` File Configuration

### For LOCAL development (no AWS needed):
```env
DJANGO_ENV=local
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=any-random-string-here
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-south-1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
ALLOWED_HOSTS=localhost,127.0.0.1
```

### For DEV (pushing to AWS):
```env
DJANGO_ENV=dev
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=a-strong-secret-key
AWS_ACCESS_KEY_ID=AKIA...your-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=ap-south-1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## Commands Reference

### Everyday Local Development

```bash
# Start server
python manage.py runserver

# Create new migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Open Django shell
python manage.py shell
```

### Switching to Dev (AWS DynamoDB)

```bash
# Step 1: Update .env
#   Change DJANGO_ENV=local  →  DJANGO_ENV=dev
#   Fill in AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

# Step 2: Create DynamoDB tables (one-time per environment)
python manage.py create_dynamo_tables

# Step 3: Start server (now reads/writes to DynamoDB)
python manage.py runserver
```

### Switching Back to Local

```bash
# Just change .env:
#   DJANGO_ENV=dev  →  DJANGO_ENV=local
# Restart the server. Back to SQLite.
```

### DynamoDB Table Management

```bash
# Create all tables
python manage.py create_dynamo_tables

# Delete all tables (DANGER — destroys data)
python manage.py create_dynamo_tables --delete
```

---

## API Endpoints

Base URL: `http://localhost:8000`

### Auth (`/api/auth/`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/register/` | Register (immediate approval, returns JWT) | None |
| POST | `/api/auth/request-access/` | Request access (pending approval) | None |
| POST | `/api/auth/request-root-access/` | Request root access | None |
| POST | `/api/auth/login/` | Login, returns JWT | None |
| POST | `/api/auth/refresh/` | Refresh JWT token | None |
| POST | `/api/auth/verify/` | Verify JWT token | None |
| POST | `/api/auth/logout/` | Blacklist refresh token | Token |
| GET | `/api/auth/me/` | Get current user | Token |
| POST | `/api/auth/change-password/` | Change password | Token |
| GET | `/api/auth/access-requests/` | List access requests | Root |
| PATCH | `/api/auth/access-requests/{id}/approve/` | Approve request | Root |
| PATCH | `/api/auth/access-requests/{id}/reject/` | Reject request | Root |

### Centres (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/centres/` | List all centres |
| POST | `/api/v1/centres/` | Create centre (with rooms) |
| GET | `/api/v1/centres/{id}/` | Get centre detail |
| PATCH | `/api/v1/centres/{id}/` | Update centre |
| DELETE | `/api/v1/centres/{id}/` | Delete centre |
| GET | `/api/v1/centres/{id}/rooms/` | List rooms |
| POST | `/api/v1/centres/{id}/rooms/` | Add room |
| PATCH | `/api/v1/centres/{id}/rooms/{roomId}/` | Update room |
| DELETE | `/api/v1/centres/{id}/rooms/{roomId}/` | Delete room |

### Sessions (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/centres/{id}/sessions/` | List sessions |
| POST | `/api/v1/centres/{id}/sessions/` | Create session |
| PATCH | `/api/v1/sessions/{id}/` | Update session |
| DELETE | `/api/v1/sessions/{id}/` | Delete session |

### Timetable / Slots (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/centres/{id}/slots/?week=2026-07-01` | List slots (filter by week) |
| POST | `/api/v1/centres/{id}/slots/` | Create slot |
| POST | `/api/v1/centres/{id}/slots/generate/` | Generate recurring slots |
| PATCH | `/api/v1/slots/{id}/` | Update slot |
| DELETE | `/api/v1/slots/{id}/` | Delete slot |

### Children (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/children/?centre={id}` | List children |
| POST | `/api/v1/children/` | Register child (with contacts) |
| GET | `/api/v1/children/{id}/` | Get child detail |
| PATCH | `/api/v1/children/{id}/` | Update child |
| GET | `/api/v1/children/{id}/contacts/` | List contacts |
| POST | `/api/v1/children/{id}/contacts/` | Add contact |
| PATCH | `/api/v1/contacts/{id}/` | Update contact |
| DELETE | `/api/v1/contacts/{id}/` | Delete contact |

### Enrolments (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/children/{id}/enrolments/` | List enrolments |
| POST | `/api/v1/enrolments/` | Create enrolment |
| DELETE | `/api/v1/enrolments/{id}/` | Delete enrolment |

### Journey & Notes (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/children/{id}/journey/` | List journey entries |
| POST | `/api/v1/children/{id}/journey/` | Add journey entry |
| GET | `/api/v1/children/{id}/notes/` | List notes |
| POST | `/api/v1/children/{id}/notes/` | Add note |

### Roles & Permissions (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/centres/{id}/roles/` | List roles |
| POST | `/api/v1/centres/{id}/roles/` | Create role |
| PATCH | `/api/v1/roles/{id}/` | Update role |
| DELETE | `/api/v1/roles/{id}/` | Delete role |
| PATCH | `/api/v1/roles/{id}/permissions/{key}/` | Update permission |
| POST | `/api/v1/roles/{id}/members/` | Add member |
| DELETE | `/api/v1/roles/{id}/members/{userId}/` | Remove member |

### Invoices (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/children/{id}/invoices/` | List invoices for child |
| POST | `/api/v1/invoices/` | Create invoice (with items) |
| PATCH | `/api/v1/invoices/{id}/` | Update invoice |
| DELETE | `/api/v1/invoices/{id}/` | Delete invoice |

### Purchases (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/children/{id}/purchases/` | List purchases |
| POST | `/api/v1/children/{id}/purchases/` | Add purchase |

---

## Git Workflow

### Working Locally
```bash
# Normal development on any branch
git checkout -b feature/my-feature
# ... make changes ...
git add .
git commit -m "feat: description"
git push -u origin feature/my-feature
```

### Deploying to Dev
```bash
# Merge to develop branch triggers dev deploy
git checkout develop
git merge feature/my-feature
git push origin develop
# → GitHub Action deploys to dev ECS cluster
```

### Deploying to Production
```bash
# Merge to main triggers production deploy
git checkout main
git merge develop
git push origin main
# → GitHub Action deploys to production ECS cluster
```

---

## Request/Response Format

All requests and responses use **camelCase** JSON.

### Login Example
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}'
```

Response:
```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": {
    "id": "uuid-string",
    "name": "John Doe",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

### Authenticated Request
```bash
curl http://localhost:8000/api/v1/centres/ \
  -H "Authorization: Bearer eyJ...access-token..."
```

---

## Project Structure

```
schindia_backend/
├── .env                    ← Environment config (DO NOT COMMIT)
├── .env.example            ← Template for .env
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── schindia_backend/       ← Django project settings
├── schindia_auth/          ← Auth: User model, login, signup, access requests
├── centres/                ← Centres & Rooms
├── sessions_app/           ← Sessions & Timetable slots
├── children/               ← Children, Contacts, Enrolments
├── progress/               ← Journey entries & Notes
├── billing/                ← Invoices & Purchases
├── roles/                  ← Roles, Permissions, Members
├── dynamo_backend/         ← DynamoDB service layer (for dev/prod)
│   ├── client.py           ← boto3 connection
│   ├── router.py           ← use_dynamo() switch
│   ├── service.py          ← Generic CRUD operations
│   ├── tables.py           ← Table name config
│   ├── setup_tables.py     ← Table creation script
│   └── services/           ← Domain-specific services
└── .github/workflows/      ← CI/CD pipeline
```
