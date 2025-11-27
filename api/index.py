import os
import sys
import json

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app
from mangum import Mangum

# Custom handler that properly handles Vercel paths
def handler(event, context):
    # Log the incoming path for debugging
    print(f"Received event path: {event.get('path', 'NO PATH')}")
    print(f"Received event rawPath: {event.get('rawPath', 'NO RAWPATH')}")
    print(f"Full event keys: {event.keys()}")
    
    # Create Mangum handler without base path first
    mangum_handler = Mangum(app, lifespan="off")
    
    # Call the handler
    return mangum_handler(event, context)
