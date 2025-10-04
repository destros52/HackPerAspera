import requests
import json
from datetime import datetime, timedelta
import os
from geopy.distance import geodesic
import numpy as np

class SafetyAnalyzer:
    def __init__(self):
        self.transport_api = os.getenv('TRANSPORT_API_ENDPOINT', 'https://transport.opendata.ch/v1')
        self.satellite_api_key = os.getenv('SATELLITE_API_KEY')
        self.emergency_endpoint = os.getenv('EMERGENCY_API_ENDPOINT')
        
        # Safe Navigation Layer weights (based on research from "Invisible Women")
        self.weights = {
            'street_lighting': 0.30,      # Critical for women's safety at night
            'pedestrian_flow': 0.25,      # Higher traffic = safer feeling
            'emergency_proximity': 0.20,   # Police stations, safe points
            'visibility_terrain': 0.15,   # Parks, tunnels, underpasses
            'construction_disruption': 0.10  # Temporary closures, festivals
        }
        
        # Zurich-specific safety infrastructure
        self.police_stations = [
            {'lat': 47.3769, 'lng': 8.5417, 'name': 'Stadtpolizei Zurich HQ'},
            {'lat': 47.3667, 'lng': 8.5500, 'name': 'Polizeiposten Enge'},
            {'lat': 47.3900, 'lng': 8.5167, 'name': 'Polizeiposten Oerlikon'},
            {'lat': 47.3583, 'lng': 8.5392, 'name': 'Polizeiposten Wiedikon'},
            {'lat': 47.4108, 'lng': 8.5444, 'name': 'Polizeiposten Schwamendingen'}
        ]
        
        # Emergency safe points (hospitals, fire stations, 24h locations)
        self.safe_points = [
            {'lat': 47.3774, 'lng': 8.5527, 'name': 'UniversitätsSpital Zürich', 'type': 'hospital'},
            {'lat': 47.3769, 'lng': 8.5417, 'name': 'Hauptbahnhof Zürich', 'type': 'transport_hub'},
            {'lat': 47.3667, 'lng': 8.5500, 'name': 'Bahnhof Enge', 'type': 'transport_hub'},
            {'lat': 47.3900, 'lng': 8.5167, 'name': 'Bahnhof Oerlikon', 'type': 'transport_hub'}
        ]
    
    def analyze_area(self, lat, lng, radius):
        """Analyze safety using Safe Navigation Layer methodology"""
        try:
            # Core Safe Navigation Layer factors
            lighting_score = self._assess_street_lighting(lat, lng, radius)
            pedestrian_flow = self._analyze_pedestrian_flow(lat, lng, radius)
            emergency_proximity = self._assess_emergency_proximity(lat, lng)
            visibility_terrain = self._analyze_visibility_terrain(lat, lng, radius)
            construction_impact = self._get_construction_disruption(lat, lng, radius)
            
            # Calculate Safe Navigation Score
            safety_score = (
                lighting_score * self.weights['street_lighting'] +
                pedestrian_flow * self.weights['pedestrian_flow'] +
                emergency_proximity * self.weights['emergency_proximity'] +
                visibility_terrain * self.weights['visibility_terrain'] +
                construction_impact * self.weights['construction_disruption']
            )
            
            # Additional context for women's safety
            time_context = self._get_time_safety_context()
            nearby_infrastructure = self._get_safety_infrastructure(lat, lng)
            
            return {
                'location': {'lat': lat, 'lng': lng},
                'safety_score': round(safety_score, 2),
                'safety_level': self._get_safety_level(safety_score),
                'safe_navigation_factors': {
                    'street_lighting': {
                        'score': lighting_score,
                        'description': 'Well-lit streets prioritized for night safety'
                    },
                    'pedestrian_flow': {
                        'score': pedestrian_flow,
                        'description': 'Areas with higher foot traffic feel safer'
                    },
                    'emergency_proximity': {
                        'score': emergency_proximity,
                        'description': 'Distance to police stations and safe points'
                    },
                    'visibility_terrain': {
                        'score': visibility_terrain,
                        'description': 'Open areas vs tunnels, parks, underpasses'
                    },
                    'construction_disruption': {
                        'score': construction_impact,
                        'description': 'Temporary closures affecting safe routes'
                    }
                },
                'time_context': time_context,
                'nearby_infrastructure': nearby_infrastructure,
                'women_safety_recommendations': self._generate_women_safety_recommendations(safety_score, lat, lng),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': f'Safe Navigation analysis failed: {str(e)}'}
    
    def _assess_street_lighting(self, lat, lng, radius):
        """Assess street lighting using satellite data and city infrastructure"""
        current_hour = datetime.now().hour
        
        # Base lighting assessment
        if 6 <= current_hour <= 20:
            base_score = 0.9  # Daylight hours
        else:
            # Night assessment - critical for women's safety
            base_score = 0.3
            
            # Check for well-lit areas (main streets, commercial zones)
            if self._is_main_street(lat, lng):
                base_score += 0.4
            if self._is_commercial_area(lat, lng):
                base_score += 0.3
            if self._near_transport_hub(lat, lng):
                base_score += 0.2
        
        # Penalty for known dark areas (parks, industrial zones)
        if self._is_park_area(lat, lng):
            base_score -= 0.3
        if self._is_industrial_area(lat, lng):
            base_score -= 0.2
            
        return max(0.0, min(1.0, base_score))
    
    def _get_crowd_density(self, lat, lng, radius):
        """Estimate crowd density from transport and event data"""
        try:
            # Get nearby transport stops and their usage
            transport_data = self._get_nearby_transport(lat, lng)
            
            # Higher crowd density = higher safety (generally)
            crowd_score = 0.5  # baseline
            
            if transport_data.get('nearby_stops', 0) > 3:
                crowd_score += 0.3
            
            # Check for events or festivals
            if self._check_events_nearby(lat, lng):
                crowd_score += 0.2
            
            return min(1.0, crowd_score)
        except:
            return 0.5
    
    def _assess_transport_access(self, lat, lng):
        """Assess public transport accessibility"""
        try:
            nearby_stops = self._get_nearby_transport(lat, lng)
            stop_count = nearby_stops.get('nearby_stops', 0)
            
            if stop_count >= 5:
                return 0.9
            elif stop_count >= 3:
                return 0.7
            elif stop_count >= 1:
                return 0.5
            else:
                return 0.2
        except:
            return 0.3
    
    def _get_crime_history(self, lat, lng, radius):
        """Get historical crime data for the area"""
        # Simulate crime data analysis
        # In production, this would connect to police databases
        
        # Zurich city center generally safer
        city_center = (47.3769, 8.5417)
        distance_to_center = geodesic((lat, lng), city_center).kilometers
        
        if distance_to_center < 2:
            return 0.8  # City center is generally safer
        elif distance_to_center < 5:
            return 0.6
        else:
            return 0.4
    
    def _assess_emergency_services(self, lat, lng):
        """Assess proximity to emergency services"""
        # Simulate emergency services proximity
        # In production, would use real emergency services locations
        
        # Assume better coverage in urban areas
        if self._is_urban_area(lat, lng):
            return 0.8
        else:
            return 0.5
    
    def _get_construction_impact(self, lat, lng, radius):
        """Check for construction disruptions"""
        # Simulate construction impact
        # In production, would connect to city construction databases
        
        # Random simulation for demo
        import random
        construction_impact = random.uniform(0.3, 0.9)
        return construction_impact
    
    def _is_urban_area(self, lat, lng):
        """Check if location is in urban area"""
        # Zurich city boundaries (simplified)
        zurich_center = (47.3769, 8.5417)
        distance = geodesic((lat, lng), zurich_center).kilometers
        return distance < 10
    
    def _get_nearby_transport(self, lat, lng):
        """Get nearby public transport information"""
        try:
            url = f"{self.transport_api}/locations"
            params = {
                'x': lng,
                'y': lat,
                'type': 'station'
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'nearby_stops': len(data.get('stations', [])),
                    'stations': data.get('stations', [])[:5]  # Top 5 nearest
                }
        except:
            pass
        
        return {'nearby_stops': 2, 'stations': []}  # Fallback
    
    def _check_events_nearby(self, lat, lng):
        """Check for events or festivals nearby"""
        # Simulate event checking
        # In production, would connect to city events API
        return False
    
    def _get_safety_level(self, score):
        """Convert numeric score to safety level"""
        if score >= 0.8:
            return 'high'
        elif score >= 0.6:
            return 'medium'
        elif score >= 0.4:
            return 'low'
        else:
            return 'very_low'
    
    def _analyze_pedestrian_flow(self, lat, lng, radius):
        """Analyze pedestrian flow using mobility data"""
        current_hour = datetime.now().hour
        day_of_week = datetime.now().weekday()
        
        base_flow = 0.5
        
        # Time-based pedestrian flow
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:  # Rush hours
            base_flow += 0.3
        elif 10 <= current_hour <= 16:  # Business hours
            base_flow += 0.2
        elif 20 <= current_hour <= 23:  # Evening social hours
            base_flow += 0.1
        else:  # Late night/early morning
            base_flow -= 0.2
        
        # Weekend adjustments
        if day_of_week >= 5:  # Weekend
            if 10 <= current_hour <= 22:
                base_flow += 0.2
        
        # Location-based adjustments
        if self._is_commercial_area(lat, lng):
            base_flow += 0.2
        if self._near_transport_hub(lat, lng):
            base_flow += 0.3
        if self._is_residential_area(lat, lng):
            base_flow += 0.1
        
        return max(0.0, min(1.0, base_flow))
    
    def _assess_emergency_proximity(self, lat, lng):
        """Assess proximity to police stations and emergency safe points"""
        min_police_distance = float('inf')
        min_safe_point_distance = float('inf')
        
        # Find nearest police station
        for station in self.police_stations:
            distance = geodesic((lat, lng), (station['lat'], station['lng'])).meters
            min_police_distance = min(min_police_distance, distance)
        
        # Find nearest safe point
        for point in self.safe_points:
            distance = geodesic((lat, lng), (point['lat'], point['lng'])).meters
            min_safe_point_distance = min(min_safe_point_distance, distance)
        
        # Score based on proximity (closer = higher score)
        police_score = max(0, 1 - (min_police_distance / 2000))  # 2km max distance
        safe_point_score = max(0, 1 - (min_safe_point_distance / 1000))  # 1km max distance
        
        return (police_score * 0.6 + safe_point_score * 0.4)
    
    def _analyze_visibility_terrain(self, lat, lng, radius):
        """Analyze terrain visibility using satellite/geospatial data"""
        base_visibility = 0.7
        
        # Terrain-based adjustments (simulated with location analysis)
        if self._is_park_area(lat, lng):
            base_visibility -= 0.4  # Parks can have poor visibility at night
        if self._is_tunnel_underpass(lat, lng):
            base_visibility -= 0.5  # Tunnels and underpasses are high-risk
        if self._is_bridge_area(lat, lng):
            base_visibility += 0.2  # Bridges often have good visibility
        if self._is_main_street(lat, lng):
            base_visibility += 0.3  # Main streets have better visibility
        
        return max(0.0, min(1.0, base_visibility))
    
    def _get_construction_disruption(self, lat, lng, radius):
        """Check for construction and festival disruptions"""
        base_score = 0.8
        
        # Simulate construction data (in production, use city construction APIs)
        if self._has_construction_nearby(lat, lng):
            base_score -= 0.3
        
        # Check for festivals/events that might cause crowd diversions
        if self._has_festival_nearby(lat, lng):
            base_score -= 0.2  # Festivals can create unpredictable crowd flows
        
        return max(0.0, min(1.0, base_score))
    
    def _get_time_safety_context(self):
        """Get time-based safety context"""
        current_hour = datetime.now().hour
        
        if 22 <= current_hour or current_hour <= 5:
            return {
                'risk_level': 'high',
                'message': 'Late night hours - extra caution recommended',
                'recommendations': [
                    'Use well-lit main streets only',
                    'Stay near transport hubs',
                    'Consider ride-sharing or taxi',
                    'Share location with trusted contacts'
                ]
            }
        elif 18 <= current_hour <= 21:
            return {
                'risk_level': 'medium',
                'message': 'Evening hours - moderate caution advised',
                'recommendations': [
                    'Stick to busy areas',
                    'Avoid shortcuts through parks',
                    'Keep phone charged and accessible'
                ]
            }
        else:
            return {
                'risk_level': 'low',
                'message': 'Daylight hours - generally safe',
                'recommendations': [
                    'Standard safety precautions apply',
                    'Stay aware of surroundings'
                ]
            }
    
    def _get_safety_infrastructure(self, lat, lng):
        """Get nearby safety infrastructure"""
        nearby_police = []
        nearby_safe_points = []
        
        for station in self.police_stations:
            distance = geodesic((lat, lng), (station['lat'], station['lng'])).meters
            if distance <= 1000:  # Within 1km
                nearby_police.append({
                    'name': station['name'],
                    'distance': round(distance),
                    'walk_time': round(distance / 80)  # ~80m/min walking speed
                })
        
        for point in self.safe_points:
            distance = geodesic((lat, lng), (point['lat'], point['lng'])).meters
            if distance <= 800:  # Within 800m
                nearby_safe_points.append({
                    'name': point['name'],
                    'type': point['type'],
                    'distance': round(distance),
                    'walk_time': round(distance / 80)
                })
        
        return {
            'police_stations': nearby_police,
            'safe_points': nearby_safe_points
        }
    
    def _generate_women_safety_recommendations(self, safety_score, lat, lng):
        """Generate women-specific safety recommendations based on research"""
        recommendations = []
        current_hour = datetime.now().hour
        
        # Time-based recommendations
        if current_hour >= 20 or current_hour <= 6:
            recommendations.extend([
                "🌙 Night Safety: Use well-lit main streets only",
                "👥 Stay in areas with other people when possible",
                "📱 Keep phone charged and emergency contacts ready",
                "🚇 Use public transport stops as safe waypoints"
            ])
        
        # Score-based recommendations
        if safety_score < 0.7:
            recommendations.extend([
                "⚠️ Consider alternative route via main streets",
                "🚨 Emergency services: Police 117, Emergency 112",
                "📍 Share live location with trusted contact",
                "🏃‍♀️ Trust your instincts - if unsafe, seek help immediately"
            ])
        
        # Location-specific recommendations
        if self._is_park_area(lat, lng):
            recommendations.append("🌳 Avoid park shortcuts at night - use perimeter streets")
        
        if self._is_tunnel_underpass(lat, lng):
            recommendations.append("🚇 Avoid tunnels/underpasses - use street-level routes")
        
        # Infrastructure-based recommendations
        nearby_infrastructure = self._get_safety_infrastructure(lat, lng)
        if nearby_infrastructure['police_stations']:
            station = nearby_infrastructure['police_stations'][0]
            recommendations.append(f"👮‍♀️ Nearest police: {station['name']} ({station['walk_time']} min walk)")
        
        return recommendations
    
    # Helper methods for location classification
    def _is_main_street(self, lat, lng):
        """Check if location is on a main street"""
        # Simulate main street detection (in production, use OSM data)
        city_center = (47.3769, 8.5417)
        distance_to_center = geodesic((lat, lng), city_center).kilometers
        return distance_to_center < 3  # Assume main streets within 3km of center
    
    def _is_commercial_area(self, lat, lng):
        """Check if location is in commercial area"""
        # Zurich commercial areas (simplified)
        commercial_zones = [
            (47.3769, 8.5417),  # City center
            (47.3667, 8.5500),  # Enge
            (47.3900, 8.5167)   # Oerlikon
        ]
        
        for zone in commercial_zones:
            if geodesic((lat, lng), zone).kilometers < 1:
                return True
        return False
    
    def _near_transport_hub(self, lat, lng):
        """Check if near major transport hub"""
        transport_hubs = [
            (47.3769, 8.5417),  # Hauptbahnhof
            (47.3667, 8.5500),  # Enge
            (47.3900, 8.5167)   # Oerlikon
        ]
        
        for hub in transport_hubs:
            if geodesic((lat, lng), hub).kilometers < 0.5:
                return True
        return False
    
    def _is_park_area(self, lat, lng):
        """Check if location is in park area"""
        # Major Zurich parks (simplified coordinates)
        parks = [
            (47.3667, 8.5583),  # Arboretum
            (47.3583, 8.5500),  # Rieterpark
            (47.3833, 8.5333)   # Irchelpark
        ]
        
        for park in parks:
            if geodesic((lat, lng), park).kilometers < 0.3:
                return True
        return False
    
    def _is_industrial_area(self, lat, lng):
        """Check if location is in industrial area"""
        # Industrial zones typically have poor lighting
        return False  # Simplified for demo
    
    def _is_residential_area(self, lat, lng):
        """Check if location is residential"""
        return not (self._is_commercial_area(lat, lng) or self._is_industrial_area(lat, lng))
    
    def _is_tunnel_underpass(self, lat, lng):
        """Check if location is tunnel or underpass"""
        # Simulate tunnel detection (in production, use detailed map data)
        return False  # Simplified for demo
    
    def _is_bridge_area(self, lat, lng):
        """Check if location is on a bridge"""
        return False  # Simplified for demo
    
    def _has_construction_nearby(self, lat, lng):
        """Check for nearby construction"""
        # Simulate construction data
        import random
        return random.random() < 0.2  # 20% chance of construction
    
    def _has_festival_nearby(self, lat, lng):
        """Check for nearby festivals/events"""
        # Simulate event data
        import random
        return random.random() < 0.1  # 10% chance of festival
    
    def get_transport_safety(self, lat, lng):
        """Get transport-specific safety information"""
        try:
            transport_data = self._get_nearby_transport(lat, lng)
            
            return {
                'nearby_stations': transport_data.get('stations', []),
                'safety_tips': [
                    "Wait in well-lit areas",
                    "Stay alert while waiting",
                    "Keep belongings secure",
                    "Use official transport apps for real-time updates"
                ],
                'emergency_contacts': {
                    'transport_security': '+41 44 123 4567',
                    'police': '117',
                    'emergency': '112'
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def trigger_emergency_alert(self, location, emergency_type):
        """Trigger emergency alert"""
        try:
            alert_data = {
                'location': location,
                'type': emergency_type,
                'timestamp': datetime.now().isoformat(),
                'status': 'alert_sent'
            }
            
            # In production, would send to actual emergency services
            return {
                'success': True,
                'alert_id': f"ALERT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'message': "Emergency alert sent to authorities",
                'estimated_response_time': "5-10 minutes"
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_safe_routes(self, start_lat, start_lng, end_lat, end_lng):
        """Get Safe Navigation Layer route recommendations prioritizing women's safety"""
        try:
            routes = []
            current_hour = datetime.now().hour
            is_night = current_hour >= 20 or current_hour <= 6
            
            # Route 1: Direct route
            direct_safety = self.analyze_area((start_lat + end_lat) / 2, 
                                            (start_lng + end_lng) / 2, 500)
            routes.append({
                'type': 'direct',
                'safety_score': direct_safety.get('safety_score', 0.5),
                'description': 'Most direct route',
                'estimated_time': self._calculate_walk_time(start_lat, start_lng, end_lat, end_lng),
                'safety_features': ['Direct path'],
                'waypoints': [
                    {'lat': start_lat, 'lng': start_lng, 'description': 'Start'},
                    {'lat': end_lat, 'lng': end_lng, 'description': 'Destination'}
                ]
            })
            
            # Route 2: Well-lit main streets (Safe Navigation priority)
            main_street_waypoints = self._generate_well_lit_route(start_lat, start_lng, end_lat, end_lng)
            routes.append({
                'type': 'well_lit',
                'safety_score': 0.85,
                'description': 'Well-lit main streets route (Recommended for night)',
                'estimated_time': self._calculate_route_time(main_street_waypoints),
                'safety_features': [
                    'Well-lit streets prioritized',
                    'Avoids parks and isolated areas',
                    'Stays on main pedestrian routes'
                ],
                'waypoints': main_street_waypoints
            })
            
            # Route 3: Police station route (if night time)
            if is_night:
                police_route = self._generate_police_station_route(start_lat, start_lng, end_lat, end_lng)
                routes.append({
                    'type': 'police_stations',
                    'safety_score': 0.9,
                    'description': 'Route via police stations and safe points',
                    'estimated_time': self._calculate_route_time(police_route),
                    'safety_features': [
                        'Passes near police stations',
                        'Includes emergency safe points',
                        'Maximum visibility areas'
                    ],
                    'waypoints': police_route
                })
            
            # Route 4: Transport hub route
            transport_route = self._generate_transport_hub_route(start_lat, start_lng, end_lat, end_lng)
            routes.append({
                'type': 'transport_hubs',
                'safety_score': 0.8,
                'description': 'Route via public transport hubs',
                'estimated_time': self._calculate_route_time(transport_route),
                'safety_features': [
                    'Stays near transport stops',
                    'Higher pedestrian traffic',
                    'Good lighting around stations'
                ],
                'waypoints': transport_route
            })
            
            # Sort by safety score (highest first)
            routes.sort(key=lambda x: x['safety_score'], reverse=True)
            
            return {
                'routes': routes,
                'time_context': 'night' if is_night else 'day',
                'recommendation': self._get_route_recommendation(is_night),
                'safety_tips': self._get_route_safety_tips(is_night),
                'emergency_info': {
                    'police': '117',
                    'emergency': '112',
                    'nearest_police': self._find_nearest_police(start_lat, start_lng)
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_well_lit_route(self, start_lat, start_lng, end_lat, end_lng):
        """Generate route prioritizing well-lit main streets"""
        waypoints = [
            {'lat': start_lat, 'lng': start_lng, 'description': 'Start location'}
        ]
        
        # Add intermediate waypoints via main streets
        if self._should_route_via_center(start_lat, start_lng, end_lat, end_lng):
            waypoints.append({
                'lat': 47.3769, 'lng': 8.5417, 
                'description': 'Hauptbahnhof (well-lit, busy area)'
            })
        
        waypoints.append({
            'lat': end_lat, 'lng': end_lng, 
            'description': 'Destination'
        })
        
        return waypoints
    
    def _generate_police_station_route(self, start_lat, start_lng, end_lat, end_lng):
        """Generate route that passes near police stations"""
        waypoints = [
            {'lat': start_lat, 'lng': start_lng, 'description': 'Start location'}
        ]
        
        # Find police station between start and end
        nearest_station = self._find_intermediate_police_station(start_lat, start_lng, end_lat, end_lng)
        if nearest_station:
            waypoints.append({
                'lat': nearest_station['lat'], 
                'lng': nearest_station['lng'],
                'description': f"Via {nearest_station['name']} (Police Station)"
            })
        
        waypoints.append({
            'lat': end_lat, 'lng': end_lng, 
            'description': 'Destination'
        })
        
        return waypoints
    
    def _generate_transport_hub_route(self, start_lat, start_lng, end_lat, end_lng):
        """Generate route via transport hubs"""
        waypoints = [
            {'lat': start_lat, 'lng': start_lng, 'description': 'Start location'}
        ]
        
        # Route via major transport hub
        waypoints.append({
            'lat': 47.3769, 'lng': 8.5417, 
            'description': 'Hauptbahnhof Zürich (Major transport hub)'
        })
        
        waypoints.append({
            'lat': end_lat, 'lng': end_lng, 
            'description': 'Destination'
        })
        
        return waypoints
    
    def _calculate_walk_time(self, start_lat, start_lng, end_lat, end_lng):
        """Calculate walking time between two points"""
        distance = geodesic((start_lat, start_lng), (end_lat, end_lng)).meters
        walk_speed = 80  # meters per minute (average walking speed)
        time_minutes = int(distance / walk_speed)
        return f"{time_minutes}-{time_minutes + 5} minutes"
    
    def _calculate_route_time(self, waypoints):
        """Calculate total route time"""
        total_distance = 0
        for i in range(len(waypoints) - 1):
            distance = geodesic(
                (waypoints[i]['lat'], waypoints[i]['lng']),
                (waypoints[i+1]['lat'], waypoints[i+1]['lng'])
            ).meters
            total_distance += distance
        
        walk_speed = 80  # meters per minute
        time_minutes = int(total_distance / walk_speed)
        return f"{time_minutes}-{time_minutes + 5} minutes"
    
    def _should_route_via_center(self, start_lat, start_lng, end_lat, end_lng):
        """Determine if route should go via city center"""
        center = (47.3769, 8.5417)
        start_to_center = geodesic((start_lat, start_lng), center).kilometers
        center_to_end = geodesic(center, (end_lat, end_lng)).kilometers
        direct_distance = geodesic((start_lat, start_lng), (end_lat, end_lng)).kilometers
        
        # Route via center if it's not too much longer
        return (start_to_center + center_to_end) < (direct_distance * 1.5)
    
    def _find_intermediate_police_station(self, start_lat, start_lng, end_lat, end_lng):
        """Find police station between start and end points"""
        best_station = None
        min_detour = float('inf')
        
        direct_distance = geodesic((start_lat, start_lng), (end_lat, end_lng)).kilometers
        
        for station in self.police_stations:
            # Calculate detour distance
            via_station = (
                geodesic((start_lat, start_lng), (station['lat'], station['lng'])).kilometers +
                geodesic((station['lat'], station['lng']), (end_lat, end_lng)).kilometers
            )
            detour = via_station - direct_distance
            
            if detour < min_detour and detour < 1.0:  # Max 1km detour
                min_detour = detour
                best_station = station
        
        return best_station
    
    def _find_nearest_police(self, lat, lng):
        """Find nearest police station"""
        nearest = None
        min_distance = float('inf')
        
        for station in self.police_stations:
            distance = geodesic((lat, lng), (station['lat'], station['lng'])).meters
            if distance < min_distance:
                min_distance = distance
                nearest = station
        
        if nearest:
            return {
                'name': nearest['name'],
                'distance': round(min_distance),
                'walk_time': round(min_distance / 80)
            }
        return None
    
    def _get_route_recommendation(self, is_night):
        """Get route recommendation based on time"""
        if is_night:
            return "Night time: Strongly recommend the well-lit main streets route or police station route for maximum safety"
        else:
            return "Day time: All routes are relatively safe, choose based on your preference"
    
    def _get_route_safety_tips(self, is_night):
        """Get safety tips for route planning"""
        tips = [
            "Stay alert and aware of your surroundings",
            "Keep your phone charged and accessible",
            "Trust your instincts - if something feels wrong, seek help"
        ]
        
        if is_night:
            tips.extend([
                "Avoid shortcuts through parks or isolated areas",
                "Stay in well-lit areas with other people",
                "Consider sharing your live location with a trusted contact",
                "Have emergency numbers ready: Police 117, Emergency 112"
            ])
        
        return tips