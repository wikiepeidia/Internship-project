import time
import random

def polite_delay(min_seconds: float = 2.0, max_seconds: float = 5.0) -> None:
    """Polite scraping delay with randomized intervals."""
    time.sleep(random.uniform(min_seconds, max_seconds))
