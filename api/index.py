import os
import sys

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app

# Set root_path for the app to handle /api prefix
app.root_path = "/api"

# Export the app directly for Vercel
# Vercel will handle ASGI automatically
handler = app
