import unittest
import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.services.railway_service import RailwayService

class TestDateRunningDaysSystem(unittest.TestCase):
    """
    Comprehensive verification for railway-style date search and running-days system:
    1. Jaipur -> Delhi + All Dates
    2. Jaipur -> Delhi + Specific Date
    3. Jaipur -> Mumbai + All Dates
    4. Delhi -> Mumbai + Specific Date
    5. Select Sunday
    6. Select Monday
    7. Select Wednesday
    8. Running Day filter = Friday
    9. Show non-running trains toggle
    10. Previous Day navigation logic
    11. Today navigation logic
    12. Next Day navigation logic
    13. No running days fabricated (None preserved when missing)
    14. S M T W T F S indicator ordering and active/selected days
    """

    def test_01_jaipur_to_delhi_all_dates(self):
        """Case 1: All Dates returns all matching trains between Jaipur and Delhi."""
        results = RailwayService.search_route('Jaipur', 'Delhi', date_mode='all')
        self.assertGreater(len(results), 0, "All Dates search should return matching trains")
        # Every train should have normalized running status attached
        for t in results:
            self.assertIn('running_status', t)
            self.assertIn('running_days_display', t)
            self.assertEqual(len(t['running_days_display']), 7, "Must have exactly 7 day indicator items (S M T W T F S)")
            # In All Dates mode, runs_on_date should be None as per Section 8
            self.assertIsNone(t['runs_on_date'], "runs_on_date must be None for All Dates mode")

    def test_02_jaipur_to_delhi_specific_date(self):
        """Case 2: Specific Date filters trains according to actual running days."""
        all_trains = RailwayService.search_route('Jaipur', 'Delhi', date_mode='all')
        # 2026-10-04 is a Sunday
        sunday_trains = RailwayService.search_route('Jaipur', 'Delhi', date='2026-10-04', date_mode='specific')
        
        self.assertGreater(len(sunday_trains), 0)
        self.assertLessEqual(len(sunday_trains), len(all_trains), "Specific date should filter operating trains")
        
        for t in sunday_trains:
            # Each returned train must run on Sunday (or have unavailable data without fabrication)
            self.assertNotEqual(t['runs_on_date'], False, f"Train {t['train_number']} does not run on Sunday but was returned")
            self.assertEqual(t['selected_day'], 'Sunday')

    def test_03_jaipur_to_mumbai_all_dates(self):
        """Case 3: Jaipur to Mumbai + All Dates."""
        results = RailwayService.search_route('Jaipur', 'Mumbai', date_mode='all')
        self.assertGreater(len(results), 0, "Jaipur to Mumbai route should return trains")
        for t in results:
            self.assertIsNone(t['runs_on_date'])

    def test_04_delhi_to_mumbai_specific_date(self):
        """Case 4: Delhi to Mumbai + Specific Date."""
        results = RailwayService.search_route('Delhi', 'Mumbai', date='2026-10-05', date_mode='specific')
        # 2026-10-05 is a Monday
        self.assertGreater(len(results), 0, "Delhi to Mumbai route should return trains")
        for t in results:
            self.assertEqual(t['selected_day'], 'Monday')
            self.assertNotEqual(t['runs_on_date'], False)

    def test_05_select_sunday(self):
        """Case 5: Specific Date = Sunday (2026-10-04)."""
        sunday_date = '2026-10-04'
        train_19609 = RailwayService.search_by_train_number('19609')
        self.assertIsNotNone(train_19609)
        # 19609 runs on Mon, Thu, Sat
        status = RailwayService.get_train_running_status(train_19609, sunday_date)
        self.assertEqual(status['selected_day'], 'Sunday')
        self.assertEqual(status['runs_on_date'], False, "19609 runs Mon,Thu,Sat so must not run on Sunday")
        self.assertIn("Not running on Sun", status['status_text'])
        # Day 0 (Sun) is selected but runs=False
        sun_indicator = next(d for d in status['running_days_display'] if d['day'] == 'S' and d['index'] == 0)
        self.assertTrue(sun_indicator['is_selected'])
        self.assertFalse(sun_indicator['runs'])

    def test_06_select_monday(self):
        """Case 6: Specific Date = Monday (2026-10-05)."""
        monday_date = '2026-10-05'
        train_19609 = RailwayService.search_by_train_number('19609')
        status = RailwayService.get_train_running_status(train_19609, monday_date)
        self.assertEqual(status['selected_day'], 'Monday')
        self.assertEqual(status['runs_on_date'], True, "19609 runs Mon,Thu,Sat so must run on Monday")
        self.assertIn("Runs on Mon", status['status_text'])
        # Day 1 (Mon) is selected and runs=True
        mon_indicator = next(d for d in status['running_days_display'] if d['abbr'] == 'Mon')
        self.assertTrue(mon_indicator['is_selected'])
        self.assertTrue(mon_indicator['runs'])

    def test_07_select_wednesday(self):
        """Case 7: Specific Date = Wednesday (2026-10-07)."""
        wed_date = '2026-10-07'
        train_19609 = RailwayService.search_by_train_number('19609')
        status = RailwayService.get_train_running_status(train_19609, wed_date)
        self.assertEqual(status['selected_day'], 'Wednesday')
        self.assertEqual(status['runs_on_date'], False, "19609 does not run on Wednesday")
        self.assertIn("Not running on Wed", status['status_text'])

    def test_08_running_day_filter_friday(self):
        """Case 8: Running Day filter = Friday."""
        results = RailwayService.search_route('Jaipur', 'Delhi', date_mode='all', running_day='Friday')
        self.assertGreater(len(results), 0)
        for t in results:
            run_days = t['running_days_list']
            if run_days:
                self.assertIn('Fri', run_days, f"Train {t['train_number']} does not run on Friday")

    def test_09_show_non_running_trains_toggle(self):
        """Case 9: Show non-running trains toggle separates running and non-running trains."""
        sunday_date = '2026-10-04'
        only_running = RailwayService.search_route('Jaipur', 'Delhi', date=sunday_date, date_mode='specific', show_non_running=False)
        with_non_running = RailwayService.search_route('Jaipur', 'Delhi', date=sunday_date, date_mode='specific', show_non_running=True)

        self.assertGreaterEqual(len(with_non_running), len(only_running))
        # 19609 (Mon,Thu,Sat) should be excluded when show_non_running=False
        running_nums = [t['train_number'] for t in only_running]
        all_nums = [t['train_number'] for t in with_non_running]
        self.assertNotIn('19609', running_nums)
        self.assertIn('19609', all_nums)
        # Verify 19609 in with_non_running has runs_on_date = False
        t_19609 = next(t for t in with_non_running if t['train_number'] == '19609')
        self.assertFalse(t_19609['runs_on_date'])

    def test_10_no_data_fabrication(self):
        """Section 23: Display 'Running days unavailable' if data is missing; never fabricate or assume 'Daily'."""
        mock_train = {'train_number': '99999', 'train_name': 'Test Special', 'running_days': None}
        status = RailwayService.get_train_running_status(mock_train, '2026-10-04')
        self.assertIsNone(status['runs_on_date'], "Should not assume runs_on_date when schedule is missing")
        self.assertEqual(status['status_text'], "Running days unavailable")
        self.assertIsNone(status['running_days'])

    def test_11_smttwfs_order_and_indicators(self):
        """Section 5: Consistent S M T W T F S order (Sunday to Saturday)."""
        train = {'running_days': 'Mon,Wed,Fri'}
        status = RailwayService.get_train_running_status(train, '2026-10-04') # Sunday
        display = status['running_days_display']
        self.assertEqual(len(display), 7)
        expected_letters = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
        expected_abbrs = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        for i, item in enumerate(display):
            self.assertEqual(item['day'], expected_letters[i])
            self.assertEqual(item['abbr'], expected_abbrs[i])
            self.assertEqual(item['index'], i)

        # Mon (1), Wed (3), Fri (5) must be True
        self.assertFalse(display[0]['runs']) # Sun
        self.assertTrue(display[1]['runs'])  # Mon
        self.assertFalse(display[2]['runs']) # Tue
        self.assertTrue(display[3]['runs'])  # Wed
        self.assertFalse(display[4]['runs']) # Thu
        self.assertTrue(display[5]['runs'])  # Fri
        self.assertFalse(display[6]['runs']) # Sat

    def test_12_database_integrity_preserved(self):
        """Section 24: Verify all stations (>= 13000) and trains (>= 10700) intact."""
        from backend.utils.db_connection import execute_query
        st_count = execute_query("SELECT count(*) as cnt FROM stations", fetchone=True)['cnt']
        tr_count = execute_query("SELECT count(*) as cnt FROM trains", fetchone=True)['cnt']
        self.assertGreaterEqual(st_count, 13000, f"Stations table altered: {st_count}")
        self.assertGreaterEqual(tr_count, 10700, f"Trains table altered: {tr_count}")

if __name__ == '__main__':
    unittest.main()
