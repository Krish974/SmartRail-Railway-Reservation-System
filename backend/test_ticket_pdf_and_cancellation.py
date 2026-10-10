"""
UNIT & INTEGRATION TESTS: OFFICIAL IRCTC CANCELLATION RULES & WORKFLOW
======================================================================
Tests verify strict compliance with Indian Railways / IRCTC Cancellation & Refund Rules:
- Rule Set: Railway Passengers (Cancellation of Ticket and Refund of Fare) Rules
- Version: IRCTC-REFUND-RULES-2026.1
- Verified Date: 2026-10-09
"""

import pytest
import json
from datetime import datetime, timedelta
from backend.app import create_app
from backend.services.cancellation_service import CancellationService
from backend.models.booking_model import BookingModel
from backend.utils.db_connection import execute_query

@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture(scope="module")
def client(app):
    return app.test_client()

class TestIRCTCCancellationRules:
    def test_01_flat_clerkage_rates_by_class(self):
        """Rule 1: Flat clerkage rates for >48h cancellation match official IRCTC gazette."""
        assert CancellationService.get_flat_clerkage_rate('1A') == 240.0
        assert CancellationService.get_flat_clerkage_rate('EC') == 240.0
        assert CancellationService.get_flat_clerkage_rate('EA') == 240.0
        assert CancellationService.get_flat_clerkage_rate('2A') == 200.0
        assert CancellationService.get_flat_clerkage_rate('FC') == 200.0
        assert CancellationService.get_flat_clerkage_rate('3A') == 180.0
        assert CancellationService.get_flat_clerkage_rate('3E') == 180.0
        assert CancellationService.get_flat_clerkage_rate('CC') == 180.0
        assert CancellationService.get_flat_clerkage_rate('SL') == 120.0
        assert CancellationService.get_flat_clerkage_rate('2S') == 60.0
        assert CancellationService.get_flat_clerkage_rate('UNKNOWN') == 120.0

    def test_02_confirmed_more_than_48h(self):
        """Rule 2: Confirmed ticket >48h before departure deducts only flat clerkage."""
        passenger = {'id': 101, 'name': 'Passenger 1', 'status': 'CONFIRMED', 'seat_number_assigned': 'B1-12'}
        # 3A fare of Rs 1500, cancelled 72 hours in advance
        res = CancellationService.evaluate_passenger(
            passenger=passenger,
            coach_class='3A',
            quota_code='GN',
            passenger_fare=1500.0,
            hours_before=72.0
        )
        assert res['cancellation_charge'] == 180.0
        assert res['refund_amount'] == 1320.0
        assert res['time_bracket'] == 'MORE_THAN_48H'

    def test_03_confirmed_between_48h_and_12h(self):
        """Rule 3: Confirmed ticket between 48h and 12h deducts 25% subject to min clerkage."""
        passenger = {'id': 102, 'name': 'Passenger 2', 'status': 'CONFIRMED', 'seat_number_assigned': 'B1-14'}
        # 3A fare of Rs 1600: 25% of 1600 is 400 (> 180), so 400 is deducted
        res = CancellationService.evaluate_passenger(
            passenger=passenger,
            coach_class='3A',
            quota_code='GN',
            passenger_fare=1600.0,
            hours_before=24.0
        )
        assert res['cancellation_charge'] == 400.0
        assert res['refund_amount'] == 1200.0
        assert res['time_bracket'] == 'BETWEEN_48H_AND_12H'

        # Low fare case where 25% is less than flat clerkage (e.g. fare 400 in 3A -> 25% is 100 < 180)
        res_min = CancellationService.evaluate_passenger(
            passenger=passenger,
            coach_class='3A',
            quota_code='GN',
            passenger_fare=400.0,
            hours_before=24.0
        )
        assert res_min['cancellation_charge'] == 180.0
        assert res_min['refund_amount'] == 220.0

    def test_04_confirmed_between_12h_and_4h(self):
        """Rule 4: Confirmed ticket between 12h and 4h deducts 50% subject to min clerkage."""
        passenger = {'id': 103, 'name': 'Passenger 3', 'status': 'CONFIRMED', 'seat_number_assigned': 'S1-42'}
        # SL fare of Rs 600: 50% of 600 is 300 (> 120), so 300 is deducted
        res = CancellationService.evaluate_passenger(
            passenger=passenger,
            coach_class='SL',
            quota_code='GN',
            passenger_fare=600.0,
            hours_before=8.0
        )
        assert res['cancellation_charge'] == 300.0
        assert res['refund_amount'] == 300.0
        assert res['time_bracket'] == 'BETWEEN_12H_AND_4H'

    def test_05_confirmed_less_than_4h_or_chart_prepared(self):
        """Rule 5: Confirmed ticket cancelled <4h before departure gets 0% refund."""
        passenger = {'id': 104, 'name': 'Passenger 4', 'status': 'CONFIRMED', 'seat_number_assigned': 'A1-21'}
        res = CancellationService.evaluate_passenger(
            passenger=passenger,
            coach_class='2A',
            quota_code='GN',
            passenger_fare=2200.0,
            hours_before=2.5
        )
        assert res['cancellation_charge'] == 2200.0
        assert res['refund_amount'] == 0.0
        assert res['time_bracket'] == 'LESS_THAN_4H'

        # Chart prepared before 12h
        res_chart = CancellationService.evaluate_passenger(
            passenger=passenger,
            coach_class='2A',
            quota_code='GN',
            passenger_fare=2200.0,
            hours_before=6.0,
            chart_prepared=True
        )
        assert res_chart['cancellation_charge'] == 2200.0
        assert res_chart['refund_amount'] == 0.0
        assert res_chart['time_bracket'] == 'CHART_PREPARED'

    def test_06_rac_and_waitlist_rules(self):
        """Rule 6: RAC/WL cancelled >=30m before departure deducts Rs 60 clerkage; <30m gets 0%."""
        rac_passenger = {'id': 105, 'name': 'RAC Passenger', 'status': 'RAC', 'seat_number_assigned': 'B1-RAC-4'}
        res_rac = CancellationService.evaluate_passenger(
            passenger=rac_passenger,
            coach_class='3A',
            quota_code='GN',
            passenger_fare=1200.0,
            hours_before=1.5
        )
        assert res_rac['cancellation_charge'] == 60.0
        assert res_rac['refund_amount'] == 1140.0
        assert res_rac['time_bracket'] == 'RAC_WL_BEFORE_30MIN'

        # Less than 30 mins before departure
        res_rac_late = CancellationService.evaluate_passenger(
            passenger=rac_passenger,
            coach_class='3A',
            quota_code='GN',
            passenger_fare=1200.0,
            hours_before=0.25 # 15 minutes
        )
        assert res_rac_late['cancellation_charge'] == 1200.0
        assert res_rac_late['refund_amount'] == 0.0
        assert res_rac_late['time_bracket'] == 'RAC_WL_AFTER_30MIN'

    def test_07_tatkal_quota_rules(self):
        """Rule 7: Confirmed Tatkal gets 0% refund; Waitlisted Tatkal deducts clerkage."""
        tatkal_cnf = {'id': 106, 'name': 'Tatkal Confirmed', 'status': 'CONFIRMED', 'seat_number_assigned': 'B1-5'}
        res_cnf = CancellationService.evaluate_passenger(
            passenger=tatkal_cnf,
            coach_class='3A',
            quota_code='TQ',
            passenger_fare=1800.0,
            hours_before=72.0
        )
        assert res_cnf['cancellation_charge'] == 1800.0
        assert res_cnf['refund_amount'] == 0.0
        assert res_cnf['time_bracket'] == 'TATKAL_CONFIRMED'

        tatkal_wl = {'id': 107, 'name': 'Tatkal WL', 'status': 'WAITLIST', 'seat_number_assigned': 'WL-5'}
        res_wl = CancellationService.evaluate_passenger(
            passenger=tatkal_wl,
            coach_class='3A',
            quota_code='TQ',
            passenger_fare=1800.0,
            hours_before=5.0
        )
        assert res_wl['cancellation_charge'] == 60.0
        assert res_wl['refund_amount'] == 1740.0

class TestCancellationWorkflowAndApi:
    def test_08_partial_cancellation_flow(self, client):
        """Test partial cancellation: cancelling 1 of 2 passengers updates booking to PARTIALLY_CANCELLED."""
        # Create a fresh 2-passenger booking
        dep_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        book_resp = client.post('/api/bookings', json={
            'train_id': 1,
            'coach_id': 1,
            'journey_date': dep_date,
            'quota_code': 'GN',
            'passengers': [
                {'name': 'Alpha Passenger', 'age': 30, 'gender': 'Male', 'id_type': 'Aadhaar', 'id_number': '111122223333'},
                {'name': 'Beta Passenger', 'age': 28, 'gender': 'Female', 'id_type': 'PAN', 'id_number': 'ABCDE1234F'}
            ]
        })
        assert book_resp.status_code == 201
        booking = book_resp.get_json()['data']
        b_id = booking['id']
        p_ids = [p['id'] for p in booking['passengers']]
        assert len(p_ids) == 2

        # 1. Preview refund quote for only the first passenger
        quote_resp = client.post(f'/api/bookings/{b_id}/refund-quote', json={'passenger_ids': [p_ids[0]]})
        assert quote_resp.status_code == 200
        q_data = quote_resp.get_json()['data']
        assert q_data['is_partial'] is True
        assert len(q_data['passengers_to_cancel']) == 1
        assert q_data['remaining_passengers_count'] == 1

        # 2. Execute partial cancellation for first passenger
        cancel_resp = client.post(f'/api/bookings/{b_id}/cancel', json={'passenger_ids': [p_ids[0]]})
        assert cancel_resp.status_code == 200
        c_data = cancel_resp.get_json()['data']
        assert c_data['status'] == 'PARTIALLY_CANCELLED'
        assert c_data['cancellation_type'] == 'PARTIAL'
        assert c_data['cancellation_reference'].startswith('CAN-2026-')
        assert 'Alpha Passenger' in c_data['cancelled_passengers']

        # 3. Verify PNR status shows PARTIALLY_CANCELLED with 1 CANCELLED and 1 CONFIRMED
        pnr_resp = client.get(f'/api/pnr/{booking["pnr"]}')
        assert pnr_resp.status_code == 200
        pnr_data = pnr_resp.get_json()['data']
        assert pnr_data['status'] == 'PARTIALLY_CANCELLED'
        passengers = pnr_data['passengers']
        p_alpha = [p for p in passengers if p['id'] == p_ids[0]][0]
        p_beta = [p for p in passengers if p['id'] == p_ids[1]][0]
        assert p_alpha['status'] == 'CANCELLED'
        assert p_beta['status'] == 'CONFIRMED'

        # 4. Cancel the second passenger (should become fully CANCELLED)
        cancel2_resp = client.post(f'/api/bookings/{b_id}/cancel', json={'passenger_ids': [p_ids[1]]})
        assert cancel2_resp.status_code == 200
        c2_data = cancel2_resp.get_json()['data']
        assert c2_data['status'] == 'CANCELLED'

        # 5. Verify duplicate cancellation attempt fails
        cancel3_resp = client.post(f'/api/bookings/{b_id}/cancel')
        assert cancel3_resp.status_code == 400
        assert "already been cancelled" in cancel3_resp.get_json()['message']

    def test_09_cancellation_audit_record_persisted(self, client):
        """Verifies cancellation audit table contains complete reference and metadata."""
        dep_date = (datetime.now() + timedelta(days=4)).strftime('%Y-%m-%d')
        book_resp = client.post('/api/bookings', json={
            'train_id': 1,
            'coach_id': 1,
            'journey_date': dep_date,
            'quota_code': 'GN',
            'passengers': [
                {'name': 'Audit Tester', 'age': 40, 'gender': 'Male', 'id_type': 'Passport', 'id_number': 'Z1234567'}
            ]
        })
        booking = book_resp.get_json()['data']
        b_id = booking['id']

        cancel_resp = client.post(f'/api/bookings/{b_id}/cancel')
        assert cancel_resp.status_code == 200
        can_ref = cancel_resp.get_json()['data']['cancellation_reference']

        # Check DB row
        row = execute_query("SELECT * FROM cancellations WHERE cancellation_reference = %s", (can_ref,), fetchone=True)
        assert row is not None
        assert row['booking_id'] == b_id
        assert row['pnr'] == booking['pnr']
        assert row['refund_status'] == 'Refund Processed'
        assert row['refund_amount'] > 0
