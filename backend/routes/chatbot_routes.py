from flask import Blueprint, request
from backend.ml.chatbot_model import process_chatbot_query
from backend.utils.helpers import api_response

chatbot_bp = Blueprint('chatbot_bp', __name__)

@chatbot_bp.route('/chatbot', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    session_id = data.get('session_id') or request.remote_addr or 'default'

    if not message:
        return api_response(False, "Message cannot be empty.", None, 400)

    try:
        reply = process_chatbot_query(message, session_id=session_id)
        return api_response(True, "Response generated.", reply)
    except Exception as e:
        return api_response(False, f"Chatbot processing error: {str(e)}", None, 500)
