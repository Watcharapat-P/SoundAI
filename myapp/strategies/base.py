from abc import ABC, abstractmethod


class TrackGeneratorStrategy(ABC):
    @abstractmethod
    def generate(self, generation_request) -> "Track":
        """
        Generate a track from a GenerationRequest instance.
        Returns a saved Track object.
        """
        pass
