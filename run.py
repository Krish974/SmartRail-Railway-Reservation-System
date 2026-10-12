#!/usr/bin/env python
"""
Smart Indian Railway Ticket Reservation System
Main Entry Point
"""

import os
import sys

# Add project root to sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

from backend.app import create_app
from backend.utils.db_connection import get_db_type

# Expose WSGI application object for Gunicorn, Waitress, and cloud platforms
app = create_app()

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    db_type = get_db_type()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    print("=" * 70)
    print("[*] SMART INDIAN RAILWAY TICKET RESERVATION SYSTEM")
    print("=" * 70)
    print(f"- Active Database   : {db_type.upper()}")
    print(f"- Server Running at : http://127.0.0.1:{port}")
    print(f"- API Health Check  : http://127.0.0.1:{port}/api/health")
    print("-" * 70)
    print("[-] DEMO CREDENTIALS:")
    print("  - Admin : admin@railway.gov.in / Admin@12345")
    print("  - User  : rahul.sharma@example.com / User@12345")
    print("  - User  : priya.patel@example.com / User@12345")
    print("[-] SAMPLE PNRS:")
    print("  - 2846190532 (Confirmed)")
    print("  - 4198273641 (RAC)")
    print("  - 6720491823 (Waitlist with AI Prediction)")
    print("=" * 70)
    print("Press CTRL+C to stop the server.\n")

    app.run(host='0.0.0.0', port=port, debug=debug)
