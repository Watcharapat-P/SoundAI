"""
Template context processors.
Exposes the currently signed-in user (from session) and an `is_admin` flag
to every template.
"""
from django.conf import settings


def _email_is_admin(email: str) -> bool:
    if not email:
        return False
    return email.strip().lower() in getattr(settings, "ADMIN_EMAILS", [])


def current_user(request):
    """
    Inject the currently signed-in user info, admin flag, and the public
    SITE_URL into all templates.

    Returns:
        current_user: dict with id/email/name/picture, or None if anonymous
        is_admin:     True if current user's email is in settings.ADMIN_EMAILS
        site_url:     base URL (no trailing slash) for building absolute links
    """
    site_url = getattr(settings, "SITE_URL", "").rstrip('/')
    user_id = request.session.get('user_id')
    if not user_id:
        return {
            'current_user': None,
            'is_admin': False,
            'site_url': site_url,
        }

    email = request.session.get('user_email', '')
    return {
        'current_user': {
            'id': user_id,
            'email': email,
            'name': request.session.get('user_name', ''),
            'picture': request.session.get('user_picture', ''),
        },
        'is_admin': _email_is_admin(email),
        'site_url': site_url,
    }
