"""
RailRadar Dataset Importer Script
---------------------------------
Safely and idempotently imports real Indian Railway stations, trains, and routes
from RailRadar API (https://api.railradar.in) into the SmartRail relational database.

Usage:
  python scripts/import_railradar_data.py --stations
  python scripts/import_railradar_data.py --trains --limit 10
  python scripts/import_railradar_data.py --routes --limit 5
"""

import sys
import os
import argparse
import logging

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import Config
from backend.utils.db_connection import execute_query, get_connection, get_db_type
from backend.services.railradar_service import RailRadarService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("RailRadarImporter")

def upsert_station(st_data):
    """
    Inserts or updates a station record by station code.
    Avoids duplicate codes.
    Returns (st_id, is_new).
    """
    code = st_data['code'].upper().strip()
    name = st_data['name'].strip()
    city = st_data.get('city') or name
    state = st_data.get('state') or 'India'
    lat = float(st_data.get('latitude') or 0.0)
    lng = float(st_data.get('longitude') or 0.0)
    aliases = st_data.get('aliases') or f"{code}, {name}, {city}, {state}"

    existing = execute_query("SELECT id FROM stations WHERE UPPER(code) = UPPER(%s)", (code,), fetchone=True)
    if existing:
        st_id = existing['id']
        update_sql = """
            UPDATE stations
            SET name = %s, city = %s, state = %s,
                latitude = CASE WHEN latitude = 0 THEN %s ELSE latitude END,
                longitude = CASE WHEN longitude = 0 THEN %s ELSE longitude END,
                aliases = %s
            WHERE id = %s
        """
        execute_query(update_sql, (name, city, state, lat, lng, aliases, st_id), commit=True)
        return st_id, False
    else:
        insert_sql = """
            INSERT INTO stations (code, name, city, state, latitude, longitude, aliases)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        st_id = execute_query(insert_sql, (code, name, city, state, lat, lng, aliases), commit=True)
        return st_id, True

def import_stations():
    """Fetches and imports all stations from RailRadar."""
    print("Testing RailRadar connectivity...")
    test_res = RailRadarService.test_connection()
    if not test_res['success']:
        print(f"RailRadar connection: FAILED ({test_res['message']})")
        return {
            "success": False,
            "received": 0,
            "inserted": 0,
            "updated": 0,
            "errors": 1,
            "message": test_res['message']
        }

    print("Fetching station directory from RailRadar (GET /v1/lookup/stations)...")
    stations = RailRadarService.fetch_stations()
    received = len(stations)
    inserted = 0
    updated = 0
    errors = 0

    existing_rows = execute_query("SELECT id, UPPER(code) as code, name, city, state, latitude, longitude FROM stations", fetchall=True) or []
    existing_by_code = {r['code']: r for r in existing_rows}

    db_type = get_db_type()
    conn = get_connection()
    cursor = conn.cursor() if db_type == 'sqlite' else conn.cursor(dictionary=True)
    placeholder = '?' if db_type == 'sqlite' else '%s'

    update_sql = f"""
        UPDATE stations
        SET name = {placeholder},
            city = CASE WHEN city IS NULL OR city = '' THEN {placeholder} ELSE city END,
            state = CASE WHEN state IS NULL OR state = '' OR state = 'India' THEN {placeholder} ELSE state END,
            latitude = CASE WHEN latitude = 0 THEN {placeholder} ELSE latitude END,
            longitude = CASE WHEN longitude = 0 THEN {placeholder} ELSE longitude END,
            aliases = CASE WHEN aliases IS NULL OR aliases = '' THEN {placeholder} ELSE aliases END
        WHERE id = {placeholder}
    """

    insert_sql = f"""
        INSERT INTO stations (code, name, city, state, latitude, longitude, aliases)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """

    try:
        for st in stations:
            try:
                code = st['code'].upper().strip()
                name = st['name'].strip()
                city = st.get('city') or name
                state = st.get('state') or 'India'
                lat = float(st.get('latitude') or 0.0)
                lng = float(st.get('longitude') or 0.0)
                aliases = st.get('aliases') or f"{code}, {name}"

                if code in existing_by_code:
                    st_id = existing_by_code[code]['id']
                    cursor.execute(update_sql, (name, city, state, lat, lng, aliases, st_id))
                    updated += 1
                else:
                    cursor.execute(insert_sql, (code, name, city, state, lat, lng, aliases))
                    new_id = cursor.lastrowid
                    existing_by_code[code] = {'id': new_id, 'code': code}
                    inserted += 1
            except Exception as e:
                errors += 1
                logger.error(f"Error upserting station {st.get('code')}: {e}")

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction failed during station import: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    total_in_db = execute_query("SELECT count(*) as count FROM stations", fetchone=True)['count']

    print("\n" + "="*40)
    print("RailRadar Station Import Report")
    print("--------------------------------")
    print(f"RailRadar stations received: {received}")
    print(f"New stations inserted: {inserted}")
    print(f"Existing stations updated: {updated}")
    print(f"Failed records: {errors}")
    print(f"Total stations in database: {total_in_db}")
    print("="*40 + "\n")

    return {
        "success": True,
        "received": received,
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
        "total_in_db": total_in_db
    }

def import_trains_directory(limit=None):
    """Fetches and imports NTES train directory from RailRadar."""
    print("Fetching NTES trains from RailRadar (GET /v1/lookup/trains/ntes)...")
    trains = RailRadarService.fetch_trains_ntes()
    if limit and limit > 0:
        trains = trains[:limit]

    received = len(trains)
    inserted = 0
    updated = 0
    errors = 0

    existing_rows = execute_query("SELECT id, train_number, train_name, train_type FROM trains", fetchall=True) or []
    existing_by_num = {str(r['train_number']).strip(): r for r in existing_rows}
    seen_numbers = set(existing_by_num.keys())

    db_type = get_db_type()
    conn = get_connection()
    cursor = conn.cursor() if db_type == 'sqlite' else conn.cursor(dictionary=True)
    placeholder = '?' if db_type == 'sqlite' else '%s'

    update_sql = f"""
        UPDATE trains
        SET train_name = {placeholder},
            train_type = {placeholder}
        WHERE id = {placeholder}
    """

    insert_sql = f"""
        INSERT INTO trains (train_number, train_name, source_station_id, dest_station_id,
                            departure_time, arrival_time, duration, running_days, train_type, is_active)
        VALUES ({placeholder}, {placeholder}, NULL, NULL, NULL, NULL, NULL, NULL, {placeholder}, 1)
    """

    try:
        for t in trains:
            t_num = str(t['train_number']).strip()
            t_name = str(t['train_name']).strip()
            t_type = t.get('train_type') or 'Express'

            try:
                if t_num in existing_by_num:
                    t_id = existing_by_num[t_num]['id']
                    cursor.execute(update_sql, (t_name, t_type, t_id))
                    updated += 1
                elif t_num in seen_numbers:
                    continue
                else:
                    cursor.execute(insert_sql, (t_num, t_name, t_type))
                    new_id = cursor.lastrowid
                    existing_by_num[t_num] = {'id': new_id, 'train_number': t_num}
                    seen_numbers.add(t_num)
                    inserted += 1
            except Exception as e:
                errors += 1
                logger.error(f"Error importing train {t_num}: {e}")

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction failed during train import: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    total_trains = execute_query("SELECT count(*) as count FROM trains", fetchone=True)['count']
    total_stations = execute_query("SELECT count(*) as count FROM stations", fetchone=True)['count']
    total_stops = execute_query("SELECT count(*) as count FROM train_stops", fetchone=True)['count']

    sample_trains = execute_query("SELECT train_number, train_name FROM trains ORDER BY id ASC LIMIT 10", fetchall=True)

    print("\n" + "="*40)
    print("RailRadar Train Directory Import")
    print("---------------------------------")
    print(f"Trains received from API: {received}")
    print(f"New trains inserted: {inserted}")
    print(f"Existing trains updated: {updated}")
    print(f"Failed records: {errors}")
    print(f"Total trains in database: {total_trains}")
    print("")
    print("Current stations:")
    print(f"{total_stations:,}")
    print("")
    print("Current train stops:")
    print(f"{total_stops:,}")
    print("="*40 + "\n")

    print("Sample Records (10 trains):")
    print("Train Number | Train Name")
    print("-------------|-----------")
    for st in sample_trains:
        print(f"{st['train_number']:<12} | {st['train_name']}")
    print("")

    return {
        "success": True,
        "received": received,
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
        "total_trains": total_trains,
        "total_stations": total_stations,
        "total_stops": total_stops,
        "sample": sample_trains
    }

def import_routes(limit=5):
    """Fetches and imports routes for trains."""
    train_rows = execute_query("SELECT train_number FROM trains ORDER BY id ASC LIMIT %s", (limit,), fetchall=True)
    if not train_rows:
        print("No trains found in database to fetch routes for.")
        return

    imported_routes = 0
    errors = 0

    for r in train_rows:
        t_num = r['train_number']
        print(f"Fetching route for Train #{t_num}...")
        route_data = RailRadarService.fetch_train_route(t_num)
        if not route_data or not route_data.get('stops'):
            print(f"  [WARN] No route stops returned for #{t_num}")
            errors += 1
            continue

        try:
            train_record = execute_query("SELECT id FROM trains WHERE train_number = %s", (t_num,), fetchone=True)
            if not train_record:
                continue
            train_id = train_record['id']

            # Update departure and arrival
            stops = route_data['stops']
            dep_time = stops[0]['departure_time']
            arr_time = stops[-1]['arrival_time']
            execute_query("UPDATE trains SET departure_time = %s, arrival_time = %s WHERE id = %s", (dep_time, arr_time, train_id), commit=True)

            # Atomically replace stops
            execute_query("DELETE FROM train_stops WHERE train_id = %s", (train_id,), commit=True)
            for s in stops:
                st_id, _ = upsert_station({'code': s['station_code'], 'name': s['station_name']})
                stop_sql = """
                    INSERT INTO train_stops (train_id, station_id, stop_sequence, arrival_time, departure_time, halt_minutes, distance_km)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                execute_query(stop_sql, (train_id, st_id, s['stop_sequence'], s['arrival_time'], s['departure_time'], s['halt_minutes'], s['distance_km']), commit=True)

            imported_routes += 1
            print(f"  [SUCCESS] #{t_num} imported with {len(stops)} stops.")
        except Exception as e:
            errors += 1
            logger.error(f"Error persisting route for #{t_num}: {e}")

    print("\n" + "="*40)
    print("RailRadar Route Import Report")
    print("-----------------------------")
    print(f"Routes successfully imported: {imported_routes}")
    print(f"Errors: {errors}")
    print("="*40 + "\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="RailRadar Dataset Importer")
    parser.add_argument('--stations', action='store_true', help="Import all railway stations")
    parser.add_argument('--trains', action='store_true', help="Import NTES train directory")
    parser.add_argument('--routes', action='store_true', help="Import train routes/timetables")
    parser.add_argument('--limit', type=int, default=None, help="Limit number of trains/routes to import")
    args = parser.parse_args()

    if args.stations:
        import_stations()
    elif args.trains:
        import_trains_directory(limit=args.limit)
    elif args.routes:
        import_routes(limit=args.limit or 5)
    else:
        # Default action: run test connection
        res = RailRadarService.test_connection()
        print("\nRailRadar API Test")
        print("------------------")
        print(f"Connection: {'SUCCESS' if res['success'] else 'FAILED'}")
        print(f"HTTP Status: {res['status_code']}")
        print(f"Stations received: {res['stations_count']}")
        print(f"Details: {res['message']}\n")
