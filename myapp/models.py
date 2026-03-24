import uuid
import secrets
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


# Enumerations

class TrackStatus(models.TextChoices):
    PENDING   = 'pending',   'Pending'
    COMPLETED = 'completed', 'Completed'
    FAILED    = 'failed',    'Failed'


class Occasion(models.TextChoices):
    WEDDING    = 'wedding',    'Wedding'
    TEMPLE_FAIR = 'temple_fair', 'Temple Fair'
    GRADUATION = 'graduation', 'Graduation'
    PARTY      = 'party',      'Party'


class Mood(models.TextChoices):
    HAPPY     = 'happy',     'Happy'
    SAD       = 'sad',       'Sad'
    ENERGETIC = 'energetic', 'Energetic'
    CALM      = 'calm',      'Calm'


class Genre(models.TextChoices):
    POP  = 'pop',  'Pop'
    ROCK = 'rock', 'Rock'
    METAL = 'metal', 'Metal'
    JAZZ = 'jazz', 'Jazz'
    LOFI = 'lofi', 'Lo-fi'


# User Entity

class User(models.Model):
    """
    Rules:
    - googleId must be unique (prevents duplicate accounts for one Google identity)
    - totalStorageUsed tracks the 500 MB limit from the SRS
    """
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # UUID primary key
    google_id      = models.CharField(max_length=255, unique=True) # Unique Google ID for authentication
    email          = models.EmailField(unique=True)
    total_storage_used = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)], # Storage quota tracking (SRS: 500 MB limit)
        help_text="Total storage used in MB"
    )
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user'

    def __str__(self):
        return f"User({self.email})"

    def clean(self):
        if self.total_storage_used < 0:
            raise ValidationError("totalStorageUsed cannot be negative.")


# GenerationRequest Entity

class GenerationRequest(models.Model):
    """
    Rules:
    - requestedDurationSeconds must be between 120 and 360 (SRS FR2.1)
    - Must belong to exactly one User
    - Enables "Regenerate" by re-submitting the same request parameters
    """
    id                       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # UUID primary key
    owner                    = models.ForeignKey(
        User,
        on_delete=models.CASCADE,   # if User deleted, requests are purged
        related_name='generation_requests'
    )
    occasion                 = models.CharField(max_length=20, choices=Occasion.choices)
    mood                     = models.CharField(max_length=20, choices=Mood.choices)
    genre                    = models.CharField(max_length=20, choices=Genre.choices)
    requested_duration_seconds = models.IntegerField(
        validators=[
            MinValueValidator(120, message="Duration must be at least 120 seconds (2 minutes)."), # Duration constraint 
            MaxValueValidator(360, message="Duration must not exceed 360 seconds (6 minutes)."), # Duration constraint 
        ]
    )
    created_at               = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'generation_request'
        ordering = ['-created_at']

    def __str__(self):
        return (f"GenerationRequest({self.occasion}/{self.mood}/{self.genre} "
                f"@ {self.requested_duration_seconds}s by {self.owner.email})")

    def clean(self):
        if not (120 <= self.requested_duration_seconds <= 360):
            raise ValidationError(
                "requested_duration_seconds must be between 120 and 360 (SRS FR2.1)."
            )


# Track Entity

class Track(models.Model):
    """
    Rules:
    - Must be owned by exactly one User
    - Must result from exactly one GenerationRequest (1-to-1 with request)
    - durationSeconds must be within ±5 seconds of the requested duration (NFR 5.4.1)
    - audioUrl stores the S3 bucket path
    """
    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) # UUID primary key
    owner              = models.ForeignKey(
        User,
        on_delete=models.CASCADE,   # if User deleted, tracks are purged
        related_name='tracks'
    )
    generation_request = models.OneToOneField( 
        GenerationRequest,
        on_delete=models.CASCADE, # if GenerationRequest deleted, track is purged (enforces 1-to-1 relationship)
        related_name='track', 
    )
    title              = models.CharField(max_length=255)
    duration_seconds   = models.IntegerField(
        validators=[MinValueValidator(1)], # Duration must be positive
    )
    audio_url          = models.CharField(
        max_length=1024, # S3 URL
    )
    status             = models.CharField(
        max_length=20,
        choices=TrackStatus.choices, # Track status for processing state: pending, completed, or failed
        default=TrackStatus.PENDING,
    )
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'track'
        ordering = ['-created_at']

    def __str__(self):
        return f"Track({self.title!r}, {self.status}, {self.duration_seconds}s)"

    def clean(self):
        """
        Validates the ±5 second accuracy tolerance (NFR 5.4.1) once the
        track is linked to a generation request.
        """
        if self.generation_request_id:
            requested = self.generation_request.requested_duration_seconds
            if abs(self.duration_seconds - requested) > 5:
                raise ValidationError(
                    f"Track duration ({self.duration_seconds}s) deviates more than ±5 seconds "
                    f"from requested duration ({requested}s). (NFR 5.4.1)"
                )

    def ownership_matches_request(self):
        """Domain invariant: track owner must match generation request owner."""
        return self.owner_id == self.generation_request.owner_id


# ShareLink Entity

def _generate_token():
    """Cryptographically random, non-guessable token (SRS Security Rule)."""
    return secrets.token_urlsafe(32)


class ShareLink(models.Model):
    """
    Rules:
    - Token must be cryptographically random (Security Rule)
    - Must reference exactly one valid Track (Orphan Link Prevention)
    - Deleted automatically when the Track is deleted (CASCADE)
    - isActive flag allows soft-revocation without deletion
    - expiresAt is optional; if set, the link becomes invalid after expiry
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track      = models.ForeignKey(
        Track, # Link to the Track being shared 
        on_delete=models.CASCADE,   # Orphan Link Prevention
        related_name='share_links',
    )
    token      = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_token, # Generate a secure token for the share link
    )
    expires_at = models.DateTimeField(
        null=True, blank=True, # Optional expiry datetime; if null, the link never expires
    )
    is_active  = models.BooleanField(
        default=True, # Active by default; can be soft-revoked by setting to False
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
