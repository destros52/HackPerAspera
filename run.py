#!/usr/bin/env python3
"""
Zurich Women Safety App
Run script for development
"""

import os
import sys
from app import app

if __name__ == '__main__':
    # Set development environment
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    
    print("🛡️  Starting Zurich Women Safety App...")
    print("📍 Access the app at: http://localhost:5000")
    print("🚨 Emergency features enabled")
    print("💬 Chat with authorities available")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Stay safe!")
        sys.exit(0)