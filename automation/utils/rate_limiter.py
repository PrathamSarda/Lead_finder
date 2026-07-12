import random
import time


DEFAULT_MIN_DELAY_SECONDS = 2.0
DEFAULT_MAX_DELAY_SECONDS = 5.0


def wait_between_requests(
    minimum_seconds: float = DEFAULT_MIN_DELAY_SECONDS,
    maximum_seconds: float = DEFAULT_MAX_DELAY_SECONDS,
) -> float:
    """
    Pause between requests to reduce load on external websites.

    Returns the delay duration so callers can log it.
    """

    if minimum_seconds < 0:
        raise ValueError("Minimum delay cannot be negative.")

    if maximum_seconds < minimum_seconds:
        raise ValueError(
            "Maximum delay must be greater than or equal to "
            "the minimum delay."
        )

    delay = random.uniform(
        minimum_seconds,
        maximum_seconds,
    )

    time.sleep(delay)

    return delay