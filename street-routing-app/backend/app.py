#!/usr/bin/env python3
import os
import math
import json
from typing import Optional, List, Union, Dict, Any
import hashlib
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import networkx as nx

# Lazy imports (OSMnx and shapely are heavier); import when used
ox = None
shapely = None
from shapely.geometry import Point  # for snapping input points

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Street Routing API", version="1.0.0")

# Serve the UI (../ui) via FastAPI so that GET / and /ui works
UI_DIR = (APP_DIR.parent / ".." / "ui").resolve()
if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")


@app.get("/", include_in_schema=False)
def root():
    # Redirect to UI if present, else show simple message
    if UI_DIR.exists():
        return RedirectResponse(url="/ui/")
    return {"message": "Routing API is running. UI folder not found."}


@app.get("/index.html", include_in_schema=False)
def legacy_index():
    return RedirectResponse(url="/ui/")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Empty 204 to silence 404 spam
    return Response(status_code=204)


# Allow local dev UIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DangerPoint(BaseModel):
    lat: float
    lon: float
    score: float = 1.0


class RouteRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    place: Optional[str] = None      # e.g., "Zurich, Switzerland"
    mode: str = "walk"               # walk, bike, drive
    force_refresh: bool = True       # ignore cache and redownload area graph
    route_pref: str = "short"        # short | safe (fast → short)
    extra_danger: Optional[List[DangerPoint]] = None  # manual points from UI


def _ensure_imports():
    global ox, shapely
    if ox is None:
        import osmnx as ox_  # type: ignore
        ox = ox_
    if shapely is None:
        import shapely.geometry as shapely_  # type: ignore
        shapely = shapely_


def _graph_cache_key(place: Optional[str], mode: str, bbox=None) -> Path:
    m = hashlib.sha1()
    key = f"{place or ''}|{mode}|{bbox or ''}"
    m.update(key.encode("utf-8"))
    return DATA_DIR / f"graph_{m.hexdigest()}.graphml"


def _load_graph(place: Optional[str], mode: str, bbox=None, force_refresh=False):
    _ensure_imports()
    cache_path = _graph_cache_key(place, mode, bbox)
    if cache_path.exists() and not force_refresh:
        return ox.load_graphml(cache_path)
    # Download from OSM
    if place:
        G = ox.graph_from_place(place, network_type=mode, simplify=True)
    elif bbox:
        north, south, east, west = bbox
        G = ox.graph_from_bbox(
            north, south, east, west,
            network_type=mode, simplify=True,
            retain_all=True, clean_periphery=True
        )
    else:
        raise HTTPException(status_code=400, detail="Either 'place' or 'bbox' must be provided.")
    # Save cache
    ox.save_graphml(G, cache_path)
    return G


def _haversine(u, v):
    # Heuristic for A* (meters), using WGS84 approx
    R = 6371000.0
    lat1, lon1 = math.radians(u[0]), math.radians(u[1])
    lat2, lon2 = math.radians(v[0]), math.radians(v[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _route_to_geojson(G, route_nodes):
    _ensure_imports()
    # Build a LineString from the route edges
    lines = []
    for u, v in zip(route_nodes[:-1], route_nodes[1:]):
        data = min(G.get_edge_data(u, v).values(), key=lambda d: d.get("length", 0))
        if "geometry" in data:
            geom = data["geometry"]
        else:
            # Straight line between nodes
            p1 = (G.nodes[u]["y"], G.nodes[u]["x"])  # (lat, lon)
            p2 = (G.nodes[v]["y"], G.nodes[v]["x"])
            geom = shapely.LineString([p1[::-1], p2[::-1]])  # lon,lat
        if getattr(geom, "geom_type", "") == "MultiLineString":
            # iterate parts of MultiLineString
            for part in geom:
                lines.append(part)
        else:
            lines.append(geom)

    # Merge lines if possible
    try:
        from shapely.ops import linemerge
        merged = linemerge(lines)
        if merged.geom_type == "MultiLineString":
            coords = [list(line.coords) for line in merged]
        else:
            coords = [list(merged.coords)]
    except Exception:
        coords = [list(line.coords) for line in lines]

    # Collect street names for basic turn hints
    steps = []
    total_len = 0.0
    for u, v in zip(route_nodes[:-1], route_nodes[1:]):
        data = min(G.get_edge_data(u, v).values(), key=lambda d: d.get("length", 0))
        street = data.get("name", "unnamed")
        length = float(data.get("length", 0.0))
        steps.append({"from": int(u), "to": int(v), "street": street, "length_m": round(length, 1)})
        total_len += length

    feature_route = {
        "type": "Feature",
        "properties": {
            "distance_m": round(total_len, 1),
            "steps": steps,
        },
        "geometry": {
            "type": "MultiLineString" if len(coords) > 1 else "LineString",
            "coordinates": coords if len(coords) > 1 else coords[0],
        },
    }
    return {
        "type": "FeatureCollection",
        "features": [feature_route],
    }


# ---- Hazards storage (computed like pedestrians) ----
HAZARDS_FILE = (DATA_DIR / "hazards.geojson")


def _load_hazards():
    pts = []
    try:
        if HAZARDS_FILE.exists():
            gj = json.loads(HAZARDS_FILE.read_text(encoding="utf-8"))
            feats = gj.get("features", [])
            for f in feats:
                if (f.get("geometry") or {}).get("type") != "Point":
                    continue
                coords = f["geometry"].get("coordinates") or []
                if len(coords) < 2:
                    continue
                lon, lat = coords[0], coords[1]
                props = f.get("properties", {}) or {}
                sc = float(props.get("safety_score", props.get("score", 1.0)))
                sc = 0.0 if sc < 0 else (1.0 if sc > 1.0 else sc)
                pts.append((lat, lon, sc))
    except Exception as e:
        print("Hazards load error:", e)
    return pts


def _save_hazards(items):
    # Save hazards as FeatureCollection; items can be list of (lat,lon,score) or dicts.
    feats = []
    for it in items:
        if isinstance(it, dict):
            lat = float(it.get("lat")); lon = float(it.get("lon")); sc = float(it.get("score", 1.0))
        else:
            lat, lon, sc = it
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"score": max(0.0, min(1.0, sc))}
        })
    HAZARDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"type": "FeatureCollection", "features": feats}
    HAZARDS_FILE.write_text(json.dumps(data), encoding="utf-8")
    return data


@app.get("/hazards")
def get_hazards():
    if not HAZARDS_FILE.exists():
        return {"type": "FeatureCollection", "features": []}
    try:
        return json.loads(HAZARDS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read hazards: {e}")


class HazardPoint(BaseModel):
    lat: float
    lon: float
    score: float = 1.0


@app.post("/hazards")
def post_hazards(payload: Union[Dict[str, Any], List[HazardPoint]]):
    # Accepts either a GeoJSON FeatureCollection or a list of {lat,lon,score} and stores it.
    try:
        items = []
        if isinstance(payload, list):
            for hp in payload:
                if isinstance(hp, dict):
                    items.append({"lat": float(hp.get("lat")), "lon": float(hp.get("lon")), "score": float(hp.get("score", 1.0))})
                else:
                    items.append({"lat": float(hp.lat), "lon": float(hp.lon), "score": float(hp.score)})
        else:
            # Assume GeoJSON FeatureCollection
            feats = (payload.get("features") or [])
            for f in feats:
                if (f.get("geometry") or {}).get("type") != "Point":
                    continue
                coords = f["geometry"].get("coordinates") or []
                if len(coords) < 2:
                    continue
                lon, lat = coords[0], coords[1]
                props = f.get("properties", {}) or {}
                sc = float(props.get("safety_score", props.get("score", 1.0)))
                items.append({"lat": lat, "lon": lon, "score": sc})
        data = _save_hazards(items)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse hazards: {e}")


@app.delete("/hazards")
def delete_hazards():
    try:
        if HAZARDS_FILE.exists():
            HAZARDS_FILE.unlink()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete hazards: {e}")
# ---- end hazards ----


@app.get("/api/ping")
def ping():
    return {"ok": True}


@app.post("/api/route")
def route(req: RouteRequest):
    _ensure_imports()
    # Validate mode
    mode = req.mode.lower()
    if mode not in {"walk", "bike", "drive"}:
        raise HTTPException(status_code=400, detail="mode must be one of: walk, bike, drive")

    # Determine area: If place not provided, derive a small bounding box around A & B
    bbox = None
    if not req.place:
        # Add buffer (~2km) around both points
        north = max(req.origin_lat, req.dest_lat) + 0.05
        south = min(req.origin_lat, req.dest_lat) - 0.05
        east = max(req.origin_lon, req.dest_lon) + 0.05
        west = min(req.origin_lon, req.dest_lon) - 0.05
        bbox = (north, south, east, west)

    try:
        G = _load_graph(req.place, mode, bbox=bbox, force_refresh=req.force_refresh)
        try:
            ox.add_edge_lengths(G)
        except Exception:
            pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load graph: {e}")

    # Project to speed up distance metrics
    try:
        Gp = ox.project_graph(G)
    except Exception:
        Gp = G  # fallback

    # ---- Safety weighting (lighting-aware) ----
    route_pref = (getattr(req, "route_pref", "short") or "short").lower()
    if route_pref == "fast":
        route_pref = "short"  # alias fast->short

    # Collect lighting points from cache
    lights_pts = []
    try:
        gj_l = _load_lighting_cached(LIGHTING_CACHE.stat().st_mtime if LIGHTING_CACHE.exists() else None)
        for f in gj_l.get("features", []):
            g = (f.get("geometry") or {})
            if g.get("type") == "Point":
                lon, lat = g.get("coordinates", [None, None])[:2]
                if lon is not None and lat is not None:
                    lights_pts.append((lat, lon))
    except Exception:
        lights_pts = []

    # Parameters for density & danger
    SAFE_SIGMA = 40.0      # m, influence of each light
    SAMPLE_STEP = 15.0     # m, sampling step
    SAFE_ALPHA = 3.0       # lighting strength
    SAFE_EPS = 1e-6

    # Pedestrians (danger) parameters
    PEDS_SIGMA = 30.0      # m: influence radius of each pedestrian/hazard point
    PEDS_ALPHA = 3.0       # (kept for extensibility)
    PEDS_GAMMA = 2.0       # non-linear boost
    PEDS_RADIUS = 100.0    # m: only points within this radius affect the weight
    PEDS_WEIGHT = 6.0      # additive weight multiplier
    HIGH_RISK_THRESHOLD = 0.85
    HIGH_RISK_RADIUS = PEDS_RADIUS
    HIGH_RISK_JUMP = 20.0  # big additive penalty if any high-risk point is near

    # load pedestrians + hazards as a unified danger set
    ped_pts = _load_pedestrians()
    ped_pts += _load_hazards()

    # manual extra danger points (from request)
    try:
        for dp in (getattr(req, 'extra_danger', None) or []):
            lat = float(getattr(dp, 'lat', dp.get('lat')))
            lon = float(getattr(dp, 'lon', dp.get('lon')))
            sc = float(getattr(dp, 'score', dp.get('score', 1.0)))
            if sc < 0:
                sc = 0.0
            if sc > 1:
                sc = 1.0
            ped_pts.append((lat, lon, sc))
    except Exception:
        pass

    ped_sigma2 = PEDS_SIGMA * PEDS_SIGMA
    ped_inv_twosig2 = 1.0 / (2.0 * ped_sigma2)

    def _edge_ped_stats(u, v):
        if not ped_pts:
            return 0.0, 0.0
        uy, ux = G.nodes[u].get("y"), G.nodes[u].get("x")
        vy, vx = G.nodes[v].get("y"), G.nodes[v].get("x")
        if None in (uy, ux, vy, vx):
            return 0.0, 0.0
        L = _haversine((uy, ux), (vy, vx))
        if L <= 0.0:
            return 0.0, 0.0
        n = max(1, int(L / SAMPLE_STEP))
        acc = 0.0
        peak = 0.0
        for i in range(n + 1):
            t = i / n
            sy = uy + (vy - uy) * t
            sx = ux + (vx - ux) * t
            loc = (sy, sx)
            s = 0.0
            for (py, px, score) in ped_pts:
                if score <= 0.0:
                    continue
                d = _haversine(loc, (py, px))
                if d > PEDS_RADIUS:
                    continue
                s += (score ** PEDS_GAMMA) * math.exp(- (d * d) * ped_inv_twosig2)
                if score >= HIGH_RISK_THRESHOLD and d <= HIGH_RISK_RADIUS:
                    peak = 1.0
            acc += s
        return acc / (n + 1), peak

    # Additional: penalize dark edges
    MIN_DENSITY = 0.05  # below this -> dark
    DARKNESS_PENALTY = 2.0

    sigma2 = SAFE_SIGMA * SAFE_SIGMA
    inv_twosig2 = 1.0 / (2.0 * sigma2)

    def _edge_density(u, v):
        # approximate the edge as straight line between node coords, sample along it
        uy, ux = G.nodes[u].get("y"), G.nodes[u].get("x")
        vy, vx = G.nodes[v].get("y"), G.nodes[v].get("x")
        if None in (uy, ux, vy, vx) or not lights_pts:
            return 0.0
        # edge length (meters)
        L = _haversine((uy, ux), (vy, vx))
        if L <= 0.0:
            return 0.0
        # number of samples (at least 1)
        n = max(1, int(L / SAMPLE_STEP))
        acc = 0.0
        # linear interpolation of lat/lon (small segments, ok to approximate)
        for i in range(n + 1):
            t = i / n
            sy = uy + (vy - uy) * t
            sx = ux + (vx - ux) * t
            # sum Gaussian kernels from nearby lights
            loc = (sy, sx)
            s = 0.0
            for (ly, lx) in lights_pts:
                d = _haversine(loc, (ly, lx))
                if d > SAFE_SIGMA * 4:
                    continue
                s += math.exp(- (d * d) * inv_twosig2)
            acc += s
        # average density per sample
        return acc / (n + 1)

    def _edge_weight(u, v, attrs):
        base = float(attrs.get("length", 1.0))
        # SHORT: strictly shortest path by length
        if route_pref == "short":
            return base
        # SAFE: lighting-aware + pedestrians/hazards
        if route_pref == "safe" and lights_pts:
            dens = _edge_density(u, v)
            # more density -> smaller weight (prefer lit areas)
            pen = DARKNESS_PENALTY if dens < MIN_DENSITY else 1.0
            # lighting term (smaller in bright areas)
            dark_term = (1.0 / (SAFE_EPS + SAFE_ALPHA * dens)) * pen
            # pedestrians/hazards terms
            ped_danger, ped_peak = _edge_ped_stats(u, v)
            ped_term = PEDS_WEIGHT * ped_danger + HIGH_RISK_JUMP * ped_peak
            return max(0.1, dark_term + ped_term)
        # fallback (no lights or unknown pref): length
        return base
    # ---- end safety block ----

    # Find nearest nodes (project points to graph CRS to avoid scikit-learn dependency)
    try:
        ptA = Point(req.origin_lon, req.origin_lat)
        ptB = Point(req.dest_lon, req.dest_lat)
        # Project input points into the projected graph's CRS
        ptA_proj, _ = ox.projection.project_geometry(ptA, to_crs=Gp.graph.get('crs'))
        ptB_proj, _ = ox.projection.project_geometry(ptB, to_crs=Gp.graph.get('crs'))
        orig = ox.nearest_nodes(Gp, X=ptA_proj.x, Y=ptA_proj.y)
        dest = ox.nearest_nodes(Gp, X=ptB_proj.x, Y=ptB_proj.y)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to snap to network: {e}")

    # A* with length weight and planar heuristic (projected CRS)
    def h(u, v):
        ux, uy = Gp.nodes[u].get("x"), Gp.nodes[u].get("y")
        vx, vy = Gp.nodes[v].get("x"), Gp.nodes[v].get("y")
        if None in (ux, uy, vx, vy):
            return 0.0
        return math.hypot(ux - vx, uy - vy)

    try:
        route_nodes = nx.astar_path(
            Gp, orig, dest,
            heuristic=h,
            weight=("length" if route_pref == "short" else _edge_weight)
        )
    except nx.NetworkXNoPath:
        raise HTTPException(status_code=404, detail="No route found between points.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing failed: {e}")

    return _route_to_geojson(G, route_nodes)


# ===================== Lighting data (download + serve) =====================
from functools import lru_cache
import urllib.request
import urllib.parse
from datetime import datetime

LIGHTING_CACHE = DATA_DIR / "lighting.geojson"
PEDESTRIANS_FILES = [
    DATA_DIR / "pedestrians.geojson",
    (UI_DIR / "pedestrians.geojson") if 'UI_DIR' in globals() else None
]
PEDESTRIANS_FILES = [p for p in PEDESTRIANS_FILES if p]
_PED_CACHE = {"pts": None, "mtime": None}  # [(lat,lon,score)]

DEFAULT_LIGHTING_URL = os.environ.get(
    "LIGHTING_URL",
    "https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Oeffentliche_Beleuchtung_der_Stadt_Zuerich"
    "?service=WFS&request=GetFeature&version=2.0.0&typeName=ewz_brennstelle_p&outputFormat=application/json&srsName=EPSG:4326"
)


def _load_pedestrians():
    # Load and cache pedestrians points with safety_score ∈ [0,1]
    try:
        path = None
        for p in PEDESTRIANS_FILES:
            try:
                if p and p.exists():
                    path = p
                    break
            except Exception:
                continue
        if not path:
            return []
        mtime = path.stat().st_mtime
        if _PED_CACHE["pts"] is not None and _PED_CACHE["mtime"] == mtime:
            return _PED_CACHE["pts"]
        with open(path, "r", encoding="utf-8") as fh:
            gj = json.load(fh)
        pts = []
        for f in gj.get("features", []):
            g = f.get("geometry") or {}
            if g.get("type") == "Point":
                lon, lat = g.get("coordinates", [None, None])[:2]
                score = f.get("properties", {}).get("safety_score", 0)
                try:
                    score = float(score)
                except Exception:
                    score = 0.0
                # clamp to [0,1]
                if score < 0: score = 0.0
                if score > 1: score = 1.0
                if lon is not None and lat is not None:
                    pts.append((lat, lon, score))
        _PED_CACHE["pts"] = pts
        _PED_CACHE["mtime"] = mtime
        return pts
    except Exception:
        return []


def _bbox_filter(features, bbox):
    if not bbox:
        return features
    minx, miny, maxx, maxy = bbox  # lon/lat order
    out = []
    for f in features:
        try:
            geom = f.get("geometry") or {}
            if geom.get("type") == "Point":
                lon, lat = geom["coordinates"][:2]
                if (minx <= lon <= maxx) and (miny <= lat <= maxy):
                    out.append(f)
            elif geom.get("type") in ("LineString", "MultiPoint", "MultiLineString", "Polygon", "MultiPolygon"):
                # quick bbox via all coords
                def iter_coords(g):
                    t = g.get("type")
                    c = g.get("coordinates")
                    if t == "Point":
                        yield c
                    elif t in ("MultiPoint", "LineString"):
                        for p in c:
                            yield p
                    elif t in ("MultiLineString", "Polygon"):
                        for ring in c:
                            for p in ring:
                                yield p
                    elif t == "MultiPolygon":
                        for poly in c:
                            for ring in poly:
                                for p in ring:
                                    yield p
                ok = False
                for p in iter_coords(geom):
                    lon, lat = p[:2]
                    if (minx <= lon <= maxx) and (miny <= lat <= maxy):
                        ok = True
                        break
                if ok:
                    out.append(f)
        except Exception:
            pass
    return out


def _download_lighting(url: str) -> dict:
    if not url:
        raise HTTPException(status_code=400, detail="Lighting URL is not configured. Set LIGHTING_URL env or pass ?url=")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
        gj = json.loads(data.decode("utf-8"))
        # minimal validation
        if gj.get("type") != "FeatureCollection":
            raise ValueError("Expected GeoJSON FeatureCollection")
        # Save with metadata
        payload = {
            "type": "FeatureCollection",
            "features": gj.get("features", []),
            "properties": {
                "downloaded_at": datetime.utcnow().isoformat() + "Z",
                "source_url": url,
                "count": len(gj.get("features", [])),
            },
        }
        LIGHTING_CACHE.write_text(json.dumps(payload))
        return payload
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to download lighting data: {e}")


@lru_cache(maxsize=1)
def _load_lighting_cached(cache_mtime: Optional[float] = None) -> dict:
    # cache key includes mtime so we can invalidate
    if not LIGHTING_CACHE.exists():
        return {"type": "FeatureCollection", "features": [], "properties": {"count": 0}}
    try:
        return json.loads(LIGHTING_CACHE.read_text())
    except Exception:
        return {"type": "FeatureCollection", "features": [], "properties": {"count": 0}}


def _invalidate_lighting_cache():
    _load_lighting_cached.cache_clear()


@app.get("/lighting/download")
def lighting_download(url: Optional[str] = Query(None, description="GeoJSON URL (FeatureCollection)")):
    payload = _download_lighting(url or DEFAULT_LIGHTING_URL)
    _invalidate_lighting_cache()
    return {"status": "ok", "saved": str(LIGHTING_CACHE), "count": payload["properties"]["count"]}


@app.get("/lighting")
def lighting(bbox: Optional[str] = Query(None, description="minLon,minLat,maxLon,maxLat"),
             limit: Optional[int] = Query(None, ge=1, le=10000)):

    # ensure data available (best-effort)
    if not LIGHTING_CACHE.exists() and DEFAULT_LIGHTING_URL:
        try:
            _download_lighting(DEFAULT_LIGHTING_URL)
        except Exception as e:
            # log but do not fail request
            print('Lighting download failed (non-fatal):', e)
    mtime = LIGHTING_CACHE.stat().st_mtime if LIGHTING_CACHE.exists() else None
    gj = _load_lighting_cached(mtime)

    features = gj.get("features", [])

    # bbox filter
    bbox_vals = None
    if bbox:
        try:
            parts = [float(x) for x in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError
            bbox_vals = parts
        except Exception:
            raise HTTPException(status_code=400, detail="bbox must be 'minLon,minLat,maxLon,maxLat'")

    features = _bbox_filter(features, bbox_vals)
    if limit:
        features = features[:limit]

    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "count": len(features),
            "total_count": gj.get("properties", {}).get("count", len(gj.get("features", []))),
            "source_url": gj.get("properties", {}).get("source_url"),
            "cached": bool(LIGHTING_CACHE.exists()),
        }
    }


@app.on_event("startup")
async def _warmup_lighting():
    try:
        if not LIGHTING_CACHE.exists() and DEFAULT_LIGHTING_URL:
            _download_lighting(DEFAULT_LIGHTING_URL)
    except Exception as e:
        print('Startup lighting warmup failed (non-fatal):', e)


@app.get("/geocode")
def geocode(q: Optional[str] = Query(None, min_length=1), limit: Optional[int] = Query(7, ge=1, le=15)):
    """Forward geocoding via Nominatim (OSM), restricted to Zurich and partial matches."""
    q = (q or "").strip()
    if not q:
        return []
    try:
        # Zurich bounding box (left, top, right, bottom)
        # Approx: 8.45,47.46,8.65,47.32 (city and close suburbs)
        viewbox = "8.45,47.46,8.65,47.32"
        params = {
            "q": q,
            "format": "jsonv2",
            "limit": limit or 7,
            "addressdetails": 1,          # include address to check city
            "countrycodes": "ch",         # Switzerland only
            "viewbox": viewbox,           # search box around Zürich
            "bounded": 1                  # restrict results to viewbox
        }
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            "User-Agent": "StreetRouter-Demo/1.0 (contact: example@example.com)",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # Filter: inside bbox
        l, t, r, b = [float(x) for x in viewbox.split(",")]
        q_tokens = [tok for tok in q.lower().split() if len(tok) >= 2]
        out = []
        for d in data:
            try:
                lat = float(d["lat"]); lon = float(d["lon"])
                if not (l <= lon <= r and b <= lat <= t):
                    continue
                addr = (d.get("address") or {})
                city_name = (addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("county") or "") or ""
                # allow inside bbox even if name differs
                display = d.get("display_name") or ""
                disp_l = display.lower()
                if any(tok not in disp_l for tok in q_tokens):
                    pass
                out.append({
                    "display_name": display,
                    "lat": lat,
                    "lon": lon,
                })
            except Exception:
                pass
        # Deduplicate by rounded coordinate
        seen = set()
        unique = []
        for it in out:
            key = (round(it["lat"], 5), round(it["lon"], 5))
            if key in seen:
                continue
            seen.add(key)
            unique.append(it)
        return unique[: (limit or 7)]
    except Exception as e:
        print("Geocode error:", e)
        return []
