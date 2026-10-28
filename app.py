#!/usr/bin/env python3
"""
Guardian Swarm V3 — Application Entry Point
============================================
Launches the Flask web server locally. For production (Render / Gunicorn),
use wsgi.py instead:
    gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

from guardian_swarm.utils.paths import PROJECT_ROOT, ensure_project_paths

sys.path.insert(0, str(PROJECT_ROOT))
ensure_project_paths()

from guardian_swarm.web.server import app  # noqa: F401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    host = "0.0.0.0" if os.environ.get("FLASK_ENV") == "production" else "127.0.0.1"
    print(f"[Guardian Swarm] Starting on http://{host}:{port}  debug={debug}")
    app.run(host=host, port=port, debug=debug)
