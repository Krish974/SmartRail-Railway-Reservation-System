import sys
import json
sys.path.insert(0, '.')
from backend.app import create_app
from backend.utils.db_connection import execute_query

app = create_app()
client = app.test_client()

print("=" * 60)
print(">>> RUNNING AUTOMATED TESTS: COACH CLEANING FEATURE <<<")
print("=" * 60)

# Pre-check: count emergency logs before tests
initial_sos_count = execute_query("SELECT COUNT(*) as cnt FROM emergency_logs", fetchone=True)['cnt']

# Test 1: Invalid train number rejected
resp = client.post('/api/emergency/cleaning', json={
    'train_number': '99999',
    'coach_number': 'B1',
    'contact_mobile': '9876543210',
    'issue_type': 'Washroom / Toilet unhygienic'
})
print("Test 1 - Invalid Train Number:", resp.status_code, resp.get_json()['message'])
assert resp.status_code == 400, "Should reject invalid train number with 400"
assert "invalid or does not exist" in resp.get_json()['message'], "Error message must mention train number"

# Test 2: Missing coach rejected
resp = client.post('/api/emergency/cleaning', json={
    'train_number': '12952',
    'coach_number': '',
    'contact_mobile': '9876543210',
    'issue_type': 'Washroom / Toilet unhygienic'
})
print("Test 2 - Missing Coach:", resp.status_code, resp.get_json()['message'])
assert resp.status_code == 400, "Should reject missing coach with 400"

# Test 3: Missing contact mobile rejected
resp = client.post('/api/emergency/cleaning', json={
    'train_number': '12952',
    'coach_number': 'B1',
    'contact_mobile': '',
    'issue_type': 'Washroom / Toilet unhygienic'
})
print("Test 3 - Missing Mobile:", resp.status_code, resp.get_json()['message'])
assert resp.status_code == 400, "Should reject missing mobile with 400"

# Test 4: Invalid cleaning issue type rejected
resp = client.post('/api/emergency/cleaning', json={
    'train_number': '12952',
    'coach_number': 'B1',
    'contact_mobile': '9876543210',
    'issue_type': 'Armed robbery in progress' # Invalid for cleaning!
})
print("Test 4 - Invalid Issue Type:", resp.status_code, resp.get_json()['message'])
assert resp.status_code == 400, "Should reject non-cleaning issue with 400"

# Test 5: Valid cleaning request creation (with seat)
resp = client.post('/api/emergency/cleaning', json={
    'train_number': '12952',
    'coach_number': 'b1',
    'seat_number': '14',
    'issue_type': 'Washroom / Toilet unhygienic',
    'passenger_name': 'Sunita Roy',
    'contact_mobile': '9876543210',
    'description': 'Washroom tap leaking and floor uncleaned.'
})
print("Test 5 - Valid Request Creation:", resp.status_code, resp.get_json()['message'])
assert resp.status_code == 201, "Should create cleaning request with 201"
data = resp.get_json()['data']
req_id_1 = data['request_id']
print(f"   Generated Request ID: {req_id_1}, Status: {data['status']}")
assert req_id_1.startswith('CLR-'), "Request ID must start with 'CLR-'"
assert data['status'] == 'PENDING', "Initial status must be 'PENDING'"
assert data['coach_number'] == 'B1', "Coach number should be normalized to uppercase"

# Test 6: Valid cleaning request creation (optional seat omitted)
resp = client.post('/api/emergency/cleaning', json={
    'train_number': '12015',
    'coach_number': 'C1',
    'issue_type': 'Spilled liquid / food waste',
    'passenger_name': 'Amit Verma',
    'contact_mobile': '9123456780',
    'description': 'Spilled cold drink in aisle near row 5.'
})
print("Test 6 - Optional Seat Omitted:", resp.status_code, resp.get_json()['message'])
assert resp.status_code == 201, "Should create cleaning request without seat"
req_id_2 = resp.get_json()['data']['request_id']
assert resp.get_json()['data']['seat_number'] is None or resp.get_json()['data']['seat_number'] == ''

# Test 7: Fetch cleaning request by ID
resp = client.get(f'/api/emergency/cleaning/{req_id_1}')
print("Test 7 - Fetch by Request ID:", resp.status_code, resp.get_json()['data']['request_id'])
assert resp.status_code == 200, "Should retrieve request by ID"
assert resp.get_json()['data']['passenger_name'] == 'Sunita Roy'

# Test 8: Non-existent request returns 404
resp = client.get('/api/emergency/cleaning/CLR-NONEXISTENT-999')
print("Test 8 - Non-existent ID:", resp.status_code, resp.get_json()['message'])
assert resp.status_code == 404, "Should return 404 for unknown request ID"

# Test 9: List all cleaning requests
resp = client.get('/api/emergency/cleaning')
print("Test 9 - List All Cleaning Requests:", resp.status_code, f"Count: {len(resp.get_json()['data'])}")
assert resp.status_code == 200, "Should list cleaning requests"
all_reqs = resp.get_json()['data']
ids = [r['request_id'] for r in all_reqs]
assert req_id_1 in ids and req_id_2 in ids, "Newly created requests must be in listing"

# Test 10: Status progression (PENDING -> ASSIGNED -> CLEANING IN PROGRESS -> RESOLVED)
# Step 10a: PENDING -> ASSIGNED
resp = client.patch(f'/api/emergency/cleaning/{req_id_1}/status', json={'status': 'ASSIGNED'})
print("Test 10a - Update to ASSIGNED:", resp.status_code, resp.get_json()['data']['status'])
assert resp.status_code == 200
assert resp.get_json()['data']['status'] == 'ASSIGNED'

# Step 10b: ASSIGNED -> CLEANING IN PROGRESS
resp = client.patch(f'/api/emergency/cleaning/{req_id_1}/status', json={'status': 'CLEANING IN PROGRESS'})
print("Test 10b - Update to CLEANING IN PROGRESS:", resp.status_code, resp.get_json()['data']['status'])
assert resp.status_code == 200
assert resp.get_json()['data']['status'] == 'CLEANING IN PROGRESS'

# Step 10c: CLEANING IN PROGRESS -> RESOLVED
resp = client.patch(f'/api/emergency/cleaning/{req_id_1}/status', json={'status': 'RESOLVED'})
print("Test 10c - Update to RESOLVED:", resp.status_code, resp.get_json()['data']['status'])
assert resp.status_code == 200
assert resp.get_json()['data']['status'] == 'RESOLVED'

# Test 11: Invalid status rejected
resp = client.patch(f'/api/emergency/cleaning/{req_id_1}/status', json={'status': 'SUPER_CLEANED'})
print("Test 11 - Invalid Status Rejected:", resp.status_code, resp.get_json()['message'])
assert resp.status_code == 400, "Should reject invalid status with 400"

# Test 12: Isolation check - ensure emergency_logs was NOT touched
final_sos_count = execute_query("SELECT COUNT(*) as cnt FROM emergency_logs", fetchone=True)['cnt']
print(f"Test 12 - Emergency Logs Isolation: Initial SOS count = {initial_sos_count}, Final SOS count = {final_sos_count}")
assert initial_sos_count == final_sos_count, "Cleaning requests must NOT contaminate emergency_logs table!"

print("\n" + "=" * 60)
print(">>> ALL 12 COACH CLEANING AUTOMATED TESTS PASSED 100%! <<<")
print("=" * 60)
