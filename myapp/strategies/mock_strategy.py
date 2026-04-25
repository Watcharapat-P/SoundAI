from .base import TrackGeneratorStrategy
from myapp.models.track import Track
from myapp.models.enums import TrackStatus


class MockTrackGeneratorStrategy(TrackGeneratorStrategy):
    """
    Offline strategy for development and testing.
    Produces a predictable Track with a real, publicly accessible MP3 URL.
    Does not call any external API.
    """

    PLACEHOLDER_AUDIO_URL = (
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    )
    PLACEHOLDER_DURATION_SECONDS = 229  # actual duration of the placeholder file

    def generate(self, generation_request) -> Track:
        # Idempotent: return existing track if already generated
        if hasattr(generation_request, "track"):
            return generation_request.track

        # Use the user's song_title if provided (SRS FR2.1), otherwise build one
        title = (
            generation_request.song_title
            or f"[Mock] {generation_request.occasion.capitalize()} "
               f"{generation_request.mood.capitalize()} "
               f"{generation_request.genre.upper()}"
        )

        track = Track.objects.create(
            owner=generation_request.owner,
            generation_request=generation_request,
            title=title,
            duration_seconds=self.PLACEHOLDER_DURATION_SECONDS,
            audio_url=self.PLACEHOLDER_AUDIO_URL,
            status=TrackStatus.COMPLETED,
        )

        print(
            f"[MockStrategy] Created track {track.id} "
            f"for request {generation_request.id}"
        )
        return track
