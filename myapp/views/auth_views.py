"""
Google OAuth 2.0 authentication views.

Implements the Authorization Code flow:
  1. /login/                  - render the login page
  2. /auth/google/            - redirect user to Google's consent screen
  3. /auth/google/callback/   - exchange code for tokens, fetch user info,
                                create/update User record, store session
  4. /logout/                 - clear session
"""
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from myapp.models import User


# Google OAuth 2.0 endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _is_google_configured() -> bool:
    """OAuth is only usable if both client id and secret are set."""
    return bool(settings.GOOGLE_CLIENT_ID) and bool(settings.GOOGLE_CLIENT_SECRET)


@require_http_methods(["GET"])
def login_view(request):
    """Render the login page with the 'Sign in with Google' button."""
    # Already logged in? send them home.
    if request.session.get('user_id'):
        return redirect('home')

    return render(request, 'login.html', {
        'google_configured': _is_google_configured(),
    })


@require_http_methods(["GET"])
def google_login(request):
    """Build the Google authorization URL and redirect."""
    if not _is_google_configured():
        messages.error(
            request,
            "Google OAuth is not configured. Please set GOOGLE_CLIENT_ID "
            "and GOOGLE_CLIENT_SECRET in your .env file."
        )
        return redirect('login')

    # CSRF protection: random state stored in session
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state

    redirect_uri = request.build_absolute_uri(reverse('google-callback'))

    # Debug: log the exact redirect URI we're sending. If Google returns
    # `redirect_uri_mismatch`, this string must be registered EXACTLY (including
    # trailing slash) under "Authorized redirect URIs" in Google Cloud Console.
    print(f"[OAuth] Sending redirect_uri to Google: {redirect_uri}")

    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@require_http_methods(["GET"])
def google_callback(request):
    """
    Handle Google's redirect after the user authenticates:
      - validate state
      - exchange code for tokens
      - fetch user profile
      - create or update local User
      - store user_id in session
    """
    if not _is_google_configured():
        messages.error(request, "Google OAuth is not configured.")
        return redirect('login')

    # Surface OAuth errors from Google
    if request.GET.get('error'):
        messages.error(request, f"Google sign-in failed: {request.GET.get('error')}")
        return redirect('login')

    # CSRF state validation
    state = request.GET.get('state')
    expected_state = request.session.pop('oauth_state', None)
    if not state or state != expected_state:
        messages.error(request, "Invalid OAuth state. Please try signing in again.")
        return redirect('login')

    code = request.GET.get('code')
    if not code:
        messages.error(request, "No authorization code returned by Google.")
        return redirect('login')

    redirect_uri = request.build_absolute_uri(reverse('google-callback'))

    # Step 1: exchange code for tokens
    try:
        token_response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                'code': code,
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            },
            timeout=10,
        )
        token_response.raise_for_status()
        tokens = token_response.json()
    except requests.RequestException as exc:
        messages.error(request, f"Failed to exchange code for token: {exc}")
        return redirect('login')

    access_token = tokens.get('access_token')
    if not access_token:
        messages.error(request, "Google did not return an access token.")
        return redirect('login')

    # Step 2: fetch user profile
    try:
        userinfo_response = requests.get(
            GOOGLE_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
    except requests.RequestException as exc:
        messages.error(request, f"Failed to fetch user info from Google: {exc}")
        return redirect('login')

    google_id = userinfo.get('sub')
    email = userinfo.get('email')
    name = userinfo.get('name', '')
    picture = userinfo.get('picture', '')

    if not google_id or not email:
        messages.error(request, "Google account is missing required fields.")
        return redirect('login')

    # Step 3: create or update local user.
    # `google_id` is the canonical lookup; email may change over time.
    user, created = User.objects.get_or_create(
        google_id=google_id,
        defaults={'email': email},
    )
    if not created and user.email != email:
        user.email = email
        user.save(update_fields=['email'])

    # Step 4: persist session
    request.session['user_id'] = str(user.id)
    request.session['user_email'] = user.email
    request.session['user_name'] = name
    request.session['user_picture'] = picture

    messages.success(request, f"Welcome, {name or email}! 🎵")
    return redirect('home')


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Clear the user's session."""
    request.session.flush()
    messages.success(request, "You have been signed out.")
    return redirect('login')
