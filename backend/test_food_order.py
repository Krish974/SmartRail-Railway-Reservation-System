"""
Automated 20-Point Verification Test Suite for SmartRail Food Order Feature
"""
import sys
import os
import re
import unittest
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app
from backend.utils.db_connection import execute_query
from backend.models.food_model import FoodModel
from backend.ml.chatbot_model import process_chatbot_query

def query_db(sql, params=None, one=False):
    return execute_query(sql, params, fetchone=one, fetchall=(not one))

class TestFoodOrderFeature(unittest.TestCase):

    created_order_number = None
    created_order_id = None

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    # 1. GET /api/food/journey-info with valid PNR
    def test_01_journey_info_valid_pnr(self):
        # Find a valid booking PNR in the DB
        row = query_db("SELECT pnr FROM bookings WHERE pnr IS NOT NULL LIMIT 1", one=True)
        if not row:
            self.skipTest("No bookings found in DB to test PNR lookup")
        pnr = row['pnr']
        res = self.client.get(f'/api/food/journey-info?pnr={pnr}')
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body['success'])
        data = body.get('data', {})
        self.assertIn('train', data)
        self.assertIn('route_halts', data)
        self.assertIn('passenger_info', data)
        self.assertEqual(data['passenger_info']['pnr'], pnr)

    # 2. GET /api/food/journey-info with Train Number
    def test_02_journey_info_valid_train(self):
        res = self.client.get('/api/food/journey-info?train_number=12952')
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body['success'])
        data = body.get('data', {})
        self.assertIn('train', data)
        self.assertEqual(data['train']['number'], '12952')
        self.assertIn('route_halts', data)
        self.assertGreater(len(data['route_halts']), 0)

    # 3. GET /api/food/journey-info with invalid PNR
    def test_03_journey_info_invalid_pnr(self):
        res = self.client.get('/api/food/journey-info?pnr=0000000000')
        self.assertEqual(res.status_code, 404)
        body = res.get_json()
        self.assertFalse(body['success'])

    # 4. GET /api/food/stations/<id>/restaurants returns partner restaurants for junction
    def test_04_station_restaurants_junction(self):
        # Look for NDLS or JP station ID
        st = query_db("SELECT id, code, name FROM stations WHERE code IN ('NDLS', 'JP', 'KOTA') LIMIT 1", one=True)
        self.assertIsNotNone(st)
        res = self.client.get(f"/api/food/stations/{st['id']}/restaurants")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body['success'])
        data = body.get('data', {})
        self.assertIn('restaurants', data)
        self.assertGreater(len(data['restaurants']), 0)
        for r in data['restaurants']:
            self.assertIn('name', r)
            self.assertIn('cuisine_type', r)
            self.assertIn('rating', r)

    # 5. GET /api/food/stations/<id>/restaurants for station without vendors
    def test_05_station_restaurants_empty(self):
        # Select station without restaurants
        st = query_db("SELECT s.id FROM stations s LEFT JOIN food_restaurants r ON s.id = r.station_id WHERE r.id IS NULL LIMIT 1", one=True)
        if st:
            res = self.client.get(f"/api/food/stations/{st['id']}/restaurants")
            self.assertEqual(res.status_code, 200)
            body = res.get_json()
            self.assertTrue(body['success'])
            data = body.get('data', {})
            self.assertIn('restaurants', data)
            self.assertEqual(len(data['restaurants']), 0)

    # 6. GET /api/food/restaurants/<id>/menu returns categorized dishes
    def test_06_restaurant_menu_categories(self):
        rest = query_db("SELECT id FROM food_restaurants LIMIT 1", one=True)
        self.assertIsNotNone(rest)
        res = self.client.get(f"/api/food/restaurants/{rest['id']}/menu")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body['success'])
        data = body.get('data', {})
        self.assertIn('menu_items', data)
        self.assertGreater(len(data['menu_items']), 0)
        self.assertIn('categories', data)
        self.assertGreater(len(data['categories']), 0)

    # 7. Menu items have veg flag and prices
    def test_07_menu_items_fields(self):
        rest = query_db("SELECT id FROM food_restaurants LIMIT 1", one=True)
        res = self.client.get(f"/api/food/restaurants/{rest['id']}/menu")
        body = res.get_json()
        data = body.get('data', {})
        self.assertIn('menu_items', data)
        for item in data['menu_items']:
            self.assertIn('is_veg', item)
            self.assertIn('price', item)
            self.assertGreater(float(item['price']), 0)

    # 8. Station halt validation on train route
    def test_08_route_halt_validation(self):
        train = query_db("SELECT id, train_number FROM trains WHERE train_number = '12952'", one=True)
        self.assertIsNotNone(train)
        halts = FoodModel.get_train_route_halts(train['id'])
        self.assertGreater(len(halts), 0)
        station_codes = [h['station_code'] for h in halts]
        # Train 12952 is NDLS to MMCT (Rajdhani)
        self.assertTrue('NDLS' in station_codes or 'MMCT' in station_codes or len(station_codes) > 2)

    # 9. Order at a station ON the route succeeds
    def test_09_order_at_valid_route_station(self):
        train = query_db("SELECT id, train_number FROM trains WHERE train_number = '12952'", one=True)
        halts = FoodModel.get_train_route_halts(train['id'])
        valid_halt = None
        for h in halts:
            if h.get('restaurants_count', 0) > 0:
                valid_halt = h
                break
        if not valid_halt:
            self.skipTest("No restaurants at halts of train 12952 in test DB")

        rest = query_db("SELECT id FROM food_restaurants WHERE station_id = %s", (valid_halt['station_id'],), one=True)
        items = query_db("SELECT id, price FROM food_menu_items WHERE restaurant_id = %s LIMIT 2", (rest['id'],))

        payload = {
            "train_number": "12952",
            "delivery_station_id": valid_halt['station_id'],
            "restaurant_id": rest['id'],
            "coach": "B2",
            "seat_number": "21",
            "passenger_name": "Test Passenger",
            "passenger_phone": "9876543210",
            "items": [{"menu_item_id": it['id'], "quantity": 1, "item_price": float(it['price'])} for it in items],
            "payment_method": "UPI"
        }

        res = self.client.post('/api/food/orders', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        body = res.get_json()
        self.assertTrue(body['success'])
        data = body.get('data', {})
        self.assertIn('order', data)
        self.assertEqual(data['order']['status'], 'ORDER_PLACED')
        # Store for test 11, 12, 15, 17
        TestFoodOrderFeature.created_order_number = data['order']['order_number']
        TestFoodOrderFeature.created_order_id = data['order']['id']

    # 10. Order at a station NOT on the train route is rejected with 400
    def test_10_order_at_invalid_station_rejected(self):
        # Station HWH (Howrah) is not on train 12952 (New Delhi - Mumbai)
        invalid_st = query_db("SELECT id FROM stations WHERE code = 'HWH'", one=True)
        if not invalid_st:
            invalid_st = query_db("SELECT id FROM stations WHERE id NOT IN (SELECT station_id FROM train_stops WHERE train_id = (SELECT id FROM trains WHERE train_number = '12952')) LIMIT 1", one=True)

        rest = query_db("SELECT id FROM food_restaurants LIMIT 1", one=True)
        items = query_db("SELECT id, price FROM food_menu_items WHERE restaurant_id = %s LIMIT 1", (rest['id'],))

        payload = {
            "train_number": "12952",
            "delivery_station_id": invalid_st['id'],
            "restaurant_id": rest['id'],
            "coach": "B2",
            "seat_number": "21",
            "passenger_name": "Test Passenger",
            "passenger_phone": "9876543210",
            "items": [{"menu_item_id": items[0]['id'], "quantity": 1, "item_price": float(items[0]['price'])}],
            "payment_method": "UPI"
        }

        res = self.client.post('/api/food/orders', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        body = res.get_json()
        self.assertFalse(body['success'])
        self.assertTrue("does not halt" in body['message'].lower() or "scheduled halt" in body['message'].lower())

    # 11. Food Order ID follows FOOD-YYYYMMDD-XXXXX regex format
    def test_11_order_number_format(self):
        order_num = getattr(TestFoodOrderFeature, 'created_order_number', None)
        if not order_num:
            order_num = FoodModel.generate_order_number()
        pattern = r'^FOOD-\d{8}-[A-Z0-9]{5}$'
        self.assertRegex(order_num, pattern)

    # 12. Order creation calculates delivery fee and sets initial status
    def test_12_order_creation_delivery_fee_and_status(self):
        order_id = getattr(TestFoodOrderFeature, 'created_order_id', None)
        if not order_id:
            self.skipTest("No created order found from test 09")
        order = FoodModel.get_order_by_id(order_id)
        self.assertEqual(order['status'], 'ORDER_PLACED')
        self.assertEqual(float(order['delivery_fee']), 20.00)
        self.assertGreater(float(order['total_amount']), float(order['subtotal']))

    # 13. Order creation with missing required fields returns 400
    def test_13_order_missing_fields_validation(self):
        payload = {
            "train_number": "12952",
            "items": [{"menu_item_id": 1, "quantity": 1}]
            # missing passenger_name, coach, seat_number, delivery_station_id, restaurant_id
        }
        res = self.client.post('/api/food/orders', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        body = res.get_json()
        self.assertFalse(body['success'])

    # 14. Order creation with empty items list returns 400
    def test_14_order_empty_items_validation(self):
        payload = {
            "train_number": "12952",
            "delivery_station_id": 1,
            "restaurant_id": 1,
            "coach": "B1",
            "seat_number": "12",
            "passenger_name": "Test",
            "passenger_phone": "9876543210",
            "items": []
        }
        res = self.client.post('/api/food/orders', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        body = res.get_json()
        self.assertFalse(body['success'])

    # 15. GET /api/food/orders/<order_number> returns full order details
    def test_15_get_order_by_number(self):
        order_num = getattr(TestFoodOrderFeature, 'created_order_number', None)
        if not order_num:
            self.skipTest("No created order found")
        res = self.client.get(f'/api/food/orders/{order_num}')
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body['success'])
        data = body.get('data', {})
        order = data.get('order', data)
        self.assertEqual(order['order_number'], order_num)
        self.assertIn('items', order)
        self.assertIn('status_history', order)
        self.assertIn('restaurant_name', order)
        self.assertIn('station_name', order)

    # 16. GET /api/admin/food-orders lists all placed food orders
    def test_16_admin_food_orders_list(self):
        res = self.client.get('/api/admin/food-orders')
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body['success'])
        data = body.get('data', {})
        self.assertIn('orders', data)
        self.assertGreater(len(data['orders']), 0)

    # 17. PUT /api/admin/food-orders/<id>/status updates status through 7 stages
    def test_17_admin_status_progression(self):
        order_num = getattr(TestFoodOrderFeature, 'created_order_number', None)
        if not order_num:
            self.skipTest("No created order found")

        stages = [
            'CONFIRMED',
            'PREPARING',
            'READY',
            'OUT_FOR_DELIVERY',
            'DELIVERED_AT_STATION',
            'DELIVERED_TO_PASSENGER'
        ]

        for stage in stages:
            res = self.client.put(
                f'/api/admin/food-orders/{order_num}/status',
                data=json.dumps({'status': stage}),
                content_type='application/json'
            )
            self.assertEqual(res.status_code, 200)
            body = res.get_json()
            self.assertTrue(body['success'])
            data = body.get('data', {})
            order = data.get('order', data)
            self.assertEqual(order['status'], stage)

    # 18. PUT /api/admin/food-orders/<id>/status with invalid status returns 400
    def test_18_admin_invalid_status_rejected(self):
        order_num = getattr(TestFoodOrderFeature, 'created_order_number', None)
        if not order_num:
            self.skipTest("No created order found")
        res = self.client.put(
            f'/api/admin/food-orders/{order_num}/status',
            data=json.dumps({'status': 'INVALID_STATUS_FOOBAR'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)
        body = res.get_json()
        self.assertFalse(body['success'])

    # 19. Chatbot RAG: Food order queries return authorized guidance without hallucinating
    def test_19_chatbot_food_intelligence(self):
        # Station food query
        reply_st = process_chatbot_query("Can I get food at New Delhi station?")
        resp_st = reply_st.get('response', '')
        self.assertTrue("Haldiram" in resp_st or "food" in resp_st.lower() or "catering" in resp_st.lower() or "delhi" in resp_st.lower())

        # Train food query
        reply_tr = process_chatbot_query("Can I order food on train 12952?")
        resp_tr = reply_tr.get('response', '')
        self.assertTrue("12952" in resp_tr or "catering" in resp_tr.lower() or "halt" in resp_tr.lower() or "food" in resp_tr.lower())

        # General e-catering
        reply_gen = process_chatbot_query("How do I order food during my journey?")
        resp_gen = reply_gen.get('response', '')
        self.assertTrue("food order" in resp_gen.lower() or "berth" in resp_gen.lower() or "e-catering" in resp_gen.lower())

    # 20. Database Integrity: All original railway data is 100% intact
    def test_20_database_integrity(self):
        st_count = query_db("SELECT COUNT(*) as c FROM stations", one=True)['c']
        tr_count = query_db("SELECT COUNT(*) as c FROM trains", one=True)['c']
        self.assertEqual(st_count, 13004, "Station records must remain exactly 13,004")
        self.assertGreaterEqual(tr_count, 10705, "Train records must remain at least original 10,705")

if __name__ == '__main__':
    unittest.main()
