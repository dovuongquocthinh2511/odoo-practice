# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import fields


def get_day_range(date=None):
    """Get start and end datetime for a full day (00:00:00 to 23:59:59)

    Args:
        date: Date to get range for (defaults to today)
              Can be datetime.date, datetime.datetime, or string 'YYYY-MM-DD'

    Returns:
        tuple: (start_datetime, end_datetime) covering the full day

    Example:
        >>> start, end = get_day_range(datetime.date(2024, 1, 15))
        >>> # Returns (2024-01-15 00:00:00, 2024-01-15 23:59:59.999999)
    """
    if date is None:
        date = fields.Date.today()
    elif isinstance(date, datetime):
        date = date.date()
    elif isinstance(date, str):
        date = fields.Date.from_string(date)

    return (
        datetime.combine(date, datetime.min.time()),
        datetime.combine(date, datetime.max.time())
    )


def get_week_start(date=None):
    """Get start of week for given date (Monday as week start)

    Args:
        date: Reference date (defaults to today)
              Can be datetime.date, datetime.datetime, or string 'YYYY-MM-DD'

    Returns:
        datetime.date: Monday of the week containing the date

    Example:
        >>> get_week_start(datetime.date(2024, 1, 17))  # Wednesday
        >>> # Returns datetime.date(2024, 1, 15)  # Previous Monday
    """
    if date is None:
        date = fields.Date.today()
    elif isinstance(date, datetime):
        date = date.date()
    elif isinstance(date, str):
        date = fields.Date.from_string(date)

    return date - timedelta(days=date.weekday())


def get_week_range(date=None):
    """Get start and end datetime for the week containing the date

    Week is defined as Monday 00:00:00 to the reference date 23:59:59.
    This is useful for "week to date" calculations.

    Args:
        date: Reference date (defaults to today)
              Can be datetime.date, datetime.datetime, or string 'YYYY-MM-DD'

    Returns:
        tuple: (week_start_datetime, current_date_end_datetime)

    Example:
        >>> start, end = get_week_range(datetime.date(2024, 1, 17))  # Wednesday
        >>> # Returns (2024-01-15 00:00:00, 2024-01-17 23:59:59.999999)
        >>> # Monday start to Wednesday end
    """
    if date is None:
        date = fields.Date.today()
    elif isinstance(date, datetime):
        date = date.date()
    elif isinstance(date, str):
        date = fields.Date.from_string(date)

    week_start = get_week_start(date)
    return (
        datetime.combine(week_start, datetime.min.time()),
        datetime.combine(date, datetime.max.time())
    )
