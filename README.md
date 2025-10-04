# 🛰️ NASA Safe Navigation Zurich - Women's Safety App

A satellite-powered, gender-aware urban navigation application that helps women return home safely at night in Zurich. Built on NASA satellite technology and research from "Invisible Women" by Caroline Criado Perez, addressing how urban infrastructure often overlooks women's safety needs.

## 🛰️ NASA Safe Navigation Layer

Our core innovation leverages NASA satellite technology, combining real-time satellite data, Zurich open city data, and advanced geospatial insights to build a "Safe Navigation Layer" that prioritizes:

### **Key Safety Factors:**
- **Street Lighting Data** (30% weight) - Mapping well-lit vs. dark areas at night
- **Pedestrian Flow Analysis** (25% weight) - Identifying crowded vs. empty streets by time
- **Emergency Proximity** (20% weight) - Distance to police stations & safe points
- **Visibility & Terrain** (15% weight) - Parks, tunnels, underpasses analysis
- **Construction & Events** (10% weight) - Temporary closures affecting safe routes

### **Features:**
- **Smart Route Planning**: Suggests safest walking routes (not shortest) prioritizing well-lit streets
- **Night Mode**: Enhanced safety analysis for evening/night hours
- **Real-time Safety Scoring**: 0-1 safety assessment for any location
- **Authority Chat**: LangGraph-powered AI assistant for emergency communication
- **Emergency Integration**: Direct connection to Zurich police (117) and emergency services (112)
- **Women-Specific Recommendations**: Based on gender-aware urban safety research

## 🌍 Impact & Scalability

- **For Citizens**: Reliable navigation tool increasing trust and safety, especially at night
- **For City Planners**: Urban safety dashboard showing where lighting/infrastructure improvements are needed
- **For Event Organizers**: Integration with festival planning for safe crowd dispersal
- **Scalable**: Any city with open data and satellite imagery can replicate the Safe Navigation Layer

## 🚀 Tech Stack

- **Backend**: Python Flask with NASA-powered Safe Navigation analysis engine
- **Frontend**: Space-themed responsive HTML5/CSS3/JavaScript with animated galaxy background
- **AI Chat**: LangGraph integration for authority communication
- **Data Sources**: NASA Satellite APIs, Zurich Open Data, Transport APIs
- **Maps**: Interactive Leaflet.js with satellite-powered safety overlays
- **UI/UX**: Futuristic space-themed interface with gradient animations

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables in `.env`
3. Run the application: `python app.py`

## API Endpoints

- `/api/safety-data` - Get current safety assessment data
- `/api/transport` - Get real-time transport information
- `/api/chat` - LangGraph chat interface
- `/api/emergency` - Emergency services integration