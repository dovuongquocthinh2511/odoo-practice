/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { useRef, onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Address Autocomplete Widget using OpenStreetMap Nominatim API
 *
 * Usage in XML:
 * <field name="work_location" widget="address_autocomplete"/>
 */
export class AddressAutocompleteField extends CharField {
    static template = "bm_fleet_gps.AddressAutocompleteField";

    setup() {
        super.setup();
        this.inputRef = useRef("input");
        this.dropdownRef = useRef("dropdown");
        this.searchTimeout = null;
        this.suggestions = [];
        this.selectedIndex = -1;

        onMounted(() => {
            this.setupAutocomplete();
        });

        onWillUnmount(() => {
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }
        });
    }

    setupAutocomplete() {
        const input = this.inputRef.el;
        if (!input) return;

        // Input event - trigger search
        input.addEventListener('input', (e) => this.onInput(e));

        // Keyboard navigation
        input.addEventListener('keydown', (e) => this.onKeyDown(e));

        // Click outside to close dropdown
        document.addEventListener('click', (e) => this.onClickOutside(e));
    }

    onInput(event) {
        const query = event.target.value;

        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        // Hide dropdown if query is too short
        if (query.length < 3) {
            this.hideDropdown();
            return;
        }

        // Debounce search - wait 300ms after user stops typing
        this.searchTimeout = setTimeout(() => {
            this.searchAddress(query);
        }, 300);
    }

    async searchAddress(query) {
        try {
            // First, search address history for previously used addresses
            const historySuggestions = await this.searchAddressHistory(query);

            // Then, search OpenMap.vn API via backend proxy (secure)
            const openMapSuggestions = await this.searchOpenMapAutocomplete(query);

            // Convert history format to unified format
            const historyFormatted = historySuggestions.map(item => ({
                display_name: item.name,
                lat: item.latitude,
                lon: item.longitude,
                source: 'history',
                usage_count: item.usage_count
            }));

            // Convert OpenMap format to unified format (no coordinates yet - will fetch on selection)
            const openMapFormatted = openMapSuggestions.map(item => ({
                display_name: item.display_name,
                place_id: item.id,  // Store place_id for later coordinate lookup
                lat: null,  // Will be fetched when selected
                lon: null,
                source: 'openmap'
            }));

            // Combine: history first, then OpenMap (avoiding duplicates)
            const historyNames = new Set(historyFormatted.map(h => h.display_name.toLowerCase()));
            const openMapFiltered = openMapFormatted.filter(item =>
                !historyNames.has(item.display_name.toLowerCase())
            );

            this.suggestions = [...historyFormatted, ...openMapFiltered];
            this.selectedIndex = -1;
            this.showDropdown();

        } catch (error) {
            console.error('Address autocomplete error:', error);
            this.hideDropdown();
        }
    }

    async searchOpenMapAutocomplete(query) {
        try {
            console.log('[OpenMap] Searching via backend proxy:', query);

            let result;

            if (this.props.record?.model?.orm) {
                result = await this.props.record.model.orm.call(
                    'bm.fleet.address.history',
                    'search_openmap_autocomplete',
                    [query, 5]
                );
            } else if (this.env.services?.rpc) {
                result = await this.env.services.rpc('/web/dataset/call_kw', {
                    model: 'bm.fleet.address.history',
                    method: 'search_openmap_autocomplete',
                    args: [query, 5],
                    kwargs: {}
                });
            } else {
                console.warn('[OpenMap] No RPC mechanism available');
                return [];
            }

            console.log('[OpenMap] Found suggestions:', result);
            return result || [];
        } catch (error) {
            console.error('[OpenMap] Search error:', error);
            return [];
        }
    }

    async getOpenMapPlaceDetail(placeId) {
        try {
            console.log('[OpenMap] Fetching place detail for:', placeId);

            let result;

            if (this.props.record?.model?.orm) {
                result = await this.props.record.model.orm.call(
                    'bm.fleet.address.history',
                    'get_openmap_place_detail',
                    [placeId]
                );
            } else if (this.env.services?.rpc) {
                result = await this.env.services.rpc('/web/dataset/call_kw', {
                    model: 'bm.fleet.address.history',
                    method: 'get_openmap_place_detail',
                    args: [placeId],
                    kwargs: {}
                });
            } else {
                console.warn('[OpenMap] No RPC mechanism available');
                return false;
            }

            console.log('[OpenMap] Place detail:', result);
            return result;
        } catch (error) {
            console.error('[OpenMap] Place detail error:', error);
            return false;
        }
    }

    async searchAddressHistory(query) {
        try {
            console.log('[Address History] Searching for:', query);

            // Use ORM service from record model (standard pattern for field widgets in Odoo 18)
            let result;

            if (this.props.record && this.props.record.model && this.props.record.model.orm) {
                // Primary method: Use ORM from record model
                result = await this.props.record.model.orm.call(
                    'bm.fleet.address.history',
                    'search_address_suggestions',
                    [query, 5]
                );
            } else if (this.env.services && this.env.services.rpc) {
                // Fallback: Use RPC service if available
                result = await this.env.services.rpc('/web/dataset/call_kw', {
                    model: 'bm.fleet.address.history',
                    method: 'search_address_suggestions',
                    args: [query, 5],
                    kwargs: {}
                });
            } else {
                console.warn('[Address History] No RPC mechanism available');
                return [];
            }

            console.log('[Address History] Found suggestions:', result);
            return result || [];
        } catch (error) {
            console.error('[Address History] Search error:', error);
            return [];
        }
    }

    onKeyDown(event) {
        const dropdown = this.dropdownRef.el;
        if (!dropdown || !dropdown.classList.contains('show')) return;

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, this.suggestions.length - 1);
                this.highlightSuggestion();
                break;

            case 'ArrowUp':
                event.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.highlightSuggestion();
                break;

            case 'Enter':
                event.preventDefault();
                if (this.selectedIndex >= 0) {
                    this.selectSuggestion(this.suggestions[this.selectedIndex]);
                }
                break;

            case 'Escape':
                this.hideDropdown();
                break;
        }
    }

    highlightSuggestion() {
        const dropdown = this.dropdownRef.el;
        if (!dropdown) return;

        const items = dropdown.querySelectorAll('.autocomplete-item');
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }

    async selectSuggestion(suggestion) {
        if (!suggestion) return;

        console.log(`[Address Widget] Selecting suggestion for field ${this.props.name}:`, suggestion.display_name);

        // Set the display_name as the value
        const input = this.inputRef.el;
        if (input) {
            input.value = suggestion.display_name;
        }

        // Update the address field in Odoo model
        this.props.record.update({ [this.props.name]: suggestion.display_name });

        // If this is an OpenMap suggestion without coordinates, fetch them now
        if (suggestion.source === 'openmap' && suggestion.place_id && (!suggestion.lat || !suggestion.lon)) {
            console.log('[OpenMap] Fetching coordinates for selected place...');
            const placeDetail = await this.getOpenMapPlaceDetail(suggestion.place_id);

            if (placeDetail) {
                suggestion.lat = placeDetail.latitude;
                suggestion.lon = placeDetail.longitude;
                // Update display_name if more detailed
                if (placeDetail.display_name) {
                    console.log('[OpenMap] Updating with detailed address:', placeDetail.display_name);
                    suggestion.display_name = placeDetail.display_name;
                    // Update both UI and model with detailed address
                    if (input) {
                        input.value = placeDetail.display_name;
                    }
                    this.props.record.update({ [this.props.name]: placeDetail.display_name });
                }
            }
        }

        // Update latitude and longitude fields if coordinates are available
        if (suggestion.lat && suggestion.lon) {
            // Smart field name mapping - handles both work_location and work_departure_location
            let latField, lonField;

            if (this.props.name === 'work_departure_location') {
                latField = 'work_departure_latitude';
                lonField = 'work_departure_longitude';
            } else if (this.props.name === 'work_location') {
                latField = 'work_location_latitude';
                lonField = 'work_location_longitude';
            } else {
                // Fallback: try to infer from field name pattern
                latField = this.props.name.replace(/_location$/, '_latitude');
                lonField = this.props.name.replace(/_location$/, '_longitude');
            }

            // Check if these fields exist in the record and update them
            if (latField in this.props.record.data) {
                this.props.record.update({ [latField]: parseFloat(suggestion.lat) });
                console.log(`[Address Widget] Updated ${latField} = ${suggestion.lat}`);
            }
            if (lonField in this.props.record.data) {
                this.props.record.update({ [lonField]: parseFloat(suggestion.lon) });
                console.log(`[Address Widget] Updated ${lonField} = ${suggestion.lon}`);
            }
        }

        this.hideDropdown();
    }

    showDropdown() {
        const dropdown = this.dropdownRef.el;
        if (dropdown && this.suggestions.length > 0) {
            dropdown.classList.add('show');
            this.renderSuggestions();
        }
    }

    hideDropdown() {
        const dropdown = this.dropdownRef.el;
        if (dropdown) {
            dropdown.classList.remove('show');
        }
        this.suggestions = [];
        this.selectedIndex = -1;
    }

    renderSuggestions() {
        const dropdown = this.dropdownRef.el;
        if (!dropdown) return;

        dropdown.innerHTML = '';

        this.suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';

            // Add visual indicator for history suggestions
            if (suggestion.source === 'history') {
                item.classList.add('from-history');
                const icon = document.createElement('span');
                icon.className = 'history-icon';
                icon.innerHTML = '★ '; // Star icon for history
                icon.title = `Đã sử dụng ${suggestion.usage_count} lần`;
                item.appendChild(icon);
            }

            const text = document.createElement('span');
            text.textContent = suggestion.display_name;
            item.appendChild(text);

            // Click handler
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectSuggestion(suggestion);
            });

            // Hover handler
            item.addEventListener('mouseenter', () => {
                this.selectedIndex = index;
                this.highlightSuggestion();
            });

            dropdown.appendChild(item);
        });
    }

    onClickOutside(event) {
        const dropdown = this.dropdownRef.el;
        const input = this.inputRef.el;

        if (dropdown && input) {
            if (!dropdown.contains(event.target) && !input.contains(event.target)) {
                this.hideDropdown();
            }
        }
    }
}

// Register the widget
registry.category("fields").add("address_autocomplete", {
    component: AddressAutocompleteField,
});
