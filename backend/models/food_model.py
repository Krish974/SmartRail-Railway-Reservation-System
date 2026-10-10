import random
import string
import datetime
from backend.utils.db_connection import execute_query

class FoodModel:
    CANONICAL_STAGES = [
        'ORDER_PLACED',
        'CONFIRMED',
        'PREPARING',
        'READY',
        'OUT_FOR_DELIVERY',
        'DELIVERED_AT_STATION',
        'DELIVERED_TO_PASSENGER',
        'CANCELLED'
    ]

    STATUS_MAP = {
        'PLACED': 'ORDER_PLACED',
        'ORDER_PLACED': 'ORDER_PLACED',
        'CONFIRMED': 'CONFIRMED',
        'PREPARING': 'PREPARING',
        'READY': 'READY',
        'OUT_FOR_DELIVERY': 'OUT_FOR_DELIVERY',
        'DELIVERED_AT_STATION': 'DELIVERED_AT_STATION',
        'DELIVERED_TO_PASSENGER': 'DELIVERED_TO_PASSENGER',
        'DELIVERED': 'DELIVERED_TO_PASSENGER',
        'CANCELLED': 'CANCELLED'
    }

    VALID_STATUSES = CANONICAL_STAGES + [
        'Placed',
        'Confirmed',
        'Preparing',
        'Ready',
        'Out for Delivery',
        'Delivered at Station',
        'Delivered to Passenger',
        'Delivered',
        'Cancelled'
    ]

    @staticmethod
    def generate_order_number() -> str:
        """
        Generates a unique Food Order ID: FOOD-YYYYMMDD-XXXXX
        Matching specification: Example FOOD-20261001-12345
        """
        date_str = datetime.date.today().strftime('%Y%m%d')
        rand_num = random.randint(10000, 99999)
        return f"FOOD-{date_str}-{rand_num}"

    @staticmethod
    def get_train_route_halts(train_id):
        """
        Retrieves scheduled route halts for a train, including delivery station restaurant availability.
        """
        sql = """
            SELECT ts.stop_sequence, ts.station_id, s.code as station_code, s.name as station_name,
                   ts.arrival_time, ts.departure_time, ts.halt_minutes, ts.distance_km,
                   (SELECT COUNT(*) FROM food_restaurants fr WHERE fr.station_id = ts.station_id AND fr.active = 1) as restaurants_count
            FROM train_stops ts
            JOIN stations s ON ts.station_id = s.id
            WHERE ts.train_id = %s
            ORDER BY ts.stop_sequence ASC
        """
        return execute_query(sql, (train_id,), fetchall=True)

    @staticmethod
    def get_restaurants_for_station(station_id_or_code):
        """
        Retrieves active restaurants available for delivery at a specific station.
        """
        if isinstance(station_id_or_code, str) and not station_id_or_code.isdigit():
            sql = """
                SELECT r.*, r.cuisine as cuisine_type, s.code as station_code, s.name as station_name, s.city as station_city
                FROM food_restaurants r
                JOIN stations s ON r.station_id = s.id
                WHERE (s.code = %s OR UPPER(s.code) = UPPER(%s)) AND r.active = 1
                ORDER BY r.rating DESC
            """
            return execute_query(sql, (station_id_or_code, station_id_or_code), fetchall=True)
        else:
            sql = """
                SELECT r.*, r.cuisine as cuisine_type, s.code as station_code, s.name as station_name, s.city as station_city
                FROM food_restaurants r
                JOIN stations s ON r.station_id = s.id
                WHERE r.station_id = %s AND r.active = 1
                ORDER BY r.rating DESC
            """
            return execute_query(sql, (int(station_id_or_code),), fetchall=True)

    @staticmethod
    def get_restaurant_by_id(restaurant_id):
        """
        Retrieves a single restaurant by ID with its station details.
        """
        sql = """
            SELECT r.*, s.code as station_code, s.name as station_name, s.city as station_city
            FROM food_restaurants r
            JOIN stations s ON r.station_id = s.id
            WHERE r.id = %s AND r.active = 1
        """
        return execute_query(sql, (restaurant_id,), fetchone=True)

    @staticmethod
    def get_menu_for_restaurant(restaurant_id, category=None, veg_only=False):
        """
        Retrieves categorized menu items for a restaurant.
        """
        params = [restaurant_id]
        sql = """
            SELECT * FROM food_menu_items
            WHERE restaurant_id = %s AND active = 1 AND available = 1
        """
        if category and category.lower() != 'all':
            sql += " AND LOWER(category) = LOWER(%s)"
            params.append(category)
        if veg_only:
            sql += " AND is_veg = 1"
        
        sql += " ORDER BY category ASC, price ASC"
        return execute_query(sql, tuple(params), fetchall=True)

    @staticmethod
    def create_order(order_data, items_data, user_id=None):
        """
        Creates a new food order with items and initial 'Placed' history log.
        """
        order_number = FoodModel.generate_order_number()
        
        subtotal = float(order_data.get('subtotal', 0.0))
        delivery_fee = float(order_data.get('delivery_fee', 20.0))
        total_amount = float(order_data.get('total_amount', subtotal + delivery_fee))

        insert_order_sql = """
            INSERT INTO food_orders (
                order_number, user_id, passenger_name, contact_phone, pnr,
                train_id, train_number, delivery_station_id, delivery_station_name,
                coach, seat, delivery_eta, subtotal, delivery_fee, total_amount,
                payment_method, payment_status, order_status, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ORDER_PLACED', %s)
        """
        order_id = execute_query(insert_order_sql, (
            order_number,
            user_id,
            order_data['passenger_name'],
            order_data['contact_phone'],
            order_data.get('pnr'),
            order_data.get('train_id'),
            order_data['train_number'],
            order_data['delivery_station_id'],
            order_data.get('delivery_station_name', ''),
            order_data['coach'],
            order_data['seat'],
            order_data.get('delivery_eta', 'On Arrival'),
            subtotal,
            delivery_fee,
            total_amount,
            order_data.get('payment_method', 'UPI'),
            order_data.get('payment_status', 'PAID'),
            order_data.get('notes', '')
        ), commit=True)

        # Insert items
        for itm in items_data:
            execute_query("""
                INSERT INTO food_order_items (
                    order_id, menu_item_id, item_name, quantity, unit_price, total_price
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                order_id,
                itm.get('menu_item_id'),
                itm['item_name'],
                int(itm['quantity']),
                float(itm['unit_price']),
                float(itm['total_price'])
            ), commit=True)

        # Insert initial status history
        execute_query("""
            INSERT INTO food_order_status_history (order_id, status, note)
            VALUES (%s, 'ORDER_PLACED', 'Order successfully placed by passenger.')
        """, (order_id,), commit=True)

        return FoodModel.get_order_by_number(order_number)

    @staticmethod
    def get_order_by_number(order_number):
        """
        Retrieves a full order by order_number (or id), including delivery station, items, and timeline.
        """
        sql = """
            SELECT fo.*, s.code as station_code, s.name as station_name, s.city as station_city
            FROM food_orders fo
            JOIN stations s ON fo.delivery_station_id = s.id
            WHERE fo.order_number = %s OR fo.id = %s
        """
        order = execute_query(sql, (order_number, order_number), fetchone=True)
        if not order:
            return None

        order['status'] = order.get('order_status')

        # Fetch items
        items_sql = """
            SELECT foi.*, fmi.category, fmi.is_veg, fmi.image_url, r.name as restaurant_name
            FROM food_order_items foi
            LEFT JOIN food_menu_items fmi ON foi.menu_item_id = fmi.id
            LEFT JOIN food_restaurants r ON fmi.restaurant_id = r.id
            WHERE foi.order_id = %s
            ORDER BY foi.id ASC
        """
        order['items'] = execute_query(items_sql, (order['id'],), fetchall=True)

        # Determine restaurant name from first item or header
        if order['items'] and order['items'][0].get('restaurant_name'):
            order['restaurant_name'] = order['items'][0]['restaurant_name']
        else:
            order['restaurant_name'] = "IRCTC Partner Vendor"

        # Fetch status history
        hist_sql = """
            SELECT * FROM food_order_status_history
            WHERE order_id = %s
            ORDER BY id ASC
        """
        order['status_history'] = execute_query(hist_sql, (order['id'],), fetchall=True)

        return order

    @staticmethod
    def get_order_by_id(order_id):
        """
        Alias to retrieve order by integer ID.
        """
        return FoodModel.get_order_by_number(order_id)

    @staticmethod
    def get_all_orders(limit=100, user_id=None, status=None):
        """
        Retrieves orders for admin dashboard or passenger order history.
        """
        params = []
        sql = """
            SELECT fo.*, s.code as station_code, s.name as station_name, s.city as station_city,
                   (SELECT COUNT(*) FROM food_order_items WHERE order_id = fo.id) as item_count,
                   (SELECT GROUP_CONCAT(item_name || ' x ' || quantity, ', ') FROM food_order_items WHERE order_id = fo.id) as items_summary
            FROM food_orders fo
            JOIN stations s ON fo.delivery_station_id = s.id
            WHERE 1=1
        """
        if user_id:
            sql += " AND fo.user_id = %s"
            params.append(user_id)
        if status:
            norm_status = FoodModel.STATUS_MAP.get(status.upper().replace(' ', '_'), status)
            sql += " AND (fo.order_status = %s OR fo.order_status = %s)"
            params.extend([status, norm_status])

        sql += " ORDER BY fo.id DESC LIMIT %s"
        params.append(limit)

        orders = execute_query(sql, tuple(params), fetchall=True)
        for o in orders:
            o['status'] = o.get('order_status')
            # Attach items
            items = execute_query("SELECT item_name, quantity, total_price FROM food_order_items WHERE order_id = %s", (o['id'],), fetchall=True)
            o['items'] = items
        return orders

    @staticmethod
    def update_order_status(order_id_or_number, new_status, note=None):
        """
        Updates the status of a food order and records a timeline history event.
        """
        normalized_status = FoodModel.STATUS_MAP.get(new_status.upper().replace(' ', '_'), new_status)
        if normalized_status not in FoodModel.VALID_STATUSES and new_status not in FoodModel.VALID_STATUSES:
            raise ValueError(f"Invalid status: '{new_status}'. Allowed: {', '.join(FoodModel.VALID_STATUSES)}")

        target_status = normalized_status if normalized_status in FoodModel.CANONICAL_STAGES else new_status

        # Find order
        sql = "SELECT id, order_number, order_status FROM food_orders WHERE order_number = %s OR id = %s"
        order = execute_query(sql, (order_id_or_number, order_id_or_number), fetchone=True)
        if not order:
            return None

        update_sql = "UPDATE food_orders SET order_status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        execute_query(update_sql, (target_status, order['id']), commit=True)

        default_notes = {
            'ORDER_PLACED': 'Order placed by passenger and transmitted to restaurant.',
            'CONFIRMED': 'Restaurant accepted order and verified train halt window.',
            'PREPARING': 'Chef is preparing fresh meal in hygienic kitchen.',
            'READY': 'Food packed in tamper-proof thermal packaging.',
            'OUT_FOR_DELIVERY': 'Delivery executive dispatched to station platform.',
            'DELIVERED_AT_STATION': 'Train arrived and delivery agent boarded coach.',
            'DELIVERED_TO_PASSENGER': 'Meal delivered to passenger at berth/seat.',
            'DELIVERED': 'Meal delivered to passenger at berth/seat.',
            'CANCELLED': 'Order cancelled.'
        }
        note_text = note or default_notes.get(target_status, f"Status updated to {target_status}")

        execute_query("""
            INSERT INTO food_order_status_history (order_id, status, note)
            VALUES (%s, %s, %s)
        """, (order['id'], target_status, note_text), commit=True)

        return FoodModel.get_order_by_number(order['order_number'])
