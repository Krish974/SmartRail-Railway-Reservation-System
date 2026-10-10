import json
from backend.app import create_app
from backend.services.railway_service import RailwayService

app = create_app()

def test_live_tracking_20977():
    print("\n========================================================")
    print("TEST 1: LIVE TRACKING FOR TRAIN 20977 (AII - CDG)")
    print("========================================================")
    with app.test_request_context('/api/tracking/13'):
        from backend.routes.tracking_routes import get_live_tracking
        resp, code = get_live_tracking(13)
        assert code == 200, f"Expected 200, got {code}"
        payload = json.loads(resp.data.decode('utf-8'))
        assert payload['success'], f"Expected success=True, got {payload}"
        data = payload['data']

        print(f"Train: {data['train_number']} - {data['train_name']}")
        print(f"Total Halts: {data['total_halts']}")
        print(f"Total Passing Points: {data['total_passing_points']}")
        print(f"Total Route Stops: {len(data['stops'])}")
        print(f"Total Sections: {len(data['sections'])}")

        assert data['total_halts'] == 10, f"Expected 10 halts, got {data['total_halts']}"
        assert len(data['stops']) == 110, f"Expected 110 route stops, got {len(data['stops'])}"
        assert data['total_passing_points'] == 100, f"Expected 100 passing points, got {data['total_passing_points']}"
        assert len(data['sections']) == 9, f"Expected 9 sections, got {len(data['sections'])}"

        # Validate sequence monotonicity
        prev_seq = 0
        for st in data['stops']:
            assert st['sequence'] > prev_seq, f"Sequence not strictly monotonic at {st['station_code']}: {st['sequence']} <= {prev_seq}"
            prev_seq = st['sequence']

        # Expected section counts
        expected_sections = [
            ("AII", "KSG", 3),
            ("KSG", "JP", 17),
            ("JP", "GADJ", 0),
            ("GADJ", "AWR", 19),
            ("AWR", "RE", 11),
            ("RE", "GGN", 9),
            ("GGN", "DEC", 5),
            ("DEC", "UMB", 32),
            ("UMB", "CDG", 4)
        ]

        total_intermediates_in_sections = 0
        for idx, (f_code, t_code, exp_count) in enumerate(expected_sections):
            sec = data['sections'][idx]
            assert sec['from_station_code'] == f_code, f"Section {idx} from {sec['from_station_code']} != {f_code}"
            assert sec['to_station_code'] == t_code, f"Section {idx} to {sec['to_station_code']} != {t_code}"
            assert sec['intermediate_count'] == exp_count, f"Section {f_code}->{t_code} intermediate count {sec['intermediate_count']} != {exp_count}"
            total_intermediates_in_sections += sec['intermediate_count']

            print(f"  Section [{sec['from_station_code']} -> {sec['to_station_code']}]: {sec['intermediate_count']} intermediate stations ({sec['distance_km']} km) -> OK")

            # Validate each intermediate station in this section
            for pt in sec['intermediate_points']:
                assert not pt['is_scheduled_halt'], f"Intermediate {pt['station_code']} should not be scheduled halt"
                assert pt['point_type'] == 'PASSING', f"Intermediate {pt['station_code']} point_type should be PASSING"
                assert pt['halt_desc'] == 'No Halt / Pass-through', f"Intermediate {pt['station_code']} unexpected halt_desc {pt['halt_desc']}"
                assert pt['arrival_time'] is None, f"Intermediate {pt['station_code']} should not have arrival_time"
                assert pt['departure_time'] is None, f"Intermediate {pt['station_code']} should not have departure_time"
                assert pt['halt_minutes'] == 0, f"Intermediate {pt['station_code']} halt_minutes should be 0"

        assert total_intermediates_in_sections == 100, f"Total section intermediates {total_intermediates_in_sections} != 100"
        print("Train 20977 Live Tracking validation PASSED!")

def test_live_tracking_12952():
    print("\n========================================================")
    print("TEST 2: LIVE TRACKING FOR TRAIN 12952 (NDLS - MMCT)")
    print("========================================================")
    with app.test_request_context('/api/tracking/1'):
        from backend.routes.tracking_routes import get_live_tracking
        resp, code = get_live_tracking(1)
        assert code == 200
        payload = json.loads(resp.data.decode('utf-8'))
        data = payload['data']

        print(f"Train: {data['train_number']} - {data['train_name']}")
        print(f"Total Halts: {data['total_halts']}")
        print(f"Total Passing Points: {data['total_passing_points']}")
        print(f"Total Route Stops: {len(data['stops'])}")
        print(f"Total Sections: {len(data['sections'])}")

        assert data['total_halts'] == 8, f"Expected 8 halts, got {data['total_halts']}"
        assert len(data['stops']) == 221, f"Expected 221 route stops, got {len(data['stops'])}"
        assert len(data['sections']) == 7, f"Expected 7 sections, got {len(data['sections'])}"
        for s in data['sections']:
            print(f"  Section [{s['from_station_code']} -> {s['to_station_code']}]: {s['intermediate_count']} intermediates ({s['distance_km']} km)")
        print("Train 12952 Live Tracking validation PASSED!")

def test_search_trains_10_routes():
    print("\n========================================================")
    print("TEST 3: SEARCH TRAINS DIRECTION VALIDATION (10 ROUTES)")
    print("========================================================")
    routes = [
        ('Jaipur', 'Delhi'),
        ('Jaipur', 'Delhi Cantt'),
        ('Jaipur', 'Ajmer'),
        ('Jaipur', 'Mumbai'),
        ('Delhi', 'Mumbai'),
        ('Mumbai', 'Delhi'),
        ('Delhi', 'Jaipur'),
        ('Jaipur', 'Rishikesh'),
        ('Mumbai', 'Ahmedabad'),
        ('Bengaluru', 'Chennai'),
    ]

    for src, dst in routes:
        results = RailwayService.search_route(src, dst)
        assert len(results) > 0, f"Expected results for {src} -> {dst}, got 0"
        for t in results:
            b_seq = int(t['boarding_sequence'])
            d_seq = int(t['deboarding_sequence'])
            assert b_seq < d_seq, f"Reverse direction detected on {src}->{dst}: train {t['train_number']} has {b_seq} >= {d_seq}"

            b_km = float(t.get('boarding_km') or 0.0)
            d_km = float(t.get('deboarding_km') or 0.0)
            if b_km > 0 and d_km > 0:
                assert b_km <= d_km, f"Distance reverse detected on {src}->{dst}: train {t['train_number']} has {b_km} > {d_km}"

            if src == 'Delhi' and dst == 'Jaipur':
                assert str(t.get('train_number')) != '20977', "Train 20977 (AII-CDG) must NEVER appear in Delhi -> Jaipur results!"

        print(f"  {src:12} -> {dst:15} : {len(results):2d} trains strictly in requested direction -> OK")

    print("All 10 routes Direction Validation PASSED!")

if __name__ == '__main__':
    test_live_tracking_20977()
    test_live_tracking_12952()
    test_search_trains_10_routes()
    print("\nALL LIVE TRACKING AND SEARCH TESTS PASSED SUCCESSFULLY!")
