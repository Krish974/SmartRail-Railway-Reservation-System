"""
Test Suite: Accurate Railway Scheduled Halts Calculation & Validation
Tests trains: 09609, 09611, 12956, 12952, 20977 (Vande Bharat), etc.
Verifies:
1. calculate_scheduled_halts validation function logic
2. Pass-through waypoints vs confirmed scheduled halts
3. Same-station arrival/departure handling
4. Exact halt count matching for 09609, 09611, and 12956
5. Distinct halt counts between different trains
6. Structured RAG context distinguishing total_route_stations from scheduled_halt_count
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.railway_service import RailwayService
from backend.ml.chatbot_model import process_chatbot_query, format_train_card
from backend.utils.db_connection import execute_query


class TestHaltCalculation(unittest.TestCase):

    def test_01_calculate_scheduled_halts_validation(self):
        """Test calculate_scheduled_halts logic according to Priority rules."""
        # Test empty / None
        self.assertIsNone(RailwayService.calculate_scheduled_halts([]))
        self.assertIsNone(RailwayService.calculate_scheduled_halts(None))

        # Test route with explicit is_halt flags
        sample_route = [
            {"station_code": "STN_A", "is_halt": True, "arrival": "START", "departure": "05:00"},
            {"station_code": "STN_B", "is_halt": False, "arrival": "05:30", "departure": "05:30"},  # Pass-through
            {"station_code": "STN_C", "is_halt": True, "arrival": "06:00", "departure": "06:05"},   # Scheduled Halt
            {"station_code": "STN_D", "is_halt": False, "arrival": "06:30", "departure": "06:30"},  # Pass-through
            {"station_code": "STN_E", "is_halt": True, "arrival": "07:15", "departure": "END"}
        ]
        self.assertEqual(RailwayService.calculate_scheduled_halts(sample_route), 3)

        # Test same station arrival/departure when stop is scheduled (Section 5)
        sample_same_time = [
            {"station_code": "STN_1", "arrival_time": "04:50", "departure_time": "04:50"},
            {"station_code": "STN_2", "arrival_time": "05:15", "departure_time": "05:17"},
            {"station_code": "STN_3", "arrival_time": "05:38", "departure_time": "05:40"}
        ]
        self.assertEqual(RailwayService.calculate_scheduled_halts(sample_same_time), 3)

        # Test pass-through waypoint with no times (Section 6)
        sample_pass_through = [
            {"station_code": "STN_X", "arrival_time": "--:--", "departure_time": "--:--"},
            {"station_code": "STN_Y", "arrival_time": "", "departure_time": ""}
        ]
        self.assertEqual(RailwayService.calculate_scheduled_halts(sample_pass_through), 0)

    def test_02_train_09609_halts(self):
        """Test train 09609 (UDZ-YNRK) verified timetable parameters and halt count."""
        # Route search for Jaipur to Rishikesh
        results = RailwayService.search_route("Jaipur", "Rishikesh")
        train_09609 = next((t for t in results if t['train_number'] == '09609'), None)
        self.assertIsNotNone(train_09609, "Train 09609 must be in search results")

        # 1. Source / Boarding
        self.assertIn("Phulera", train_09609['boarding_name'])
        # 2. Destination / Deboarding
        self.assertIn("Rishikesh", train_09609['deboarding_name'])
        # 3. Departure
        self.assertEqual(train_09609['leg_departure_time'], "20:47")
        # 4. Arrival
        self.assertEqual(train_09609['leg_arrival_time'], "10:15")
        # 5. Duration
        self.assertEqual(train_09609['duration'], "13h 28m")
        # 6. Distance
        self.assertAlmostEqual(train_09609['leg_distance_km'], 616.7, delta=1.0)
        # 7. Actual scheduled halt count (NOT 105!)
        self.assertNotEqual(train_09609['scheduled_halt_count'], 105, "Must NOT be 105 route stations!")
        self.assertEqual(train_09609['scheduled_halt_count'], 14, "Actual confirmed intermediate halts is 14")
        self.assertEqual(train_09609['total_route_stations'], 114)

    def test_03_train_09611_halts(self):
        """Test train 09611 (AII-YNRK TOD SPL) verified timetable parameters and halt count."""
        results = RailwayService.search_route("Jaipur", "Rishikesh")
        train_09611 = next((t for t in results if t['train_number'] == '09611'), None)
        self.assertIsNotNone(train_09611, "Train 09611 must be in search results")

        # 1. Source / Boarding
        self.assertIn("Phulera", train_09611['boarding_name'])
        # 2. Destination / Deboarding
        self.assertIn("Rishikesh", train_09611['deboarding_name'])
        # 3. Departure
        self.assertEqual(train_09611['leg_departure_time'], "20:47")
        # 4. Arrival
        self.assertEqual(train_09611['leg_arrival_time'], "12:50")
        # 5. Duration
        self.assertEqual(train_09611['duration'], "16h 3m")
        # 6. Distance
        self.assertAlmostEqual(train_09611['leg_distance_km'], 616.8, delta=1.0)
        # 7. Actual scheduled halt count (NOT 111!)
        self.assertNotEqual(train_09611['scheduled_halt_count'], 111, "Must NOT be 111 route stations!")
        self.assertEqual(train_09611['scheduled_halt_count'], 15, "Actual confirmed intermediate halts is 15")
        self.assertEqual(train_09611['total_route_stations'], 120)

    def test_04_train_12956_halts(self):
        """Test train 12956 (JP MMCT SF EXP) verified timetable parameters and halt count."""
        results = RailwayService.search_route("Jaipur", "Mumbai")
        train_12956 = next((t for t in results if t['train_number'] == '12956'), None)
        self.assertIsNotNone(train_12956, "Train 12956 must be in search results")

        # 1. Source / Boarding
        self.assertIn("Jaipur", train_12956['boarding_name'])
        # 2. Destination / Deboarding
        self.assertIn("Mumbai", train_12956['deboarding_name'])
        # 3. Departure
        self.assertEqual(train_12956['leg_departure_time'], "14:00")
        # 4. Arrival
        self.assertEqual(train_12956['leg_arrival_time'], "06:55")
        # 5. Duration
        self.assertEqual(train_12956['duration'], "16h 55m")
        # 6. Distance
        self.assertAlmostEqual(train_12956['leg_distance_km'], 1162.4, delta=2.0)
        # 7. Actual scheduled halt count (NOT 180!)
        self.assertNotEqual(train_12956['scheduled_halt_count'], 180, "Must NOT be 180 route stations!")
        self.assertEqual(train_12956['scheduled_halt_count'], 18, "Actual confirmed intermediate halts is 18")
        self.assertEqual(train_12956['total_route_stations'], 180)

    def test_05_distinct_halt_counts_between_different_trains(self):
        """Verify that two different trains do NOT automatically receive the same halt count."""
        results = RailwayService.search_route("Jaipur", "Rishikesh")
        train_09609 = next(t for t in results if t['train_number'] == '09609')
        train_09611 = next(t for t in results if t['train_number'] == '09611')
        train_19609 = next(t for t in results if t['train_number'] == '19609')
        train_19031 = next(t for t in results if t['train_number'] == '19031')

        self.assertEqual(train_09609['scheduled_halt_count'], 14)
        self.assertEqual(train_09611['scheduled_halt_count'], 15)
        self.assertEqual(train_19609['scheduled_halt_count'], 21)
        self.assertEqual(train_19031['scheduled_halt_count'], 23)

        # Check that halt counts vary based on actual timetable halts
        self.assertNotEqual(train_09609['scheduled_halt_count'], train_09611['scheduled_halt_count'])
        self.assertNotEqual(train_09609['scheduled_halt_count'], train_19609['scheduled_halt_count'])

    def test_06_train_card_display_format(self):
        """Verify train card output shows 'Halts: X' and NOT '105 scheduled stops'."""
        reply = process_chatbot_query("trains from Jaipur to Rishikesh")
        resp = reply['response']

        # Ensure no legacy bug strings
        self.assertNotIn("105 scheduled stops", resp)
        self.assertNotIn("111 scheduled stops", resp)
        self.assertNotIn("180 scheduled stops", resp)

        # Ensure correct card format
        self.assertIn("**Halts:** 14", resp)
        self.assertIn("**Halts:** 15", resp)

    def test_07_rag_structured_data_isolation(self):
        """Verify RAG context maintains total_route_points separate from actual_scheduled_halts."""
        reply = process_chatbot_query("trains from Jaipur to Rishikesh", session_id="rag_test")
        from backend.ml.chatbot_model import CONVERSATION_CONTEXT
        ctx = CONVERSATION_CONTEXT.get("rag_test", {})
        rag_trains = ctx.get("rag_trains_context", [])
        self.assertTrue(len(rag_trains) > 0)

        t_09609 = next((t for t in rag_trains if t['train_number'] == '09609'), None)
        self.assertIsNotNone(t_09609)
        self.assertEqual(t_09609['total_route_points'], 114)
        self.assertEqual(t_09609['actual_scheduled_halts'], 14)


if __name__ == '__main__':
    unittest.main()
