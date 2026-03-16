BACKEND_VULNERABILITIES = (
    {
        "id": "unauthenticated_control_access",
        "severity": "high",
        "surface": ["/", "/ws"],
        "summary": "The backend exposes its HTTP and websocket control surfaces without authentication or authorization.",
        "evidence": [
            "backend/main.py registers the root route and the /ws websocket route directly.",
            "backend/api/websocket_manager/manager.py accepts websocket connections without validating identity or permissions.",
        ],
        "remediation": "Require authenticated clients before serving control routes or accepting websocket sessions.",
    },
    {
        "id": "permissive_cors_policy",
        "severity": "medium",
        "surface": ["/", "/ws", "/songs", "/meta"],
        "summary": "The backend allows cross-origin requests from any origin with every method and header enabled.",
        "evidence": [
            "backend/main.py configures CORSMiddleware with allow_origins=['*'].",
            "backend/main.py also enables allow_methods=['*'] and allow_headers=['*'].",
        ],
        "remediation": "Limit CORS origins, methods, and headers to the trusted frontend deployment.",
    },
    {
        "id": "unauthenticated_static_asset_exposure",
        "severity": "medium",
        "surface": ["/songs", "/meta"],
        "summary": "Song audio files and analyzer metadata are served as static files without access control.",
        "evidence": [
            "backend/main.py mounts /songs from the songs directory via StaticFiles.",
            "backend/main.py mounts /meta from the metadata directory via StaticFiles.",
        ],
        "remediation": "Protect static routes with authentication or serve time-limited URLs for authorized clients only.",
    },
)


def list_backend_vulnerabilities():
    vulnerabilities = [dict(item) for item in BACKEND_VULNERABILITIES]
    return {"count": len(vulnerabilities), "vulnerabilities": vulnerabilities}
