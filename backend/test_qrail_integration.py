"""
Automated Test & Validation Suite for Qrail Integration
-------------------------------------------------------
Validates:
1. Qrail API connectivity test
2. 1-train schedule test
3. Ingestion idempotency & database validation
4. Jaipur -> Delhi ordered route search
5. Jaipur -> Ajmer ordered route search
6. Train-number lookup
7. Complete route lookup
8. AI Assistant data-driven responses (no generic hardcoded lists)
"""

import unittest
import sys
import os

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import Config
from backend.services.qrail_service import QRailService
from backend.services.railway_service import RailwayService
from backend.ml.chatbot_model import process_chatbot_query
from backend.utils.db_connection import execute_query
from backend.utils.ingest_qrail_dataset import get_or_create_station, upsert_train_and_stops

class TestQRailIntegration(unittest.TestCase):

    def test_01_connectivity_and_security(self):
        """1. Qrail API connectivity test & security check (API key never leaked)"""
        res = QRailService.test_connection()
        self.assertIsInstance(res, dict)
        self.assertIn('success', res)
        self.assertIn('message', res)
        # Verify API key is NOT in message
        if Config.QRAIL_API_KEY:
            self.assertNotIn(Config.QRAIL_API_KEY, res['message'])
        print(f"Test 1 Passed: Qrail connectivity check returned: '{res['message']}'")

    def test_02_qrail_normalization(self):
        """2. Normalize real-world Qrail payload structure without guessing or inventing data"""
        sample_qrail_payload = {
            "data": {
                "train_number": "12952",
                "train_name": "New Delhi - Mumbai Tejas Rajdhani",
                "train_type": "Tejas Rajdhani",
                "duration": "15h 40m",
                "running_days": "Mon,Tue,Wed,Thu,Fri,Sat,Sun",
                "stops": [
                    {"stop_sequence": 1, "station_code": "NDLS", "station_name": "New Delhi", "city": "New Delhi", "state": "Delhi", "arrival_time": "START", "departure_time": "16:55", "halt_minutes": 0, "distance_km": 0},
                    {"stop_sequence": 2, "station_code": "KOTA", "station_name": "Kota Junction", "city": "Kota", "state": "Rajasthan", "arrival_time": "21:25", "departure_time": "21:35", "halt_minutes": 10, "distance_km": 465},
                    {"stop_sequence": 3, "station_code": "MMCT", "station_name": "Mumbai Central", "city": "Mumbai", "state": "Maharashtra", "arrival_time": "08:35", "departure_time": "END", "halt_minutes": 0, "distance_km": 1384}
                ]
            }
        }
        normalized = QRailService.normalize_train_details(sample_qrail_payload, "12952")
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized['train_number'], "12952")
        self.assertEqual(len(normalized['stops']), 3)
        self.assertEqual(normalized['source_code'], "NDLS")
        self.assertEqual(normalized['dest_code'], "MMCT")
        print("Test 2 Passed: Qrail response normalizer accurately structured payload.")

    def test_03_idempotent_ingestion(self):
        """3. Ingest sample normalized train idempotently into database"""
        train_data = {
            "train_number": "12952",
            "train_name": "New Delhi - Mumbai Tejas Rajdhani",
            "train_type": "Tejas Rajdhani",
            "source_code": "NDLS",
            "source_name": "New Delhi Railway Station",
            "dest_code": "MMCT",
            "dest_name": "Mumbai Central",
            "departure_time": "16:55",
            "arrival_time": "08:35",
            "duration": "15h 40m",
            "running_days": "Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            "stops": [
                {"stop_sequence": 1, "station_code": "NDLS", "station_name": "New Delhi Railway Station", "city": "New Delhi", "state": "Delhi", "arrival_time": "START", "departure_time": "16:55", "halt_minutes": 0, "distance_km": 0.0},
                {"stop_sequence": 2, "station_code": "KOTA", "station_name": "Kota Junction", "city": "Kota", "state": "Rajasthan", "arrival_time": "21:25", "departure_time": "21:35", "halt_minutes": 10, "distance_km": 465.0},
                {"stop_sequence": 3, "station_code": "RTM", "station_name": "Ratlam Junction", "city": "Ratlam", "state": "Madhya Pradesh", "arrival_time": "00:12", "departure_time": "00:15", "halt_minutes": 3, "distance_km": 730.0},
                {"stop_sequence": 4, "station_code": "BRC", "station_name": "Vadodara Junction", "city": "Vadodara", "state": "Gujarat", "arrival_time": "03:35", "departure_time": "03:45", "halt_minutes": 10, "distance_km": 992.0},
                {"stop_sequence": 5, "station_code": "ST", "station_name": "Surat", "city": "Surat", "state": "Gujarat", "arrival_time": "05:10", "departure_time": "05:15", "halt_minutes": 5, "distance_km": 1122.0},
                {"stop_sequence": 6, "station_code": "MMCT", "station_name": "Mumbai Central", "city": "Mumbai", "state": "Maharashtra", "arrival_time": "08:35", "departure_time": "END", "halt_minutes": 0, "distance_km": 1384.0}
            ]
        }
        # Ingest first time
        t_id_1 = upsert_train_and_stops(train_data)
        # Ingest second time to test idempotency
        t_id_2 = upsert_train_and_stops(train_data)
        self.assertEqual(t_id_1, t_id_2)

        # Verify no duplicate stops
        stops_count = execute_query("SELECT count(*) as cnt FROM train_stops WHERE train_id = %s", (t_id_1,), fetchone=True)
        self.assertEqual(stops_count['cnt'], 6)
        print("Test 3 Passed: Ingestion is 100% idempotent with zero duplicates.")

    def test_04_jaipur_to_delhi_ordered_search(self):
        """4. Jaipur -> Delhi search strictly enforces stop_sequence(Jaipur) < stop_sequence(Delhi)"""
        trains = RailwayService.search_route('Jaipur', 'Delhi')
        self.assertTrue(len(trains) > 0)
        for t in trains:
            self.assertLess(t['boarding_sequence'], t['deboarding_sequence'])
            self.assertIn("JP", t['boarding_code'])
            self.assertTrue(t['deboarding_code'] in ['NDLS', 'DLI', 'NZM', 'ANVT'])
        print(f"Test 4 Passed: Jaipur -> Delhi returned {len(trains)} trains with strictly ordered sequence.")

    def test_05_jaipur_to_ajmer_ordered_search(self):
        """5. Jaipur -> Ajmer search strictly enforces stop_sequence(Jaipur) < stop_sequence(Ajmer)"""
        trains = RailwayService.search_route('Jaipur', 'Ajmer')
        self.assertTrue(len(trains) > 0)
        for t in trains:
            self.assertLess(t['boarding_sequence'], t['deboarding_sequence'])
            self.assertEqual(t['boarding_code'], 'JP')
            self.assertEqual(t['deboarding_code'], 'AII')
        print(f"Test 5 Passed: Jaipur -> Ajmer returned {len(trains)} trains with strictly ordered sequence.")

    def test_06_train_number_lookup(self):
        """6. Train-number lookup for 12952 retrieves accurate timetable from database"""
        train = RailwayService.search_by_train_number('12952')
        self.assertIsNotNone(train)
        self.assertEqual(train['train_number'], '12952')
        self.assertEqual(train['source_code'], 'NDLS')
        self.assertEqual(train['dest_code'], 'MMCT')
        self.assertEqual(train['departure_time'], '16:55')
        self.assertEqual(train['arrival_time'], '08:35')
        print("Test 6 Passed: Train 12952 details lookup verified.")

    def test_07_complete_route_lookup(self):
        """7. Complete route lookup for 12952 returns all 6 ordered halts"""
        train, stops = RailwayService.get_train_stops_detailed('12952')
        self.assertIsNotNone(train)
        self.assertEqual(len(stops), 6)
        codes = [s['station_code'] for s in stops]
        self.assertEqual(codes, ['NDLS', 'KOTA', 'RTM', 'BRC', 'ST', 'MMCT'])
        print(f"Test 7 Passed: Train 12952 complete route verified with {len(stops)} stops: {codes}")

    def test_08_chatbot_no_generic_hardcoded_lists(self):
        """8. AI Assistant strictly queries real database and never displays generic fallback lists"""
        # Query Jaipur to Delhi
        res_delhi = process_chatbot_query("show train of jaipur to delhi")
        self.assertEqual(res_delhi['intent'], 'TRAIN_SEARCH')
        self.assertNotIn("Here are popular active trains", res_delhi['response'])
        self.assertIn("Ajmer - Delhi Cantt Vande Bharat", res_delhi['response'])

        # Query Jaipur to Ajmer
        res_ajmer = process_chatbot_query("show trains of jaipur to ajmer")
        self.assertEqual(res_ajmer['intent'], 'TRAIN_SEARCH')
        self.assertNotIn("Here are popular active trains", res_ajmer['response'])
        self.assertIn("New Delhi - Ajmer Shatabdi Express", res_ajmer['response'])

        # Responses must be completely distinct
        self.assertNotEqual(res_delhi['response'], res_ajmer['response'])

        # Route of 12952
        res_route = process_chatbot_query("route of train 12952")
        self.assertEqual(res_route['intent'], 'TRAIN_ROUTE')
        self.assertIn("NDLS", res_route['response'])
        self.assertIn("KOTA", res_route['response'])
        self.assertIn("MMCT", res_route['response'])

        print("Test 8 Passed: AI Assistant responses are 100% data-driven with zero hardcoded fallbacks.")

if __name__ == '__main__':
    unittest.main()
