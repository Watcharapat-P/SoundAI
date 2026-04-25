import uuid
import secrets
from django.db import models
from django.utils import timezone

from .track import Track


def _generate_token():
    """Cryptographically random, non-guessable token (SRS Security Rule)."""
    return secrets.token_urlsafe(32)


class ShareLink(models.Model):
    """
    Represents a unique, public, non-guessable link providing access to a
    specific track without requiring authentication.

    Rules:
    - Token must be cryptographically random (Security Rule)
    - Must reference exactly one valid Track (Orphan Link Prevention)
    - Deleted automatically when the Track is deleted (CASCADE)
    - isActive flag allows soft-revocation without deletion
    - expiresAt is optional; if set, the link becomes invalid after expiry
    """
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track    = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,       # Orphan Link Prevention
        related_name='share_links',
    )
    token    = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_token,        # Generate a secure token for the share link
    )
    expires_at = models.DateTimeField(
        null=True, blank=True,          # Optional expiry datetime; if null, the link never expires
    )
    is_active  = models.BooleanField(
        default=True,                   # Active by default; can be soft-revoked by setting to False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'share_link'
        ordering = ['-created_at']

    def __str__(self):
        status = "active" if self.is_valid() else "inactive"
        return f"ShareLink({self.token[:12]}…, {status}, track={self.track.title!r})"

    def is_valid(self) -> bool:
        """Returns True if the link is active and not yet expired."""
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def revoke(self):
        """Soft-revoke this share link."""
        self.is_active = False
        self.save(update_fields=['is_active'])
