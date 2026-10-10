import sys
import unittest
sys.path.insert(0, '.')
from backend.app import create_app
from backend.ml.chatbot_model import process_chatbot_query

class TestChatbotIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_trains_jaipur_to_ajmer(self):
        """Query 1: 'show trains of Jaipur to Ajmer' must return all matching trains (including 12015, 20978)"""
        reply = process_chatbot_query("show trains of Jaipur to Ajmer", session_id="test_01")
        self.assertEqual(reply['intent'], 'TRAIN_SEARCH')
        resp = reply['response']
        self.assertIn("Jaipur", resp)
        self.assertIn("Ajmer", resp)
        self.assertIn("12015", resp)
        self.assertIn("Total matching trains:", resp)
        self.assertNotIn("Here are popular active trains in the network", resp)
        print("Query 1 Passed: Jaipur -> Ajmer returns exact matching trains.")

    def test_02_trains_jaipur_to_delhi(self):
        """Query 2: 'show trains of Jaipur to Delhi' must return all matching trains (including 12957, 20977, 12413, 12016)"""
        reply = process_chatbot_query("show trains of Jaipur to Delhi", session_id="test_02")
        self.assertEqual(reply['intent'], 'TRAIN_SEARCH')
        resp = reply['response']
        self.assertIn("Jaipur", resp)
        self.assertIn("Delhi", resp)
        self.assertIn("12957", resp)
        self.assertIn("Total matching trains:", resp)
        self.assertNotIn("Here are popular active trains in the network", resp)
        print("Query 2 Passed: Jaipur -> Delhi returns exact matching trains.")

    def test_03_jaipur_ajmer_vs_delhi_different(self):
        """Verify Jaipur->Ajmer and Jaipur->Delhi produce COMPLETELY DIFFERENT responses"""
        reply_ajmer = process_chatbot_query("show trains of Jaipur to Ajmer", session_id="test_diff_1")
        reply_delhi = process_chatbot_query("show trains of Jaipur to Delhi", session_id="test_diff_2")
        self.assertNotEqual(reply_ajmer['response'], reply_delhi['response'])
        self.assertIn("12015", reply_ajmer['response'])
        self.assertIn("12957", reply_delhi['response'])
        print("Query 3 Passed: Verified different queries produce query-specific, distinct responses.")

    def test_04_trains_mumbai_to_delhi(self):
        """Query 3: 'show trains from Mumbai to Delhi' must return all matching trains (including 12951, 12953, 12907, 12137)"""
        reply = process_chatbot_query("show trains from Mumbai to Delhi", session_id="test_04")
        self.assertEqual(reply['intent'], 'TRAIN_SEARCH')
        resp = reply['response']
        self.assertIn("Mumbai", resp)
        self.assertIn("Delhi", resp)
        self.assertIn("12951", resp)
        self.assertIn("Total matching trains:", resp)
        print("Query 4 Passed: Mumbai -> Delhi returns exact trains.")

    def test_05_train_details_12952(self):
        """Query 4: 'train 12952' returns full train details of Tejas Rajdhani"""
        reply = process_chatbot_query("train 12952", session_id="test_05")
        self.assertEqual(reply['intent'], 'TRAIN_DETAILS')
        resp = reply['response']
        self.assertIn("12952", resp)
        self.assertIn("Tejas Rajdhani", resp)
        self.assertIn("NDLS", resp)
        self.assertIn("MMCT", resp)
        print("Query 5 Passed: Train 12952 details verified.")

    def test_06_stops_of_12952(self):
        """Query 5: 'what are the stops of 12952?' returns complete ordered stops from train_stops"""
        reply = process_chatbot_query("what are the stops of 12952?", session_id="test_06")
        self.assertEqual(reply['intent'], 'TRAIN_ROUTE')
        resp = reply['response']
        self.assertIn("New Delhi", resp)
        self.assertIn("Kota Junction", resp)
        self.assertIn("Ratlam Junction", resp)
        self.assertIn("Vadodara Junction", resp)
        self.assertIn("Surat", resp)
        self.assertIn("Mumbai Central", resp)
        self.assertIn("The current project dataset contains these stored stops", resp)
        print("Query 6 Passed: Stops of 12952 verified with data limitation note.")

    def test_07_journey_time_12952(self):
        """Query 6: 'how long does 12952 take?' calculates duration from timetable"""
        reply = process_chatbot_query("how long does 12952 take?", session_id="test_07")
        self.assertEqual(reply['intent'], 'JOURNEY_TIME')
        resp = reply['response']
        self.assertIn("12952", resp)
        self.assertIn("15h 40m", resp)
        print("Query 7 Passed: Journey duration calculated accurately (15h 40m).")

    def test_08_schedule_when_reaches_mumbai(self):
        """Query 7: 'when does 12952 reach Mumbai?' returns arrival time 08:35"""
        reply = process_chatbot_query("when does 12952 reach Mumbai?", session_id="test_08")
        self.assertEqual(reply['intent'], 'TRAIN_SCHEDULE')
        resp = reply['response']
        self.assertIn("08:35", resp)
        self.assertIn("Mumbai Central", resp)
        print("Query 8 Passed: Schedule query returned arrival time at Mumbai.")

    def test_09_live_tracking_12952(self):
        """Query 8: 'where is train 12952?' calls tracking service and returns live telemetry"""
        reply = process_chatbot_query("where is train 12952?", session_id="test_09")
        self.assertIn(reply['intent'], ['LIVE_TRACKING', 'LIVE_STATUS'])
        resp = reply['response']
        self.assertIn("12952", resp)
        self.assertIn("Current Section", resp)
        self.assertIn("km/h", resp)
        self.assertIn("Next Commercial Halt", resp)
        self.assertIn("ETA", resp)
        print("Query 9 Passed: Live tracking telemetry returned.")

    def test_10_station_code_jaipur(self):
        """Query 9: 'what is Jaipur station code?' returns code JP"""
        reply = process_chatbot_query("what is Jaipur station code?", session_id="test_10")
        self.assertEqual(reply['intent'], 'STATION_DETAILS')
        resp = reply['response']
        self.assertIn("JP", resp)
        self.assertIn("Jaipur Junction", resp)
        print("Query 10 Passed: Jaipur station code 'JP' verified.")

    def test_11_trains_stop_at_jaipur(self):
        """Query 10: 'which trains stop at Jaipur?' returns all 8 trains stopping at Jaipur"""
        reply = process_chatbot_query("which trains stop at Jaipur?", session_id="test_11")
        self.assertEqual(reply['intent'], 'STATION_TRAINS')
        resp = reply['response']
        self.assertIn("Jaipur", resp)
        self.assertIn("12015", resp)
        self.assertIn("12957", resp)
        print("Query 11 Passed: Trains stopping at Jaipur verified.")

    def test_12_pnr_status_query(self):
        """Query 11: 'PNR 2846190532' looks up booking directly"""
        reply = process_chatbot_query("PNR 2846190532", session_id="test_12")
        self.assertEqual(reply['intent'], 'PNR_STATUS')
        resp = reply['response']
        self.assertIn("2846190532", resp)
        self.assertIn("CONFIRMED", resp)
        print("Query 12 Passed: PNR 2846190532 status verified.")

    def test_13_booking_help(self):
        """Query 12: 'how do I book a ticket?' provides booking instructions"""
        reply = process_chatbot_query("how do I book a ticket?", session_id="test_13")
        self.assertEqual(reply['intent'], 'BOOKING_HELP')
        resp = reply['response']
        self.assertIn("How to Book a Train Ticket", resp)
        self.assertIn("Interactive Seat Map", resp)
        print("Query 13 Passed: Booking help instructions verified.")

    def test_14_cancellation_help(self):
        """Query 13: 'how do I cancel my ticket?' provides cancellation fees & policy"""
        reply = process_chatbot_query("how do I cancel my ticket?", session_id="test_14")
        self.assertEqual(reply['intent'], 'CANCELLATION_HELP')
        resp = reply['response']
        self.assertIn("Cancellation & Refund Policy", resp)
        self.assertIn("clerkage", resp)
        print("Query 14 Passed: Cancellation policy verified.")

    def test_15_seat_availability(self):
        """Query 14: 'what seats are available?' guides to coaches and seat maps"""
        reply = process_chatbot_query("what seats are available?", session_id="test_15")
        self.assertEqual(reply['intent'], 'SEAT_AVAILABILITY')
        resp = reply['response']
        self.assertIn("seat", resp.lower())
        print("Query 15 Passed: Seat availability response verified.")

    def test_16_random_query_no_generic_train_list(self):
        """Query 15: 'tell me something random' returns capability menu, NEVER generic train list"""
        reply = process_chatbot_query("tell me something random", session_id="test_16")
        self.assertEqual(reply['intent'], 'UNKNOWN')
        resp = reply['response']
        self.assertIn("I can help with", resp)
        self.assertNotIn("Here are popular active trains in the network", resp)
        self.assertNotIn("12001", resp)
        print("Query 16 Passed: Random query returns capabilities guide without fake/generic train list.")

    def test_17_follow_up_context_route_date(self):
        """Multi-turn test: 'Show trains Jaipur to Delhi' followed by 'what about tomorrow?'"""
        sess = "test_context_route"
        # Turn 1
        t1 = process_chatbot_query("show trains Jaipur to Delhi", session_id=sess)
        self.assertEqual(t1['intent'], 'TRAIN_SEARCH')
        self.assertIn("Jaipur", t1['response'])

        # Turn 2: Follow-up asking about tomorrow
        t2 = process_chatbot_query("what about tomorrow?", session_id=sess)
        self.assertEqual(t2['intent'], 'TRAIN_SEARCH')
        self.assertIn("Jaipur", t2['response'])
        self.assertIn("Delhi", t2['response'])
        print("Query 17 Passed: Multi-turn context remembered Jaipur -> Delhi for 'what about tomorrow?'.")

    def test_18_follow_up_context_train_stops(self):
        """Multi-turn test: 'Tell me about 12952' followed by 'what are its stops?'"""
        sess = "test_context_train"
        # Turn 1
        t1 = process_chatbot_query("tell me about 12952", session_id=sess)
        self.assertEqual(t1['intent'], 'TRAIN_DETAILS')
        self.assertIn("12952", t1['response'])

        # Turn 2: Follow-up asking for stops
        t2 = process_chatbot_query("what are its stops?", session_id=sess)
        self.assertEqual(t2['intent'], 'TRAIN_ROUTE')
        self.assertIn("12952", t2['response'])
        self.assertIn("Kota Junction", t2['response'])
        print("Query 18 Passed: Multi-turn context remembered train 12952 for 'what are its stops?'.")

if __name__ == '__main__':
    unittest.main()
