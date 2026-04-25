from django.conf import settings

from .base import TrackGeneratorStrategy


def get_generator_strategy() -> TrackGeneratorStrategy:
    """
    Return the active TrackGeneratorStrategy based on the GENERATOR_STRATEGY
    Django setting (or environment variable).

    Values:
        "mock"  — MockTrackGeneratorStrategy  (default, offline)
        "suno"  — SunoTrackGeneratorStrategy  (live Suno API)

    Usage in settings.py or .env:
        GENERATOR_STRATEGY = "mock"   # or "suno"
    """
    strategy_name = getattr(settings, "GENERATOR_STRATEGY", "mock").lower()

    if strategy_name == "suno":
        from .suno_strategy import SunoTrackGeneratorStrategy
        return SunoTrackGeneratorStrategy()

    # Default: mock
    from .mock_strategy import MockTrackGeneratorStrategy
    return MockTrackGeneratorStrategy()
