import sys
import json
sys.path.insert(0, '.')
from backend.app import create_app

app = create_app()
client = app.test_client()

print("=== STARTING FULL END-TO-END FLOW VERIFICATION ===")

# 1. REGISTER
test_email = "e2e.passenger@railway.gov.in"
reg_resp = client.post('/api/auth/register', json={
    'name': 'E2E Passenger',
    'email': test_email,
    'phone': '9876500000',
    'password': 'Password@123',
    'confirm_password': 'Password@123'
})
print("1. REGISTER:", reg_resp.status_code, reg_resp.get_json()['message'])
assert reg_resp.status_code in (201, 409), "Registration failed"

# 2. LOGIN
login_resp = client.post('/api/auth/login', json={
    'email': test_email,
    'password': 'Password@123'
})
print("2. LOGIN:", login_resp.status_code, login_resp.get_json()['message'])
assert login_resp.status_code == 200, "Login failed"
user_id = login_resp.get_json()['data']['id']

# 3. SEARCH TRAIN
search_resp = client.get('/api/trains/search?source=Delhi&destination=Mumbai&date=2026-10-15&class=3A&quota=GN')
trains = search_resp.get_json()['data']
print("3. SEARCH TRAIN:", search_resp.status_code, f"Found {len(trains)} trains")
assert len(trains) > 0, "No trains found"
selected_train = trains[0]
train_id = selected_train['id']

# 4. SELECT TRAIN & VIEW SEATS
selected_coach = selected_train['classes'][0]
coach_id = selected_coach['coach_id']
seats_resp = client.get(f'/api/coaches/{coach_id}/seats?date=2026-10-15&session_id=test_session_999')
seats_data = seats_resp.get_json()['data']
print("4. VIEW SEATS:", seats_resp.status_code, f"Coach {seats_data['coach']['coach_number']} has {len(seats_data['seats'])} seats")
assert len(seats_data['seats']) > 0, "Seats empty"

# 5. AI SEAT RECOMMENDATION
rec_resp = client.post('/api/seats/recommend', json={
    'coach_id': coach_id,
    'journey_date': '2026-10-15',
    'passenger_type': 'elderly',
    'preference': 'LOWER',
    'count': 2
})
recs = rec_resp.get_json()['data']['recommendations']
print("5. AI SEAT RECOMMENDATION:", rec_resp.status_code, f"Top pick: Seat {recs[0]['seat_number']} ({recs[0]['recommendation_score']}%)")
assert len(recs) > 0, "AI Recommendation failed"
chosen_seat_ids = [r['seat_id'] for r in recs]

# 6. LOCK SEAT
lock_resp = client.post('/api/seats/lock', json={
    'seat_ids': chosen_seat_ids,
    'journey_date': '2026-10-15',
    'session_id': 'test_session_999',
    'user_id': user_id
})
print("6. LOCK SEAT:", lock_resp.status_code, lock_resp.get_json()['message'])
assert lock_resp.status_code == 200, "Seat lock failed"

# 7. QUOTA VALIDATE
quota_resp = client.post('/api/quota/validate', json={
    'quota_code': 'SS',
    'passengers': [
        {'name': 'Elderly Passenger 1', 'age': 65, 'gender': 'Male', 'id_type': 'Aadhaar', 'id_number': '1234-5678-9012'},
        {'name': 'Elderly Passenger 2', 'age': 62, 'gender': 'Female', 'id_type': 'Aadhaar', 'id_number': '1234-5678-9013'}
    ]
})
print("7. QUOTA VALIDATE (Senior Citizen):", quota_resp.status_code, quota_resp.get_json()['message'])
assert quota_resp.status_code == 200, "Quota validation failed"

# 8. BOOKING & DEMO PAYMENT (GENERATE PNR)
booking_resp = client.post('/api/bookings', json={
    'user_id': user_id,
    'train_id': train_id,
    'coach_id': coach_id,
    'journey_date': '2026-10-15',
    'quota_code': 'SS',
    'session_id': 'test_session_999',
    'passengers': [
        {'name': 'Elderly Passenger 1', 'age': 65, 'gender': 'Male', 'seat_id': chosen_seat_ids[0]},
        {'name': 'Elderly Passenger 2', 'age': 62, 'gender': 'Female', 'seat_id': chosen_seat_ids[1]}
    ]
})
booking_data = booking_resp.get_json()['data']
generated_pnr = booking_data['pnr']
booking_id = booking_data['id']
print("8. GENERATE PNR & BOOKING:", booking_resp.status_code, f"PNR: {generated_pnr}, Total Fare: {booking_data['total_fare']}")
assert len(generated_pnr) == 10, "Invalid PNR format"

# 9. CHECK PNR STATUS
pnr_resp = client.get(f'/api/pnr/{generated_pnr}')
print("9. CHECK PNR:", pnr_resp.status_code, pnr_resp.get_json()['data']['status'])
assert pnr_resp.status_code == 200, "PNR check failed"

# 10. PNR PREDICTION (FOR WAITLIST)
pred_resp = client.post('/api/pnr/predict', json={
    'waiting_list_number': 12,
    'days_left': 8,
    'train_type': 'Rajdhani Express',
    'class_type': '3A',
    'quota': 'GN'
})
pred_data = pred_resp.get_json()['data']
print("10. PNR PREDICTION:", pred_resp.status_code, f"{pred_data['probability']}% ({pred_data['category']} Chance)")
assert 'probability' in pred_data, "Prediction failed"

# 11. LIVE TRAIN TRACKING
tracking_resp = client.get(f'/api/tracking/{train_id}')
track_data = tracking_resp.get_json()['data']
print("11. LIVE TRACKING:", tracking_resp.status_code, f"Speed: {track_data['current_speed']} km/h, Next: {track_data['next_station']}")
assert 'latitude' in track_data, "Tracking failed"

# 12. CHATBOT NLP
chat_resp = client.post('/api/chatbot', json={'message': f'What is the status of PNR {generated_pnr}?'})
print("12. CHATBOT NLP:", chat_resp.status_code, f"Intent: {chat_resp.get_json()['data']['intent']}")
assert chat_resp.status_code == 200, "Chatbot query failed"

# 13. EMERGENCY SOS
sos_resp = client.post('/api/emergency/sos', json={
    'emergency_type': 'Medical Emergency',
    'train_number': selected_train['train_number'],
    'coach': 'B1',
    'seat': '14',
    'description': 'Immediate doctor needed at next station.',
    'user_name': 'E2E Passenger',
    'user_phone': '9876500000'
})
incident_id = sos_resp.get_json()['data']['incident_id']
print("13. EMERGENCY SOS:", sos_resp.status_code, f"Incident: {incident_id}")
assert incident_id.startswith('SOS-2026-'), "SOS dispatch failed"

# 14. ADMIN DASHBOARD STATS
admin_resp = client.get('/api/admin/stats')
print("14. ADMIN STATS:", admin_resp.status_code, f"Total Revenue: {admin_resp.get_json()['data']['kpis']['total_revenue']}")
assert admin_resp.status_code == 200, "Admin stats failed"

# 15. CANCEL BOOKING
cancel_resp = client.post(f'/api/bookings/{booking_id}/cancel')
print("15. CANCEL BOOKING:", cancel_resp.status_code, cancel_resp.get_json()['message'])
assert cancel_resp.status_code == 200, "Cancellation failed"

print("\n" + "="*60)
print(">>> ALL 15 END-TO-END STEPS VERIFIED 100% SUCCESSFULLY! <<<")
print("="*60)
