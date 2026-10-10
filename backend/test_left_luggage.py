import os
import sys
import json
import unittest

# Ensure repo root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import create_app
from backend.models.luggage_model import LuggageAssistanceModel, generate_luggage_request_id, ensure_luggage_table, LUGGAGE_STATUSES
from backend.ml.chatbot_model import process_chatbot_query

class TestLeftLuggageAssistance(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        ensure_luggage_table()

    def test_01_id_generation(self):
        req_id = generate_luggage_request_id()
        self.assertTrue(req_id.startswith("LUG-"))
        parts = req_id.split("-")
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[1]), 8)  # YYYYMMDD
        self.assertEqual(len(parts[2]), 5)  # 5-digit number or sequence

    def test_02_model_crud(self):
        req = LuggageAssistanceModel.create_request(
            train_number="12956",
            journey_date="2026-10-18",
            coach="B2",
            seat="45",
            deboarding_station="JP",
            luggage_description="Black American Tourister trolley bag",
            passenger_mobile="9876543210",
            pnr="1234567890",
            boarding_station="MMCT",
            train_name="Jaipur Superfast",
            luggage_contents="Laptop charger, clothes, files",
            additional_details="Left under lower berth 45"
        )
        self.assertIsNotNone(req)
        self.assertTrue(req['request_id'].startswith("LUG-"))
        self.assertEqual(req['status'], "Submitted")
        self.assertEqual(req['coach'], "B2")
        self.assertEqual(req['seat'], "45")
        self.assertEqual(req['deboarding_station'], "JP")
        self.assertEqual(req['passenger_mobile'], "9876543210")
        self.assertEqual(req['pnr'], "1234567890")

        # Fetch by ID
        fetched = LuggageAssistanceModel.get_by_request_id(req['request_id'])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched['train_number'], "12956")
        self.assertEqual(fetched['luggage_description'], "Black American Tourister trolley bag")

        # Update status
        updated = LuggageAssistanceModel.update_status(req['request_id'], "Under Investigation", "RPF informed at JP station.")
        self.assertEqual(updated['status'], "Under Investigation")
        self.assertEqual(updated['admin_notes'], "RPF informed at JP station.")

        # Update to Found
        updated_found = LuggageAssistanceModel.update_status(req['request_id'], "Found")
        self.assertEqual(updated_found['status'], "Found")

        # Invalid status should raise ValueError
        with self.assertRaises(ValueError):
            LuggageAssistanceModel.update_status(req['request_id'], "InvalidStatus")

    def test_03_api_post_valid_request(self):
        payload = {
            "train_number": "12956",
            "journey_date": "2026-10-25",
            "coach": "S4",
            "seat": "22",
            "deboarding_station": "KOTA",
            "luggage_description": "Blue Wildcraft backpack with college books",
            "passenger_mobile": "9811223344",
            "pnr": "9876543210",
            "boarding_station": "NDLS",
            "luggage_contents": "Books, umbrella, powerbank"
        }
        res = self.client.post('/api/emergency/luggage',
                               data=json.dumps(payload),
                               content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['request_id'].startswith('LUG-'))
        self.assertEqual(data['data']['status'], 'Submitted')
        self.assertEqual(data['data']['coach'], 'S4')
        self.assertEqual(data['data']['deboarding_station'], 'KOTA')

    def test_04_api_validations(self):
        # Missing train number
        res = self.client.post('/api/emergency/luggage',
                               data=json.dumps({
                                   "journey_date": "2026-10-20",
                                   "coach": "B1",
                                   "seat": "10",
                                   "deboarding_station": "JP",
                                   "luggage_description": "Red bag",
                                   "passenger_mobile": "9876543210"
                               }),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)

        # Missing coach
        res = self.client.post('/api/emergency/luggage',
                               data=json.dumps({
                                   "train_number": "12952",
                                   "journey_date": "2026-10-20",
                                   "seat": "10",
                                   "deboarding_station": "JP",
                                   "luggage_description": "Red bag",
                                   "passenger_mobile": "9876543210"
                               }),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)

        # Missing deboarding station
        res = self.client.post('/api/emergency/luggage',
                               data=json.dumps({
                                   "train_number": "12952",
                                   "journey_date": "2026-10-20",
                                   "coach": "B1",
                                   "seat": "10",
                                   "luggage_description": "Red bag",
                                   "passenger_mobile": "9876543210"
                               }),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)

        # Invalid mobile (< 10 digits)
        res = self.client.post('/api/emergency/luggage',
                               data=json.dumps({
                                   "train_number": "12952",
                                   "journey_date": "2026-10-20",
                                   "coach": "B1",
                                   "seat": "10",
                                   "deboarding_station": "JP",
                                   "luggage_description": "Red bag",
                                   "passenger_mobile": "12345"
                               }),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)

        # Invalid PNR (not 10 digits)
        res = self.client.post('/api/emergency/luggage',
                               data=json.dumps({
                                   "train_number": "12952",
                                   "journey_date": "2026-10-20",
                                   "coach": "B1",
                                   "seat": "10",
                                   "deboarding_station": "JP",
                                   "luggage_description": "Red bag",
                                   "passenger_mobile": "9876543210",
                                   "pnr": "123"
                               }),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)

    def test_05_api_get_single_and_list(self):
        # Create request first
        req = LuggageAssistanceModel.create_request(
            train_number="12951",
            journey_date="2026-10-22",
            coach="A1",
            seat="15",
            deboarding_station="NDLS",
            luggage_description="Brown leather briefcase",
            passenger_mobile="9988776655"
        )
        req_id = req['request_id']

        # Get single request
        res = self.client.get(f'/api/emergency/luggage/{req_id}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['request_id'], req_id)
        self.assertEqual(data['data']['coach'], "A1")

        # Get non-existent
        res_404 = self.client.get('/api/emergency/luggage/LUG-99999999-99999')
        self.assertEqual(res_404.status_code, 404)

        # Get list
        res_list = self.client.get('/api/emergency/luggage?limit=10')
        self.assertEqual(res_list.status_code, 200)
        list_data = res_list.get_json()
        self.assertTrue(list_data['success'])
        self.assertIsInstance(list_data['data'], list)
        self.assertTrue(len(list_data['data']) > 0)

    def test_06_api_status_update(self):
        req = LuggageAssistanceModel.create_request(
            train_number="12955",
            journey_date="2026-10-23",
            coach="B3",
            seat="52",
            deboarding_station="JP",
            luggage_description="Grey duffel bag",
            passenger_mobile="9123456780"
        )
        req_id = req['request_id']

        # PATCH update
        patch_res = self.client.patch(f'/api/emergency/luggage/{req_id}/status',
                                      data=json.dumps({"status": "Under Investigation"}),
                                      content_type='application/json')
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.get_json()['data']['status'], "Under Investigation")

        # PUT update
        put_res = self.client.put(f'/api/emergency/luggage/{req_id}/status',
                                  data=json.dumps({"status": "Found", "admin_notes": "Secured at Jaipur RPF Thana"}),
                                  content_type='application/json')
        self.assertEqual(put_res.status_code, 200)
        self.assertEqual(put_res.get_json()['data']['status'], "Found")
        self.assertEqual(put_res.get_json()['data']['admin_notes'], "Secured at Jaipur RPF Thana")

        # Invalid status update
        bad_res = self.client.patch(f'/api/emergency/luggage/{req_id}/status',
                                    data=json.dumps({"status": "NotAValidStatus"}),
                                    content_type='application/json')
        self.assertEqual(bad_res.status_code, 400)

    def test_07_chatbot_intent(self):
        queries = [
            "I left my bag in the train",
            "I forgot my luggage after getting down",
            "My luggage is still in the train in coach B2",
            "I deboarded but my bag is inside the train"
        ]
        for q in queries:
            res = process_chatbot_query(q)
            self.assertEqual(res.get('intent'), "LEFT_LUGGAGE", f"Failed for query: {q}")
            self.assertIn("emergency.html?service=luggage", json.dumps(res))

if __name__ == '__main__':
    unittest.main()
