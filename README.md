
**Student ID:** 6710545881  
**Project:** SoundAI 


## Domain Entities Implemented

| Model | Domain Role |
|---|---|
| `User` | Authenticated creator (Google OAuth identity) with storage tracking |
| `GenerationRequest` | Structured AI parameters (Occasion, Mood, Genre, Duration) |
| `Track` | Generated MP3 file with status lifecycle |
| `ShareLink` | Public, non-guessable share token for anonymous track access |

### Enumerations
- **TrackStatus**: `pending`, `completed`, `failed`
- **Occasion**: `wedding`, `temple_fair`, `graduation`, `party`
- **Mood**: `happy`, `sad`, `energetic`, `calm`
- **Genre**: `pop`, `rock`, `metal`, `jazz`, `lofi`

---

## Project Structure

Separation of concerns applied to models and views (one file per class). Admin is kept in a single `admin.py` as all admin classes are tightly related and co-located for clarity.

```
SOUNDAI/
├── manage.py
├── requirements.txt
├── db.sqlite3
├── .gitignore
├── README.md
├── venv/

├── soundai/                    # Django project config
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py

└── myapp/                      # Django app (NOT "domain")
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── tests.py
    ├── urls.py

    ├── models/                 # Split models
    │   ├── __init__.py
    │   ├── enums.py
    │   ├── user.py
    │   ├── generation_request.py
    │   ├── track.py
    │   └── share_link.py

    ├── views/                  # Split views
    │   ├── __init__.py
    │   ├── helpers.py
    │   ├── user_views.py
    │   ├── generation_request_views.py
    │   ├── track_views.py
    │   └── share_link_views.py

    ├── templates/
    │   ├── base.html
    │   └── home.html

    ├── migrations/
    │   └── __init__.py
    │   └── 0001_initial.py
```
---

## Setup Instructions

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd SoundAI
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply migrations
```bash
python manage.py migrate
```

### 5. Create a superuser (for Django Admin)
```bash
python manage.py createsuperuser
```

### 6. Run the development server
```bash
python manage.py runserver
```

---

## CRUD Evidence

### Option A — Django Admin (recommended for screenshots)
Visit `http://127.0.0.1:8000/admin/` and log in with your superuser.  
All four domain entities are fully registered with list views, search, filters, and inline relationships.

### Option B — JSON API endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/api/users/` | List / create users |
| GET/PATCH/DELETE | `/api/users/<id>/` | Retrieve / update / delete user |
| GET/POST | `/api/requests/` | List / create generation requests |
| GET/DELETE | `/api/requests/<id>/` | Retrieve / delete request |
| GET/POST | `/api/tracks/` | List / create tracks |
| GET/PATCH/DELETE | `/api/tracks/<id>/` | Retrieve / update / delete track |
| GET/POST | `/api/share-links/` | List / create share links |
| GET/DELETE | `/api/share-links/<id>/` | Retrieve / delete share link |
| POST | `/api/share-links/<id>/revoke/` | Soft-revoke a share link |
| GET | `/api/s/<token>/` | Public track access (no auth) |

This is the Postman Agent SoundAI API Guidelines
https://www.postman.com/test3858/workspace/soundai/collection/47929779-a843ebf5-f614-49a3-a121-b377950544af?action=share&creator=47929779&active-environment=47929779-3d2e51f9-fad1-4930-a06b-72ad19353da5

**Example — create a user:**
```bash
curl -X POST http://127.0.0.1:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"google_id": "google_abc123", "email": "alice@example.com"}'
```

**Example — create a generation request:**
```bash
curl -X POST http://127.0.0.1:8000/api/requests/ \
  -H "Content-Type: application/json" \
  -d '{
    "owner_id": "<user-uuid>",
    "occasion": "wedding",
    "mood": "happy",
    "genre": "pop",
    "requested_duration_seconds": 180
  }'
```

---

## Business Rules Enforced

| Rule | Where Enforced |
|------|---------------|
| `googleId` must be unique per user | `unique=True` on `User.google_id` |
| Duration must be 120–360 s (SRS FR2.1) | `MinValueValidator(120)` + `MaxValueValidator(360)` on `GenerationRequest` |
| Track duration within ±5 s of requested (NFR 5.4.1) | `Track.clean()` validation |
| Track deleted when User deleted (Composition) | `ForeignKey(on_delete=CASCADE)` |
| ShareLinks deleted when Track deleted (Orphan Prevention) | `ForeignKey(on_delete=CASCADE)` on `ShareLink.track` |
| Token must be cryptographically random | `secrets.token_urlsafe(32)` default |
| Each Track results from exactly one GenerationRequest | `OneToOneField` on `Track.generation_request` |
| Track owner must match GenerationRequest owner | Checked in `views.py` + `Track.ownership_matches_request()` |

---

## Deviations from Domain Model

| Deviation | Justification |
|-----------|--------------|
| `User` inherits from `models.Model` (not Django's `AbstractUser`) | Auth is out of scope (Exercise 3 constraint); Google OAuth would be added in a later exercise |
| `User.id` is UUID (domain model shows `int userId`) | UUID is safer for public-facing IDs and aligns with the domain model's description of UUID type for other entities |

---
