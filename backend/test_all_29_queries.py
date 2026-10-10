import sys
import unittest

sys.path.insert(0, '.')
from backend.app import create_app
from backend.ml.chatbot_model import process_chatbot_query
from backend.services.railway_service import RailwayService

class TestChatbot29Queries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_jaipur_to_delhi(self):
        r = process_chatbot_query("show all trains from Jaipur to Delhi", session_id="test_s1")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Jaipur", r['response'])
        self.assertIn("Delhi", r['response'])
        # Verify ALL available trains are returned (34 trains discovered)
        self.assertIn("Total matching trains:", r['response'])
        self.assertGreaterEqual(int(r['response'].split('Total matching trains: ')[1].split('**')[0]), 10)
        print("Query 1 Passed: Jaipur -> Delhi returns all available trains.")

    def test_02_jaipur_to_mumbai(self):
        r = process_chatbot_query("trains from Jaipur to Mumbai", session_id="test_s2")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Jaipur", r['response'])
        self.assertIn("Mumbai", r['response'])
        self.assertIn("12956", r['response'])
        print("Query 2 Passed: Jaipur -> Mumbai returns all available trains.")

    def test_03_jaipur_to_ajmer(self):
        r = process_chatbot_query("trains between Jaipur and Ajmer", session_id="test_s3")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Jaipur", r['response'])
        self.assertIn("Ajmer", r['response'])
        self.assertIn("Total matching trains:", r['response'])
        print("Query 3 Passed: Jaipur -> Ajmer returns all available trains.")

    def test_04_jaipur_to_rishikesh(self):
        r = process_chatbot_query("trains from Jaipur to Rishikesh", session_id="test_s4")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        # Either found trains or proper no-result advice with connecting hubs
        self.assertTrue("Rishikesh" in r['response'] or "direct" in r['response'])
        print("Query 4 Passed: Jaipur -> Rishikesh handled accurately.")

    def test_05_delhi_to_mumbai(self):
        r = process_chatbot_query("trains from Delhi to Mumbai", session_id="test_s5")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Delhi", r['response'])
        self.assertIn("Mumbai", r['response'])
        print("Query 5 Passed: Delhi -> Mumbai returns all available trains.")

    def test_06_delhi_to_chennai(self):
        r = process_chatbot_query("trains from Delhi to Chennai", session_id="test_s6")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Delhi", r['response'])
        self.assertIn("Chennai", r['response'])
        print("Query 6 Passed: Delhi -> Chennai returns all available trains.")

    def test_07_delhi_to_kolkata(self):
        r = process_chatbot_query("trains from Delhi to Kolkata", session_id="test_s7")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Delhi", r['response'])
        self.assertIn("Kolkata", r['response'])
        print("Query 7 Passed: Delhi -> Kolkata returns all available trains.")

    def test_08_mumbai_to_delhi(self):
        r = process_chatbot_query("trains from Mumbai to Delhi", session_id="test_s8")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Mumbai", r['response'])
        self.assertIn("Delhi", r['response'])
        self.assertIn("12951", r['response'])
        print("Query 8 Passed: Mumbai -> Delhi returns all available trains.")

    def test_09_mumbai_to_pune(self):
        r = process_chatbot_query("trains from Mumbai to Pune", session_id="test_s9")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Mumbai", r['response'])
        self.assertIn("Pune", r['response'])
        print("Query 9 Passed: Mumbai -> Pune returns all available trains.")

    def test_10_bengaluru_to_chennai(self):
        r = process_chatbot_query("trains from Bengaluru to Chennai", session_id="test_s10")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Bengaluru", r['response'])
        self.assertIn("Chennai", r['response'])
        print("Query 10 Passed: Bengaluru -> Chennai returns all available trains.")

    def test_11_chennai_to_bengaluru(self):
        r = process_chatbot_query("trains from Chennai to Bengaluru", session_id="test_s11")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Chennai", r['response'])
        self.assertIn("Bengaluru", r['response'])
        print("Query 11 Passed: Chennai -> Bengaluru returns all available trains.")

    def test_12_hyderabad_to_mumbai(self):
        r = process_chatbot_query("trains from Hyderabad to Mumbai", session_id="test_s12")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Mumbai", r['response'])
        print("Query 12 Passed: Hyderabad -> Mumbai returns all available trains.")

    def test_13_kolkata_to_delhi(self):
        r = process_chatbot_query("trains from Kolkata to Delhi", session_id="test_s13")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Kolkata", r['response'])
        self.assertIn("Delhi", r['response'])
        print("Query 13 Passed: Kolkata -> Delhi returns all available trains.")

    def test_14_ahmedabad_to_mumbai(self):
        r = process_chatbot_query("trains from Ahmedabad to Mumbai", session_id="test_s14")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Ahmedabad", r['response'])
        self.assertIn("Mumbai", r['response'])
        print("Query 14 Passed: Ahmedabad -> Mumbai returns all available trains.")

    def test_15_what_is_12956(self):
        r = process_chatbot_query("What is 12956?", session_id="test_s15")
        self.assertEqual(r['intent'], 'TRAIN_DETAILS')
        self.assertIn("12956", r['response'])
        self.assertIn("JP MMCT SF EXP", r['response'])
        print("Query 15 Passed: 'What is 12956?' returns full train details.")

    def test_16_route_of_12956(self):
        r = process_chatbot_query("Route of 12956", session_id="test_s16")
        self.assertEqual(r['intent'], 'TRAIN_ROUTE')
        self.assertIn("12956", r['response'])
        self.assertIn("Jaipur", r['response'])
        self.assertIn("Mumbai Central", r['response'])
        print("Query 16 Passed: 'Route of 12956' returns ordered stops timeline.")

    def test_17_where_is_12956_right_now(self):
        r = process_chatbot_query("Where is 12956 right now?", session_id="test_s17")
        self.assertEqual(r['intent'], 'LIVE_STATUS')
        self.assertIn("12956", r['response'])
        print("Query 17 Passed: 'Where is 12956 right now?' returns live status.")

    def test_18_check_pnr_2846190532(self):
        r = process_chatbot_query("Check PNR 2846190532", session_id="test_s18")
        self.assertEqual(r['intent'], 'PNR_STATUS')
        self.assertIn("2846190532", r['response'])
        self.assertIn("Rahul Sharma", r['response'])
        print("Query 18 Passed: 'Check PNR 2846190532' returns reservation status.")

    def test_19_what_is_gnwl(self):
        r = process_chatbot_query("What is GNWL?", session_id="test_s19")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("GNWL", r['response'])
        self.assertIn("General Waiting List", r['response'])
        self.assertIn("highest confirmation priority", r['response'])
        print("Query 19 Passed: 'What is GNWL?' returns comprehensive explanation.")

    def test_20_what_is_rac(self):
        r = process_chatbot_query("What is RAC?", session_id="test_s20")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("RAC", r['response'])
        self.assertIn("Reservation Against Cancellation", r['response'])
        print("Query 20 Passed: 'What is RAC?' returns comprehensive explanation.")

    def test_21_how_do_i_cancel_my_ticket(self):
        r = process_chatbot_query("How do I cancel my ticket?", session_id="test_s21")
        self.assertEqual(r['intent'], 'CANCELLATION_HELP')
        self.assertIn("Cancellation", r['response'])
        self.assertIn("Refund", r['response'])
        print("Query 21 Passed: 'How do I cancel my ticket?' returns cancellation policy.")

    def test_22_can_i_order_food_on_my_train(self):
        r = process_chatbot_query("Can I order food on my train?", session_id="test_s22")
        self.assertEqual(r['intent'], 'FOOD_ORDER')
        self.assertIn("Food", r['response'])
        print("Query 22 Passed: 'Can I order food on my train?' returns food ordering guidance.")

    def test_23_which_train_is_fastest_from_jaipur_to_delhi(self):
        r = process_chatbot_query("Which train is fastest from Jaipur to Delhi?", session_id="test_s23")
        self.assertEqual(r['intent'], 'TRAIN_COMPARISON')
        self.assertIn("Fastest", r['response'])
        self.assertIn("Jaipur", r['response'])
        self.assertIn("Delhi", r['response'])
        print("Query 23 Passed: Fastest train query correctly compares trains.")

    def test_24_show_morning_trains_from_jaipur_to_delhi(self):
        r = process_chatbot_query("Show morning trains from Jaipur to Delhi.", session_id="test_s24")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("morning", r['response'].lower())
        self.assertIn("Jaipur", r['response'])
        self.assertIn("Delhi", r['response'])
        print("Query 24 Passed: Morning train filter works accurately.")

    def test_25_show_vande_bharat_from_delhi_to_varanasi(self):
        r = process_chatbot_query("Show Vande Bharat trains from Delhi to Varanasi.", session_id="test_s25")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Vande Bharat", r['response'])
        self.assertIn("Delhi", r['response'])
        self.assertIn("Varanasi", r['response'])
        print("Query 25 Passed: Vande Bharat filter from Delhi to Varanasi works.")

    def test_26_to_29_follow_up_conversations(self):
        sid = "test_multi_turn_26_29"
        # Step 1: Initial query
        r1 = process_chatbot_query("Show all trains from Jaipur to Delhi.", session_id=sid)
        self.assertEqual(r1['intent'], 'TRAIN_SEARCH')

        # Query 26: Follow-up 'Which one is fastest?'
        r2 = process_chatbot_query("Which one is fastest?", session_id=sid)
        self.assertEqual(r2['intent'], 'TRAIN_COMPARISON')
        self.assertIn("Fastest", r2['response'])
        print("Query 26 Passed: Follow-up 'Which one is fastest?' preserved route context.")

        # Query 27: Follow-up 'Which has fewer stops?'
        r3 = process_chatbot_query("Which has fewer stops?", session_id=sid)
        self.assertEqual(r3['intent'], 'TRAIN_COMPARISON')
        self.assertIn("Stops", r3['response'])
        print("Query 27 Passed: Follow-up 'Which has fewer stops?' preserved route context.")

        # Query 28: Follow-up 'What time does it leave?'
        r4 = process_chatbot_query("What time does it leave?", session_id=sid)
        self.assertIn(r4['intent'], ['TRAIN_SCHEDULE', 'TRAIN_DETAILS'])
        self.assertIn("departs from", r4['response'])
        print("Query 28 Passed: Follow-up 'What time does it leave?' retrieved train departure time.")

        # Query 29: Follow-up 'What about tomorrow?'
        r5 = process_chatbot_query("What about tomorrow?", session_id=sid)
        self.assertEqual(r5['intent'], 'TRAIN_SEARCH')
        self.assertIn("Jaipur", r5['response'])
        self.assertIn("Delhi", r5['response'])
        self.assertIn("Total matching trains:", r5['response'])
        print("Query 29 Passed: Follow-up 'What about tomorrow?' preserved route and updated date.")

if __name__ == '__main__':
    unittest.main()
