# Street Routing App (Python backend + Leaflet UI)

This project provides:
- **FastAPI** backend that automatically downloads **OpenStreetMap** street data for your area (via **OSMnx**) and caches it on disk.
- **A* routing** with edge length weights (works for `walk`, `bike`, or `drive` modes).
- **Leaflet** front-end to pick start/end points, call the backend, and visualize the route on top of real street tiles.

## Quick start

### 1) Install Python deps (prefer Python 3.10+)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Run the backend
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
The first request will **download** OSM street data for your area and **cache** it under `backend/data/`.

### 3) Open the UI
Just open `ui/index.html` in your browser (or serve the `ui/` folder from any static server).  
Update the backend URL at the top of the HTML if needed.

## Usage
- Click **"Pick A"** and then click on the map to set the origin.
- Click **"Pick B"** and then click on the map to set the destination.
- Choose a **mode** (walk/bike/drive).
- **Place** (optional): e.g., "Zurich, Switzerland". If not provided, the backend will compute a bounding box around A and B and download data automatically.
- Click **"Route"**. The route polyline appears and distance is shown.
- **Refresh graph** forces a redownload of the OSM graph, ignoring cache.

## Notes
- OSMnx fetches live data from OpenStreetMap on demand. Keep an eye on request limits if you route extremely often in many areas.
- For production, you may want to pre-download a city graph once (by calling the API with `force_refresh=true` and `place="Your City"`), then reuse it.
- Turn-by-turn is a basic list of street segments. For rich instructions, consider libraries like `osmnx.routing` helpers or external OSRM/GraphHopper.
