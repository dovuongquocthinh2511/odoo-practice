# -*- coding: utf-8 -*-

import functools
import logging
import time
from .exceptions import AdsunRequestTokenException

_logger = logging.getLogger(__name__)


def retry(max_attempts=3, delay=1, backoff=2, exceptions=(Exception,), exclude_exceptions=()):
    """Retry decorator with exponential backoff

    Automatically retries a function if it raises specified exceptions,
    with exponential backoff between retry attempts.

    Args:
        max_attempts (int): Maximum number of retry attempts (default: 3)
        delay (float): Initial delay between retries in seconds (default: 1)
        backoff (float): Backoff multiplier for delay (default: 2)
        exceptions (tuple): Tuple of exceptions to catch and retry (default: Exception)
        exclude_exceptions (tuple): Tuple of exceptions to NOT retry (default: empty)

    Returns:
        Decorated function that retries on failure

    Example:
        @retry(max_attempts=3, delay=1, backoff=2,
               exceptions=(requests.RequestException,),
               exclude_exceptions=(AdsunRequestTokenException,))
        def _request_new_token(self):
            # If RequestException raised, retry up to 3 times (1s, 2s, 4s delays)
            # But if AdsunRequestTokenException raised, don't retry (raise immediately)
            pass

    Behavior:
        - Attempt 1: Execute function
        - If fails with retryable exception:
            - Wait `delay` seconds
            - Attempt 2: Execute function
            - If fails: Wait `delay * backoff` seconds
            - Attempt 3: Execute function
            - If fails: Raise exception
        - If fails with excluded exception: Raise immediately without retry
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)

                except exclude_exceptions as e:
                    # Don't retry these exceptions - raise immediately
                    _logger.error(f"{func.__name__} raised excluded exception: {e}")
                    raise

                except exceptions as e:
                    attempt += 1

                    if attempt >= max_attempts:
                        _logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    _logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {current_delay}s... Error: {e}"
                    )

                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper
    return decorator
