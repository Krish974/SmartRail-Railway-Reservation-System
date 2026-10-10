from flask import Blueprint, request
from backend.models.quota_model import QuotaModel
from backend.utils.helpers import api_response

quota_bp = Blueprint('quota_bp', __name__)

@quota_bp.route('/quotas', methods=['GET'])
def get_quotas():
    try:
        quotas = QuotaModel.get_all()
        return api_response(True, "Quotas retrieved successfully.", quotas)
    except Exception as e:
        return api_response(False, f"Failed to retrieve quotas: {str(e)}", None, 500)

@quota_bp.route('/quota/validate', methods=['POST'])
def validate_quota():
    data = request.get_json() or {}
    quota_code = data.get('quota_code', 'GN')
    passengers = data.get('passengers', [])

    is_valid, msg = QuotaModel.validate_eligibility(quota_code, passengers)
    if not is_valid:
        return api_response(False, msg, {"eligible": False}, 422)

    return api_response(True, msg, {"eligible": True}, 200)
