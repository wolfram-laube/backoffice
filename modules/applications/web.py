#!/usr/bin/env python3
"""
WEB-VERSION - Bewerbungs-Tool
==============================
FastAPI-basierte Web-Oberfläche.

Status: 🚧 In Entwicklung

Geplante Features:
- [ ] Dashboard mit offenen Bewerbungen
- [ ] Formular zum Erstellen neuer Bewerbungen
- [ ] Gmail Draft per Klick
- [ ] CSV Import/Export
- [ ] Statistiken

Usage (lokal):
  uvicorn src.web:app --reload

Usage (Docker):
  docker run -p 8000:8000 bewerbung-tool
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

# ══════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════

app = FastAPI(
    title="Bewerbungs-Tool",
    description="Automatisiertes Tool für Freelance-Bewerbungen",
    version="1.0.0",
)

# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def root():
    """Landing Page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bewerbungs-Tool</title>
        <style>
            body { 
                font-family: system-ui, sans-serif; 
                max-width: 800px; 
                margin: 100px auto; 
                padding: 20px;
                text-align: center;
            }
            h1 { color: #2563eb; }
            .status { 
                background: #fef3c7; 
                border: 1px solid #f59e0b;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
            }
            code { 
                background: #f1f5f9; 
                padding: 2px 6px; 
                border-radius: 4px;
            }
            a { color: #2563eb; }
        </style>
    </head>
    <body>
        <h1>📧 Bewerbungs-Tool</h1>
        
        <div class="status">
            <h2>🚧 Web-Version in Entwicklung</h2>
            <p>Die Web-Oberfläche ist noch nicht fertig.</p>
            <p>Nutze vorerst das CLI-Tool:</p>
            <code>python src/bewerbung.py</code>
        </div>
        
        <h3>API Endpoints</h3>
        <ul style="list-style: none; padding: 0;">
            <li><a href="/health">/health</a> - Health Check</li>
            <li><a href="/api/bewerbungen">/api/bewerbungen</a> - Liste aller Bewerbungen</li>
            <li><a href="/docs">/docs</a> - Swagger UI</li>
        </ul>
        
        <h3>Roadmap</h3>
        <p>v2.0 - Web UI mit Dashboard, Formular, Gmail-Integration</p>
    </body>
    </html>
    """


@app.get("/health")
async def health():
    """Health Check für Docker/K8s."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/bewerbungen")
async def list_bewerbungen():
    """Liste aller konfigurierten Bewerbungen."""
    # Import hier um zirkuläre Imports zu vermeiden
    try:
        from src.bewerbung import BEWERBUNGEN
    except ImportError:
        # Fallback wenn als Modul importiert
        from bewerbung import BEWERBUNGEN
    
    return {
        "count": len(BEWERBUNGEN),
        "bewerbungen": [
            {
                "key": key,
                "name": bew["name"],
                "has_email": bew["to"] is not None,
                "freelancermap": bew.get("freelancermap"),
            }
            for key, bew in BEWERBUNGEN.items()
        ]
    }


@app.get("/api/bewerbungen/{key}")
async def get_bewerbung(key: str):
    """Details einer Bewerbung."""
    try:
        from src.bewerbung import BEWERBUNGEN
    except ImportError:
        from bewerbung import BEWERBUNGEN
    
    if key not in BEWERBUNGEN:
        return JSONResponse(
            status_code=404,
            content={"error": f"Bewerbung '{key}' nicht gefunden"}
        )
    
    bew = BEWERBUNGEN[key]
    return {
        "key": key,
        "name": bew["name"],
        "to": bew["to"],
        "subject": bew["subject"],
        "body": bew["body"],
        "freelancermap": bew.get("freelancermap"),
    }


# ══════════════════════════════════════════════════════════════
# FUTURE ENDPOINTS (v2.0)
# ══════════════════════════════════════════════════════════════

# @app.post("/api/bewerbungen/{key}/draft")
# async def create_draft(key: str):
#     """Erstellt Gmail Draft für Bewerbung."""
#     pass

# @app.post("/api/bewerbungen")
# async def create_bewerbung(bewerbung: BewerbungCreate):
#     """Neue Bewerbung anlegen."""
#     pass

# @app.get("/dashboard")
# async def dashboard():
#     """Dashboard mit Übersicht."""
#     pass
