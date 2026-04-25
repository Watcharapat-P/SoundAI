from myapp.strategies.factory import get_generator_strategy


def generate_track_from_request(generation_request):
    """
    Generate a Track for the given GenerationRequest using whichever
    strategy is currently active (controlled by GENERATOR_STRATEGY setting).

    Returns a Track instance (may be PENDING if Suno strategy is used).
    """
    strategy = get_generator_strategy()
    return strategy.generate(generation_request)
