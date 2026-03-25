/** @odoo-module **/

import { Component, onMounted, onWillUnmount, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

/**
 * Fleet Journey Map Widget using Leaflet (OpenStreetMap)
 *
 * Features:
 * - Vehicle selection sidebar
 * - Journey path rendering from waypoints (fleet.transportation.journey)
 * - Animated vehicle movement along route
 * - Route deletion during playback
 * - Playback controls (play, pause, stop, speed)
 */
export class FleetJourneyMapWidget extends Component {
    /**
     * Validate services and throw descriptive error if not available
     */
    validateServices() {
        // RPC is now imported directly, no service validation needed
        if (!this.notification) {
            console.warn('⚠️ Notification service not available, using console fallback');
            // Fallback: create a simple notification method
            this.notification = {
                add: (message, options) => {
                    console.log(`🔔 ${options.type?.toUpperCase() || 'INFO'}: ${message}`);
                }
            };
        }
        if (!this.orm) {
            console.warn('⚠️ ORM service not available, some operations may be limited');
        }
        return true;
    }

    /**
     * Test ADSUN API connectivity
     */
    async testAdsunConnection() {
        console.log('🧪 Testing ADSUN API connectivity...');
        try {
            // Validate services are available before making RPC call
            this.validateServices();
            const response = await rpc('/fleet/gps/test-connection', {});
            console.log('🔍 Connection test result:', response);

            if (response.success) {
                this.notification.add(
                    `✅ ADSUN API connected successfully to ${response.api_url}`,
                    { type: 'success' }
                );
            } else {
                this.notification.add(
                    `❌ ADSUN API connection failed: ${response.error} (Stage: ${response.test_stage})`,
                    { type: 'danger' }
                );
            }

            return response;
        } catch (error) {
            console.error('💥 Connection test failed:', error);
            this.env.services.notification.add(
                `Connection test failed: ${error.message}`,
                { type: 'danger' }
            );
            return { success: false, error: error.message };
        }
    }

    setup() {
        // ✅ CORRECT - Use useService() hooks for available services only
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        // Note: RPC is imported directly, not injected as service

        // Extract vehicle filter from action context if provided (from smart button)
        const actionContext = this.props.action?.context || {};
        this.vehicleFilterId = actionContext.fleet_journey_vehicle_filter || null;

        // Extract date range from context (from booking smart button)
        this.contextDateFrom = actionContext.fleet_journey_date_from || null;
        this.contextDateTo = actionContext.fleet_journey_date_to || null;

        // Color palette for multiple vehicles
        this.vehicleColors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B195', '#C06C84',
            '#6C5CE7', '#00B894', '#FDCB6E', '#E17055', '#74B9FF',
            '#A29BFE', '#FD79A8', '#FFEAA7', '#DFE6E9', '#00CEC9'
        ];

        this.state = useState({
            vehicles: [],
            selectedVehicleId: null,
            selectedDate: this.getTodayString(),
            viewMode: 'single', // 'single' or 'all'
            allVehiclesData: [], // For multi-vehicle view
            // DateTime filter fields - use context dates if provided, else defaults
            filterStartDatetime: this.contextDateFrom ? this.formatDatetimeLocal(new Date(this.contextDateFrom)) : this.getDefaultStartDatetime(),
            filterEndDatetime: this.contextDateTo ? this.formatDatetimeLocal(new Date(this.contextDateTo)) : this.getDefaultEndDatetime(),
            map: null,
            journeyLayer: null,
            loading: false,
            mapTransforming: false, // Flag to track zoom/pan operations
            // Animation state
            isPlaying: false,
            isPaused: false,
            playbackSpeed: 1,
            currentWaypointIndex: 0,
            animationFrameId: null,
            vehicleMarker: null,
            routePolyline: null,
            traveledPathPolyline: null, // Đường đã đi (màu đỏ)
            currentWaypoints: [],
            currentDataSource: null, // Track if data is from 'database' or 'api'
            routedPathCache: [], // Cache for routed path coordinates
        });

        // Initialize component with proper lifecycle hook
        onWillStart(async () => {
            // Validate services and perform initial setup
            this.validateServices();
            console.log('🚀 Fleet Journey Map initialized with proper RPC service');
        });

        onMounted(async () => {
            await this.loadVehicles();
            this.initializeMap();

            // Make test method available in console for debugging
            window.testAdsunConnection = () => this.testAdsunConnection();
            console.log('🔧 Debug: testAdsunConnection() available in console');

            // If vehicle filter was provided (from smart button), auto-load its journey
            if (this.vehicleFilterId && this.state.selectedVehicleId) {
                // Wait for map initialization then load journey
                setTimeout(() => {
                    if (this.state.map) {
                        // If context has date range, use datetime filter; otherwise load all
                        if (this.contextDateFrom || this.contextDateTo) {
                            this.applyDatetimeFilter();
                        } else {
                            this.loadAndRenderJourney(this.state.selectedVehicleId);
                        }
                    }
                }, 500); // Small delay to ensure map is fully initialized
            }
        });

        onWillUnmount(() => {
            // Stop animation first
            this.stopAnimation();

            // Clear all layers before removing map
            if (this.state.journeyLayer) {
                try {
                    this.state.journeyLayer.clearLayers();
                } catch (error) {
                    console.warn('Error clearing journey layer:', error);
                }
            }

            // Remove map safely
            if (this.state.map) {
                try {
                    this.state.map.off(); // Remove all event listeners
                    this.state.map.remove();
                    this.state.map = null;
                } catch (error) {
                    console.warn('Error removing map:', error);
                }
            }
        });
    }

    /**
     * Get today's date as YYYY-MM-DD string
     */
    getTodayString() {
        const today = new Date();
        return today.toISOString().split('T')[0];
    }

    /**
     * Get default start datetime (today at 00:00)
     * Format: YYYY-MM-DDTHH:MM (for datetime-local input)
     */
    getDefaultStartDatetime() {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return this.formatDatetimeLocal(today);
    }

    /**
     * Get default end datetime (today at 23:59)
     * Format: YYYY-MM-DDTHH:MM (for datetime-local input)
     */
    getDefaultEndDatetime() {
        const today = new Date();
        today.setHours(23, 59, 0, 0);
        return this.formatDatetimeLocal(today);
    }

    /**
     * Format Date object to datetime-local input format (YYYY-MM-DDTHH:MM)
     */
    formatDatetimeLocal(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    }

  
    /**
     * Handle datetime filter change
     */
    onFilterDatetimeChange(type, value) {
        if (type === 'start') {
            this.state.filterStartDatetime = value;
        } else if (type === 'end') {
            this.state.filterEndDatetime = value;
        }
    }

    /**
     * Apply datetime filter - reload journey with selected datetime range
     */
    async applyDatetimeFilter() {
        if (!this.state.selectedVehicleId) {
            this.env.services.notification.add('Vui lòng chọn xe trước', { type: 'warning' });
            return;
        }

        if (!this.state.filterStartDatetime || !this.state.filterEndDatetime) {
            this.env.services.notification.add('Vui lòng chọn thời gian bắt đầu và kết thúc', { type: 'warning' });
            return;
        }

        // Parse datetime-local input directly as UTC for database queries
        // The datetime-local input values should be treated as UTC timestamps
        // since GPS data is stored in UTC in the database
        const startDate = new Date(this.state.filterStartDatetime);
        const endDate = new Date(this.state.filterEndDatetime);

        if (startDate >= endDate) {
            this.env.services.notification.add('Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc', { type: 'danger' });
            return;
        }

        // Use the datetime values directly for database queries (they're treated as UTC)
        await this.loadAndRenderJourneyWithDatetimeFilter(this.state.selectedVehicleId, startDate, endDate);
    }

    /**
     * Reset datetime filter to today's default
     */
    resetDatetimeFilter() {
        this.state.filterStartDatetime = this.getDefaultStartDatetime();
        this.state.filterEndDatetime = this.getDefaultEndDatetime();

        if (this.state.selectedVehicleId) {
            this.applyDatetimeFilter();
        }
    }

    /**
     * Initialize Leaflet map
     */
    initializeMap() {
        const mapContainer = document.getElementById('journey_map_container');
        if (!mapContainer) {
            console.error('Map container not found');
            this.env.services.notification.add('Lỗi khởi tạo bản đồ: không tìm thấy container', { type: 'danger' });
            return;
        }

        // Clear any existing map content
        mapContainer.innerHTML = '';

        if (typeof L === 'undefined') {
            console.error('Leaflet library not loaded. Retrying in 500ms...');
            setTimeout(() => this.initializeMap(), 500);
            return;
        }

        try {
            this.state.map = L.map('journey_map_container', {
                zoomAnimation: false,  // Disable zoom animation globally to prevent errors
                markerZoomAnimation: false,  // Disable marker zoom animation
            }).setView([16.0544, 108.2022], 6);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                maxZoom: 19,
            }).addTo(this.state.map);

            this.state.journeyLayer = L.layerGroup().addTo(this.state.map);

            // Add map event handlers to prevent errors during zoom/pan
            this.state.map.on('zoomstart movestart', () => {
                // Temporarily flag that map is transforming
                this.state.mapTransforming = true;
            });

            this.state.map.on('zoomend moveend', () => {
                // Map transformation complete
                this.state.mapTransforming = false;
            });

          } catch (error) {
            console.error('Error initializing map:', error);
            this.env.services.notification.add('Lỗi khởi tạo bản đồ', { type: 'danger' });
        }
    }

    /**
     * Load vehicles with GPS devices
     * Respects vehicle filter from context (when opened from smart button)
     */
    async loadVehicles() {
        try {
            this.state.loading = true;

            // Build domain based on vehicle filter from context
            let domain = [];
            if (this.vehicleFilterId) {
                // IMPORTANT: When opened from smart button, only show the filtered vehicle
                domain = [['id', '=', this.vehicleFilterId]];
              }
            // When opened from menu (no filter), domain stays empty to load all vehicles

            const vehicles = await this.orm.searchRead(
                "fleet.vehicle",
                domain,  // Apply domain filter
                ["id", "name", "license_plate", "adsun_device_serial_number"],
                { limit: 500, order: "name" }
            );

            this.state.vehicles = vehicles;

            // If single vehicle filter from context, auto-select it and load its journey
            if (this.vehicleFilterId && vehicles.length > 0) {
                this.state.selectedVehicleId = this.vehicleFilterId;
                // Will be loaded after map initialization in onMounted
            }

            this.renderVehicleList();

            const withGPS = vehicles.filter(v => v.adsun_device_serial_number).length;

            } catch (error) {
            console.error('Error loading vehicles:', error);
            this.env.services.notification.add('Lỗi tải danh sách xe', { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Render vehicle selection list
     */
    renderVehicleList() {
        const container = document.getElementById('vehicle_list_container');
        if (!container) {
            console.warn('Vehicle list container not found');
            return;
        }

        if (this.state.vehicles.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fa fa-info-circle"></i>
                    Không tìm thấy xe
                </div>
            `;
            return;
        }

        const html = this.state.vehicles.map(vehicle => {
            const hasGPS = vehicle.adsun_device_serial_number ? true : false;
            const gpsIcon = hasGPS
                ? '<i class="fa fa-signal text-success" title="Có GPS"></i>'
                : '<i class="fa fa-signal text-muted opacity-50" title="Chưa có GPS"></i>';

            return `
                <div class="vehicle-item p-2 mb-2 border rounded ${!hasGPS ? 'opacity-75' : ''}"
                     data-vehicle-id="${vehicle.id}"
                     style="cursor: pointer;">
                    <div class="d-flex align-items-center">
                        <i class="fa fa-car me-2 text-muted"></i>
                        <div class="flex-grow-1">
                            <div class="fw-bold">${vehicle.license_plate || vehicle.name}</div>
                            <small class="text-muted">${vehicle.name}</small>
                        </div>
                        ${gpsIcon}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;

        container.querySelectorAll('.vehicle-item').forEach(item => {
            const vehicleId = parseInt(item.dataset.vehicleId);

            // Auto-highlight if this is the selected vehicle from context filter
            if (vehicleId === this.state.selectedVehicleId) {
                item.classList.add('vehicle-selected');
            }

            item.addEventListener('click', (e) => {
                const clickedVehicleId = parseInt(e.currentTarget.dataset.vehicleId);
                this.selectVehicle(clickedVehicleId);
            });

            item.addEventListener('mouseenter', (e) => {
                e.currentTarget.style.backgroundColor = '#f8f9fa';
            });
            item.addEventListener('mouseleave', (e) => {
                if (parseInt(e.currentTarget.dataset.vehicleId) !== this.state.selectedVehicleId) {
                    e.currentTarget.style.backgroundColor = '';
                }
            });
        });
    }

    /**
     * Toggle between single vehicle and all vehicles view
     */
    async toggleViewMode() {
        if (this.state.viewMode === 'single') {
            // Switch to all vehicles mode
            this.state.viewMode = 'all';
            await this.showAllVehicles();
        } else {
            // Switch back to single vehicle mode
            this.state.viewMode = 'single';
            this.stopAnimation();
            if (this.state.journeyLayer) {
                this.state.journeyLayer.clearLayers();
            }
            this.env.services.notification.add('Đã chuyển sang chế độ xem từng xe', { type: 'info' });
        }
    }

    /**
     * Show all vehicles on map with realtime positions
     */
    async showAllVehicles() {
        try {
            this.state.loading = true;
            this.stopAnimation();

            if (this.state.journeyLayer) {
                this.state.journeyLayer.clearLayers();
            }

            // Use wider date range: last 7 days to ensure we get waypoints
            const endDate = new Date();
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - 7); // Last 7 days

            // Load all vehicles with GPS
            const vehicles = await this.orm.searchRead(
                "fleet.vehicle",
                [["adsun_device_serial_number", "!=", false]],
                ["id", "name", "license_plate", "current_latitude", "current_longitude"],
                { order: "name" }
            );

            if (vehicles.length === 0) {
                this.env.services.notification.add('Không có xe nào có GPS', { type: 'warning' });
                return;
            }

            const allVehiclesData = [];
            const allCoords = [];

            // Load latest waypoint for each vehicle
            for (let i = 0; i < vehicles.length; i++) {
                const vehicle = vehicles[i];
                const color = this.vehicleColors[i % this.vehicleColors.length];

                // Get latest waypoint for this vehicle (last 7 days)
                const waypoints = await this.orm.searchRead(
                    "bm.fleet.transportation.journey",
                    [
                        ["vehicle_id", "=", vehicle.id],
                        ["timestamp", ">=", startDate.toISOString()],
                        ["timestamp", "<=", endDate.toISOString()],
                        ["latitude", "!=", 0],
                        ["longitude", "!=", 0],
                    ],
                    ["latitude", "longitude", "timestamp", "speed", "machine_status", "address"],
                    { order: "timestamp desc", limit: 1 }
                );

                if (waypoints.length > 0) {
                    const latestWp = waypoints[0];
                    const position = [latestWp.latitude, latestWp.longitude];

                    // Create marker for this vehicle
                    const marker = L.marker(position, {
                        icon: this.createMarkerIcon(color, 'car'),
                        zIndexOffset: 1000 + i,
                        zoomAnimation: false,
                        bubblingMouseEvents: false,
                    }).addTo(this.state.journeyLayer);

                    // Add popup with vehicle info
                    const address = latestWp.address || `${latestWp.latitude.toFixed(6)}, ${latestWp.longitude.toFixed(6)}`;
                    marker.bindPopup(`
                        <div style="min-width: 200px;">
                            <h6 class="mb-2">
                                <i class="fa fa-car" style="color: ${color};"></i>
                                ${vehicle.license_plate || vehicle.name}
                            </h6>
                            <p class="mb-1"><strong>Tên xe:</strong> ${vehicle.name}</p>
                            <p class="mb-1"><strong>Thời gian:</strong> ${this.formatTime(latestWp.timestamp)}</p>
                            <p class="mb-1"><strong>Tốc độ:</strong> ${latestWp.speed} km/h</p>
                            <p class="mb-1"><strong>Máy nổ:</strong> ${latestWp.machine_status ? 'Bật' : 'Tắt'}</p>
                            <p class="mb-0"><strong>Địa chỉ:</strong> ${address}</p>
                        </div>
                    `);

                    allVehiclesData.push({
                        vehicle: vehicle,
                        marker: marker,
                        color: color,
                        latestWaypoint: latestWp
                    });

                    allCoords.push(position);
                }
            }

            this.state.allVehiclesData = allVehiclesData;

            // Fit map to show all vehicles
            if (allCoords.length > 0) {
                const bounds = L.latLngBounds(allCoords);
                this.state.map.fitBounds(bounds, { padding: [50, 50] });
            }

            this.env.services.notification.add(
                `Hiển thị ${allVehiclesData.length} xe trên bản đồ`,
                { type: 'success' }
            );

        } catch (error) {
            console.error('Error showing all vehicles:', error);
            this.env.services.notification.add('Lỗi hiển thị tất cả xe', { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Select vehicle and load journey
     */
    async selectVehicle(vehicleId) {
        // Validate vehicle exists and has GPS device
        const vehicle = this.state.vehicles.find(v => v.id === vehicleId);
        if (!vehicle) {
            this.env.services.notification.add('Không tìm thấy thông tin xe', { type: 'danger' });
            return;
        }

        if (!vehicle.adsun_device_serial_number) {
            this.env.services.notification.add(`Xe "${vehicle.name}" chưa được cấu hình thiết bị GPS`, { type: 'warning' });
            return;
        }

        // Switch to single vehicle mode if in all vehicles mode
        if (this.state.viewMode === 'all') {
            this.state.viewMode = 'single';
        }
        // Stop any ongoing animation
        this.stopAnimation();

        // Clear previous journey layers safely
        if (this.state.journeyLayer) {
            try {
                this.state.journeyLayer.clearLayers();
            } catch (error) {
                console.warn('Error clearing previous journey:', error);
            }
        }

        // Update UI
        document.querySelectorAll('.vehicle-item').forEach(item => {
            item.classList.remove('vehicle-selected');
            item.style.backgroundColor = '';
        });

        const selectedItem = document.querySelector(`[data-vehicle-id="${vehicleId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('vehicle-selected');
        }

        this.state.selectedVehicleId = vehicleId;

        // Load and render journey
        await this.loadAndRenderJourney(vehicleId);
    }

    /**
     * Load waypoints from ADSUN API and render journey on map
     */
    async loadAndRenderJourney(vehicleId) {
        if (!this.state.map) {
            this.env.services.notification.add('Bản đồ chưa sẵn sàng', { type: 'warning' });
            return;
        }

        try {
            this.state.loading = true;

            // Get vehicle information to find device serial number
            const vehicles = await this.orm.searchRead(
                "fleet.vehicle",
                [["id", "=", vehicleId]],
                ["id", "name", "license_plate", "adsun_device_serial_number"],
                { limit: 1 }
            );

            if (vehicles.length === 0 || !vehicles[0].adsun_device_serial_number) {
                this.env.services.notification.add(
                    'Xe này không có thiết bị GPS',
                    { type: 'warning' }
                );
                this.state.journeyLayer.clearLayers();
                return;
            }

            const vehicle = vehicles[0];
            const deviceSerial = vehicle.adsun_device_serial_number;

            // Prepare time range for ADSUN API
            const selectedDate = new Date(this.state.selectedDate);
            const startOfDay = new Date(selectedDate);
            startOfDay.setHours(0, 0, 0, 0);

            const endOfDay = new Date(selectedDate);
            endOfDay.setHours(23, 59, 59, 999);

            // Format times for ADSUN API (YYYY-MM-DD HH:MM:SS)
            const formatTimeForAPI = (date) => {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                const seconds = String(date.getSeconds()).padStart(2, '0');
                return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
            };

            const startTime = formatTimeForAPI(startOfDay);
            const endTime = formatTimeForAPI(endOfDay);

            // Call ADSUN API via RPC
            console.log('🚀 Calling ADSUN API with:', {
                vehicle_id: vehicleId,
                device_serial: deviceSerial,
                start_time: startTime,
                end_time: endTime
            });

            // Validate services are available before making RPC call
            this.validateServices();
            const response = await rpc('/fleet/gps/journey/history', {
                vehicle_id: vehicleId,
                device_serial: deviceSerial,
                start_time: startTime,
                end_time: endTime
            });

            console.log('📥 ADSUN API Response:', {
                success: response.success,
                error: response.error,
                waypoints_count: response.waypoints?.length || 0,
                full_response: response
            });

            if (!response.success) {
                const errorMsg = response.error || 'Unknown error';
                console.error('❌ ADSUN API Error:', errorMsg);
                this.env.services.notification.add(
                    `Lỗi tải dữ liệu từ ADSUN: ${errorMsg}`,
                    { type: 'danger' }
                );
                this.state.journeyLayer.clearLayers();
                return;
            }

            const waypoints = response.waypoints || [];
            const dataSource = response.source || 'api';

            if (waypoints.length === 0) {
                this.env.services.notification.add(
                    `Không có dữ liệu hành trình cho xe này vào ngày ${this.state.selectedDate}`,
                    { type: 'warning' }
                );
                this.state.journeyLayer.clearLayers();
                return;
            }

            // Store waypoints for animation
            this.state.currentWaypoints = waypoints;
            this.state.currentDataSource = dataSource;

            this.renderJourneyOnMap(waypoints);

            // Show notification with simple message
            this.env.services.notification.add(
                `✅ Đã tải ${waypoints.length} điểm GPS`,
                { type: 'success' }
            );

        } catch (error) {
            console.error('💥 Network/RPC Error loading journey from ADSUN API:', {
                error_message: error.message,
                error_stack: error.stack,
                error_name: error.name,
                error_data: error.data || 'No additional error data'
            });
            this.env.services.notification.add(`Lỗi tải dữ liệu hành trình từ ADSUN: ${error.message || 'Network error'}`, { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Load waypoints from ADSUN API with custom datetime filter and render journey on map
     */
    async loadAndRenderJourneyWithDatetimeFilter(vehicleId, startDate, endDate) {
        if (!this.state.map) {
            this.env.services.notification.add('Bản đồ chưa sẵn sàng', { type: 'warning' });
            return;
        }

        try {
            this.state.loading = true;

            // Get vehicle information to find device serial number
            const vehicles = await this.orm.searchRead(
                "fleet.vehicle",
                [["id", "=", vehicleId]],
                ["id", "name", "license_plate", "adsun_device_serial_number"],
                { limit: 1 }
            );

            if (vehicles.length === 0 || !vehicles[0].adsun_device_serial_number) {
                this.env.services.notification.add(
                    'Xe này không có thiết bị GPS',
                    { type: 'warning' }
                );
                this.state.journeyLayer.clearLayers();
                return;
            }

            const vehicle = vehicles[0];
            const deviceSerial = vehicle.adsun_device_serial_number;

            // Format times for ADSUN API (YYYY-MM-DD HH:MM:SS)
            const formatTimeForAPI = (date) => {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                const seconds = String(date.getSeconds()).padStart(2, '0');
                return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
            };

            const startTime = formatTimeForAPI(startDate);
            const endTime = formatTimeForAPI(endDate);

            // Call ADSUN API via RPC
            console.log('🚀 Calling ADSUN API with:', {
                vehicle_id: vehicleId,
                device_serial: deviceSerial,
                start_time: startTime,
                end_time: endTime
            });

            // Validate services are available before making RPC call
            this.validateServices();
            const response = await rpc('/fleet/gps/journey/history', {
                vehicle_id: vehicleId,
                device_serial: deviceSerial,
                start_time: startTime,
                end_time: endTime
            });

            console.log('📥 ADSUN API Response:', {
                success: response.success,
                error: response.error,
                waypoints_count: response.waypoints?.length || 0,
                full_response: response
            });

            if (!response.success) {
                const errorMsg = response.error || 'Unknown error';
                console.error('❌ ADSUN API Error:', errorMsg);
                this.env.services.notification.add(
                    `Lỗi tải dữ liệu từ ADSUN: ${errorMsg}`,
                    { type: 'danger' }
                );
                this.state.journeyLayer.clearLayers();
                return;
            }

            const waypoints = response.waypoints || [];

            if (waypoints.length === 0) {
                const startStr = this.formatDatetimeDisplay(startDate);
                const endStr = this.formatDatetimeDisplay(endDate);

                // Try to get latest location if no waypoints in range
                this.validateServices();
                const latestResponse = await rpc('/fleet/gps/journey/latest-position', {
                    vehicle_id: vehicleId,
                    device_serial: deviceSerial
                });

                if (latestResponse.success && latestResponse.waypoint) {
                    const location = latestResponse.waypoint;
                    const timestamp = location.timestamp;

                    this.env.services.notification.add(
                        `Không có dữ liệu hành trình từ ${startStr} đến ${endStr}. Hiển thị vị trí mới nhất: ${this.formatDatetimeDisplay(new Date(timestamp))}`,
                        { type: 'info' }
                    );

                    // Clear existing layers
                    this.state.journeyLayer.clearLayers();

                    // Show latest location marker
                    const marker = L.marker([location.latitude, location.longitude], {
                        icon: L.divIcon({
                            className: 'vehicle-marker-latest',
                            html: `<div style="background-color: #FF6B6B; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; display: flex; align-items: center; justify-content: center;"><i class="fa fa-car" style="color: white;"></i></div>`,
                            iconSize: [30, 30],
                            iconAnchor: [15, 15]
                        })
                    }).addTo(this.state.journeyLayer);

                    // Add popup with location info
                    marker.bindPopup(`
                        <b>Vị trí mới nhất</b><br/>
                        Thời gian: ${this.formatTime(timestamp)}<br/>
                        ${location.address || 'Không có địa chỉ'}<br/>
                        Tốc độ: ${location.speed || 0} km/h
                    `).openPopup();

                    // Center map on latest location
                    this.state.map.setView([location.latitude, location.longitude], 15);

                    return;
                } else {
                    this.env.services.notification.add(
                        `Không có dữ liệu GPS cho xe này`,
                        { type: 'warning' }
                    );
                    this.state.journeyLayer.clearLayers();
                    return;
                }
            }

            // Store waypoints for animation
            this.state.currentWaypoints = waypoints;
            this.state.currentDataSource = response.source || 'api';

            this.renderJourneyOnMap(waypoints);

            // Show notification with simple message
            this.env.services.notification.add(
                `✅ Đã tải ${waypoints.length} điểm GPS`,
                { type: 'success' }
            );

        } catch (error) {
            console.error('Error loading journey from ADSUN API with datetime filter:', error);
            this.env.services.notification.add('Lỗi tải dữ liệu hành trình từ ADSUN', { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Format datetime for display (DD/MM/YYYY HH:MM)
     */
    formatDatetimeDisplay(date) {
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${day}/${month}/${year} ${hours}:${minutes}`;
    }

    /**
     * Render journey path on map with markers
     */
    async renderJourneyOnMap(waypoints) {
        if (!this.state.journeyLayer) {
            console.error('Journey layer not initialized');
            return;
        }

        // Clear existing journey layer
        this.state.journeyLayer.clearLayers();

        if (waypoints.length === 0) return;

        // Use OSRM routing for road-based path (avoids going through buildings)
        // This creates a path that follows actual roads/streets
        const routedCoordinates = await this.getRoutedPath(waypoints);

        // Cache routed path for animation, fallback to direct waypoints if OSRM fails
        if (routedCoordinates.length > 0) {
            this.state.routedPathCache = routedCoordinates;
              } else {
            // Fallback: use direct waypoint connection
            this.state.routedPathCache = waypoints.map(wp => [wp.latitude, wp.longitude]);
                }

        // Draw journey path (blue line - route to be traveled / chưa đi)
        // Màu xanh dương đậm để phân biệt với đường đã đi
        this.state.routePolyline = L.polyline(this.state.routedPathCache, {
            color: '#0066ff',      // Xanh dương đậm cho tuyến đường sẽ đi
            weight: 3,             // Độ dày vừa phải để dễ nhìn (giảm từ 6 xuống 3)
            opacity: 0.7,          // Độ rõ hơn một chút
            dashArray: '8, 4',     // Đường gạch ngang mịn hơn
        }).addTo(this.state.journeyLayer);

        // Add start marker (green flag)
        const startPoint = waypoints[0];
        const startMarker = L.marker([startPoint.latitude, startPoint.longitude], {
            icon: this.createMarkerIcon('green', 'flag'),
            bubblingMouseEvents: false,  // Prevent event bubbling
            zoomAnimation: false,  // Disable zoom animation to prevent errors
        }).addTo(this.state.journeyLayer);

        // Async popup with address loading
        startMarker.on('click', async () => {
            const address = await this.getWaypointAddress(startPoint);
            startMarker.bindPopup(`
                <div style="min-width: 200px;">
                    <h6 class="mb-2"><i class="fa fa-flag-checkered text-success"></i> Điểm bắt đầu</h6>
                    <p class="mb-1"><strong>Thời gian:</strong> ${this.formatTime(startPoint.timestamp)}</p>
                    <p class="mb-1"><strong>Tọa độ:</strong> ${startPoint.latitude.toFixed(6)}, ${startPoint.longitude.toFixed(6)}</p>
                    <p class="mb-0"><strong>Địa chỉ:</strong> ${address}</p>
                </div>
            `).openPopup();
        });

        // Add end marker (red flag)
        const endPoint = waypoints[waypoints.length - 1];
        const endMarker = L.marker([endPoint.latitude, endPoint.longitude], {
            icon: this.createMarkerIcon('red', 'flag'),
            bubblingMouseEvents: false,  // Prevent event bubbling
            zoomAnimation: false,  // Disable zoom animation to prevent errors
        }).addTo(this.state.journeyLayer);

        // Async popup with address loading
        endMarker.on('click', async () => {
            const address = await this.getWaypointAddress(endPoint);
            endMarker.bindPopup(`
                <div style="min-width: 200px;">
                    <h6 class="mb-2"><i class="fa fa-flag text-danger"></i> Điểm kết thúc</h6>
                    <p class="mb-1"><strong>Thời gian:</strong> ${this.formatTime(endPoint.timestamp)}</p>
                    <p class="mb-1"><strong>Tốc độ:</strong> ${endPoint.speed} km/h</p>
                    <p class="mb-1"><strong>Tọa độ:</strong> ${endPoint.latitude.toFixed(6)}, ${endPoint.longitude.toFixed(6)}</p>
                    <p class="mb-0"><strong>Địa chỉ:</strong> ${address}</p>
                </div>
            `).openPopup();
        });

        // Add stop markers (blue)
        const stopPoints = waypoints.filter((wp, index) =>
            index > 0 &&
            index < waypoints.length - 1 &&
            !wp.machine_status
        );

        const maxStops = 20;
        const step = Math.ceil(stopPoints.length / maxStops);
        const sampledStops = stopPoints.filter((_, index) => index % step === 0);

        sampledStops.forEach(stop => {
            const stopMarker = L.marker([stop.latitude, stop.longitude], {
                icon: this.createMarkerIcon('blue', 'stop', 'small'),
                bubblingMouseEvents: false,  // Prevent event bubbling
                zoomAnimation: false,  // Disable zoom animation to prevent errors
            }).addTo(this.state.journeyLayer);

            // Async popup with address loading
            stopMarker.on('click', async () => {
                const address = await this.getWaypointAddress(stop);
                stopMarker.bindPopup(`
                    <div style="min-width: 180px;">
                        <h6 class="mb-2"><i class="fa fa-pause-circle text-primary"></i> Điểm dừng</h6>
                        <p class="mb-1"><strong>Thời gian:</strong> ${this.formatTime(stop.timestamp)}</p>
                        <p class="mb-1"><strong>Tọa độ:</strong> ${stop.latitude.toFixed(6)}, ${stop.longitude.toFixed(6)}</p>
                        <p class="mb-0"><strong>Địa chỉ:</strong> ${address}</p>
                    </div>
                `).openPopup();
            });
        });

        // Fit map to show all waypoints
        this.state.map.fitBounds(this.state.routePolyline.getBounds(), { padding: [50, 50] });

        }

    /**
     * Create custom marker icon
     */
    createMarkerIcon(color, type = 'car', size = 'normal') {
        let iconHtml;
        let fontSize, iconSize, anchor;

        if (size === 'small') {
            fontSize = '20px';
            iconSize = [20, 20];
            anchor = [10, 20];
        } else {
            fontSize = '28px';
            iconSize = [28, 28];
            anchor = [14, 28];
        }

        if (type === 'car') {
            // SVG xe hơi nhìn từ trên xuống - realistic top view (thân dài hơn)
            iconHtml = `
                <svg width="40" height="50" viewBox="0 0 40 50" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">
                    <!-- Bóng xe -->
                    <ellipse cx="20" cy="44" rx="16" ry="5" fill="rgba(0,0,0,0.2)" opacity="0.5"/>

                    <!-- Thân xe chính (dài hơn) -->
                    <rect x="10" y="6" width="20" height="36" rx="4" fill="${color}" stroke="#333" stroke-width="0.5"/>

                    <!-- Nóc xe (cabin) -->
                    <rect x="12" y="14" width="16" height="16" rx="2" fill="${color}" opacity="0.9"/>

                    <!-- Kính trước -->
                    <rect x="13" y="15" width="14" height="4" rx="1.5" fill="rgba(135,206,250,0.7)" stroke="rgba(255,255,255,0.5)" stroke-width="0.5"/>

                    <!-- Kính sau -->
                    <rect x="13" y="25" width="14" height="4" rx="1.5" fill="rgba(135,206,250,0.6)" stroke="rgba(255,255,255,0.4)" stroke-width="0.5"/>

                    <!-- Bánh xe trước trái -->
                    <rect x="7" y="12" width="4" height="8" rx="2" fill="#1a1a1a" stroke="#333" stroke-width="0.3"/>
                    <!-- Bánh xe trước phải -->
                    <rect x="29" y="12" width="4" height="8" rx="2" fill="#1a1a1a" stroke="#333" stroke-width="0.3"/>

                    <!-- Bánh xe sau trái -->
                    <rect x="7" y="30" width="4" height="8" rx="2" fill="#1a1a1a" stroke="#333" stroke-width="0.3"/>
                    <!-- Bánh xe sau phải -->
                    <rect x="29" y="30" width="4" height="8" rx="2" fill="#1a1a1a" stroke="#333" stroke-width="0.3"/>

                    <!-- Gương chiếu hậu trái -->
                    <rect x="6" y="20" width="2.5" height="3" rx="0.5" fill="${color}" opacity="0.8"/>
                    <!-- Gương chiếu hậu phải -->
                    <rect x="31.5" y="20" width="2.5" height="3" rx="0.5" fill="${color}" opacity="0.8"/>

                    <!-- Đèn pha -->
                    <circle cx="14" cy="7" r="1.2" fill="rgba(255,255,200,0.9)"/>
                    <circle cx="26" cy="7" r="1.2" fill="rgba(255,255,200,0.9)"/>

                    <!-- Đèn hậu -->
                    <circle cx="14" cy="41" r="1.2" fill="rgba(255,0,0,0.7)"/>
                    <circle cx="26" cy="41" r="1.2" fill="rgba(255,0,0,0.7)"/>

                    <!-- Highlight/shine effect -->
                    <ellipse cx="20" cy="20" rx="8" ry="4" fill="rgba(255,255,255,0.2)"/>
                </svg>
            `;
            iconSize = [40, 50];
            anchor = [20, 25];
        } else if (type === 'flag') {
            iconHtml = `<i class="fa fa-map-marker" style="color: ${color}; font-size: ${fontSize}; text-shadow: 0 0 3px white;"></i>`;
        } else if (type === 'stop') {
            iconHtml = `<i class="fa fa-circle" style="color: ${color}; font-size: ${fontSize}; text-shadow: 0 0 3px white;"></i>`;
        }

        return L.divIcon({
            className: 'custom-marker',
            html: iconHtml,
            iconSize: iconSize,
            iconAnchor: anchor,
            popupAnchor: [0, -anchor[1]],
        });
    }

    /**
     * Start animation playback
     */
    startAnimation() {
        if (this.state.currentWaypoints.length === 0 || this.state.routedPathCache.length === 0) {
            this.env.services.notification.add('Chưa có dữ liệu hành trình để phát', { type: 'warning' });
            return;
        }

        this.state.isPlaying = true;
        this.state.isPaused = false;
        this.state.currentWaypointIndex = 0;

        // Keep route polyline visible with reduced opacity during animation
        // Tuyến đường sẽ đi vẫn hiển thị mờ để biết hướng đi
        if (this.state.routePolyline) {
            this.state.routePolyline.setStyle({
                opacity: 0.25,          // Rất mờ để làm nền
                color: '#d0d0d0',       // Màu xám nhạt hơn
                weight: 2               // Mỏng hơn (giảm từ 4 xuống 2)
            });
        }

        // Initialize traveled path polyline (empty at start)
        // Màu xanh lá đậm cho tuyến đường đã đi
        this.state.traveledPathPolyline = L.polyline([], {
            color: '#00cc44',      // Xanh lá sáng cho tuyến đường đã đi
            weight: 4,             // Độ dày vừa phải (giảm từ 7 xuống 4)
            opacity: 0.85,         // Độ đậm vừa để dễ nhìn
            lineJoin: 'round',     // Bo góc mượt mà
            lineCap: 'round'       // Đầu đường bo tròn
        }).addTo(this.state.journeyLayer);

        // Create vehicle marker at start position
        // Màu cam nổi bật để dễ theo dõi xe đang di chuyển
        const startPos = this.state.routedPathCache[0];
        this.state.vehicleMarker = L.marker(startPos, {
            icon: this.createMarkerIcon('#ff6600', 'car'),  // Màu cam cho xe di chuyển
            zIndexOffset: 1000, // Keep vehicle on top
            zoomAnimation: false,  // Disable zoom animation to prevent errors
            bubblingMouseEvents: false,  // Prevent event bubbling
        }).addTo(this.state.journeyLayer);

        // Add vehicle marker popup
        this.state.vehicleMarker.bindPopup(`
            <div style="min-width: 150px;">
                <h6 class="mb-2">
                    <i class="fa fa-car text-warning"></i> Xe đang di chuyển
                </h6>
                <p class="mb-0"><small>Theo dõi vị trí xe trong hành trình</small></p>
            </div>
        `);

        // Start animation loop
        this.animateVehicle();

        this.env.services.notification.add('Bắt đầu phát hành trình', { type: 'info' });
    }

  
    /**
     * Animate vehicle movement
     */
    animateVehicle() {
        if (!this.state.isPlaying || this.state.isPaused) {
            return;
        }

        const routedPath = this.state.routedPathCache;
        const currentIndex = this.state.currentWaypointIndex;

        // CRITICAL FIX: Check if we've reached the end of available waypoints
        // Stop animation immediately when no more waypoints available
        if (!routedPath || routedPath.length === 0) {
            console.warn('No routed path available for animation');
            this.stopAnimation();
            this.env.services.notification.add('Không có tuyến đường để phát', { type: 'warning' });
            return;
        }

        if (currentIndex >= routedPath.length - 1) {
            // Reached the end - stop completely, don't loop or continue
            this.stopAnimation();
            this.env.services.notification.add('Hoàn thành hành trình - Đã đến điểm cuối', { type: 'success' });
                  return;
        }

        const nextIndex = currentIndex + 1;
        const currentPos = routedPath[currentIndex];
        const nextPos = routedPath[nextIndex];

        // Validate positions exist
        if (!currentPos || !nextPos) {
            console.warn('Invalid position data at index', currentIndex);
            this.stopAnimation();
            this.env.services.notification.add('Lỗi dữ liệu vị trí', { type: 'danger' });
            return;
        }

        // Calculate bearing for vehicle rotation
        const bearing = this.calculateBearing(
            currentPos[0], currentPos[1],
            nextPos[0], nextPos[1]
        );

        // Smooth transition using interpolation
        const steps = 10; // Fewer steps since routed path already has many points
        const stepDelay = 30 / this.state.playbackSpeed; // Faster base delay

        let step = 0;
        const interpolate = () => {
            if (!this.state.isPlaying || this.state.isPaused) {
                return;
            }

            step++;
            const progress = step / steps;

            const lat = currentPos[0] + (nextPos[0] - currentPos[0]) * progress;
            const lng = currentPos[1] + (nextPos[1] - currentPos[1]) * progress;

            // Update vehicle marker position with rotation - FIX: Check if marker and map still exist
            if (this.state.vehicleMarker && this.state.map && this.state.journeyLayer) {
                try {
                    // Skip marker updates during map transformations but keep animation running
                    if (!this.state.mapTransforming) {
                        // Only update marker when map is NOT transforming

                        // Verify marker is still on the map before updating
                        if (!this.state.journeyLayer.hasLayer(this.state.vehicleMarker)) {
                            console.warn('Vehicle marker no longer on map, stopping animation');
                            this.stopAnimation();
                            return;
                        }

                        this.state.vehicleMarker.setLatLng([lat, lng]);

                        // Rotate vehicle icon based on bearing
                        const iconElement = this.state.vehicleMarker.getElement();
                        if (iconElement) {
                            const svg = iconElement.querySelector('svg');
                            if (svg) {
                                // Apply rotation transform - vehicle rotates to face movement direction
                                svg.style.transform = `rotate(${bearing}deg)`;
                                svg.style.transition = 'transform 0.1s ease-out';
                            }
                        }
                    }
                    // If transforming, just skip the update but continue animation loop
                } catch (error) {
                    console.warn('Error updating vehicle position:', error);
                    this.stopAnimation();
                    return;
                }
            }

            // Update traveled path - add current position to the path
            // Also skip during map transformation to avoid errors
            if (this.state.traveledPathPolyline && !this.state.mapTransforming) {
                const traveledPath = this.state.traveledPathPolyline.getLatLngs();
                traveledPath.push([lat, lng]);
                this.state.traveledPathPolyline.setLatLngs(traveledPath);
            }

            // Always continue animation regardless of map transformation state
            if (step < steps) {
                this.state.animationFrameId = setTimeout(interpolate, stepDelay);
            } else {
                // Move to next point
                this.state.currentWaypointIndex = nextIndex;

                // CRITICAL: Before continuing, verify we haven't reached the end
                if (nextIndex >= routedPath.length - 1) {
                    // This is the last waypoint - complete animation
                    this.stopAnimation();
                    this.env.services.notification.add('Hoàn thành hành trình', { type: 'success' });
                    } else {
                    // Continue to next segment
                    this.state.animationFrameId = setTimeout(() => this.animateVehicle(), stepDelay);
                }
            }
        };

        interpolate();
    }

    /**
     * Pause animation
     */
    pauseAnimation() {
        this.state.isPaused = true;
        if (this.state.animationFrameId) {
            clearTimeout(this.state.animationFrameId);
            this.state.animationFrameId = null;
        }
        this.env.services.notification.add('Tạm dừng phát', { type: 'info' });
    }

    /**
     * Resume animation
     */
    resumeAnimation() {
        if (!this.state.isPlaying) return;

        this.state.isPaused = false;
        this.animateVehicle();
        this.env.services.notification.add('Tiếp tục phát', { type: 'info' });
    }

    /**
     * Stop animation and reset
     */
    stopAnimation() {
        this.state.isPlaying = false;
        this.state.isPaused = false;
        this.state.currentWaypointIndex = 0;

        if (this.state.animationFrameId) {
            clearTimeout(this.state.animationFrameId);
            this.state.animationFrameId = null;
        }

        // Remove vehicle marker - FIX: Check if marker exists and is on map
        if (this.state.vehicleMarker) {
            try {
                // Remove from map first to prevent Leaflet errors
                if (this.state.map && this.state.journeyLayer) {
                    this.state.journeyLayer.removeLayer(this.state.vehicleMarker);
                }
            } catch (error) {
                console.warn('Error removing vehicle marker:', error);
            } finally {
                this.state.vehicleMarker = null;
            }
        }

        // Remove traveled path polyline
        if (this.state.traveledPathPolyline) {
            try {
                if (this.state.map && this.state.journeyLayer) {
                    this.state.journeyLayer.removeLayer(this.state.traveledPathPolyline);
                }
            } catch (error) {
                console.warn('Error removing traveled path:', error);
            } finally {
                this.state.traveledPathPolyline = null;
            }
        }

        // Show route polyline again (restore original style)
        // Khôi phục lại tuyến đường sẽ đi với màu xanh dương
        if (this.state.routePolyline && this.state.map) {
            try {
                this.state.routePolyline.setStyle({
                    color: '#0066ff',
                    weight: 3,
                    opacity: 0.7,
                    dashArray: '8, 4'
                });
            } catch (error) {
                console.warn('Error restoring route style:', error);
            }
        }
    }

    /**
     * Change playback speed
     */
    setPlaybackSpeed(speed) {
        this.state.playbackSpeed = speed;
        this.env.services.notification.add(`Tốc độ phát: ${speed}x`, { type: 'info' });
    }

    /**
     * Calculate compass bearing between two GPS coordinates
     * Returns bearing in degrees (0-360) where 0° = North, 90° = East, 180° = South, 270° = West
     */
    calculateBearing(lat1, lng1, lat2, lng2) {
        // Convert to radians
        const φ1 = lat1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const Δλ = (lng2 - lng1) * Math.PI / 180;

        // Calculate bearing using the formula
        const y = Math.sin(Δλ) * Math.cos(φ2);
        const x = Math.cos(φ1) * Math.sin(φ2) -
                  Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);

        // Convert to degrees and normalize to 0-360
        const bearing = Math.atan2(y, x) * 180 / Math.PI;
        return (bearing + 360) % 360;
    }

    /**
     * Get routed path using OSRM (Open Source Routing Machine)
     * This ensures the path follows actual roads instead of straight lines
     * and prevents route from going through buildings
     */
    async getRoutedPath(waypoints) {
        if (waypoints.length < 2) return [];

        try {
            // OSRM supports up to 100 coordinates per request
            // Increase sampling to capture more route details
            const maxWaypoints = 100;
            let sampledWaypoints = waypoints;

            if (waypoints.length > maxWaypoints) {
                // Intelligent sampling: keep waypoints with significant direction changes
                sampledWaypoints = this.sampleWaypointsIntelligently(waypoints, maxWaypoints);
                console.log(`Intelligently sampled ${waypoints.length} waypoints down to ${sampledWaypoints.length} for OSRM routing`);
            }

            // Build OSRM coordinates string (lon,lat;lon,lat;...)
            const coordinates = sampledWaypoints
                .map(wp => `${wp.longitude},${wp.latitude}`)
                .join(';');

            // OSRM API endpoint with options for better road following
            const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${coordinates}?overview=full&geometries=geojson&continue_straight=false`;

            const response = await fetch(osrmUrl, { timeout: 10000 });

            if (!response.ok) {
                console.warn(`OSRM routing failed with status ${response.status}, using direct waypoint path`);
                return [];
            }

            const data = await response.json();

            if (data.code !== 'Ok' || !data.routes || data.routes.length === 0) {
                console.warn('OSRM returned no valid routes, using direct waypoint path');
                return [];
            }

            // Extract routed coordinates from GeoJSON
            const routeGeometry = data.routes[0].geometry.coordinates;

            // Convert from [lon, lat] to [lat, lon] for Leaflet
            const routedCoordinates = routeGeometry.map(coord => [coord[1], coord[0]]);

            console.log(`OSRM routed path: ${routedCoordinates.length} points following roads (from ${sampledWaypoints.length} waypoints)`);
            return routedCoordinates;

        } catch (error) {
            console.error('OSRM routing error:', error.message);
            return []; // Fallback to direct waypoint path
        }
    }

    /**
     * Intelligently sample waypoints to preserve route shape
     * Keeps waypoints with significant direction changes
     */
    sampleWaypointsIntelligently(waypoints, maxCount) {
        if (waypoints.length <= maxCount) return waypoints;

        const sampled = [waypoints[0]]; // Always keep start
        const step = Math.floor(waypoints.length / maxCount);

        for (let i = step; i < waypoints.length - 1; i += step) {
            sampled.push(waypoints[i]);
        }

        sampled.push(waypoints[waypoints.length - 1]); // Always keep end

        // Also include waypoints with significant speed changes (stops/starts)
        for (let i = 1; i < waypoints.length - 1; i++) {
            if (sampled.length >= maxCount) break;

            const prev = waypoints[i - 1];
            const curr = waypoints[i];
            const next = waypoints[i + 1];

            // Detect significant speed change (stop or start)
            const speedChange = Math.abs(curr.speed - prev.speed) + Math.abs(curr.speed - next.speed);
            if (speedChange > 20 && !sampled.includes(curr)) { // 20 km/h threshold
                sampled.push(curr);
            }
        }

        return sampled.sort((a, b) => waypoints.indexOf(a) - waypoints.indexOf(b));
    }

    /**
     * Reverse geocode coordinates to address using Nominatim
     * @param {number} lat - Latitude
     * @param {number} lng - Longitude
     * @returns {Promise<string>} Address or coordinates if failed
     */
    async reverseGeocode(lat, lng) {
        try {
            const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&addressdetails=1&accept-language=vi`;

            const response = await fetch(url, {
                headers: {
                    'User-Agent': 'Odoo Fleet GPS Module/1.0'
                }
            });

            if (!response.ok) {
                console.warn(`Geocoding failed for (${lat}, ${lng}): HTTP ${response.status}`);
                return `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            }

            const data = await response.json();

            if (data.error) {
                console.warn(`Geocoding error: ${data.error}`);
                return `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            }

            // Build address from components
            const addr = data.address || {};
            const parts = [];

            // Add road/street
            if (addr.road || addr.street) parts.push(addr.road || addr.street);

            // Add suburb/neighbourhood
            if (addr.suburb || addr.neighbourhood || addr.quarter) {
                parts.push(addr.suburb || addr.neighbourhood || addr.quarter);
            }

            // Add city/town
            if (addr.city || addr.town || addr.village) {
                parts.push(addr.city || addr.town || addr.village);
            }

            // Add state/province
            if (addr.state || addr.province) {
                parts.push(addr.state || addr.province);
            }

            if (parts.length > 0) {
                return parts.join(', ');
            }

            // Fallback to display_name
            return data.display_name || `${lat.toFixed(6)}, ${lng.toFixed(6)}`;

        } catch (error) {
            console.error('Reverse geocoding error:', error);
            return `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
        }
    }

    /**
     * Get or fetch address for waypoint
     * @param {Object} waypoint - Waypoint with latitude, longitude, and optional address
     * @returns {Promise<string>} Address string
     */
    async getWaypointAddress(waypoint) {
        // If address exists in database, use it
        if (waypoint.address && waypoint.address.trim()) {
            return waypoint.address;
        }

        // Otherwise, fetch from reverse geocoding
        return await this.reverseGeocode(waypoint.latitude, waypoint.longitude);
    }

    /**
     * Format timestamp for display
     *
     * ADSUN API returns properly formatted timestamps
     * No UTC conversion needed - API handles timezone correctly
     */
    formatTime(timestamp) {
        if (!timestamp) return '';

        // ADSUN API returns properly formatted datetime that can be parsed directly
        // No UTC conversion needed - ADSUN handles timezone correctly
        const date = new Date(timestamp);

        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');

        return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
    }

    // Event handler methods for template are already defined above with proper functionality

    toggleAnimation() {
        if (this.state.isPaused) {
            this.resumeAnimation();
        } else {
            this.pauseAnimation();
        }
    }

    // Event handler method for template - setPlaybackSpeed is already properly implemented above
}

FleetJourneyMapWidget.template = "bm_fleet_gps.JourneyMapTemplate";

// Register as a client action
registry.category("actions").add("fleet_journey_map_action", FleetJourneyMapWidget);
