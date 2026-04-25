class SunoOfflineError(Exception):
    """Raised when the Suno API is unreachable."""
    pass


class SunoInsufficientCreditsError(Exception):
    """Raised when Suno API credits are exhausted."""
    pass
