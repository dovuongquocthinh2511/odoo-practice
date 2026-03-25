# -*- coding: utf-8 -*-

from odoo import _


def show_notification(title, message, notification_type='warning', sticky=True):
    """Show notification to user

    Args:
        title: Notification title
        message: Notification message
        notification_type: Type of notification ('success', 'warning', 'danger', 'info')
        sticky: Whether notification should stay until user dismisses it

    Returns:
        dict: Notification action dictionary
    """
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': _(title),
            'message': _(message),
            'type': notification_type,
            'sticky': sticky,
        }
    }


def show_validation_error(missing_fields):
    """Show validation error for missing required fields

    Args:
        missing_fields: List of missing field display names

    Returns:
        dict: Notification action dictionary
    """
    return show_notification(
        title='Trường không hợp lệ',
        message=f'{_("Vui lòng nhập đầy đủ")}: {", ".join(missing_fields)}',
        notification_type='warning',
        sticky=True
    )
