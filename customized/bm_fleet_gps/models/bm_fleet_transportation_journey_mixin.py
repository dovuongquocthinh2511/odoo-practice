# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class TransportationJourneyMixin(models.AbstractModel):
    """Mixin for models that need to display transportation journey (GPS waypoints)

    This mixin provides a reusable action method to open transportation journey
    list view filtered by vehicle. Used by both fleet.vehicle and fleet.vehicle.log.services.
    """
    _name = 'bm.fleet.transportation.journey.mixin'
    _description = 'Transportation Journey Mixin'

    def _get_vehicle_for_journey(self):
        """Get the vehicle record for transportation journey display

        Override this method in implementing models to return the appropriate
        vehicle record.

        Returns:
            fleet.vehicle record or False if no vehicle
        """
        raise NotImplementedError(
            "Subclasses must implement _get_vehicle_for_journey() method"
        )

    def action_view_transportation_journeys(self):
        """Open transportation journeys (GPS waypoints) for the vehicle

        Generic action method that opens a list view of bm.fleet.transportation.journey
        records filtered by the vehicle returned from _get_vehicle_for_journey().

        Returns:
            dict: Action dictionary to open journey list view

        Raises:
            UserError: If no vehicle is assigned
        """
        self.ensure_one()
        vehicle = self._get_vehicle_for_journey()

        if not vehicle:
            raise UserError(_('Chưa có xe được điều cho bản ghi này'))

        return {
            'name': _('Hành trình - %s') % vehicle.name,
            'type': 'ir.actions.act_window',
            'res_model': 'bm.fleet.transportation.journey',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', vehicle.id)],
            'context': {
                'default_vehicle_id': vehicle.id,
                'search_default_vehicle_id': vehicle.id,
            }
        }
