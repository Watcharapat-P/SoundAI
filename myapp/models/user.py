import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


class User(models.Model):
    """
    Represents an authenticated end user who generates, manages, and shares
    music tracks via Google OAuth.

    Rules:
    - googleId must be unique (prevents duplicate accounts for one Google identity)
    - totalStorageUsed tracks the 500 MB limit from the SRS
    """
    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    google_id          = models.CharField(max_length=255, unique=True)  # Unique Google ID for authentication
    email              = models.EmailField(unique=True)
    total_storage_used = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],  # Storage quota tracking (SRS: 500 MB limit)
        help_text="Total storage used in MB"
    )
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user'

    def __str__(self):
        return f"User({self.email})"

    def clean(self):
        if self.total_storage_used < 0:
            raise ValidationError("totalStorageUsed cannot be negative.")
