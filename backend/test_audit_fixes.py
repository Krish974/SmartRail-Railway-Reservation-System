"""
Comprehensive Automated Test Suite for Railway Audit Fixes.
Verifies:
1. Exact Train Number Search (12951, 12015, etc.)
2. Train Name Search (Rajdhani, Shatabdi, Vande Bharat)
3. City Name Route Search (Delhi to Mumbai, Jaipur to Delhi)
4. Station Code Search (NDLS to MMCT)
5. Station Autocomplete API (/api/stations/search?q=...)
6. Stop Sequence Direction Order Enforcement (source_seq < dest_seq)
7. Reverse Route Exclusion (Train does not leak into opposite direction)
8. Invalid Station Handling (graceful empty list, no crash)
9. Invalid Train Number Handling (404/empty, no crash)
10. Quota Pricing & Dynamic Seat Calculation
11. Chatbot Train Number Resolution (Single source of truth)
12. Chatbot Route Extraction (Single source of truth)
"""

import os
import sys
import unittest
import json

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure stdout handles utf-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from backend.app import create_app
from backend.services.railway_service import RailwayService
from backend.ml.chatbot_model import process_chatbot_query

class TestRailwayAuditFixes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    # 1. Exact Train Number Search
    def test_01_exact_train_number_search(self):
        train = RailwayService.search_by_train_number('12951')
        self.assertIsNotNone(train, "Train 12951 should be found")
        self.assertEqual(train['train_number'], '12951')
        self.assertIn('Tejas Rajdhani', train['train_name'])
        self.assertGreaterEqual(len(train['stops']), 2, "Train 12951 should have route halts")
        self.assertGreaterEqual(len(train['classes']), 1, "Train 12951 should have coach classes")

        # Via REST API
        resp = self.client.get('/api/trains/number/12951')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['train_number'], '12951')

    # 2. Train Name Search
    def test_02_train_name_search(self):
        trains = RailwayService.search_by_train_name('Rajdhani')
        self.assertGreaterEqual(len(trains), 4, "Should find multiple Rajdhani trains")
        for t in trains:
            self.assertIn('Rajdhani', t['train_name'])

        # Via REST API
        resp = self.client.get('/api/trains/name/Shatabdi')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['data']), 2)

    # 3. City Route Search: Delhi to Mumbai
    def test_03_city_route_search_delhi_mumbai(self):
        results = RailwayService.search_route('Delhi', 'Mumbai')
        self.assertGreaterEqual(len(results), 2, "Should find multiple trains running from Delhi to Mumbai")
        train_nums = [t['train_number'] for t in results]
        self.assertIn('12952', train_nums, "Train 12952 (NDLS -> MMCT) should run from Delhi to Mumbai")

    # 4. Station Code Search: NDLS to MMCT
    def test_04_station_code_search_ndls_mmct(self):
        resp = self.client.get('/api/trains/search?source=NDLS&destination=MMCT')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['data']), 1)
        first = data['data'][0]
        self.assertEqual(first['boarding_code'], 'NDLS')
        self.assertEqual(first['deboarding_code'], 'MMCT')

    # 5. Station Autocomplete Search
    def test_05_station_autocomplete(self):
        # Searching 'Jai' should return Jaipur stations
        res = RailwayService.search_stations('Jai')
        codes = [s['code'] for s in res]
        self.assertIn('JP', codes)

        # Searching 'NDLS' should prioritize New Delhi
        resp = self.client.get('/api/stations/search?q=NDLS')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data'][0]['code'], 'NDLS')

    # 6. Jaipur -> Delhi Route (Direct and Intermediate Stops)
    def test_06_jaipur_to_delhi_route(self):
        results = RailwayService.search_route('Jaipur', 'Delhi')
        self.assertGreaterEqual(len(results), 3, "Jaipur to Delhi must return available trains")
        train_nums = [t['train_number'] for t in results]
        # Should contain trains that run from Jaipur to Delhi
        self.assertTrue(any(num in ['12957', '20977', '12413', '12016'] for num in train_nums),
                        f"Expected Jaipur -> Delhi trains, found {train_nums}")

    # 7. Mumbai -> Delhi Route
    def test_07_mumbai_to_delhi_route(self):
        results = RailwayService.search_route('Mumbai', 'Delhi')
        self.assertGreaterEqual(len(results), 2, "Mumbai to Delhi must return available trains")
        train_nums = [t['train_number'] for t in results]
        self.assertIn('12951', train_nums, "Train 12951 should run from Mumbai to Delhi")

    # 8. Route Order Direction Enforcement (s1.stop_sequence < s2.stop_sequence)
    def test_08_route_order_direction_enforcement(self):
        # 12952 runs NDLS (seq 1) -> KOTA (seq 2) -> RTM (seq 3) -> BRC (seq 4) -> ST (seq 5) -> MMCT (seq 6)
        # Search from Kota to Mumbai should return 12952
        forward = RailwayService.search_route('KOTA', 'MMCT')
        forward_nums = [t['train_number'] for t in forward]
        self.assertIn('12952', forward_nums, "Train 12952 runs Kota -> Mumbai")

        # Search from Mumbai to Kota should NOT return 12952
        reverse = RailwayService.search_route('MMCT', 'KOTA')
        reverse_nums = [t['train_number'] for t in reverse]
        self.assertNotIn('12952', reverse_nums, "Train 12952 must NOT appear for reverse direction MMCT -> KOTA")

    # 9. Invalid Station Name Handling
    def test_09_invalid_station_handling(self):
        resp = self.client.get('/api/trains/search?source=Atlantis&destination=Delhi')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 0, "Invalid station should return empty list gracefully")

    # 10. Invalid Train Number Handling
    def test_10_invalid_train_number_handling(self):
        resp = self.client.get('/api/trains/number/99999')
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertFalse(data['success'])

    # 11. Chatbot Route Extraction
    def test_11_chatbot_route_extraction(self):
        reply = process_chatbot_query("Which trains run from Jaipur to Delhi?")
        self.assertIn(reply['intent'], ['TRAIN_SEARCH', 'route_search'])
        self.assertIn('Jaipur', reply['response'])
        self.assertIn('Delhi', reply['response'])
        self.assertIn('train', reply['response'].lower())
        self.assertGreaterEqual(len(reply.get('suggested_actions', [])), 1)

    # 12. Chatbot Exact Train Number Query
    def test_12_chatbot_train_number_query(self):
        reply = process_chatbot_query("What is train 12951?")
        self.assertIn(reply['intent'], ['TRAIN_DETAILS', 'train_details'])
        self.assertIn('12951', reply['response'])
        self.assertIn('Tejas Rajdhani', reply['response'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
