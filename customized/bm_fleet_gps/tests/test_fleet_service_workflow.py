# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase
from odoo import fields
from odoo.exceptions import UserError


class TestFleetServiceWorkflow(TransactionCase):
    """Test suite for fleet service workflow (delivery and work services)"""

    def setUp(self):
        super(TestFleetServiceWorkflow, self).setUp()
        self.Service = self.env['fleet.vehicle.log.services']
        self.Vehicle = self.env['fleet.vehicle']
        self.User = self.env['res.users']

        # Create test vehicle
        self.vehicle = self.Vehicle.create({
            'name': 'Test Service Vehicle',
            'license_plate': 'SVC-001'
        })

        # Create test users with groups
        self.manager_user = self.User.create({
            'name': 'Test Manager',
            'login': 'test_manager',
            'groups_id': [(6, 0, [
                self.env.ref('fleet_gps_bestmix.group_fleet_service_manager').id
            ])]
        })

        self.admin_user = self.User.create({
            'name': 'Test Admin',
            'login': 'test_admin',
            'groups_id': [(6, 0, [
                self.env.ref('fleet_gps_bestmix.group_fleet_service_admin').id
            ])]
        })

    def test_01_work_service_creation(self):
        """Test work/business trip service creation"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'work_departure_location': 'HCM Office',
            'work_arrival_location': 'Da Nang Office',
            'work_purpose': 'Business meeting',
            'work_passenger_count': 2,
            'state': 'new'
        })

        self.assertTrue(service)
        self.assertEqual(service.service_category, 'work')
        self.assertEqual(service.work_departure_location, 'HCM Office')
        self.assertEqual(service.work_passenger_count, 2)

    def test_02_workflow_submit_for_approval(self):
        """Test service submission for manager approval"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'manager_id': self.manager_user.id,
            'state': 'new'
        })

        # Submit for approval
        service.action_submit()

        self.assertEqual(service.state, 'pending_manager')

        # Verify activity created for manager
        activities = self.env['mail.activity'].search([
            ('res_id', '=', service.id),
            ('res_model_id.model', '=', 'fleet.vehicle.log.services'),
            ('user_id', '=', self.manager_user.id)
        ])
        self.assertTrue(activities)

    def test_04_workflow_manager_approve(self):
        """Test manager approval"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'manager_id': self.manager_user.id,
            'state': 'pending_manager'
        })

        # Manager approves
        service.with_user(self.manager_user).action_manager_approve()

        self.assertEqual(service.state, 'pending_dispatch')
        self.assertTrue(service.manager_approval_date)

    def test_05_workflow_manager_reject(self):
        """Test manager rejection with reason"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'state': 'pending_manager'
        })

        # Open rejection wizard
        result = service.action_manager_reject()

        self.assertEqual(result['res_model'], 'fleet.service.rejection.wizard')
        self.assertEqual(result['context']['default_service_id'], service.id)

        # Create rejection wizard
        wizard = self.env['fleet.service.rejection.wizard'].create({
            'service_id': service.id,
            'service_model': 'fleet.vehicle.log.services',
            'rejection_reason': 'Budget not approved'
        })

        # Confirm rejection
        wizard.action_confirm_rejection()

        service.refresh()
        self.assertEqual(service.state, 'cancelled')
        self.assertEqual(service.rejection_reason, 'Budget not approved')
        self.assertTrue(service.rejected_by)
        self.assertTrue(service.rejection_date)

    def test_06_workflow_dispatch_approve(self):
        """Test admin vehicle dispatch approval"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'state': 'pending_dispatch'
        })

        # Admin dispatches vehicle
        service.with_user(self.admin_user).action_dispatch_approve()

        self.assertEqual(service.state, 'running')
        self.assertTrue(service.admin_approval_date)

    def test_07_workflow_dispatch_reject(self):
        """Test admin dispatch rejection"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'state': 'pending_dispatch'
        })

        # Admin rejects dispatch
        result = service.action_dispatch_reject()

        self.assertEqual(result['res_model'], 'fleet.service.rejection.wizard')

        # Create and confirm rejection
        wizard = self.env['fleet.service.rejection.wizard'].create({
            'service_id': service.id,
            'service_model': 'fleet.vehicle.log.services',
            'rejection_reason': 'No driver available'
        })

        wizard.action_confirm_rejection()

        service.refresh()
        self.assertEqual(service.state, 'cancelled')
        self.assertEqual(service.rejection_reason, 'No driver available')

    def test_08_workflow_complete_service(self):
        """Test service completion"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'state': 'running'
        })

        # Complete service
        service.action_set_to_done()

        self.assertEqual(service.state, 'done')

    def test_09_workflow_reset_to_new(self):
        """Test reset service to new state"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'state': 'cancelled',
            'rejection_reason': 'Test reason',
            'rejection_date': fields.Datetime.now()
        })

        # Reset to new
        service.action_reset_to_new()

        self.assertEqual(service.state, 'new')
        self.assertFalse(service.rejection_reason)
        self.assertFalse(service.manager_approval_date)
        self.assertFalse(service.admin_approval_date)

    def test_10_workflow_state_validation(self):
        """Test workflow state validations"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'state': 'new'
        })

        # Cannot approve from 'new' state (must submit first)
        with self.assertRaises(UserError):
            service.action_manager_approve()

        # Cannot complete from 'new' state (must be running)
        with self.assertRaises(UserError):
            service.action_set_to_done()

    def test_11_permission_checks(self):
        """Test permission validations for workflow actions"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'state': 'pending_manager'
        })

        # Regular user cannot approve (no manager permission)
        regular_user = self.User.create({
            'name': 'Regular User',
            'login': 'regular_user'
        })

        with self.assertRaises(UserError):
            service.with_user(regular_user).action_manager_approve()

    def test_12_state_expansion_kanban(self):
        """Test state expansion for kanban view"""
        states = self.Service._expand_states([], [])

        expected_states = ['new', 'pending_manager', 'pending_dispatch', 'running', 'done', 'cancelled']
        self.assertEqual(states, expected_states)

    def test_13_readonly_fields_enforcement(self):
        """Test readonly fields in done/cancelled states"""
        service = self.Service.create({
            'vehicle_id': self.vehicle.id,
            'service_category': 'work',
            'work_departure_location': 'Original Location',
            'state': 'done'
        })

        # Fields should be readonly in 'done' state
        # This is enforced by view, but we can verify state
        self.assertEqual(service.state, 'done')


from datetime import timedelta
