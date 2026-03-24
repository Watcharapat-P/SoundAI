from django.db import models


class TrackStatus(models.TextChoices):
    PENDING   = 'pending',   'Pending'
    COMPLETED = 'completed', 'Completed'
    FAILED    = 'failed',    'Failed'


class Occasion(models.TextChoices):
    WEDDING     = 'wedding',     'Wedding'
    TEMPLE_FAIR = 'temple_fair', 'Temple Fair'
    GRADUATION  = 'graduation',  'Graduation'
    PARTY       = 'party',       'Party'


class Mood(models.TextChoices):
    HAPPY     = 'happy',     'Happy'
    SAD       = 'sad',       'Sad'
    ENERGETIC = 'energetic', 'Energetic'
    CALM      = 'calm',      'Calm'


class Genre(models.TextChoices):
    POP   = 'pop',   'Pop'
    ROCK  = 'rock',  'Rock'
    METAL = 'metal', 'Metal'
    JAZZ  = 'jazz',  'Jazz'
    LOFI  = 'lofi',  'Lo-fi'
