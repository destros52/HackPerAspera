from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import requests
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
from safety_analyzer import SafetyAnalyzer
from chat_handler import ChatHandler

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-in-production')
CORS(app)

# Initialize components
safety_analyzer = SafetyAnalyzer()
chat_handler = ChatHandler()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/safety-data')
def get_safety_data():
    """Get current safety assessment data for Zurich"""
    try:
        lat = request.args.get('lat', 47.3769)
        lng = request.args.get('lng', 8.5417)
        radius = request.args.get('radius', 1000)  # meters
        
        safety_data = safety_analyzer.analyze_area(float(lat), float(lng), int(radius))
        return jsonify(safety_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transport')
def get_transport_data():
    """Get real-time transport information"""
    try:
        lat = request.args.get('lat', 47.3769)
        lng = request.args.get('lng', 8.5417)
        
        transport_data = safety_analyzer.get_transport_safety(float(lat), float(lng))
        return jsonify(transport_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_with_authorities():
    """Handle chat messages with authorities via LangGraph"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        user_location = data.get('location', {})
        
        response = chat_handler.process_message(message, user_location)
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emergency', methods=['POST'])
def emergency_alert():
    """Handle emergency alerts"""
    try:
        data = request.get_json()
        location = data.get('location', {})
        emergency_type = data.get('type', 'general')
        
        alert_response = safety_analyzer.trigger_emergency_alert(location, emergency_type)
        return jsonify(alert_response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/safe-routes')
def get_safe_routes():
    """Get safe route recommendations"""
    try:
        start_lat = float(request.args.get('start_lat'))
        start_lng = float(request.args.get('start_lng'))
        end_lat = float(request.args.get('end_lat'))
        end_lng = float(request.args.get('end_lng'))
        
        routes = safety_analyzer.get_safe_routes(start_lat, start_lng, end_lat, end_lng)
        return jsonify(routes)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)