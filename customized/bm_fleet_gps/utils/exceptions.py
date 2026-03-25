# -*- coding: utf-8 -*-

from odoo.exceptions import UserError


class AdsunRequestTokenException(UserError):
    """Exception raised when ADSUN API token request fails after retries

    This exception is raised when:
    - Token request fails after maximum retry attempts (3 times)
    - Authentication credentials are invalid
    - ADSUN Auth API is unreachable
    - API response doesn't contain a valid token

    Usage:
        raise AdsunRequestTokenException("Failed to obtain token after 3 retries")

    Note:
        This exception should NOT be retried by the retry decorator
        as it indicates a fundamental authentication or configuration problem.
    """
    pass
