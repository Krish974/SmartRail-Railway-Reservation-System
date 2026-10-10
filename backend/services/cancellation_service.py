"""
SMART RAILWAY - CANCELLATION & REFUND SERVICE
==============================================
Implementation of official Indian Railways / IRCTC Cancellation and Refund Rules.
Ruleset Version: IRCTC-REFUND-RULES-2026.1
Verified Date: 2026-10-09

Official Regulatory References:
1. Indian Railways (Railway Passengers (Cancellation of Ticket and Refund of Fare) Rules, 2015)
   and subsequent commercial circular amendments (Commercial Circular No. 43 of 2015).
2. IRCTC Official Portal: https://www.irctc.co.in/nget/en-route/refund-rules

Rules Summary Implemented:
---------------------------
1. Confirmed Tickets:
   - > 48 hours before scheduled departure:
     Flat cancellation charges per passenger:
       * 1A / EC / EA : Rs 240
       * 2A / FC      : Rs 200
       * 3A / 3E / CC : Rs 180
       * SL           : Rs 120
       * 2S           : Rs 60
   - Between 48 hours and 12 hours before scheduled departure:
     25% of the fare per passenger, subject to minimum flat clerkage charge for that class.
   - Between 12 hours and 4 hours before scheduled departure (or before chart preparation):
     50% of the fare per passenger, subject to minimum flat clerkage charge for that class.
   - Less than 4 hours before scheduled departure / post chart preparation / after departure:
     No refund admissible (0% refund).

2. RAC / Waitlisted Tickets:
   - Cancelled up to 30 minutes before scheduled departure:
     Flat clerkage charge of Rs 60 per passenger deducted; balance refunded.
   - Cancelled less than 30 minutes before scheduled departure or after departure:
     No refund admissible (0% refund).

3. Tatkal Quota Tickets (TQ):
   - Confirmed Tatkal: 0% refund (No refund admissible under any circumstance).
   - Waitlisted / RAC Tatkal: Standard clerkage of Rs 60 per passenger deducted.

4. Non-refundable Fees:
   - IRCTC / SmartRail Convenience Fee is non-refundable.

5. Partial Cancellation:
   - Supports cancelling a subset of passengers in multi-passenger bookings.
   - Fare and cancellation fees are calculated per passenger.
   - Updates booking and PNR record status to PARTIALLY_CANCELLED or CANCELLED atomically.
"""

import uuid
import json
from datetime import datetime
from backend.utils.db_connection import execute_query

class CancellationService:
    RULE_SET_NAME = "Railway Passengers (Cancellation of Ticket and Refund of Fare) Rules"
    RULE_VERSION = "IRCTC-REFUND-RULES-2026.1"
    VERIFIED_DATE = "2026-10-09"
    SOURCE_URL = "https://www.irctc.co.in/nget/en-route/refund-rules"

    # Flat clerkage charges for confirmed tickets cancelled >48 hrs before departure
    FLAT_CLERKAGE = {
        '1A': 240.0,
        'EC': 240.0,
        'EA': 240.0,
        '2A': 200.0,
        'FC': 200.0,
        '3A': 180.0,
        '3E': 180.0,
        'CC': 180.0,
        'SL': 120.0,
        '2S': 60.0,
        'DEFAULT': 120.0
    }

    RAC_WL_CLERKAGE = 60.0

    @classmethod
    def ensure_table(cls):
        """Creates cancellations audit table if it does not already exist."""
        sql = """
            CREATE TABLE IF NOT EXISTS cancellations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cancellation_reference TEXT NOT NULL UNIQUE,
                booking_id INTEGER NOT NULL,
                pnr TEXT NOT NULL,
                user_id INTEGER,
                cancellation_type TEXT DEFAULT 'FULL',
                cancelled_passengers_count INTEGER NOT NULL,
                cancelled_passenger_ids TEXT NOT NULL,
                cancelled_passenger_names TEXT,
                original_fare REAL NOT NULL,
                cancellation_charge REAL NOT NULL,
                refund_amount REAL NOT NULL,
                refund_status TEXT DEFAULT 'Refund Processed',
                rule_applied TEXT,
                hours_before_departure REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
            )
        """
        try:
            execute_query(sql, commit=True)
        except Exception:
            pass

    @classmethod
    def get_flat_clerkage_rate(cls, coach_class):
        cls_code = str(coach_class or '').strip().upper()
        return cls.FLAT_CLERKAGE.get(cls_code, cls.FLAT_CLERKAGE['DEFAULT'])

    @classmethod
    def parse_departure_datetime(cls, journey_date_val, departure_time_val):
        """
        Robustly parses journey_date and departure_time into a datetime object.
        """
        date_str = str(journey_date_val or '').strip().split()[0] # handles YYYY-MM-DD
        time_str = str(departure_time_val or '00:00').strip()

        # Normalize time_str
        if len(time_str) > 5 and ':' in time_str:
            time_str = time_str[:5] # '16:55:00' -> '16:55'

        for fmt in ('%Y-%m-%d %H:%M', '%d-%m-%Y %H:%M', '%Y/%m/%d %H:%M'):
            try:
                return datetime.strptime(f"{date_str} {time_str}", fmt)
            except ValueError:
                continue

        # Fallback to date only
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return datetime.now()

    @classmethod
    def calculate_hours_before(cls, journey_date_val, departure_time_val, reference_time=None):
        dep_dt = cls.parse_departure_datetime(journey_date_val, departure_time_val)
        ref_dt = reference_time or datetime.now()
        delta = dep_dt - ref_dt
        return delta.total_seconds() / 3600.0

    @classmethod
    def evaluate_passenger(cls, passenger, coach_class, quota_code, passenger_fare, hours_before, chart_prepared=False):
        """
        Evaluates cancellation charge and refund for a single passenger.
        Returns detailed dict with breakdown and applied rule description.
        """
        p_status = str(passenger.get('status') or 'CONFIRMED').upper()
        p_seat = str(passenger.get('seat_number_assigned') or '').upper()
        is_rac_or_wl = ('WL' in p_status or 'WAITLIST' in p_status or 'RAC' in p_status or
                        'WL' in p_seat or 'RAC' in p_seat)
        is_tatkal = str(quota_code or 'GN').upper() in ('TQ', 'CK')
        flat_fee = cls.get_flat_clerkage_rate(coach_class)

        time_bracket = ""
        rule_desc = ""
        charge = 0.0

        if is_tatkal and not is_rac_or_wl:
            # Confirmed Tatkal: 0% refund
            time_bracket = "TATKAL_CONFIRMED"
            charge = passenger_fare
            rule_desc = "Confirmed Tatkal: No refund of fare admissible under official IRCTC rules."
        elif is_rac_or_wl:
            # RAC or Waitlist
            if hours_before >= 0.5:
                # Cancelled up to 30 mins before departure
                time_bracket = "RAC_WL_BEFORE_30MIN"
                charge = min(cls.RAC_WL_CLERKAGE, passenger_fare)
                rule_desc = f"RAC/Waitlisted cancelled up to 30 mins before departure: Flat clerkage of ₹{cls.RAC_WL_CLERKAGE:.2f} deducted."
            else:
                # Less than 30 mins before departure
                time_bracket = "RAC_WL_AFTER_30MIN"
                charge = passenger_fare
                rule_desc = "RAC/Waitlisted cancelled less than 30 mins before departure: No refund admissible."
        else:
            # Confirmed Ticket
            if chart_prepared and hours_before < 12.0:
                time_bracket = "CHART_PREPARED"
                charge = passenger_fare
                rule_desc = "Chart prepared: No refund admissible on confirmed tickets after chart preparation."
            elif hours_before > 48.0:
                time_bracket = "MORE_THAN_48H"
                charge = min(flat_fee, passenger_fare)
                rule_desc = f"> 48 hours before departure: Flat clerkage deduction of ₹{flat_fee:.2f} for class {coach_class}."
            elif 12.0 <= hours_before <= 48.0:
                time_bracket = "BETWEEN_48H_AND_12H"
                calc_charge = max(round(passenger_fare * 0.25, 2), flat_fee)
                charge = min(calc_charge, passenger_fare)
                rule_desc = f"Between 48h and 12h before departure: 25% of fare (minimum ₹{flat_fee:.2f}) deducted."
            elif 4.0 <= hours_before < 12.0:
                time_bracket = "BETWEEN_12H_AND_4H"
                calc_charge = max(round(passenger_fare * 0.50, 2), flat_fee)
                charge = min(calc_charge, passenger_fare)
                rule_desc = f"Between 12h and 4h before departure: 50% of fare (minimum ₹{flat_fee:.2f}) deducted."
            else:
                # Less than 4 hours before departure or already departed
                time_bracket = "LESS_THAN_4H"
                charge = passenger_fare
                rule_desc = "Less than 4 hours before departure / departed: No refund admissible on confirmed tickets."

        charge = round(min(charge, passenger_fare), 2)
        refund = round(max(0.0, passenger_fare - charge), 2)

        return {
            "passenger_id": passenger.get('id'),
            "passenger_name": passenger.get('name'),
            "age": passenger.get('age'),
            "gender": passenger.get('gender'),
            "seat_assigned": passenger.get('seat_number_assigned'),
            "berth_type": passenger.get('berth_type'),
            "booking_status": p_status,
            "passenger_fare": passenger_fare,
            "cancellation_charge": charge,
            "refund_amount": refund,
            "time_bracket": time_bracket,
            "rule_description": rule_desc
        }

    @classmethod
    def calculate_cancellation_quote(cls, booking, passenger_ids=None, reference_time=None):
        """
        Calculates quote/preview for cancelling either selected passengers or the entire booking.
        """
        if not booking:
            return False, "Booking not found."

        if str(booking.get('status')).upper() == 'CANCELLED':
            return False, "This booking has already been cancelled."

        all_passengers = booking.get('passengers', [])
        if not all_passengers:
            return False, "No passenger records found in this booking."

        active_passengers = [p for p in all_passengers if str(p.get('status')).upper() != 'CANCELLED']
        if not active_passengers:
            return False, "All passengers on this ticket have already been cancelled."

        # Filter passengers to cancel
        if passenger_ids is not None:
            # Cast passenger_ids to int/str matching
            p_id_set = {int(pid) for pid in passenger_ids if str(pid).isdigit()}
            selected = [p for p in active_passengers if p['id'] in p_id_set]
            if not selected:
                return False, "Selected passenger(s) not found or already cancelled."
        else:
            selected = active_passengers

        total_passengers_count = len(all_passengers)
        total_fare_paid = float(booking.get('total_fare', 0.0))
        convenience_fee = float(booking.get('convenience_fee', 17.70))
        base_fare = float(booking.get('base_fare', total_fare_paid - convenience_fee))
        tax_amount = float(booking.get('tax_amount', 0.0))

        # Eligible fare to refund from (ticket fare without convenience fee)
        total_eligible_fare = max(0.0, total_fare_paid - convenience_fee)
        
        # Fare per passenger
        per_p_fare = round(total_eligible_fare / total_passengers_count, 2)

        journey_date = booking.get('journey_date')
        departure_time = booking.get('departure_time', '16:55')
        hours_before = cls.calculate_hours_before(journey_date, departure_time, reference_time)

        chart_prepared = bool(booking.get('chart_prepared')) or (str(booking.get('chart_status')).lower() == 'chart prepared')
        coach_class = booking.get('coach_class', '3A')
        quota_code = booking.get('quota_code', 'GN')

        evaluated_passengers = []
        # Calculate for each selected passenger
        for idx, p in enumerate(selected):
            # Ensure rounding does not mismatch total
            p_fare = per_p_fare
            eval_res = cls.evaluate_passenger(
                passenger=p,
                coach_class=coach_class,
                quota_code=quota_code,
                passenger_fare=p_fare,
                hours_before=hours_before,
                chart_prepared=chart_prepared
            )
            evaluated_passengers.append(eval_res)

        total_cancelled_fare = sum(p['passenger_fare'] for p in evaluated_passengers)
        total_cancellation_charge = round(sum(p['cancellation_charge'] for p in evaluated_passengers), 2)
        total_refund_amount = round(sum(p['refund_amount'] for p in evaluated_passengers), 2)

        is_partial = len(selected) < len(active_passengers) or len(selected) < total_passengers_count
        remaining_passengers = [p for p in active_passengers if p['id'] not in {sp['passenger_id'] for sp in evaluated_passengers}]

        # Determine overarching time window label
        if hours_before > 48.0:
            time_label = "> 48 hours before departure"
        elif 12.0 <= hours_before <= 48.0:
            time_label = "Between 48h and 12h before departure"
        elif 4.0 <= hours_before < 12.0:
            time_label = "Between 12h and 4h before departure"
        elif 0.5 <= hours_before < 4.0:
            time_label = "Between 4h and 30m before departure"
        elif hours_before > 0:
            time_label = "< 30 minutes before departure"
        else:
            time_label = "Train already departed"

        quote = {
            "booking_id": booking['id'],
            "pnr": booking['pnr'],
            "booking_reference": booking.get('booking_reference'),
            "train_number": booking.get('train_number'),
            "train_name": booking.get('train_name'),
            "journey_date": str(journey_date),
            "departure_time": departure_time,
            "coach_class": coach_class,
            "quota_code": quota_code,
            "hours_before_departure": round(hours_before, 2),
            "time_window_label": time_label,
            "total_fare_paid": round(total_fare_paid, 2),
            "convenience_fee": round(convenience_fee, 2),
            "total_eligible_fare": round(total_eligible_fare, 2),
            "selected_fare": round(total_cancelled_fare, 2),
            "cancellation_charge": total_cancellation_charge,
            "estimated_refund": total_refund_amount,
            "is_partial": is_partial,
            "passengers_to_cancel": evaluated_passengers,
            "remaining_passengers_count": len(remaining_passengers),
            "rules_metadata": {
                "rule_set": cls.RULE_SET_NAME,
                "version": cls.RULE_VERSION,
                "verified_date": cls.VERIFIED_DATE,
                "official_source": cls.SOURCE_URL,
                "flat_clerkage_class": cls.get_flat_clerkage_rate(coach_class)
            }
        }
        return True, quote

    @classmethod
    def execute_cancellation(cls, booking_id_or_pnr, passenger_ids=None, user_id=None, reference_time=None):
        """
        Executes cancellation transactionally:
        - Validates ownership and eligibility.
        - Computes official refund.
        - Generates unique CAN-2026-XXXX reference.
        - Updates passengers, bookings, and pnr_records tables.
        - Creates audit row in cancellations table.
        """
        from backend.models.booking_model import BookingModel
        cls.ensure_table()

        booking = None
        if str(booking_id_or_pnr).isdigit() and len(str(booking_id_or_pnr)) == 10:
            booking = BookingModel.get_by_pnr(str(booking_id_or_pnr))
        else:
            booking = BookingModel.get_by_id(booking_id_or_pnr)

        if not booking:
            return False, "Booking not found in railway reservation records."

        if str(booking.get('status')).upper() == 'CANCELLED':
            return False, "This booking has already been cancelled."

        # Ownership validation if user_id is provided
        if user_id is not None:
            # Allow admin or booking owner
            b_user_id = booking.get('user_id')
            if b_user_id and int(b_user_id) != int(user_id):
                # Check if user is admin
                admin_check = execute_query("SELECT role FROM users WHERE id = %s", (user_id,), fetchone=True)
                if not admin_check or admin_check.get('role') != 'ADMIN':
                    return False, "Unauthorized: You can only cancel tickets booked under your account."

        ok, quote = cls.calculate_cancellation_quote(booking, passenger_ids=passenger_ids, reference_time=reference_time)
        if not ok:
            return False, quote

        # Generate unique cancellation reference
        can_ref = f"CAN-2026-{uuid.uuid4().hex[:6].upper()}"

        cancelled_p_ids = [p['passenger_id'] for p in quote['passengers_to_cancel']]
        cancelled_p_names = [p['passenger_name'] for p in quote['passengers_to_cancel']]
        is_partial = quote['is_partial']

        # Determine primary rule description for audit log
        primary_rule = quote['passengers_to_cancel'][0]['rule_description'] if quote['passengers_to_cancel'] else "Official IRCTC Refund Rule"

        try:
            # 1. Update cancelled passengers
            for pid in cancelled_p_ids:
                execute_query("UPDATE passengers SET status = 'CANCELLED' WHERE id = %s", (pid,), commit=True)

            # 2. Check if any active passengers remain in the booking
            remaining_check = execute_query(
                "SELECT COUNT(*) as count FROM passengers WHERE booking_id = %s AND status != 'CANCELLED'",
                (booking['id'],), fetchone=True
            )
            active_count = remaining_check.get('count', 0) if remaining_check else 0

            new_status = 'CANCELLED' if active_count == 0 else 'PARTIALLY_CANCELLED'

            # 3. Update bookings status
            execute_query("UPDATE bookings SET status = %s WHERE id = %s", (new_status, booking['id']), commit=True)

            # 4. Update pnr_records status
            execute_query("UPDATE pnr_records SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE booking_id = %s", 
                          (new_status, booking['id']), commit=True)

            # 5. Insert audit row in cancellations
            insert_can_sql = """
                INSERT INTO cancellations (
                    cancellation_reference, booking_id, pnr, user_id, cancellation_type,
                    cancelled_passengers_count, cancelled_passenger_ids, cancelled_passenger_names,
                    original_fare, cancellation_charge, refund_amount, refund_status,
                    rule_applied, hours_before_departure
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Refund Processed', %s, %s)
            """
            execute_query(insert_can_sql, (
                can_ref,
                booking['id'],
                booking['pnr'],
                booking.get('user_id'),
                'PARTIAL' if is_partial else 'FULL',
                len(cancelled_p_ids),
                json.dumps(cancelled_p_ids),
                ', '.join(cancelled_p_names),
                quote['selected_fare'],
                quote['cancellation_charge'],
                quote['estimated_refund'],
                primary_rule,
                quote['hours_before_departure']
            ), commit=True)

            result_data = {
                "cancellation_reference": can_ref,
                "pnr": booking['pnr'],
                "booking_reference": booking.get('booking_reference'),
                "status": new_status,
                "cancellation_type": "PARTIAL" if is_partial else "FULL",
                "cancelled_passengers": cancelled_p_names,
                "cancelled_passenger_details": quote['passengers_to_cancel'],
                "cancelled_passengers_count": len(cancelled_p_ids),
                "remaining_passengers_count": active_count,
                "selected_fare": quote['selected_fare'],
                "cancellation_charge": quote['cancellation_charge'],
                "refund_amount": quote['estimated_refund'],
                "refund_status": "Refund Processed",
                "refund_timeline": "Refund will be credited to source payment method within 3-5 business days.",
                "rule_applied": primary_rule,
                "rules_metadata": quote['rules_metadata'],
                "hours_before_departure": quote['hours_before_departure'],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            return True, result_data
        except Exception as e:
            return False, f"Cancellation failed during database update: {str(e)}"
