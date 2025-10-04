import os
from datetime import datetime
import json
from typing import Dict, Any

# Simulated LangGraph implementation
# In production, you would use actual LangGraph/LangChain components

class ChatHandler:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.conversation_history = []
        
        # Authority contact information
        self.authorities = {
            'police': {
                'name': 'Zurich Police',
                'contact': '117',
                'email': 'info@stadtpolizei.zh.ch'
            },
            'emergency': {
                'name': 'Emergency Services',
                'contact': '112',
                'email': 'emergency@zurich.ch'
            },
            'transport': {
                'name': 'Transport Security',
                'contact': '+41 44 123 4567',
                'email': 'security@zvv.ch'
            }
        }
    
    def process_message(self, message: str, user_location: Dict[str, Any]) -> Dict[str, Any]:
        """Process user message and generate appropriate response"""
        try:
            # Analyze message intent
            intent = self._analyze_intent(message)
            
            # Generate response based on intent
            response = self._generate_response(message, intent, user_location)
            
            # Store conversation
            self.conversation_history.append({
                'timestamp': datetime.now().isoformat(),
                'user_message': message,
                'user_location': user_location,
                'intent': intent,
                'response': response
            })
            
            return {
                'success': True,
                'response': response,
                'intent': intent,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response': {
                    'message': 'I apologize, but I encountered an error. Please try again or contact emergency services directly at 112.',
                    'type': 'error'
                }
            }
    
    def _analyze_intent(self, message: str) -> str:
        """Analyze user message to determine intent"""
        message_lower = message.lower()
        
        # Emergency keywords
        emergency_keywords = ['help', 'emergency', 'danger', 'unsafe', 'scared', 'threatened', 'attack']
        if any(keyword in message_lower for keyword in emergency_keywords):
            return 'emergency'
        
        # Safety inquiry keywords
        safety_keywords = ['safe', 'safety', 'secure', 'route', 'area', 'location']
        if any(keyword in message_lower for keyword in safety_keywords):
            return 'safety_inquiry'
        
        # Transport related
        transport_keywords = ['transport', 'bus', 'tram', 'train', 'station', 'stop']
        if any(keyword in message_lower for keyword in transport_keywords):
            return 'transport_inquiry'
        
        # Reporting incident
        report_keywords = ['report', 'incident', 'suspicious', 'harassment', 'crime']
        if any(keyword in message_lower for keyword in report_keywords):
            return 'incident_report'
        
        return 'general_inquiry'
    
    def _generate_response(self, message: str, intent: str, user_location: Dict[str, Any]) -> Dict[str, Any]:
        """Generate appropriate response based on intent"""
        
        if intent == 'emergency':
            return self._handle_emergency(message, user_location)
        elif intent == 'safety_inquiry':
            return self._handle_safety_inquiry(message, user_location)
        elif intent == 'transport_inquiry':
            return self._handle_transport_inquiry(message, user_location)
        elif intent == 'incident_report':
            return self._handle_incident_report(message, user_location)
        else:
            return self._handle_general_inquiry(message, user_location)
    
    def _handle_emergency(self, message: str, user_location: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency situations"""
        return {
            'message': 'I understand this is an emergency. I am immediately connecting you with emergency services.',
            'type': 'emergency',
            'actions': [
                {
                    'type': 'emergency_alert',
                    'description': 'Emergency alert sent to authorities',
                    'contact': '112'
                },
                {
                    'type': 'location_share',
                    'description': 'Your location has been shared with emergency services'
                }
            ],
            'immediate_steps': [
                'Stay calm and find a safe location if possible',
                'Keep your phone with you',
                'Emergency services have been notified',
                'If safe to do so, move to a well-lit public area'
            ],
            'emergency_contacts': {
                'police': '117',
                'emergency': '112',
                'fire': '118'
            }
        }
    
    def _handle_safety_inquiry(self, message: str, user_location: Dict[str, Any]) -> Dict[str, Any]:
        """Handle safety-related inquiries"""
        lat = user_location.get('lat', 47.3769)
        lng = user_location.get('lng', 8.5417)
        
        return {
            'message': f'I can help you with safety information for your current area. Based on your location, here are some safety insights:',
            'type': 'safety_info',
            'safety_tips': [
                'Stay in well-lit areas, especially after dark',
                'Use main streets and avoid isolated shortcuts',
                'Keep your phone charged and accessible',
                'Trust your instincts - if something feels wrong, seek help',
                'Use public transport when available'
            ],
            'local_resources': [
                'Nearest police station: Zurich City Police',
                'Emergency number: 112',
                'Women\'s helpline: 143',
                'Transport security: +41 44 123 4567'
            ],
            'actions': [
                {
                    'type': 'safety_analysis',
                    'description': 'Get detailed safety analysis for your area'
                },
                {
                    'type': 'safe_routes',
                    'description': 'Find the safest route to your destination'
                }
            ]
        }
    
    def _handle_transport_inquiry(self, message: str, user_location: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transport-related inquiries"""
        return {
            'message': 'I can help you with safe transport options in Zurich.',
            'type': 'transport_info',
            'transport_safety_tips': [
                'Wait for transport in well-lit areas',
                'Sit near the driver or in visible areas',
                'Keep your belongings secure',
                'Be aware of your surroundings',
                'Use official ZVV app for real-time updates'
            ],
            'emergency_procedures': [
                'Emergency button available on trams and buses',
                'Contact transport security: +41 44 123 4567',
                'Report incidents via ZVV app or website'
            ],
            'actions': [
                {
                    'type': 'nearby_stops',
                    'description': 'Find nearby transport stops with safety ratings'
                },
                {
                    'type': 'real_time_updates',
                    'description': 'Get real-time transport updates'
                }
            ]
        }
    
    def _handle_incident_report(self, message: str, user_location: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incident reporting"""
        incident_id = f"INC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            'message': 'Thank you for reporting this incident. Your report has been logged and will be forwarded to the appropriate authorities.',
            'type': 'incident_report',
            'incident_id': incident_id,
            'next_steps': [
                'Your report has been assigned ID: ' + incident_id,
                'Authorities will be notified within 15 minutes',
                'You may be contacted for additional information',
                'Keep this incident ID for reference'
            ],
            'support_resources': [
                'Victim support: 0848 842 846',
                'Women\'s helpline: 143',
                'Police non-emergency: +41 44 411 71 17'
            ],
            'actions': [
                {
                    'type': 'follow_up',
                    'description': 'Schedule follow-up contact'
                },
                {
                    'type': 'support_services',
                    'description': 'Connect with support services'
                }
            ]
        }
    
    def _handle_general_inquiry(self, message: str, user_location: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general inquiries"""
        return {
            'message': 'I\'m here to help with your safety concerns in Zurich. I can assist with safety information, emergency situations, transport safety, and incident reporting.',
            'type': 'general_info',
            'available_services': [
                'Real-time safety analysis of your area',
                'Safe route recommendations',
                'Emergency assistance and alerts',
                'Transport safety information',
                'Incident reporting',
                'Connection with local authorities'
            ],
            'quick_actions': [
                'Ask about safety in your current area',
                'Get safe route to destination',
                'Report a safety concern',
                'Emergency help'
            ],
            'contact_info': self.authorities
        }
    
    def get_conversation_history(self) -> list:
        """Get conversation history"""
        return self.conversation_history
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []