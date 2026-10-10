import os
import sys
import unittest
import json
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import create_app
from backend.routes.tracking_routes import determine_train_operating_status, IST_TZ

class TestLiveTrackingRunningStatus(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_determine_train_operating_status_non_running_day(self):
        # Train that runs only on Monday and Thursday
        train = {
            'train_number': '12908',
            'train_name': 'MHRST SMPRK K EX',
            'running_days': 'Mon,Thu',
            'departure_time': '16:30',
            'arrival_time': '09:15',
            'duration': '16h 45m'
        }
        # Simulate Wednesday 14:00 IST (2026-10-07 is Wednesday)
        sim_time = datetime.datetime(2026, 10, 7, 14, 0, tzinfo=IST_TZ)
        res = determine_train_operating_status(train, sim_time)
        self.assertEqual(res['status_code'], 'NOT_RUNNING_TODAY')
        self.assertFalse(res['is_running'])
        self.assertIn('not scheduled to run today', res['status_message'].lower())

    def test_determine_train_operating_status_scheduled_not_started(self):
        # Train that runs on Wednesday, departure at 20:00
        train = {
            'train_number': '12907',
            'train_name': 'BDTS SMPRK K EX',
            'running_days': 'Wed,Sun',
            'departure_time': '20:00',
            'arrival_time': '10:15',
            'duration': '14h 15m'
        }
        # Simulate Wednesday 15:00 IST
        sim_time = datetime.datetime(2026, 10, 7, 15, 0, tzinfo=IST_TZ)
        res = determine_train_operating_status(train, sim_time)
        self.assertEqual(res['status_code'], 'SCHEDULED_NOT_STARTED')
        self.assertFalse(res['is_running'])
        self.assertIn('depart today at 20:00', res['status_message'])

    def test_determine_train_operating_status_completed(self):
        # Train that departed at 06:00 and arrived at 12:00
        train = {
            'train_number': '12015',
            'train_name': 'AJMER SHATABDI',
            'running_days': 'Daily',
            'departure_time': '06:10',
            'arrival_time': '12:55',
            'duration': '6h 45m'
        }
        # Simulate Wednesday 18:00 IST
        sim_time = datetime.datetime(2026, 10, 7, 18, 0, tzinfo=IST_TZ)
        res = determine_train_operating_status(train, sim_time)
        self.assertEqual(res['status_code'], 'COMPLETED')
        self.assertFalse(res['is_running'])
        self.assertIn('completed today', res['status_message'].lower())

    def test_determine_train_operating_status_overnight_in_transit(self):
        # Train that runs Wed, Sun, departs Wed 17:30, arrives Thu 10:15
        train = {
            'train_number': '12907',
            'train_name': 'BDTS SMPRK K EX',
            'running_days': 'Wed,Sun',
            'departure_time': '17:30',
            'arrival_time': '10:15',
            'duration': '16h 45m'
        }
        # Simulate Thursday 06:00 IST (overnight from Wednesday run)
        sim_time = datetime.datetime(2026, 10, 8, 6, 0, tzinfo=IST_TZ)
        res = determine_train_operating_status(train, sim_time)
        self.assertEqual(res['status_code'], 'IN_WINDOW')
        self.assertTrue(res['is_running'])
        self.assertIsNotNone(res['active_cycle'])
        self.assertEqual(res['active_cycle']['days_ago'], 1)

    def test_endpoint_tracking_not_running_today(self):
        # Train 6: 12908 runs Mon,Thu. Today is Wednesday.
        resp = self.client.get('/api/tracking/6')
        self.assertEqual(resp.status_code, 200)
        json_data = resp.get_json()
        self.assertTrue(json_data['success'])
        data = json_data['data']

        self.assertEqual(data['status_code'], 'NOT_RUNNING_TODAY')
        self.assertFalse(data['is_running'])
        self.assertIsNone(data['current_speed'])
        self.assertEqual(data['speed_display'], 'Not Running')
        self.assertEqual(data['delay_status'], 'Not Running Today')
        self.assertEqual(data['next_station'], 'Not Available')
        self.assertEqual(data['eta'], 'Not Available')
        self.assertEqual(data['distance_travelled_km'], 0.0)
        self.assertEqual(data['percentage_completed'], 0.0)

        # Check that NO station is marked as is_current
        current_stops = [s for s in data['stops'] if s.get('is_current')]
        self.assertEqual(len(current_stops), 0)

        # Check that NO section is marked as is_current_section
        current_secs = [s for s in data['sections'] if s.get('is_current_section')]
        self.assertEqual(len(current_secs), 0)

    def test_endpoint_tracking_completed_train(self):
        # Train 9: 12015 Ajmer Shatabdi runs 06:10 to 12:55.
        # At current IST (~23:00), today's journey is completed.
        resp = self.client.get('/api/tracking/9')
        self.assertEqual(resp.status_code, 200)
        json_data = resp.get_json()
        self.assertTrue(json_data['success'])
        data = json_data['data']

        self.assertEqual(data['status_code'], 'COMPLETED')
        self.assertFalse(data['is_running'])
        self.assertEqual(data['current_speed'], 0.0)
        self.assertEqual(data['speed_display'], 'Completed')
        self.assertEqual(data['delay_status'], 'Journey Completed')
        self.assertEqual(data['eta'], 'Arrived')
        self.assertEqual(data['percentage_completed'], 100.0)

        # Check that NO station is pulsing as current
        current_stops = [s for s in data['stops'] if s.get('is_current')]
        self.assertEqual(len(current_stops), 0)

    def test_endpoint_tracking_active_window(self):
        # Train 5: 12907 runs Wed,Sun, departs 17:30, arrives 10:15 next day.
        # Today is Wednesday 23:00, so it is in its active window.
        resp = self.client.get('/api/tracking/5')
        self.assertEqual(resp.status_code, 200)
        json_data = resp.get_json()
        self.assertTrue(json_data['success'])
        data = json_data['data']

        self.assertIn(data['status_code'], ['RUNNING', 'LIVE_DATA_UNAVAILABLE'])
        if data['status_code'] == 'LIVE_DATA_UNAVAILABLE':
            self.assertFalse(data['is_running'])
            self.assertIsNone(data['current_speed'])
            self.assertEqual(data['speed_display'], 'Unavailable')
            self.assertEqual(data['delay_status'], 'Live Data Unavailable')
            self.assertEqual(data['eta'], 'Not Available')
            # No fake cycling pulse
            current_stops = [s for s in data['stops'] if s.get('is_current')]
            self.assertEqual(len(current_stops), 0)
        else:
            # If live telemetry is connected
            self.assertTrue(data['is_running'])
            self.assertIsNotNone(data['current_speed'])

    def test_live_speed_extraction_hierarchy(self):
        from backend.services.railradar_service import RailRadarService

        # Case 1: Direct positive speed in currentLocation
        d1 = {
            'data': {
                'trainNumber': '12952',
                'currentLocation': {'speedKmh': 105.4, 'status': 'in-transit', 'isHalt': False}
            }
        }
        res1 = RailRadarService.normalize_live_telemetry(d1)
        self.assertEqual(res1['current_speed'], 105.4)

        # Case 2: Genuine halt at a scheduled commercial halt (speed = 0.0)
        d2 = {
            'data': {
                'trainNumber': '12952',
                'currentLocation': {'speedKmh': 0, 'status': 'at-station', 'isHalt': True}
            }
        }
        res2 = RailRadarService.normalize_live_telemetry(d2)
        self.assertEqual(res2['current_speed'], 0.0)
        self.assertTrue(res2['is_halted'])

        # Case 3: Pass-through station with route segment speed
        d3 = {
            'data': {
                'trainNumber': '12952',
                'currentLocation': {'stationCode': 'SVA', 'sequence': 85, 'status': 'at-station', 'isHalt': False},
                'route': [
                    {'sequence': 85, 'stationCode': 'SVA', 'speedToNextStationKmph': 98.7, 'isHalt': False}
                ]
            }
        }
        res3 = RailRadarService.normalize_live_telemetry(d3)
        self.assertEqual(res3['current_speed'], 98.7)

        # Case 4: No speed available anywhere (must NOT default to 0.0)
        d4 = {
            'data': {
                'trainNumber': '12952',
                'currentLocation': {'stationCode': 'SVA', 'sequence': 85, 'status': 'in-transit', 'isHalt': False},
                'route': [
                    {'sequence': 85, 'stationCode': 'SVA', 'isHalt': False}
                ]
            }
        }
        res4 = RailRadarService.normalize_live_telemetry(d4)
        self.assertIsNone(res4['current_speed'])

    def test_endpoint_running_train_live_speed(self):
        # Train 1: 12952 Rajdhani runs daily overnight (active right now)
        from backend.routes.tracking_routes import LiveTrackingCache
        LiveTrackingCache._cache.clear()

        resp = self.client.get('/api/tracking/1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']

        self.assertEqual(data['status_code'], 'RUNNING')
        self.assertTrue(data['is_running'])
        # Must have positive live speed from RailRadar
        self.assertIsNotNone(data['current_speed'])
        self.assertGreater(data['current_speed'], 0.0)
        self.assertNotEqual(data['speed_display'], '0.0')
        self.assertNotEqual(data['speed_display'], '0')

if __name__ == '__main__':
    unittest.main()
