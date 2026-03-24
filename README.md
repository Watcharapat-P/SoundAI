# SoundAI

## Quick start

1. create venv
   - `python -m venv .venv`
   - `# Windows` `.venv\Scripts\activate`
   - `# Mac/Linux` `source .venv/bin/activate`
2. install dependencies
   - `pip install -r requirements.txt`
3. apply migrations
   - `python manage.py migrate`
4. run server
   - `python manage.py runserver`
5. open browser at `http://127.0.0.1:8000/`

## API endpoints

- GET `/` — home template with route overview
- Users
  - GET `/users/`
  - POST `/users/`
  - GET `/users/<uuid>/`
  - PATCH `/users/<uuid>/`
  - DELETE `/users/<uuid>/`
- Generation Requests
  - GET `/requests/`
  - POST `/requests/`
  - GET `/requests/<uuid>/`
  - DELETE `/requests/<uuid>/`
- Tracks
  - GET `/tracks/`
  - POST `/tracks/`
  - GET `/tracks/<uuid>/`
  - PATCH `/tracks/<uuid>/`
  - DELETE `/tracks/<uuid>/`
- Share Links
  - GET `/share-links/`
  - POST `/share-links/`
  - GET `/share-links/<uuid>/`
  - DELETE `/share-links/<uuid>/`
  - POST `/share-links/<uuid>/revoke/`
  - GET `/s/<token>/` (public) 
