import os
import sys
import json
import unittest

# Ensure repo root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import create_app
from backend.models.tte_model import TTEAssistanceModel, generate_tte_request_id, ensure_tte_table
from backend.ml.chatbot_model import process_chatbot_query

class TestTTEAssistance(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        ensure_tte_table()

    def test_01_id_generation(self):
        req_id = generate_tte_request_id()
        self.assertTrue(req_id.startswith("TTE-"))
        parts = req_id.split("-")
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[1]), 8)  # YYYYMMDD
        self.assertEqual(len(parts[2]), 5)  # 5-digit number or ms

    def test_02_model_crud(self):
        req = TTEAssistanceModel.create_request(
            train_number="12952",
            journey_date="2026-10-15",
            assistance_type="Berth / Seat Issue",
            description="Another passenger has occupied my lower berth 36.",
            coach="B1",
            berth="36",
            pnr="8234567890",
            train_name="Mumbai Rajdhani"
        )
        self.assertIsNotNone(req)
        self.assertTrue(req['request_id'].startswith("TTE-"))
        self.assertEqual(req['status'], "Pending")
        self.assertEqual(req['coach'], "B1")
        self.assertEqual(req['berth'], "36")
        self.assertEqual(req['pnr'], "8234567890")

        # Fetch by ID
        fetched = TTEAssistanceModel.get_by_request_id(req['request_id'])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched['train_number'], "12952")
        self.assertEqual(fetched['assistance_type'], "Berth / Seat Issue")

        # Update status
        updated = TTEAssistanceModel.update_status(req['request_id'], "Resolved")
        self.assertEqual(updated['status'], "Resolved")

        # Invalid status should raise ValueError
        with self.assertRaises(ValueError):
            TTEAssistanceModel.update_status(req['request_id'], "InvalidStatus")

    def test_03_api_post_valid_request(self):
        payload = {
            "train_number": "12952",
            "journey_date": "2026-10-20",
            "assistance_type": "Wrong Passenger Occupying Berth",
            "description": "Passenger refuses to vacate reserved seat in coach B2 berth 42.",
            "coach": "B2",
            "berth": "42",
            "pnr": "9876543210"
        }
        res = self.client.post('/api/emergency/tte',
                               data=json.dumps(payload),
                               content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['request_id'].startswith('TTE-'))
        self.assertEqual(data['data']['status'], 'Pending')

    def test_04_api_validations(self):
        # Missing train number
        res = self.client.post('/api/emergency/tte',
                               data=json.dumps({
                                   "journey_date": "2026-10-20",
                                   "assistance_type": "Berth / Seat Issue",
                                   "description": "Help needed"
                               }),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)

        # Missing date
        res = self.client.post('/api/emergency/tte',
                               data=json.dumps({
                                   "train_number": "12952",
                                   "assistance_type": "Berth / Seat Issue",
                                   "description": "Help needed"
                               }),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)

        # Invalid PNR length
        res = self.client.post('/api/emergency/tte',
                               data=json.dumps({
                                   "train_number": "12952",
                                   "journey_date": "2026-10-20",
                                   "assistance_type": "Berth / Seat Issue",
                                   "description": "Help needed with berth",
                                   "pnr": "12345"
                               }),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)
        self.assertIn("PNR must be a valid 10-digit", res.get_json()['message'])

    def test_05_api_tracking_and_admin_update(self):
        # Create request first
        res = self.client.post('/api/emergency/tte',
                               data=json.dumps({
                                   "train_number": "12002",
                                   "journey_date": "2026-10-25",
                                   "assistance_type": "RAC Assistance",
                                   "description": "RAC ticket holder needing confirmation on berth availability."
                               }),
                               content_type='application/json')
        self.assertEqual(res.status_code, 201)
        req_id = res.get_json()['data']['request_id']

        # Tracking GET
        res_get = self.client.get(f'/api/emergency/tte/{req_id}')
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.get_json()['data']['request_id'], req_id)

        # Admin status update with session
        with self.client.session_transaction() as sess:
            sess['user'] = {'id': 1, 'role': 'ADMIN', 'name': 'Admin'}

        res_patch = self.client.patch(f'/api/emergency/tte/{req_id}/status',
                                      data=json.dumps({"status": "Submitted"}),
                                      content_type='application/json')
        self.assertEqual(res_patch.status_code, 200)
        self.assertEqual(res_patch.get_json()['data']['status'], "Submitted")

    def test_06_chatbot_tte_intent(self):
        test_queries = [
            "How can I contact TTE?",
            "I have a berth issue",
            "Someone is sitting on my reserved seat",
            "Can I contact TTE?",
            "how to contact train staff for seat dispute"
        ]

        for q in test_queries:
            resp = process_chatbot_query(q)
            self.assertEqual(resp.get('intent'), "TTE_ASSISTANCE", f"Failed intent for query: {q}")
            self.assertIn("139", resp.get('response', ''))
            self.assertIn("emergency.html?service=tte", [a.get('url') for a in resp.get('suggested_actions', [])])

if __name__ == '__main__':
    unittest.main()
