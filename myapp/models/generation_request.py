import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

from .enums import Occasion, Mood, Genre
from .user import User


class GenerationRequest(models.Model):
    """
    Captures the structured input parameters used to generate a music track
    via the AI engine (MusicGPT).

    Rules:
    - requestedDurationSeconds must be between 120 and 360 (SRS FR2.1)
    - Must belong to exactly one User
    - Enables "Regenerate" by re-submitting the same request parameters
    """
    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner  = models.ForeignKey(
        User,
        on_delete=models.CASCADE,       # if User deleted, requests are purged
        related_name='generation_requests'
    )
    occasion  = models.CharField(max_length=20, choices=Occasion.choices)
    mood      = models.CharField(max_length=20, choices=Mood.choices)
    genre     = models.CharField(max_length=20, choices=Genre.choices)
    requested_duration_seconds = models.IntegerField(
        validators=[
            MinValueValidator(120, message="Duration must be at least 120 seconds (2 minutes)."),
            MaxValueValidator(360, message="Duration must not exceed 360 seconds (6 minutes)."),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)

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
