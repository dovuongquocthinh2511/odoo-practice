# -*- coding: utf-8 -*-
{
    'name': 'BM Fleet GPS Tracking',
    'version': '18.0.9.0.0',
    'category': 'Fleet',
    'summary': 'Real-time GPS tracking and fleet management with service booking workflow',
    'description': """
        Fleet GPS Tracking - BESTMIX Integration
        =======================================

        This module integrates BESTMIX GPS tracking system with Odoo Fleet Management:

        Features:
        ---------
        * Real-time vehicle location tracking
        * Direct API integration with ADSUN GPS (GetDeviceTripBySerial)
        * Transportation journey tracking with automatic sync
        * Automated API token management
        * Distance, speed, and running time statistics
        * Address geocoding (reverse lookup)
        * Branch/company vehicle assignment

        Service Management:
        -------------------
        * Delivery service management with approval workflow
        * Work/Business trip service management
        * Manager approval and admin vehicle dispatch workflow
        * Service states: New → Manager Approval → Dispatch → Running → Done
        * Rejection workflow with reason tracking
        * Kanban view for approval workflow visualization
        * Activity-based notifications for approvers
        * Address autocomplete with OpenMap.vn API integration
        * Address history tracking with usage statistics
        * Intelligent address suggestions based on usage frequency

        Technical:
        ----------
        * REST API integration with ADSUN GPS platform
        * Automated scheduled actions for data synchronization
        * Computed fields for statistics and analytics
        * Secure token management with auto-refresh
        * Mail tracking and activity management for approvals
        * OpenMap.vn API for Vietnam-specific address data
    """,
    'author': 'Bestmix',
    'website': 'https://www.bestmix.vn/',
    'license': 'LGPL-3',
    'depends': [
        'fleet',
        'base',
        'mail',
        'branch',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'py_files': [
        'models',
    ],
    'data': [
        # Security - Groups must load FIRST before rules and access rights
        'security/bm_fleet_gps_groups.xml',
        'security/fleet_service_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/fleet_service_type_data.xml',
        'data/fleet_service_sequence.xml',
        'data/ir_config_parameter.xml',
        'data/ir_cron_data.xml',

        # Views
        'views/res_config_settings_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/fleet_transportation_journey_views.xml',
        'views/fleet_journey_map_leaflet.xml',
        'views/fleet_service_rejection_wizard_views.xml',
        'views/fleet_service_booking_wizard_views.xml',
        'views/fleet_team_views.xml',
        'views/fleet_vehicle_log_services_views.xml',  # Load actions BEFORE menus reference them
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Leaflet CSS and JS (Local - OpenStreetMap)
            'bm_fleet_gps/static/src/lib/leaflet/leaflet.css',
            'bm_fleet_gps/static/src/lib/leaflet/leaflet.js',
            # Leaflet Routing Machine (Local - for road routing)
            'bm_fleet_gps/static/src/lib/leaflet/leaflet-routing-machine.css',
            'bm_fleet_gps/static/src/lib/leaflet/leaflet-routing-machine.js',
            # Journey Map Widget
            'bm_fleet_gps/static/src/css/journey_map.css',
            'bm_fleet_gps/static/src/js/journey_map_leaflet.js',
            'bm_fleet_gps/static/src/xml/journey_map_template.xml',
            # Address Autocomplete Widget
            'bm_fleet_gps/static/src/css/address_autocomplete.css',
            'bm_fleet_gps/static/src/js/address_autocomplete_widget.js',
            'bm_fleet_gps/static/src/xml/address_autocomplete_template.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,  # Not a standalone app - extends Fleet module
    'auto_install': False,
}
