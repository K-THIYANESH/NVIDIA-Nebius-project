#!/usr/bin/env python3
"""
WSGI entry-point for Gunicorn / Render Web Service auto-deploy.

Usage (local test):
    gunicorn wsgi:app --bind 0.0.0.0:5000 --workers 2 --timeout 120

Render start command:
    gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
"""

import os
from dotenv import load_dotenv

load_dotenv()

from guardian_swarm.utils.paths import PROJECT_ROOT, ensure_project_paths
import sys
sys.path.insert(0, str(PROJECT_ROOT))
ensure_project_paths()

from guardian_swarm.web.server import app  # noqa: F401  — exported for Gunicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
