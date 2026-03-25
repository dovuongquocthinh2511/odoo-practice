# Changelog

All notable changes to the BM Fleet GPS Tracking module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Address Geocoding Tracking**:
  - Added `is_address_synced` boolean field to `bm.fleet.transportation.journey` model
  - Tracks which waypoints have been processed for address geocoding
  - Prevents re-processing waypoints that have already been attempted
  - Indexed field for query performance optimization

### Changed
- **Geocoding Batch Limit Configuration**:
  - Made geocoding batch limit fully configurable via system parameter `bm_fleet_gps.geocoding_batch_limit`
  - Removed hardcoded `limit=100` from `fetch_missing_addresses()` method signature
  - Method now reads from system parameter when `limit=None` (default behavior)
  - Backward compatible: explicit limit values still work (e.g., `fetch_missing_addresses(limit=200)`)
  - Default system parameter value: 100 waypoints per run
  - Allows customization per environment (e.g., increase for development, decrease for API rate-limited environments)

- **Address Geocoding Logic Optimization**:
  - Search domain now filters by `is_address_synced != True` instead of `address = False`
  - Waypoints marked as synced after geocoding attempt (regardless of success/failure)
  - Improves efficiency by avoiding repeated failed geocoding attempts
  - Prevents infinite retry loops for waypoints with invalid coordinates or API failures

### Removed
- **Data Normalization - Journey Model Field Cleanup**:
  - Removed redundant `adsun_device_serial_number` field from `bm.fleet.transportation.journey` model
  - Field already stored in `fleet.vehicle` model and accessible via `journey.vehicle_id.adsun_device_serial_number`
  - Improves data integrity by maintaining single source of truth
  - Reduces storage overhead and eliminates potential data inconsistency
  - Migration script 18.0.8.1.1 automatically drops database column on upgrade

## [18.0.8.0.0] - 2025-10-15

### Major Refactoring Release

This release represents a comprehensive refactoring of the module codebase to improve maintainability, performance, security, and code quality.

### Added
- Created `bm.fleet.adsun.token` helper class for centralized token management
- Implemented `bm.fleet.geocoding.mixin` for reusable geocoding functionality
- Added incremental GPS sync cron job (`cron_sync_incremental`) for lightweight 5-minute updates
- Created unified `ir_config_parameter.xml` for all configuration parameters
- Added `read_group()` optimization for fuel consumption calculations

### Changed
- **Configuration Consolidation (Phase 1)**:
  - Merged `openmap_config.xml` into `ir_config_parameter.xml`
  - Unified all config parameters in single XML file

- **Token Management Simplification (Phase 2)**:
  - Replaced `fleet.gps.token` model with lightweight `bm.fleet.adsun.token` helper
  - Removed database table dependency for token storage
  - Migrated to `ir.config_parameter` for token persistence
  - Simplified token refresh logic

- **Model Renaming (Phase 5)**:
  - Renamed `fleet.geocoding.mixin` → `bm.fleet.geocoding.mixin`
  - Renamed `fleet.constraint.fixer` → `bm.fleet.constraint.fixer`
  - Renamed `fleet.user.booking.profile` → `bm.fleet.request.user`
  - Renamed `bm.fleet.department` → `bm.fleet.team`
  - Added `bm.` prefix to all custom models for namespace consistency

- **File Renaming (Phase 5)**:
  - `geocoding_mixin.py` → `bm_fleet_geocoding_mixin.py`
  - `fleet_constraint_fixer.py` → `bm_fleet_constraint_fixer.py`
  - `fleet_user_booking_profile.py` → `bm_fleet_request_user.py`
  - `bm_fleet_department.py` → `bm_fleet_team.py`
  - `fleet_gps_token.py` → `bm_adsun_token_helper.py`

### Removed
- **Redundant Database Fields (Phase 3)**:
  - Removed `current_speed`, `gps_status`, `machine_status` from `fleet.vehicle` model
  - Data now stored only in journey waypoints (`bm.fleet.transportation.journey`)
  - Removed migration script `0001_remove_redundant_vehicle_status.py` (legacy cleanup)

- **Duplicate Code Cleanup (Phase 6)**:
  - Removed `_sync_vehicle_gps_data()` wrapper method (38 lines)
  - Removed `action_sync_gps_now()` legacy compatibility method (3 lines)
  - Refactored `cron_sync_incremental()` to use underlying API methods directly
  - Updated XML views to use direct action methods

- **Legacy Models & Files**:
  - Deleted `fleet.gps.token` model and database table
  - Removed `openmap_config.xml` data file
  - Removed unused wrapper methods and compatibility layers

### Fixed
- **Cron Job Optimization (Phase 4)**:
  - Separated daily full sync (`cron_sync_gps_data`) from incremental sync (`cron_sync_incremental`)
  - Daily sync: Full day data (00:00:00 - 23:59:59)
  - Incremental sync: Last 5 minutes only (runs every 30 minutes)
  - Prevents API rate limiting and improves responsiveness

- **Performance Optimization (Phase 7)**:
  - Fixed N+1 query issue in `_compute_total_fuel_used()`
  - Replaced individual vehicle searches with single `read_group()` aggregation
  - Performance improvement: O(N) → O(1) database queries for fuel calculations
  - Already optimized: `_compute_running_stats()`, `_compute_last_stop_time()`, `_compute_transportation_journey_count()`

- **Security Fixes (Phase 8)**:
  - Removed hardcoded `SSL_VERIFY` constants
  - Implemented dynamic SSL verification via config parameter
  - All API calls now read from `bm_fleet_gps.ssl_verify` (defaults to `True`)
  - Secure by default: SSL verification enabled for production
  - Configurable per environment for development/testing needs

### Technical Improvements
- **Code Organization**:
  - Consistent `bm.` prefix for all custom models
  - Consistent `bm_` prefix for all Python files
  - Improved module namespace clarity
  - Better separation of concerns

- **Performance**:
  - Optimized computed field queries
  - Reduced database query count through batch operations
  - Improved cron job efficiency with incremental sync

- **Security**:
  - SSL verification enabled by default
  - Dynamic security configuration
  - Removed insecure development-only code patterns

- **Maintainability**:
  - Removed duplicate code
  - Simplified token management
  - Centralized configuration
  - Better code documentation

### Migration Notes
For upgrading from previous versions:

1. **Token System**: The old `fleet.gps.token` model has been replaced with `bm.fleet.adsun.token` helper. Tokens are now stored in `ir.config_parameter`. No manual migration needed - tokens will refresh automatically.

2. **Model Names**: Update any custom code referencing:
   - `fleet.geocoding.mixin` → `bm.fleet.geocoding.mixin`
   - `fleet.constraint.fixer` → `bm.fleet.constraint.fixer`
   - `fleet.user.booking.profile` → `bm.fleet.request.user`
   - `bm.fleet.department` → `bm.fleet.team`

3. **Removed Fields**: The following fields have been removed from `fleet.vehicle`:
   - `current_speed` - Use `transportation_journey_ids` waypoints
   - `gps_status` - Use `transportation_journey_ids` waypoints
   - `machine_status` - Use `transportation_journey_ids` waypoints

4. **Cron Jobs**: Two separate cron jobs now exist:
   - `cron_sync_gps_data` - Daily full sync (once per day)
   - `cron_sync_incremental` - Incremental sync (every 30 minutes)

5. **SSL Verification**: Check `bm_fleet_gps.ssl_verify` config parameter. Default is `True` (recommended for production).

### Testing Recommendations
After upgrading:
1. Test GPS sync functionality: Sync GPS Today button
2. Test Find GPS Serial button for vehicle assignment
3. Verify transportation journey tracking
4. Check fuel consumption calculations
5. Verify address geocoding functionality
6. Test service booking workflow
7. Validate cron job execution

---

## [18.0.7.0.0] - Previous Version

Previous release with service booking workflow and GPS tracking features.
