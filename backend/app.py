import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.utils.db_connection import init_db
from backend.utils.helpers import api_response

# Import all blueprints
from backend.routes.auth_routes import auth_bp
from backend.routes.train_routes import train_bp
from backend.routes.seat_routes import seat_bp
from backend.routes.quota_routes import quota_bp
from backend.routes.booking_routes import booking_bp
from backend.routes.pnr_routes import pnr_bp
from backend.routes.tracking_routes import tracking_bp
from backend.routes.chatbot_routes import chatbot_bp
from backend.routes.emergency_routes import emergency_bp
from backend.routes.admin_routes import admin_bp
from backend.routes.food_routes import food_bp

def create_app():
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    app.config.from_object(Config)

    # Enable CORS for all routes
    CORS(app, supports_credentials=True)

    # Initialize Database and seed if needed
    try:
        init_db()
    except Exception as e:
        print(f"[APP DB INIT WARNING] {e}")

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(train_bp, url_prefix='/api')
    app.register_blueprint(seat_bp, url_prefix='/api')
    app.register_blueprint(quota_bp, url_prefix='/api')
    app.register_blueprint(booking_bp, url_prefix='/api')
    app.register_blueprint(pnr_bp, url_prefix='/api')
    app.register_blueprint(tracking_bp, url_prefix='/api')
    app.register_blueprint(chatbot_bp, url_prefix='/api')
    app.register_blueprint(emergency_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    app.register_blueprint(food_bp, url_prefix='/api/food')

    # Frontend Page Routes (Dual access mode: works through Flask or standalone HTTP)
    @app.route('/')
    def serve_index():
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/food-order')
    def serve_food_order():
        return send_from_directory(frontend_dir, 'food-order.html')

    @app.route('/food-checkout')
    def serve_food_checkout():
        return send_from_directory(frontend_dir, 'food-checkout.html')

    @app.route('/food-order-tracking/<order_id>')
    @app.route('/food-order-tracking')
    def serve_food_tracking(order_id=None):
        return send_from_directory(frontend_dir, 'food-order-tracking.html')

    @app.route('/<path:path>')
    def serve_frontend(path):
        target_path = os.path.join(frontend_dir, path)
        if os.path.exists(target_path):
            return send_from_directory(frontend_dir, path)
        # Check if path.html exists
        if os.path.exists(target_path + '.html'):
            return send_from_directory(frontend_dir, path + '.html')
        return send_from_directory(frontend_dir, 'index.html')


    # Global Error Handlers
    @app.errorhandler(404)
    def not_found(e):
        return api_response(False, "Requested resource or endpoint was not found.", None, 404)

    @app.errorhandler(500)
    def server_error(e):
        return api_response(False, f"Internal server error occurred: {str(e)}", None, 500)

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return api_response(True, "Smart Indian Railway API Gateway is online and operational.", {
            "status": "HEALTHY",
            "version": "2.0.0"
        })

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
