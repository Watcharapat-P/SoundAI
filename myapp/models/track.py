import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

from .enums import TrackStatus
from .user import User
from .generation_request import GenerationRequest


class Track(models.Model):
    """
    Represents a generated music file stored in the system and owned by a user.

    Rules:
    - Must be owned by exactly one User
    - Must result from exactly one GenerationRequest (1-to-1 with request)
    - durationSeconds must be within ±5 seconds of the requested duration (NFR 5.4.1)
    - audioUrl stores the S3 bucket path
    """
    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner              = models.ForeignKey(
        User,
        on_delete=models.CASCADE,       # if User deleted, tracks are purged
        related_name='tracks'
    )
    generation_request = models.OneToOneField(
        GenerationRequest,
        on_delete=models.CASCADE,       # if GenerationRequest deleted, track is purged
        related_name='track',
    )
    title            = models.CharField(max_length=255)
    duration_seconds = models.IntegerField(
        validators=[MinValueValidator(1)],   # Duration must be positive
    )
    audio_url        = models.CharField(max_length=1024)    # S3 URL
    status           = models.CharField(
        max_length=20,
        choices=TrackStatus.choices,    # Track status for processing state: pending, completed, or failed
        default=TrackStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'track'
        ordering = ['-created_at']

    def __str__(self):
        return f"Track({self.title!r}, {self.status}, {self.duration_seconds}s)"

    def clean(self):
        """Validates the ±5 second accuracy tolerance (NFR 5.4.1)."""
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
