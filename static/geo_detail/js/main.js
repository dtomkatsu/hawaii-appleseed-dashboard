// Main application
class GeoDetailApp {
    constructor() {
        this.geoId = this.getGeoIdFromUrl();
        this.geoData = null;
        this.charts = {};
        
        if (!this.geoId) {
            this.showError('No geographic ID provided in URL');
            return;
        }
        
        this.init();
    }
    
    async init() {
        try {
            // Show loading state
            document.getElementById('loading').style.display = 'block';
            
            // Load data
            await this.loadGeoData();
            
            // Initialize UI
            this.renderGeoInfo();
            this.setupEventListeners();
            this.initMap();
            this.renderCharts();
            
            // Show content
            document.getElementById('loading').style.display = 'none';
            document.getElementById('content').style.display = 'block';
            
        } catch (error) {
            console.error('Error initializing app:', error);
            this.showError('Failed to load data. Please try again later.');
        }
    }
    
    getGeoIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('geo_id');
    }
    
    async loadGeoData() {
        try {
            // In a real app, this would fetch from your API
            // For now, we'll use a mock data approach
            const response = await fetch(`/api/geo/${this.geoId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.geoData = await response.json();
            
        } catch (error) {
            console.error('Error loading geo data:', error);
            throw error;
        }
    }
    
    renderGeoInfo() {
        if (!this.geoData) return;
        
        // Set page title
        document.title = `${this.geoData.name} | Hawaii Data Dashboard`;
        
        // Update header
        document.getElementById('geo-name').textContent = this.geoData.name;
        
        // Render key indicators
        this.renderKeyIndicators();
    }
    
    renderKeyIndicators() {
        const container = document.getElementById('key-indicators');
        if (!container || !this.geoData) return;
        
        const indicators = [
            {
                label: 'Population',
                value: this.formatNumber(this.geoData.demographics?.total_population),
                icon: '👥'
            },
            {
                label: 'Median Income',
                value: this.formatCurrency(this.geoData.economic?.median_income),
                icon: '💰'
            },
            {
                label: 'Poverty Rate',
                value: this.formatPercent(this.geoData.economic?.poverty_rate),
                icon: '📉'
            },
            {
                label: 'Homeownership',
                value: this.formatPercent(this.geoData.housing?.homeownership_rate),
                icon: '🏠'
            }
        ];
        
        container.innerHTML = indicators.map(indicator => `
            <div class="indicator">
                <div class="indicator-icon">${indicator.icon}</div>
                <div class="indicator-value">${indicator.value}</div>
                <div class="indicator-label">${indicator.label}</div>
            </div>
        `).join('');
    }
    
    initMap() {
        // Only initialize map if we have coordinates
        if (!this.geoData?.geometry) return;
        
        const map = L.map('map').setView([this.geoData.centroid[1], this.geoData.centroid[0]], 10);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        // Add GeoJSON feature
        L.geoJSON(this.geoData.geometry, {
            style: {
                fillColor: '#2b6cb0',
                weight: 2,
                opacity: 1,
                color: 'white',
                fillOpacity: 0.7
            }
        }).addTo(map);
        
        // Fit bounds if available
        if (this.geoData.bbox) {
            const bounds = [
                [this.geoData.bbox[1], this.geoData.bbox[0]],
                [this.geoData.bbox[3], this.geoData.bbox[2]]
            ];
            map.fitBounds(bounds);
        }
    }
    
    renderCharts() {
        this.renderDemographicsChart();
        this.renderEconomicChart();
        this.renderHousingChart();
    }
    
    renderDemographicsChart() {
        const ctx = document.getElementById('demographics-chart');
        if (!ctx || !this.geoData?.demographics) return;
        
        const data = this.geoData.demographics;
        const labels = Object.keys(data.age_distribution || {});
        const values = Object.values(data.age_distribution || {});
        
        if (this.charts.demographics) {
            this.charts.demographics.destroy();
        }
        
        this.charts.demographics = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Population by Age',
                    data: values,
                    backgroundColor: 'rgba(43, 108, 176, 0.7)',
                    borderColor: 'rgba(43, 108, 176, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    title: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }
    
    renderEconomicChart() {
        const ctx = document.getElementById('economic-chart');
        if (!ctx || !this.geoData?.economic) return;
        
        const data = this.geoData.economic;
        
        if (this.charts.economic) {
            this.charts.economic.destroy();
        }
        
        this.charts.economic = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Employed', 'Unemployed', 'Not in Labor Force'],
                datasets: [{
                    data: [
                        data.employment?.employed || 0,
                        data.employment?.unemployed || 0,
                        data.employment?.not_in_labor_force || 0
                    ],
                    backgroundColor: [
                        'rgba(66, 153, 225, 0.7)',
                        'rgba(245, 101, 101, 0.7)',
                        'rgba(159, 122, 234, 0.7)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'right' },
                    title: { display: false }
                }
            }
        });
    }
    
    renderHousingChart() {
        const ctx = document.getElementById('housing-chart');
        if (!ctx || !this.geoData?.housing) return;
        
        const data = this.geoData.housing;
        
        if (this.charts.housing) {
            this.charts.housing.destroy();
        }
        
        this.charts.housing = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Object.keys(data.median_home_value_trend || {}),
                datasets: [{
                    label: 'Median Home Value',
                    data: Object.values(data.median_home_value_trend || {}),
                    borderColor: 'rgba(43, 108, 176, 1)',
                    backgroundColor: 'rgba(43, 108, 176, 0.1)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    title: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: (value) => this.formatCurrency(value)
                        }
                    }
                }
            }
        });
    }
    
    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const tabId = e.target.getAttribute('data-tab');
                this.switchTab(tabId);
            });
        });
    }
    
    switchTab(tabId) {
        // Update active tab button
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
        });
        
        // Show active tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === tabId);
        });
        
        // Resize charts when tab becomes visible
        if (this.charts[tabId]) {
            setTimeout(() => {
                this.charts[tabId].resize();
            }, 100);
        }
    }
    
    // Helper methods
    formatNumber(num) {
        if (num === undefined || num === null) return 'N/A';
        return new Intl.NumberFormat('en-US').format(num);
    }
    
    formatCurrency(amount) {
        if (amount === undefined || amount === null) return 'N/A';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0
        }).format(amount);
    }
    
    formatPercent(value) {
        if (value === undefined || value === null) return 'N/A';
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 1,
            maximumFractionDigits: 1
        }).format(value / 100);
    }
    
    showError(message) {
        const loadingEl = document.getElementById('loading');
        if (loadingEl) {
            loadingEl.innerHTML = `
                <div class="error-message">
                    <p>${message}</p>
                    <button onclick="window.location.href='/'">Back to Map</button>
                </div>
            `;
        } else {
            alert(message);
            window.location.href = '/';
        }
    }
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new GeoDetailApp();
});
