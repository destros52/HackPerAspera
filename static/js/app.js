// Zurich Women Safety App - Main JavaScript

class SafetyApp {
    constructor() {
        this.map = null;
        this.userLocation = null;
        this.safetyMarkers = [];
        this.currentRoute = null;
        this.nightMode = false;
        this.routeLayer = null;
        this.nightOverlays = [];
        
        // Zurich police stations (matching backend data)
        this.police_stations = [
            {lat: 47.3769, lng: 8.5417, name: 'Stadtpolizei Zurich HQ'},
            {lat: 47.3667, lng: 8.5500, name: 'Polizeiposten Enge'},
            {lat: 47.3900, lng: 8.5167, name: 'Polizeiposten Oerlikon'},
            {lat: 47.3583, lng: 8.5392, name: 'Polizeiposten Wiedikon'},
            {lat: 47.4108, lng: 8.5444, name: 'Polizeiposten Schwamendingen'}
        ];
        
        this.init();
    }
    
    init() {
        this.initMap();
        this.bindEvents();
        this.requestLocation();
        this.initChat();
    }
    
    initMap() {
        // Initialize Leaflet map centered on Zurich
        this.map = L.map('map').setView([47.3769, 8.5417], 13);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
        
        // Add click handler for safety analysis
        this.map.on('click', (e) => {
            this.analyzeSafetyAtLocation(e.latlng.lat, e.latlng.lng);
        });
    }
    
    bindEvents() {
        // Emergency button
        document.getElementById('emergency-btn').addEventListener('click', () => {
            this.showEmergencyModal();
        });
        
        // Location button
        document.getElementById('location-btn').addEventListener('click', () => {
            this.requestLocation();
        });
        
        // Route planner
        document.getElementById('route-planner-btn').addEventListener('click', () => {
            this.showRouteModal();
        });
        
        // Safety layer toggle
        document.getElementById('safety-layer-btn').addEventListener('click', () => {
            this.toggleNightMode();
        });
        
        // Chat toggle
        document.getElementById('chat-toggle').addEventListener('click', () => {
            this.toggleChat();
        });
        
        // Chat send
        document.getElementById('send-btn').addEventListener('click', () => {
            this.sendChatMessage();
        });
        
        // Chat input enter key
        document.getElementById('chat-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendChatMessage();
            }
        });
        
        // Modal close buttons
        document.querySelectorAll('.close-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.closeModal(e.target.closest('.modal'));
            });
        });
        
        // Route calculation
        document.getElementById('calculate-route').addEventListener('click', () => {
            this.calculateSafeRoutes();
        });
        
        // Emergency actions
        document.getElementById('call-police').addEventListener('click', () => {
            this.callEmergency('117');
        });
        
        document.getElementById('call-emergency').addEventListener('click', () => {
            this.callEmergency('112');
        });
        
        document.getElementById('send-alert').addEventListener('click', () => {
            this.sendEmergencyAlert();
        });
        
        document.getElementById('share-location').addEventListener('click', () => {
            this.shareLocation();
        });
    }
    
    requestLocation() {
        this.showLoading('Getting your location...');
        
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.userLocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    
                    this.map.setView([this.userLocation.lat, this.userLocation.lng], 15);
                    this.addUserLocationMarker();
                    this.analyzeSafetyAtLocation(this.userLocation.lat, this.userLocation.lng);
                    this.hideLoading();
                },
                (error) => {
                    console.error('Location error:', error);
                    this.hideLoading();
                    this.showNotification('Could not get your location. Using Zurich city center.', 'warning');
                    this.userLocation = { lat: 47.3769, lng: 8.5417 };
                    this.analyzeSafetyAtLocation(this.userLocation.lat, this.userLocation.lng);
                }
            );
        } else {
            this.hideLoading();
            this.showNotification('Geolocation not supported. Using Zurich city center.', 'warning');
            this.userLocation = { lat: 47.3769, lng: 8.5417 };
        }
    }
    
    addUserLocationMarker() {
        if (this.userLocationMarker) {
            this.map.removeLayer(this.userLocationMarker);
        }
        
        const userIcon = L.divIcon({
            className: 'user-location-marker',
            html: '📍',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
        
        this.userLocationMarker = L.marker([this.userLocation.lat, this.userLocation.lng], {
            icon: userIcon
        }).addTo(this.map);
        
        this.userLocationMarker.bindPopup('<strong>Your Location</strong>').openPopup();
    }
    
    async analyzeSafetyAtLocation(lat, lng) {
        this.showLoading('Analyzing safety data...');
        
        try {
            const response = await fetch(`/api/safety-data?lat=${lat}&lng=${lng}&radius=500`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.updateSafetyIndicator(data);
            this.addSafetyMarker(lat, lng, data);
            this.hideLoading();
            
        } catch (error) {
            console.error('Safety analysis error:', error);
            this.hideLoading();
            this.showNotification('Could not analyze safety data', 'error');
        }
    }
    
    updateSafetyIndicator(safetyData) {
        const scoreElement = document.querySelector('.score-value');
        const levelElement = document.getElementById('safety-level');
        
        scoreElement.textContent = safetyData.safety_score || '--';
        levelElement.textContent = safetyData.safety_level || 'Unknown';
        levelElement.className = `safety-level ${safetyData.safety_level || ''}`;
        
        // Update Safe Navigation Layer indicators
        this.updateNavigationIndicators(safetyData);
    }
    
    updateNavigationIndicators(safetyData) {
        if (!safetyData.safe_navigation_factors) return;
        
        const factors = safetyData.safe_navigation_factors;
        
        // Update individual indicators
        this.updateIndicator('lighting-indicator', factors.street_lighting?.score);
        this.updateIndicator('flow-indicator', factors.pedestrian_flow?.score);
        this.updateIndicator('emergency-indicator', factors.emergency_proximity?.score);
        this.updateIndicator('visibility-indicator', factors.visibility_terrain?.score);
    }
    
    updateIndicator(elementId, score) {
        const element = document.getElementById(elementId);
        if (!element || score === undefined) return;
        
        const percentage = Math.round(score * 100);
        element.textContent = `${percentage}%`;
        
        // Update indicator class based on score
        element.className = 'indicator';
        if (score >= 0.7) {
            element.classList.add('high');
        } else if (score >= 0.4) {
            element.classList.add('medium');
        } else {
            element.classList.add('low');
        }
    }
    
    addSafetyMarker(lat, lng, safetyData) {
        const color = this.getSafetyColor(safetyData.safety_level);
        
        const safetyIcon = L.divIcon({
            className: 'safety-marker',
            html: `<div style="background: ${color}; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
        
        const marker = L.marker([lat, lng], { icon: safetyIcon }).addTo(this.map);
        
        const popupContent = this.createSafeNavigationPopup(safetyData, color);
        marker.bindPopup(popupContent);
        this.safetyMarkers.push(marker);
    }
    
    createSafeNavigationPopup(safetyData, color) {
        let content = `
            <div class="safety-popup">
                <h4>Safe Navigation Analysis</h4>
                <div class="score" style="color: ${color};">${safetyData.safety_score}/1.0</div>
                <div class="level ${safetyData.safety_level}">${safetyData.safety_level}</div>
        `;
        
        // Add Safe Navigation factors
        if (safetyData.safe_navigation_factors) {
            content += '<div style="margin-top: 0.5rem; font-size: 0.8rem;"><strong>Safety Factors:</strong><br>';
            Object.entries(safetyData.safe_navigation_factors).forEach(([key, factor]) => {
                const percentage = Math.round(factor.score * 100);
                content += `• ${factor.description}: ${percentage}%<br>`;
            });
            content += '</div>';
        }
        
        // Add time context
        if (safetyData.time_context) {
            content += `<div style="margin-top: 0.5rem; font-size: 0.8rem;">
                <strong>Time Context:</strong> ${safetyData.time_context.message}
            </div>`;
        }
        
        // Add women-specific recommendations
        if (safetyData.women_safety_recommendations) {
            content += '<div style="margin-top: 0.5rem; font-size: 0.8rem;"><strong>Safety Tips:</strong><br>';
            safetyData.women_safety_recommendations.slice(0, 3).forEach(rec => {
                content += `${rec}<br>`;
            });
            content += '</div>';
        }
        
        content += '</div>';
        return content;
    }
    
    getSafetyColor(level) {
        const colors = {
            'high': '#48bb78',
            'medium': '#ed8936',
            'low': '#e53e3e',
            'very_low': '#c53030'
        };
        return colors[level] || '#718096';
    }
    
    // Chat functionality
    initChat() {
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
    }
    
    toggleChat() {
        const chatContainer = document.getElementById('chat-container');
        const toggleBtn = document.getElementById('chat-toggle');
        
        if (chatContainer.style.display === 'none') {
            chatContainer.style.display = 'flex';
            toggleBtn.textContent = '−';
        } else {
            chatContainer.style.display = 'none';
            toggleBtn.textContent = '+';
        }
    }
    
    async sendChatMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;
        
        this.addChatMessage(message, 'user');
        this.chatInput.value = '';
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    location: this.userLocation
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addChatMessage(data.response, 'assistant');
            } else {
                this.addChatMessage('Sorry, I encountered an error. Please try again.', 'assistant');
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            this.addChatMessage('Connection error. Please check your internet connection.', 'assistant');
        }
    }
    
    addChatMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        if (typeof content === 'object') {
            messageDiv.innerHTML = this.formatChatResponse(content);
            if (content.type === 'emergency') {
                messageDiv.classList.add('emergency');
            }
        } else {
            messageDiv.textContent = content;
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    formatChatResponse(response) {
        let html = `<p><strong>${response.message}</strong></p>`;
        
        if (response.safety_tips) {
            html += '<div><strong>Safety Tips:</strong><ul>';
            response.safety_tips.forEach(tip => {
                html += `<li>${tip}</li>`;
            });
            html += '</ul></div>';
        }
        
        if (response.immediate_steps) {
            html += '<div><strong>Immediate Steps:</strong><ul>';
            response.immediate_steps.forEach(step => {
                html += `<li>${step}</li>`;
            });
            html += '</ul></div>';
        }
        
        if (response.emergency_contacts) {
            html += '<div><strong>Emergency Contacts:</strong><ul>';
            Object.entries(response.emergency_contacts).forEach(([key, value]) => {
                html += `<li>${key}: ${value}</li>`;
            });
            html += '</ul></div>';
        }
        
        return html;
    }
    
    // Modal functionality
    showEmergencyModal() {
        document.getElementById('emergency-modal').classList.add('active');
    }
    
    showRouteModal() {
        document.getElementById('route-modal').classList.add('active');
        
        // Pre-fill current location if available
        if (this.userLocation) {
            document.getElementById('route-from').value = `${this.userLocation.lat}, ${this.userLocation.lng}`;
        }
    }
    
    closeModal(modal) {
        modal.classList.remove('active');
    }
    
    async calculateSafeRoutes() {
        const fromInput = document.getElementById('route-from').value;
        const toInput = document.getElementById('route-to').value;
        
        if (!fromInput || !toInput) {
            this.showNotification('Please enter both starting point and destination', 'warning');
            return;
        }
        
        this.showLoading('Calculating safe routes...');
        
        try {
            // For demo, use coordinates if available, otherwise use Zurich coordinates
            const fromCoords = this.parseCoordinates(fromInput) || { lat: 47.3769, lng: 8.5417 };
            const toCoords = this.parseCoordinates(toInput) || { lat: 47.3869, lng: 8.5517 };
            
            const response = await fetch(`/api/safe-routes?start_lat=${fromCoords.lat}&start_lng=${fromCoords.lng}&end_lat=${toCoords.lat}&end_lng=${toCoords.lng}`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.displayRouteResults(data);
            this.hideLoading();
            
        } catch (error) {
            console.error('Route calculation error:', error);
            this.hideLoading();
            this.showNotification('Could not calculate routes', 'error');
        }
    }
    
    parseCoordinates(input) {
        const coords = input.split(',').map(s => parseFloat(s.trim()));
        if (coords.length === 2 && !isNaN(coords[0]) && !isNaN(coords[1])) {
            return { lat: coords[0], lng: coords[1] };
        }
        return null;
    }
    
    displayRouteResults(routeData) {
        const resultsDiv = document.getElementById('route-results');
        
        let html = `
            <h4>Safe Navigation Routes</h4>
            <div class="route-context">
                <p><strong>Context:</strong> ${routeData.time_context === 'night' ? '🌙 Night time' : '☀️ Day time'}</p>
                <p><em>${routeData.recommendation}</em></p>
            </div>
        `;
        
        routeData.routes.forEach((route, index) => {
            const isRecommended = index === 0;
            const safetyLevel = route.safety_score >= 0.8 ? 'high' : route.safety_score >= 0.6 ? 'medium' : 'low';
            
            html += `
                <div class="route-option ${isRecommended ? 'recommended' : ''}" onclick="app.selectRoute(${index}, ${JSON.stringify(route).replace(/"/g, '&quot;')})">
                    <div class="route-header">
                        <div>
                            <strong>${route.description}</strong>
                            ${isRecommended ? '<span class="recommended-badge">✨ Recommended</span>' : ''}
                        </div>
                        <div class="route-score">
                            <div class="score-value ${safetyLevel}">${route.safety_score}/1.0</div>
                            <div class="route-time">${route.estimated_time}</div>
                        </div>
                    </div>
                    <div class="route-features">
                        ${route.safety_features.map(feature => `<span class="feature-tag">${feature}</span>`).join('')}
                    </div>
                </div>
            `;
        });
        
        // Add safety tips
        if (routeData.safety_tips) {
            html += `
                <div class="safety-tips">
                    <h5>🛡️ Safety Tips for Your Journey:</h5>
                    <ul>
                        ${routeData.safety_tips.map(tip => `<li>${tip}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        resultsDiv.innerHTML = html;
    }
    
    selectRoute(routeIndex, routeData) {
        this.currentRoute = routeData;
        this.drawRouteOnMap(routeData);
        this.showNotification(`${routeData.description} selected! Route shown on map.`, 'success');
        this.closeModal(document.getElementById('route-modal'));
    }
    
    drawRouteOnMap(route) {
        // Clear existing route
        if (this.routeLayer) {
            this.map.removeLayer(this.routeLayer);
        }
        
        // Create route line
        const waypoints = route.waypoints.map(wp => [wp.lat, wp.lng]);
        
        const routeColor = route.safety_score >= 0.8 ? '#48bb78' : 
                          route.safety_score >= 0.6 ? '#ed8936' : '#e53e3e';
        
        this.routeLayer = L.polyline(waypoints, {
            color: routeColor,
            weight: 4,
            opacity: 0.8
        }).addTo(this.map);
        
        // Add waypoint markers
        route.waypoints.forEach((waypoint, index) => {
            const icon = L.divIcon({
                className: 'waypoint-marker',
                html: `<div style="background: ${routeColor}; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">${index + 1}</div>`,
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });
            
            L.marker([waypoint.lat, waypoint.lng], { icon })
                .bindPopup(`<strong>${waypoint.description}</strong>`)
                .addTo(this.map);
        });
        
        // Fit map to route
        this.map.fitBounds(this.routeLayer.getBounds(), { padding: [20, 20] });
    }
    
    toggleNightMode() {
        this.nightMode = !this.nightMode;
        const btn = document.getElementById('safety-layer-btn');
        
        if (this.nightMode) {
            btn.textContent = '☀️ Day Mode';
            btn.style.background = '#2d3748';
            this.showNotification('Night mode activated - prioritizing well-lit routes', 'info');
            
            // Update map style for night mode
            this.updateMapForNightMode(true);
        } else {
            btn.textContent = '🌙 Night Mode';
            btn.style.background = '#4c51bf';
            this.showNotification('Day mode activated', 'info');
            
            // Update map style for day mode
            this.updateMapForNightMode(false);
        }
    }
    
    updateMapForNightMode(isNight) {
        // In a real implementation, you would switch to a darker tile layer
        // and highlight well-lit areas differently
        
        if (isNight) {
            // Add night-specific overlays
            this.addNightSafetyOverlays();
        } else {
            // Remove night-specific overlays
            this.removeNightSafetyOverlays();
        }
    }
    
    addNightSafetyOverlays() {
        // Add overlays showing well-lit areas, police stations, etc.
        this.police_stations.forEach(station => {
            const icon = L.divIcon({
                className: 'police-marker',
                html: '🚔',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });
            
            const marker = L.marker([station.lat, station.lng], { icon })
                .bindPopup(`<strong>${station.name}</strong><br>Police Station`)
                .addTo(this.map);
            
            if (!this.nightOverlays) this.nightOverlays = [];
            this.nightOverlays.push(marker);
        });
    }
    
    removeNightSafetyOverlays() {
        if (this.nightOverlays) {
            this.nightOverlays.forEach(overlay => {
                this.map.removeLayer(overlay);
            });
            this.nightOverlays = [];
        }
    }
    
    // Emergency functions
    callEmergency(number) {
        if (confirm(`Call ${number}?`)) {
            window.location.href = `tel:${number}`;
        }
    }
    
    async sendEmergencyAlert() {
        if (!this.userLocation) {
            this.showNotification('Location required for emergency alert', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/emergency', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    location: this.userLocation,
                    type: 'general_emergency'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Emergency alert sent to authorities!', 'success');
                this.closeModal(document.getElementById('emergency-modal'));
            } else {
                throw new Error(data.error);
            }
            
        } catch (error) {
            console.error('Emergency alert error:', error);
            this.showNotification('Could not send emergency alert', 'error');
        }
    }
    
    shareLocation() {
        if (!this.userLocation) {
            this.showNotification('Location not available', 'error');
            return;
        }
        
        const locationText = `My location: https://maps.google.com/?q=${this.userLocation.lat},${this.userLocation.lng}`;
        
        if (navigator.share) {
            navigator.share({
                title: 'My Location - Emergency',
                text: locationText
            });
        } else {
            navigator.clipboard.writeText(locationText).then(() => {
                this.showNotification('Location copied to clipboard', 'success');
            });
        }
    }
    
    // Utility functions
    showLoading(message = 'Loading...') {
        const loading = document.getElementById('loading');
        const nasaMessages = [
            '🛰️ Connecting to NASA satellites...',
            '🌍 Analyzing satellite imagery...',
            '📡 Processing geospatial data...',
            '🚀 Calculating safe navigation routes...',
            '⭐ Initializing space-powered safety analysis...'
        ];
        
        // Use NASA-themed message if it's a generic loading message
        if (message === 'Loading...' || message.includes('Analyzing') || message.includes('Getting')) {
            message = nasaMessages[Math.floor(Math.random() * nasaMessages.length)];
        }
        
        loading.querySelector('p').textContent = message;
        loading.classList.add('active');
    }
    
    hideLoading() {
        document.getElementById('loading').classList.remove('active');
    }
    
    showNotification(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 4000;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        `;
        
        const colors = {
            success: '#48bb78',
            error: '#e53e3e',
            warning: '#ed8936',
            info: '#4c51bf'
        };
        
        notification.style.background = colors[type] || colors.info;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new SafetyApp();
});