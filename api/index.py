import os
import sys

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mangum import Mangum
from backend.app import app

# Create the Mangum adapter
mangum_handler = Mangum(app)

# Vercel expects a function named 'handler'
def handler(event, context):
    return mangum_handler(event, context)
