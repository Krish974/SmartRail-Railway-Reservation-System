import sys
import unittest
sys.path.insert(0, '.')
from backend.app import create_app

class TestLiveTrackingTimeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_origin_display(self):
        """Test 1: Origin station has point_type='ORIGIN' and departure_time"""
        resp = self.client.get('/api/tracking/1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        first_stop = data['stops'][0]
        self.assertEqual(first_stop['point_type'], 'ORIGIN')
        self.assertTrue(first_stop['is_scheduled_halt'])
        self.assertEqual(first_stop['station_code'], 'NDLS')
        self.assertEqual(first_stop['departure_time'], '16:55')
        print("Test 1 Passed: Origin node verified.")

    def test_02_destination_display(self):
        """Test 2: Destination station has point_type='DESTINATION' and arrival_time"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        last_stop = data['stops'][-1]
        self.assertEqual(last_stop['point_type'], 'DESTINATION')
        self.assertTrue(last_stop['is_scheduled_halt'])
        self.assertEqual(last_stop['station_code'], 'MMCT')
        self.assertEqual(last_stop['arrival_time'], '08:35')
        print("Test 2 Passed: Destination node verified.")

    def test_03_scheduled_halt_display(self):
        """Test 3: Intermediate scheduled halt has arrival_time, departure_time, and halt_minutes"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        kota_stops = [s for s in data['stops'] if s['station_code'] == 'KOTA']
        self.assertEqual(len(kota_stops), 1)
        kota = kota_stops[0]
        self.assertEqual(kota['point_type'], 'HALT')
        self.assertTrue(kota['is_scheduled_halt'])
        self.assertIn(kota['arrival_time'], ['21:25', '21:30'])
        self.assertIn(kota['departure_time'], ['21:35', '21:40'])
        self.assertIn(kota['halt_minutes'], [0, 10])
        print("Test 3 Passed: Scheduled Halt verified.")

    def test_04_passing_station_display(self):
        """Test 4: Non-stopping passing station has point_type='PASSING' and no departure time"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        passing_stops = [s for s in data['stops'] if s['point_type'] == 'PASSING']
        self.assertGreater(len(passing_stops), 0)
        csb = [s for s in passing_stops if s['station_code'] == 'CSB'][0]
        self.assertFalse(csb['is_scheduled_halt'])
        self.assertEqual(csb['station_name'], 'Shivaji Bridge')
        self.assertIsNone(csb['arrival_time'])
        self.assertIsNone(csb['departure_time'])
        self.assertIsNotNone(csb['estimated_time'])
        print("Test 4 Passed: Passing Station verified.")

    def test_05_current_position(self):
        """Test 5: Telemetry reports current position mode and status text"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        curr_pos = data['current_position']
        self.assertIn(curr_pos['mode'], ['BETWEEN_STATIONS', 'PASSING_POINT', 'AT_STATION', 'AT_ORIGIN', 'AT_DESTINATION'])
        self.assertIsNotNone(curr_pos['status_text'])
        print(f"Test 5 Passed: Current position verified ({curr_pos['mode']}: {curr_pos['status_text']}).")

    def test_06_passed_stations(self):
        """Test 6: Stations prior to current position are marked COMPLETED / Passed"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        curr_idx = data['current_stop_index']
        if curr_idx > 0:
            for s in data['stops'][:curr_idx]:
                self.assertEqual(s['status'], 'COMPLETED')
                self.assertIn(s['status_label'], ['Passed', 'Departed'])
        print("Test 6 Passed: Passed stations marked as COMPLETED.")

    def test_07_upcoming_stations(self):
        """Test 7: Stations after current position are marked UPCOMING"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        curr_idx = data['current_stop_index']
        if curr_idx < len(data['stops']) - 1:
            for s in data['stops'][curr_idx + 1:]:
                self.assertEqual(s['status'], 'UPCOMING')
        print("Test 7 Passed: Upcoming stations marked as UPCOMING.")

    def test_08_correct_sequence_and_distance_order(self):
        """Test 8: Entire timeline is strictly sorted by sequence and cumulative distance"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        stops = data['stops']
        for i in range(len(stops) - 1):
            self.assertLessEqual(stops[i]['distance_km'], stops[i + 1]['distance_km'], "Distance must be non-decreasing")
            self.assertEqual(stops[i]['sequence'], i + 1, "Sequence must be strictly 1-indexed sequential")
        print(f"Test 8 Passed: All {len(stops)} stops strictly ordered by sequence & distance.")

    def test_09_arrival_departure_display_distinction(self):
        """Test 9: Halts have arrival & departure times; passing points have neither"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        for s in data['stops']:
            if s['point_type'] == 'HALT':
                self.assertIsNotNone(s['arrival_time'])
                self.assertIsNotNone(s['departure_time'])
            elif s['point_type'] == 'PASSING':
                self.assertIsNone(s['arrival_time'])
                self.assertIsNone(s['departure_time'])
        print("Test 9 Passed: Timetable fields properly distinguished.")

    def test_10_passing_time_display(self):
        """Test 10: Passing points have explicit is_estimated flag and passing_label"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        passing_stops = [s for s in data['stops'] if s['point_type'] == 'PASSING']
        for s in passing_stops:
            self.assertTrue(s['is_estimated'])
            self.assertIsNotNone(s['passing_label'])
        print("Test 10 Passed: Passing-time display format verified.")

    def test_11_next_station_and_eta(self):
        """Test 11: Next station and ETA telemetry fields are present"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        self.assertIsNotNone(data['next_station'])
        self.assertIsNotNone(data['eta'])
        print(f"Test 11 Passed: Next Station = '{data['next_station']}', ETA = '{data['eta']}'.")

    def test_12_speedometer(self):
        """Test 12: Speedometer reports numeric km/h"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        self.assertIsInstance(data['current_speed'], (int, float))
        self.assertGreaterEqual(data['current_speed'], 0.0)
        print(f"Test 12 Passed: Live Speed = {data['current_speed']} km/h.")

    def test_13_distance_covered(self):
        """Test 13: Cumulative distance covered is computed"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        self.assertGreaterEqual(data['distance_travelled_km'], 0.0)
        self.assertGreater(data['total_distance_km'], 0.0)
        print(f"Test 13 Passed: Distance covered = {data['distance_travelled_km']} / {data['total_distance_km']} km.")

    def test_14_journey_percentage(self):
        """Test 14: Percentage completed is between 0 and 100"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        self.assertGreaterEqual(data['percentage_completed'], 0.0)
        self.assertLessEqual(data['percentage_completed'], 100.0)
        print(f"Test 14 Passed: Journey progress = {data['percentage_completed']}%.")

    def test_15_scheduled_halts_only_filter(self):
        """Test 15: Filter 'halts' returns only scheduled commercial stops (Origin, Halts, Destination)"""
        resp = self.client.get('/api/tracking/1?filter=halts')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        for s in data['stops']:
            self.assertTrue(s['is_scheduled_halt'], "Halts filter must not contain passing points")
            self.assertIn(s['point_type'], ['ORIGIN', 'HALT', 'DESTINATION'])
        self.assertEqual(len(data['stops']), data['total_halts'])
        print(f"Test 15 Passed: 'Scheduled Halts Only' filter returns exactly {len(data['stops'])} commercial halts.")

    def test_16_all_stations_view(self):
        """Test 16: 'All Stations' view returns both halts and operational passing points"""
        resp = self.client.get('/api/tracking/1?filter=all')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        point_types = set(s['point_type'] for s in data['stops'])
        self.assertIn('ORIGIN', point_types)
        self.assertIn('DESTINATION', point_types)
        self.assertIn('HALT', point_types)
        self.assertIn('PASSING', point_types)
        self.assertEqual(len(data['stops']), data['total_halts'] + data['total_passing_points'])
        print(f"Test 16 Passed: 'All Stations' view returns {len(data['stops'])} combined stations/waypoints.")

    def test_17_level_1_halts_and_level_2_sections(self):
        """Test 17: Two-level structure returns Level 1 commercial halts and Level 2 inter-halt sections"""
        resp = self.client.get('/api/tracking/1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        self.assertIn('halts', data)
        self.assertIn('sections', data)
        halts = data['halts']
        sections = data['sections']
        self.assertEqual(len(halts), data['total_halts'])
        self.assertEqual(len(sections), len(halts) - 1)
        for h in halts:
            self.assertTrue(h['is_scheduled_halt'])
        print(f"Test 17 Passed: Level 1 has {len(halts)} commercial halts and Level 2 has {len(sections)} sections.")

    def test_18_intermediate_points_inside_sections(self):
        """Test 18: Intermediate passing points are nested within sections with proper metadata and NO departure times"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        sections = data['sections']
        total_pts = 0
        for sec in sections:
            self.assertEqual(sec['intermediate_count'], len(sec['intermediate_points']))
            total_pts += sec['intermediate_count']
            for pt in sec['intermediate_points']:
                self.assertFalse(pt['is_scheduled_halt'])
                self.assertEqual(pt['point_type'], 'PASSING')
                self.assertIsNone(pt['departure_time'], "Passing points must not display departure time")
                self.assertIsNotNone(pt['estimated_time'])
                self.assertIn(pt['status'], ['COMPLETED', 'CURRENT', 'UPCOMING'])
        self.assertEqual(total_pts, data['total_passing_points'])
        print(f"Test 18 Passed: All {total_pts} passing points properly distributed across sections with no departure times.")

    def test_19_next_station_is_commercial_halt(self):
        """Test 19: 'Next Station' in telemetry dashboard strictly refers to the next commercial halt, not a passing point"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        next_station = data['next_station']
        halt_names_and_codes = [f"{h['station_name']} ({h['station_code']})" for h in data['halts']]
        if "Destination Reached" not in next_station:
            self.assertIn(next_station, halt_names_and_codes, "Next Station must be one of the commercial halting stations")
        print(f"Test 19 Passed: Next Station '{next_station}' is strictly a commercial halt.")

    def test_20_current_section_identification(self):
        """Test 20: Telemetry identifies current active route section if train is running between halts"""
        resp = self.client.get('/api/tracking/1')
        data = resp.get_json()['data']
        sections = data['sections']
        cur_sections = [s for s in sections if s['is_current_section']]
        self.assertLessEqual(len(cur_sections), 1, "At most one section should be identified as current section")
        if cur_sections:
            title = cur_sections[0]['section_title'].encode('ascii', 'replace').decode('ascii')
            print(f"Test 20 Passed: Current active section identified as '{title}'.")
        else:
            print("Test 20 Passed: Train at origin/destination terminus (no active transit section).")

if __name__ == '__main__':
    unittest.main()

