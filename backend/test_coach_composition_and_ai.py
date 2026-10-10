import os
import sys
import json
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app
from backend.services.railway_service import RailwayService
from backend.utils.db_connection import execute_query

class TestCoachCompositionAndAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_tejas_rajdhani_coach_composition(self):
        """Train 1 (12952 Tejas Rajdhani) must have authentic 1A, 2A, 3A composition."""
        resp = self.client.get('/api/trains/1/coaches')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']

        self.assertEqual(data['train_number'], '12952')
        class_codes = [c['class_code'] for c in data['classes']]
        self.assertIn('1A', class_codes)
        self.assertIn('2A', class_codes)
        self.assertIn('3A', class_codes)

        # Check coach counts per class
        class_map = {c['class_code']: c for c in data['classes']}
        self.assertEqual(class_map['1A']['coach_count'], 1)
        self.assertEqual(class_map['2A']['coach_count'], 5)
        self.assertEqual(class_map['3A']['coach_count'], 11)

        # Check coaches in 3A: B1 to B11
        coaches_3a = class_map['3A']['coaches']
        expected_3a = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11']
        self.assertEqual(coaches_3a, expected_3a)

        # Check coaches in 2A: A1 to A5
        coaches_2a = class_map['2A']['coaches']
        expected_2a = ['A1', 'A2', 'A3', 'A4', 'A5']
        self.assertEqual(coaches_2a, expected_2a)

        # Total coaches for this train must be 17
        self.assertEqual(len(data['all_coaches']), 17)

    def test_02_mail_express_sleeper_composition(self):
        """Train 7 (12137 Punjab Mail) must have full Sleeper (S1-S12), 3A, 2A, 1A."""
        resp = self.client.get('/api/trains/7/coaches')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']

        self.assertEqual(data['train_number'], '12137')
        class_map = {c['class_code']: c for c in data['classes']}
        self.assertIn('SL', class_map)
        self.assertEqual(class_map['SL']['coach_count'], 12)
        expected_sl = [f'S{i}' for i in range(1, 13)]
        self.assertEqual(class_map['SL']['coaches'], expected_sl)

        self.assertEqual(class_map['3A']['coach_count'], 6)
        expected_3a = [f'B{i}' for i in range(1, 7)]
        self.assertEqual(class_map['3A']['coaches'], expected_3a)

    def test_03_shatabdi_and_vande_bharat_composition(self):
        """Train 9 (Shatabdi) & Train 13 (Vande Bharat) must have authentic EC and CC."""
        # Shatabdi
        resp9 = self.client.get('/api/trains/9/coaches')
        self.assertEqual(resp9.status_code, 200)
        data9 = resp9.get_json()['data']
        class_map9 = {c['class_code']: c for c in data9['classes']}
        self.assertEqual(class_map9['EC']['coach_count'], 2)
        self.assertEqual(class_map9['CC']['coach_count'], 10)

        # Vande Bharat
        resp13 = self.client.get('/api/trains/13/coaches')
        self.assertEqual(resp13.status_code, 200)
        data13 = resp13.get_json()['data']
        class_map13 = {c['class_code']: c for c in data13['classes']}
        self.assertEqual(class_map13['EC']['coach_count'], 2)
        self.assertEqual(class_map13['CC']['coach_count'], 8)

    def test_04_class_filtering_on_coaches_endpoint(self):
        """Filtering by ?class=3A must return only 3A coaches in data['coaches']."""
        resp = self.client.get('/api/trains/1/coaches?class=3A')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']

        coaches = data['coaches']
        self.assertEqual(len(coaches), 11)
        for c in coaches:
            self.assertEqual(c['coach_class'], '3A')

    def test_05_seats_inventory_integrity(self):
        """Each coach must have complete valid seat rows in seats table."""
        comp = RailwayService.get_train_coach_composition(1)
        coach_b2 = next(c for c in comp['coaches'] if c['coach_number'] == 'B2')
        
        # Load seats via API
        resp = self.client.get(f'/api/coaches/{coach_b2["id"]}/seats')
        self.assertEqual(resp.status_code, 200)
        seats = resp.get_json()['data']['seats']
        self.assertEqual(len(seats), 72)
        
        # Verify Indian Railways 3A berth type mapping
        seat1 = next(s for s in seats if s['seat_number'] == 1)
        self.assertEqual(seat1['seat_type'], 'LOWER')
        self.assertTrue(seat1['is_window'])

        seat2 = next(s for s in seats if s['seat_number'] == 2)
        self.assertEqual(seat2['seat_type'], 'MIDDLE')

        seat3 = next(s for s in seats if s['seat_number'] == 3)
        self.assertEqual(seat3['seat_type'], 'UPPER')

        seat7 = next(s for s in seats if s['seat_number'] == 7)
        self.assertEqual(seat7['seat_type'], 'SIDE_LOWER')
        self.assertTrue(seat7['is_window'])

    def test_06_ai_seat_recommender_full_ranking(self):
        """AI seat recommender must evaluate ALL available seats across coaches and return complete ranked list."""
        payload = {
            'train_id': 1,
            'coach_class': '3A',
            'passenger_type': 'elderly',
            'preference': 'LOWER',
            'journey_date': '2026-10-15'
        }
        resp = self.client.post('/api/seats/recommend', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']

        total_eval = data['total_evaluated']
        recs = data['recommendations']
        self.assertGreater(total_eval, 500)
        self.assertEqual(len(recs), total_eval)

        # Sorted descending by score
        scores = [r['recommendation_score'] for r in recs]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # Top match should be Lower Berth and senior friendly
        top = data['top_match']
        self.assertIsNotNone(top)
        self.assertEqual(top['seat_type'], 'LOWER')
        self.assertGreaterEqual(top['recommendation_score'], 85)
        self.assertIn('Lower Berth', top['match_factors'])
        self.assertIn('Senior Friendly', top['match_factors'])
        self.assertIn('Coach', top['explanation'])

    def test_07_ai_recommender_filters_occupied_and_locked(self):
        """AI recommender must not recommend occupied or locked seats."""
        # Find an available seat
        comp = RailwayService.get_train_coach_composition(1)
        b1_coach = next(c for c in comp['coaches'] if c['coach_number'] == 'B1')
        seat_row = execute_query(
            "SELECT id, seat_number FROM seats WHERE coach_id = %s AND seat_number = 25",
            (b1_coach['id'],),
            fetchone=True
        )
        seat_id = seat_row['id']

        # Lock this seat with session A
        lock_res = self.client.post('/api/seats/lock', json={
            'seat_ids': [seat_id],
            'journey_date': '2026-10-20',
            'session_id': 'other_session_xyz_999'
        })
        self.assertEqual(lock_res.status_code, 200)

        # AI recommendation requested by session B
        rec_res = self.client.post('/api/seats/recommend', json={
            'train_id': 1,
            'coach_class': '3A',
            'coach_id': b1_coach['id'],
            'journey_date': '2026-10-20',
            'session_id': 'session_abc_111'
        })
        self.assertEqual(rec_res.status_code, 200)
        recs = rec_res.get_json()['data']['recommendations']

        # Locked seat must NOT be in recommendations
        rec_ids = [r['seat_id'] for r in recs]
        self.assertNotIn(seat_id, rec_ids)

        # Clean up lock
        self.client.post('/api/seats/release', json={
            'session_id': 'other_session_xyz_999',
            'seat_ids': [seat_id]
        })

    def test_08_idempotency_of_coach_seeding(self):
        """Calling ensure_train_coaches repeatedly must not duplicate coaches or seats."""
        before_coaches = execute_query("SELECT count(*) as cnt FROM coaches WHERE train_id = 1", fetchone=True)['cnt']
        before_seats = execute_query(
            "SELECT count(*) as cnt FROM seats WHERE coach_id IN (SELECT id FROM coaches WHERE train_id = 1)",
            fetchone=True
        )['cnt']

        # Run ensure multiple times
        RailwayService.ensure_train_coaches(1)
        RailwayService.ensure_train_coaches(1)

        after_coaches = execute_query("SELECT count(*) as cnt FROM coaches WHERE train_id = 1", fetchone=True)['cnt']
        after_seats = execute_query(
            "SELECT count(*) as cnt FROM seats WHERE coach_id IN (SELECT id FROM coaches WHERE train_id = 1)",
            fetchone=True
        )['cnt']

        self.assertEqual(before_coaches, after_coaches)
        self.assertEqual(before_seats, after_seats)

if __name__ == '__main__':
    unittest.main()
