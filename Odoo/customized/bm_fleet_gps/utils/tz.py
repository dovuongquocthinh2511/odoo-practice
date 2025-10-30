# -*- coding: utf-8 -*-
"""
Timezone Conversion Utilities for ADSUN GPS API
================================================

Centralized timezone handling for converting ADSUN API timestamps
(Vietnam time) to UTC for Odoo database storage.
"""

from datetime import datetime
import pytz
import logging

_logger = logging.getLogger(__name__)

# Vietnam timezone constant
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


def adsun_time_to_utc(timestamp_str):
    """Convert ADSUN API timestamp (Vietnam time) to UTC

    ADSUN API returns timestamps in Vietnam time (UTC+7) without timezone info.
    This function converts them to UTC for Odoo database storage.

    Args:
        timestamp_str (str): ISO format timestamp from ADSUN API
                           Example: '2025-10-15T14:30:00'

    Returns:
        datetime: Naive UTC datetime for Odoo storage, or None if invalid

    Example:
        >>> adsun_time_to_utc('2025-10-15T14:30:00')
        datetime(2025, 10, 15, 7, 30, 0)  # UTC time (VN time - 7 hours)
    """
    if not timestamp_str:
        return None

    try:
        # Parse as naive datetime (API returns VN time without timezone)
        timestamp_vn = datetime.fromisoformat(timestamp_str)

        # Localize to Vietnam timezone
        timestamp_aware = VIETNAM_TZ.localize(timestamp_vn)

        # Convert to UTC
        timestamp_utc = timestamp_aware.astimezone(pytz.UTC)

        # Return as naive UTC (Odoo convention)
        return timestamp_utc.replace(tzinfo=None)

    except (ValueError, AttributeError) as e:
        _logger.warning(f"Failed to convert timestamp '{timestamp_str}': {e}")
        return None


def utc_to_vietnam_time(utc_datetime):
    """Convert UTC datetime to Vietnam time for ADSUN API requests

    ADSUN API expects datetime parameters in Vietnam time (UTC+7).
    This function converts UTC datetime to Vietnam time for API requests.

    Args:
        utc_datetime (datetime): Naive UTC datetime from Odoo (datetime object without timezone)
                                Example: datetime(2025, 10, 23, 0, 0, 0)

    Returns:
        datetime: Naive Vietnam time datetime for API, or None if invalid

    Example:
        >>> utc_to_vietnam_time(datetime(2025, 10, 23, 0, 0, 0))
        datetime(2025, 10, 23, 7, 0, 0)  # Vietnam time (UTC + 7 hours)
    """
    if not utc_datetime:
        return None

    try:
        # Treat input as UTC (Odoo stores all datetime in UTC)
        timestamp_utc = pytz.UTC.localize(utc_datetime)

        # Convert to Vietnam timezone
        timestamp_vn = timestamp_utc.astimezone(VIETNAM_TZ)

        # Return as naive datetime (for API string formatting)
        return timestamp_vn.replace(tzinfo=None)

    except (ValueError, AttributeError) as e:
        _logger.warning(f"Failed to convert UTC to Vietnam time '{utc_datetime}': {e}")
        return None
