#!/usr/bin/env python3
"""
Samba Manager - Web interface for managing Samba shares
Run this script to start the web application
"""

from app import create_app
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Samba Manager Web Interface')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--dev', action='store_true', help='Enable development mode (no sudo required)')
    args = parser.parse_args()
    
    # Set development mode if requested
    if args.dev:
        os.environ['SAMBA_MANAGER_DEV_MODE'] = '1'
        print("Running in development mode (no sudo required)")
    
    # Create and run the application
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()
