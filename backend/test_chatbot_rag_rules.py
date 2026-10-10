import sys
import unittest

sys.path.insert(0, '.')
from backend.app import create_app
from backend.ml.chatbot_model import process_chatbot_query

class TestChatbotRAGRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_rac23_brother_side_upper_daytime(self):
        """Motivating prompt query: RAC23 + brother + side upper sitting on lower berth during day"""
        q = "If my seat is RAC23 with my brother who has also RAC23 so side upper seat passenger can seat on my lower berth on the day time?"
        r = process_chatbot_query(q, session_id="rag_test_1")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertNotIn("I didn't quite catch that", r['response'])
        self.assertIn("Side Upper", r['response'])
        self.assertIn("Side Lower", r['response'])
        self.assertIn("6:00 AM", r['response'])
        self.assertIn("10:00 PM", r['response'])
        self.assertIn("brother", r['response'].lower())
        print("Query 1 Passed: RAC 23 + brother + side upper daytime answered accurately.")

    def test_02_can_side_upper_sit_on_lower_berth_daytime(self):
        q = "can side upper passenger sit on lower berth during day?"
        r = process_chatbot_query(q, session_id="rag_test_2")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertIn("Side Upper", r['response'])
        self.assertIn("Side Lower", r['response'])
        self.assertTrue("6:00 AM" in r['response'] or "06:00 AM" in r['response'])
        print("Query 2 Passed: Side upper passenger sitting on lower berth during day verified.")

    def test_03_can_two_rac_passengers_share_one_berth(self):
        q = "can two RAC passengers share one berth?"
        r = process_chatbot_query(q, session_id="rag_test_3")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertIn("Side Lower", r['response'])
        self.assertIn("share", r['response'].lower())
        print("Query 3 Passed: Two RAC passengers sharing berth verified.")

    def test_04_hinglish_brother_rac_berth_share(self):
        q = "brother bhi RAC hai to kya dono same berth share karenge?"
        r = process_chatbot_query(q, session_id="rag_test_4")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertNotIn("I didn't quite catch that", r['response'])
        self.assertIn("Side Lower", r['response'])
        print("Query 4 Passed: Hinglish brother RAC berth sharing verified.")

    def test_05_what_does_rac_23_mean(self):
        q = "what does RAC 23 mean?"
        r = process_chatbot_query(q, session_id="rag_test_5")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertIn("RAC", r['response'])
        self.assertIn("23", r['response'])
        self.assertIn("sitting seat", r['response'].lower())
        print("Query 5 Passed: What does RAC 23 mean verified.")

    def test_06_hinglish_rac_23_matlab(self):
        q = "rac 23 ka kya matlab hai?"
        r = process_chatbot_query(q, session_id="rag_test_6")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertNotIn("I didn't quite catch that", r['response'])
        self.assertIn("RAC", r['response'])
        print("Query 6 Passed: Hinglish RAC 23 ka kya matlab hai verified.")

    def test_07_can_rac_passengers_travel(self):
        q = "can RAC passengers travel?"
        r = process_chatbot_query(q, session_id="rag_test_7")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertIn("board the train", r['response'].lower())
        print("Query 7 Passed: Can RAC passengers travel verified.")

    def test_08_hinglish_kya_rac_me_travel_ho_sakta_hai(self):
        q = "kya RAC me travel ho sakta hai?"
        r = process_chatbot_query(q, session_id="rag_test_8")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertNotIn("I didn't quite catch that", r['response'])
        self.assertIn("Yes", r['response'])
        print("Query 8 Passed: Hinglish kya RAC me travel ho sakta hai verified.")

    def test_09_what_is_rac(self):
        q = "what is RAC?"
        r = process_chatbot_query(q, session_id="rag_test_9")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("Reservation Against Cancellation", r['response'])
        print("Query 9 Passed: What is RAC verified.")

    def test_10_can_i_sleep_on_lower_berth_during_daytime(self):
        q = "can I sleep on lower berth during daytime?"
        r = process_chatbot_query(q, session_id="rag_test_10")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertIn("10:00 PM", r['response'])
        self.assertIn("06:00 AM", r['response'])
        print("Query 10 Passed: Lower berth daytime sleeping rules verified.")

    def test_11_middle_berth_rules(self):
        q = "middle berth rules"
        r = process_chatbot_query(q, session_id="rag_test_11")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertIn("10:00 PM", r['response'])
        self.assertIn("middle berth", r['response'].lower())
        print("Query 11 Passed: Middle berth timing rules verified.")

    def test_12_can_i_change_my_berth(self):
        q = "can I change my berth?"
        r = process_chatbot_query(q, session_id="rag_test_12")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertIn("TTE", r['response'])
        print("Query 12 Passed: Berth change / TTE authority rules verified.")

    def test_13_what_is_gnwl(self):
        q = "what is GNWL?"
        r = process_chatbot_query(q, session_id="rag_test_13")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("General Waiting List", r['response'])
        print("Query 13 Passed: What is GNWL verified.")

    def test_14_what_is_rlwl(self):
        q = "what is RLWL?"
        r = process_chatbot_query(q, session_id="rag_test_14")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("Remote Location Waiting List", r['response'])
        print("Query 14 Passed: What is RLWL verified.")

    def test_15_what_is_pqwl(self):
        q = "what is PQWL?"
        r = process_chatbot_query(q, session_id="rag_test_15")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("Pooled Quota Waiting List", r['response'])
        print("Query 15 Passed: What is PQWL verified.")

    def test_16_what_is_tqwl(self):
        q = "what is TQWL?"
        r = process_chatbot_query(q, session_id="rag_test_16")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("Tatkal Waiting List", r['response'])
        print("Query 16 Passed: What is TQWL verified.")

    def test_17_can_waitlist_passengers_travel(self):
        q = "can waitlist passengers travel?"
        r = process_chatbot_query(q, session_id="rag_test_17")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertIn("cancelled", r['response'].lower())
        print("Query 17 Passed: Can waitlist passengers travel verified.")

    def test_18_what_happens_if_wl_is_not_confirmed(self):
        q = "what happens if WL is not confirmed?"
        r = process_chatbot_query(q, session_id="rag_test_18")
        self.assertNotEqual(r['intent'], 'UNKNOWN')
        self.assertIn("refund", r['response'].lower())
        print("Query 18 Passed: What happens if WL is not confirmed verified.")

    def test_19_difference_between_rac_and_wl(self):
        q = "what is the difference between RAC and WL?"
        r = process_chatbot_query(q, session_id="rag_test_19")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("RAC", r['response'])
        self.assertIn("WL", r['response'])
        print("Query 19 Passed: Difference between RAC and WL verified.")

    def test_20_how_does_tatkal_work(self):
        q = "how does Tatkal work?"
        r = process_chatbot_query(q, session_id="rag_test_20")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("Tatkal", r['response'])
        self.assertIn("10:00 AM", r['response'])
        self.assertIn("11:00 AM", r['response'])
        print("Query 20 Passed: How does Tatkal work verified.")

    def test_21_what_is_premium_tatkal(self):
        q = "what is Premium Tatkal?"
        r = process_chatbot_query(q, session_id="rag_test_21")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("Premium Tatkal", r['response'])
        self.assertIn("dynamic", r['response'].lower())
        print("Query 21 Passed: What is Premium Tatkal verified.")

    def test_22_when_does_tatkal_booking_open(self):
        q = "when does Tatkal booking open?"
        r = process_chatbot_query(q, session_id="rag_test_22")
        self.assertEqual(r['intent'], 'RAILWAY_KNOWLEDGE')
        self.assertIn("10:00 AM", r['response'])
        self.assertIn("11:00 AM", r['response'])
        print("Query 22 Passed: When does Tatkal booking open verified.")

    def test_23_how_can_i_cancel_my_ticket(self):
        q = "how can I cancel my ticket?"
        r = process_chatbot_query(q, session_id="rag_test_23")
        self.assertEqual(r['intent'], 'CANCELLATION_HELP')
        self.assertIn("Cancellation", r['response'])
        print("Query 23 Passed: How can I cancel my ticket verified.")

    def test_24_what_are_the_cancellation_charges(self):
        q = "what are the cancellation charges?"
        r = process_chatbot_query(q, session_id="rag_test_24")
        self.assertEqual(r['intent'], 'CANCELLATION_HELP')
        self.assertIn("clerkage", r['response'].lower())
        print("Query 24 Passed: What are the cancellation charges verified.")

    def test_25_hinglish_route_search(self):
        q = "Jaipur se Delhi ki train"
        r = process_chatbot_query(q, session_id="rag_test_25")
        self.assertEqual(r['intent'], 'TRAIN_SEARCH')
        self.assertIn("Jaipur", r['response'])
        self.assertIn("Delhi", r['response'])
        print("Query 25 Passed: Hinglish 'Jaipur se Delhi ki train' verified.")

    def test_26_hinglish_live_tracking(self):
        q = "12956 abhi kaha hai"
        r = process_chatbot_query(q, session_id="rag_test_26")
        self.assertEqual(r['intent'], 'LIVE_STATUS')
        self.assertIn("12956", r['response'])
        print("Query 26 Passed: Hinglish '12956 abhi kaha hai' verified.")

if __name__ == '__main__':
    unittest.main()
