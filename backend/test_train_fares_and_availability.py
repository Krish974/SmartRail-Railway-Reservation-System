import os
import sys
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app
from backend.services.railway_service import RailwayService
from backend.models.booking_model import BookingModel
from backend.utils.db_connection import execute_query

class TestTrainFaresAndAvailability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_jaipur_delhi_leg_fares(self):
        """Jaipur to Delhi (~308 km) fares must be authentic distance-based telescopic fares."""
        res = RailwayService.search_route('JP', 'DLI', date='2026-10-14')
        self.assertGreater(len(res), 0, "Expected trains on JP to DLI")
        t = res[0]
        self.assertGreater(t.get('leg_distance_km', 0), 250)
        self.assertLess(t.get('leg_distance_km', 0), 350)

        classes = {c['class_code']: c for c in t.get('classes', [])}
        # Verify SL fare is NOT the static fallback 650.0
        if 'SL' in classes:
            sl_fare = classes['SL']['adjusted_fare']
            self.assertNotEqual(sl_fare, 650.0, "SL fare must not be static fallback ₹650")
            self.assertGreaterEqual(sl_fare, 150.0)
            self.assertLessEqual(sl_fare, 300.0)

        # Verify 3A fare is NOT the static fallback 1750.0
        if '3A' in classes:
            a3_fare = classes['3A']['adjusted_fare']
            self.assertNotEqual(a3_fare, 1750.0, "3A fare must not be static fallback ₹1750")
            self.assertGreaterEqual(a3_fare, 450.0)
            self.assertLessEqual(a3_fare, 750.0)

        # Verify 2A fare is NOT the static fallback 2550.0
        if '2A' in classes:
            a2_fare = classes['2A']['adjusted_fare']
            self.assertNotEqual(a2_fare, 2550.0, "2A fare must not be static fallback ₹2550")
            self.assertGreaterEqual(a2_fare, 700.0)
            self.assertLessEqual(a2_fare, 1100.0)

        # Verify 1A fare is NOT the static fallback 4200.0
        if '1A' in classes:
            a1_fare = classes['1A']['adjusted_fare']
            self.assertNotEqual(a1_fare, 4200.0, "1A fare must not be static fallback ₹4200")
            self.assertGreaterEqual(a1_fare, 1100.0)
            self.assertLessEqual(a1_fare, 1700.0)

    def test_02_jaipur_mumbai_leg_fares(self):
        """Jaipur to Mumbai (~1150 km) fares must be substantially higher than Jaipur to Delhi."""
        res_dli = RailwayService.search_route('JP', 'DLI', date='2026-10-14')
        res_mumbai = RailwayService.search_route('JP', 'BDTS', date='2026-10-14')
        self.assertGreater(len(res_dli), 0)
        self.assertGreater(len(res_mumbai), 0)

        t_dli = res_dli[0]
        t_mum = res_mumbai[0]

        cls_dli = {c['class_code']: c for c in t_dli.get('classes', [])}
        cls_mum = {c['class_code']: c for c in t_mum.get('classes', [])}

        if '3A' in cls_dli and '3A' in cls_mum:
            self.assertGreater(
                cls_mum['3A']['adjusted_fare'],
                cls_dli['3A']['adjusted_fare'] * 1.5,
                "Jaipur-Mumbai 3A fare must be significantly higher than Jaipur-Delhi"
            )

        if 'SL' in cls_dli and 'SL' in cls_mum:
            self.assertGreater(
                cls_mum['SL']['adjusted_fare'],
                cls_dli['SL']['adjusted_fare'] * 1.5,
                "Jaipur-Mumbai SL fare must be significantly higher than Jaipur-Delhi"
            )

    def test_03_delhi_kanpur_vs_delhi_howrah(self):
        """Delhi to Kanpur (~435 km) must not be charged full Delhi to Howrah (~1445 km) fare."""
        fare_kanpur = RailwayService.calculate_railway_fare('Superfast Express', '3A', 435.0, quota='GN')
        fare_howrah = RailwayService.calculate_railway_fare('Superfast Express', '3A', 1445.0, quota='GN')

        self.assertIsNotNone(fare_kanpur['adjusted_fare'])
        self.assertIsNotNone(fare_howrah['adjusted_fare'])
        self.assertLess(fare_kanpur['adjusted_fare'], fare_howrah['adjusted_fare'])
        # Kanpur 3A ~₹615 vs Howrah 3A ~₹1710
        self.assertLess(fare_kanpur['adjusted_fare'], 900.0)
        self.assertGreater(fare_howrah['adjusted_fare'], 1500.0)

    def test_04_tejas_rajdhani_fare_premium_and_no_sleeper(self):
        """Tejas Rajdhani (12952) must have premium fares and strictly omit Sleeper (SL)."""
        resp = self.client.get('/api/trains/1/coaches')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        class_codes = [c['class_code'] for c in data['classes']]

        self.assertNotIn('SL', class_codes, "Rajdhani Express must not include Sleeper (SL)")
        self.assertNotIn('CC', class_codes, "Rajdhani Express must not include Chair Car (CC)")
        self.assertIn('3A', class_codes)
        self.assertIn('2A', class_codes)
        self.assertIn('1A', class_codes)

        # Tejas Rajdhani fare calculation for 1384 km
        raj_fare = RailwayService.calculate_railway_fare('Tejas Rajdhani', '3A', 1384.0)
        exp_fare = RailwayService.calculate_railway_fare('Express', '3A', 1384.0)
        self.assertGreater(raj_fare['adjusted_fare'], exp_fare['adjusted_fare'], "Rajdhani must carry premium supplement")

    def test_05_shatabdi_and_vande_bharat_classes(self):
        """Shatabdi and Vande Bharat must strictly show ONLY EC and CC."""
        # Train 9 is Shatabdi
        resp9 = self.client.get('/api/trains/9/coaches')
        self.assertEqual(resp9.status_code, 200)
        classes9 = [c['class_code'] for c in resp9.get_json()['data']['classes']]
        self.assertEqual(set(classes9), {'EC', 'CC'}, "Shatabdi must strictly have EC and CC only")

        # Train 13 is Vande Bharat
        resp13 = self.client.get('/api/trains/13/coaches')
        self.assertEqual(resp13.status_code, 200)
        classes13 = [c['class_code'] for c in resp13.get_json()['data']['classes']]
        self.assertEqual(set(classes13), {'EC', 'CC'}, "Vande Bharat must strictly have EC and CC only")

    def test_06_garib_rath_classes(self):
        """Garib Rath must show only 3A with subsidized fare."""
        comp = RailwayService.get_default_composition_for_train('Garib Rath Express')
        class_types = set(c[1] for c in comp)
        self.assertEqual(class_types, {'3A'}, "Garib Rath must have 3A only")

        # Garib rath 3A fare must be subsidized compared to standard 3A
        gr_fare = RailwayService.calculate_railway_fare('Garib Rath Express', '3A', 1000.0)
        sf_fare = RailwayService.calculate_railway_fare('Superfast Express', '3A', 1000.0)
        self.assertLess(gr_fare['adjusted_fare'], sf_fare['adjusted_fare'])

    def test_07_no_static_identical_availability(self):
        """Different trains must NOT all repeat identical availability counts (24, 144, 288, 720)."""
        res = RailwayService.search_route('JP', 'DLI', date='2026-10-14')
        self.assertGreater(len(res), 1, "Need at least 2 trains on JP-DLI")

        # Collect availability status strings across different trains
        train_statuses = []
        for t in res:
            statuses = {c['class_code']: c.get('status') for c in t.get('classes', [])}
            train_statuses.append(statuses)

        # Check that compositions and capacities vary among trains
        capacities_3a = [t_s.get('3A') for t_s in train_statuses if '3A' in t_s]
        # At least one train should not be "AVAILABLE 288"
        self.assertFalse(
            all(s == 'AVAILABLE 288' for s in capacities_3a),
            "Not all trains should show AVAILABLE 288"
        )

    def test_08_no_date_all_dates_mode(self):
        """When no date is provided (All Dates mode), status must be 'Select date for live availability'."""
        comp = RailwayService.get_train_coach_composition(1, date=None)
        self.assertIsNotNone(comp)
        for cls in comp['classes']:
            self.assertEqual(
                cls['status'],
                'Select date for live availability',
                "All dates mode must prompt to select date for live availability"
            )
            self.assertIsNone(cls['available_seats'])

    def test_09_non_running_train_on_date(self):
        """When a train does not operate on the selected date, status must reflect 'Not Running'."""
        # Train 5 (12907 BDTS NZM Sampark Kranti) runs only Wed, Sun
        # Check a Monday: 2026-10-12 is Monday
        comp = RailwayService.get_train_coach_composition(5, date='2026-10-12')
        self.assertIsNotNone(comp)
        for cls in comp['classes']:
            self.assertEqual(cls['status'], 'Not Running')
            self.assertEqual(cls['available_seats'], 0)

    def test_10_quota_tatkal_surcharge_and_rules(self):
        """Tatkal (TQ) must apply Tatkal surcharges and NOT be applicable in 1A."""
        # General fare
        fare_gn = RailwayService.calculate_railway_fare('Superfast Express', '3A', 500.0, quota='GN')
        # Tatkal fare
        fare_tq = RailwayService.calculate_railway_fare('Superfast Express', '3A', 500.0, quota='TQ')
        self.assertGreater(fare_tq['adjusted_fare'], fare_gn['adjusted_fare'])
        self.assertTrue(fare_tq['is_applicable'])

        # 1A Tatkal is NOT applicable
        fare_1a_tq = RailwayService.calculate_railway_fare('Superfast Express', '1A', 500.0, quota='TQ')
        self.assertFalse(fare_1a_tq['is_applicable'])
        self.assertIsNone(fare_1a_tq['adjusted_fare'])

        # Check composition with Tatkal quota
        comp_tq = RailwayService.get_train_coach_composition(7, date='2026-10-14', quota='TQ')
        cls_map = {c['class_code']: c for c in comp_tq['classes']}
        if '1A' in cls_map:
            self.assertEqual(cls_map['1A']['status'], 'Not Applicable')

    def test_11_quota_ladies_and_senior_citizen(self):
        """Ladies (LD) and Senior Citizen (SS) must allocate dedicated quota and not apply in 1A."""
        # Ladies quota
        is_ld_valid, ld_seats_3a = RailwayService.get_quota_allocated_seats('3A', 288, quota='LD')
        self.assertTrue(is_ld_valid)
        self.assertEqual(ld_seats_3a, 6)

        is_ld_1a, _ = RailwayService.get_quota_allocated_seats('1A', 24, quota='LD')
        self.assertFalse(is_ld_1a, "Ladies quota not applicable in 1A")

        # Senior citizen concession
        fare_ss = RailwayService.calculate_railway_fare('Superfast Express', '3A', 800.0, quota='SS')
        fare_gn = RailwayService.calculate_railway_fare('Superfast Express', '3A', 800.0, quota='GN')
        self.assertLess(fare_ss['adjusted_fare'], fare_gn['adjusted_fare'])

    def test_12_seat_selection_fare_matches_search(self):
        """Fetching /api/trains/<id>/coaches?from=JP&to=DLI returns leg fare matching search."""
        search_res = RailwayService.search_route('JP', 'DLI', date='2026-10-14')
        self.assertGreater(len(search_res), 0)
        t = search_res[0]
        search_3a = next((c for c in t['classes'] if c['class_code'] == '3A'), None)

        resp = self.client.get(f'/api/trains/{t["id"]}/coaches?from=JP&to=DLI&date=2026-10-14&quota=GN')
        self.assertEqual(resp.status_code, 200)
        coaches_data = resp.get_json()['data']
        coaches_3a = next((c for c in coaches_data['classes'] if c['class_code'] == '3A'), None)

        if search_3a and coaches_3a:
            self.assertEqual(search_3a['adjusted_fare'], coaches_3a['adjusted_fare'],
                             "Fare on search page must match fare on seat selection page")

    def test_13_booking_creation_real_time_sold_out_rejection(self):
        """BookingModel must reject booking if the selected seat is already confirmed for that date."""
        import time
        t_date = f"2028-06-{int(time.time() * 1000) % 25 + 1:02d}"
        # 1. Create initial booking for seat 10
        booking1 = BookingModel.create_booking(
            user_id=2,
            train_id=1,
            coach_id=1,
            journey_date=t_date,
            quota_code='GN',
            passengers=[{'name': 'Test Passenger 1', 'age': 30, 'gender': 'Male', 'seat_id': 10}],
            base_fare=1500.0
        )
        self.assertIsNotNone(booking1['pnr'])

        # 2. Attempt duplicate booking for same seat and journey date -> must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            BookingModel.create_booking(
                user_id=2,
                train_id=1,
                coach_id=1,
                journey_date=t_date,
                quota_code='GN',
                passengers=[{'name': 'Test Passenger 2', 'age': 25, 'gender': 'Female', 'seat_id': 10}],
                base_fare=1500.0
            )
        self.assertIn("no longer available", str(ctx.exception).lower())

    def test_14_booking_uses_leg_fare(self):
        """BookingModel must record leg base fare when leg parameters or base_fare are passed."""
        import time
        t_date = f"2028-07-{int(time.time() * 1000) % 25 + 1:02d}"
        booking = BookingModel.create_booking(
            user_id=2,
            train_id=1,
            coach_id=1,
            journey_date=t_date,
            quota_code='GN',
            passengers=[{'name': 'Leg Passenger', 'age': 28, 'gender': 'Male', 'seat_id': 15}],
            base_fare=635.0,
            from_station='JP',
            to_station='DLI'
        )
        self.assertEqual(booking['base_fare'], 635.0)
        self.assertGreater(booking['total_fare'], 635.0) # includes GST + convenience fee

    def test_15_unavailable_fare_and_availability_states(self):
        """When distance is 0 or invalid, fare returns honest unavailable state."""
        fare_unavail = RailwayService.calculate_railway_fare('Express', '3A', 0)
        self.assertIsNone(fare_unavail['base_fare'])
        self.assertIsNone(fare_unavail['adjusted_fare'])
        self.assertFalse(fare_unavail['is_applicable'])

    def test_16_track_distance_calculation(self):
        """get_station_track_distance must return realistic track distances."""
        # JP to DLI
        dist_jp_dli = RailwayService.get_station_track_distance(boarding_code='JP', deboarding_code='DLI')
        self.assertIsNotNone(dist_jp_dli)
        self.assertGreaterEqual(dist_jp_dli, 280)
        self.assertLessEqual(dist_jp_dli, 330)

        # JP to BDTS
        dist_jp_bdts = RailwayService.get_station_track_distance(boarding_code='JP', deboarding_code='BDTS')
        self.assertIsNotNone(dist_jp_bdts)
        self.assertGreaterEqual(dist_jp_bdts, 1100)
        self.assertLessEqual(dist_jp_bdts, 1200)

if __name__ == '__main__':
    unittest.main()
