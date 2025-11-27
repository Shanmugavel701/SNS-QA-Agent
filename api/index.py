import os
import sys

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app
from mangum import Mangum

# Vercel handler with api_gateway_base_path to strip /api prefix
handler = Mangum(app, lifespan="off", api_gateway_base_path="/api")
