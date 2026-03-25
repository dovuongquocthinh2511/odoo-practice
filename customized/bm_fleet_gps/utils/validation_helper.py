# -*- coding: utf-8 -*-

from odoo import _
from odoo.exceptions import UserError


def validate_required_fields(record, field_map):
    """Validate required fields and return list of missing field names

    Args:
        record: Odoo record/model instance to validate
        field_map: dict mapping field names to display names
                   Example: {'field_name': 'Display Name', ...}

    Returns:
        list: List of missing field display names (empty if all valid)
    """
    missing_fields = []
    for field_name, display_name in field_map.items():
        if not record[field_name]:
            missing_fields.append(display_name)
    return missing_fields


def validate_state(record, expected_state, error_message=None):
    """Validate record is in expected state

    Generic state validation helper to reduce duplication across action methods.

    Args:
        record: Odoo record/model instance with state field
        expected_state: Expected state value (str)
        error_message: Custom error message (optional). If not provided,
                      uses default message format.

    Raises:
        UserError: If record is not in expected state

    Example:
        validate_state(record, 'pending_manager',
                      'Can only approve when in Manager Approval state')
    """
    if record.state != expected_state:
        if error_message:
            raise UserError(_(error_message))
        else:
            raise UserError(
                _('Cannot perform action: record must be in "%s" state') % expected_state
            )
