"""
Qrail Dataset Importer Script
-----------------------------
Safely and idempotently ingests real train schedules and intermediate halts
from the Qrail API into the SmartRail relational database (MySQL / SQLite).

Features:
- Idempotent upserts for stations, trains, and train_stops.
- Configurable limits via QRAIL_IMPORT_LIMIT or --limit CLI flag.
- Safe logging: NEVER prints or exposes the QRAIL_API_KEY.
- Generates standard Qrail Import Report.

Usage:
  python backend/utils/ingest_qrail_dataset.py [--limit 5] [--trains 12952,12015,...]
"""

import sys
import os
import argparse
import logging

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import Config
from backend.utils.db_connection import execute_query
from backend.services.qrail_service import QRailService
from backend.services.railway_service import RailwayService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("QrailImporter")

def get_or_create_station(station_data):
    """
    Idempotently retrieves an existing station by code or creates it.
    Never creates duplicate stations with the same code.
    """
    code = station_data['station_code'].upper().strip()
    name = station_data['station_name'].strip()
    city = station_data.get('city') or name
    state = station_data.get('state') or 'India'

    existing = execute_query("SELECT id FROM stations WHERE UPPER(code) = UPPER(%s)", (code,), fetchone=True)
    if existing:
        return existing['id']

    # Insert new station with default zero lat/long (can be geocoded later)
    aliases = f"{code}, {name}, {city}, {state}"
    insert_sql = """
        INSERT INTO stations (code, name, city, state, latitude, longitude, aliases)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    st_id = execute_query(insert_sql, (code, name, city, state, 0.0, 0.0, aliases), commit=True)
    return st_id

def upsert_train_and_stops(train_profile):
    """
    Idempotently upserts train record and all intermediate stops.
    """
    stops = train_profile['stops']
    if not stops:
        return None

    # 1. Resolve source and destination stations
    source_st_id = get_or_create_station(stops[0])
    dest_st_id = get_or_create_station(stops[-1])

    t_num = train_profile['train_number']
    t_name = train_profile['train_name']
    t_type = train_profile.get('train_type') or 'Express'
    dep_time = train_profile['departure_time']
    arr_time = train_profile['arrival_time']
    duration = train_profile.get('duration') or RailwayService.calculate_travel_duration(dep_time, arr_time)
    running_days = train_profile.get('running_days') or 'Mon,Tue,Wed,Thu,Fri,Sat,Sun'

    # Check if train already exists
    existing_train = execute_query("SELECT id FROM trains WHERE train_number = %s", (t_num,), fetchone=True)
    if existing_train:
        train_id = existing_train['id']
        update_sql = """
            UPDATE trains
            SET train_name = %s, source_station_id = %s, dest_station_id = %s,
                departure_time = %s, arrival_time = %s, duration = %s,
                running_days = %s, train_type = %s, is_active = 1
            WHERE id = %s
        """
        execute_query(update_sql, (t_name, source_st_id, dest_st_id, dep_time, arr_time, duration, running_days, t_type, train_id), commit=True)
    else:
        insert_sql = """
            INSERT INTO trains (train_number, train_name, source_station_id, dest_station_id,
                                departure_time, arrival_time, duration, running_days, train_type, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
        """
        train_id = execute_query(insert_sql, (t_num, t_name, source_st_id, dest_st_id, dep_time, arr_time, duration, running_days, t_type), commit=True)

    # 2. Update stops: replace stops idempotently
    execute_query("DELETE FROM train_stops WHERE train_id = %s", (train_id,), commit=True)

    for s in stops:
        st_id = get_or_create_station(s)
        stop_sql = """
            INSERT INTO train_stops (train_id, station_id, stop_sequence, arrival_time, departure_time, halt_minutes, distance_km)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(stop_sql, (train_id, st_id, s['stop_sequence'], s['arrival_time'], s['departure_time'], s['halt_minutes'], s['distance_km']), commit=True)

    # 3. Ensure coaches exist for booking
    existing_coaches = execute_query("SELECT count(*) as cnt FROM coaches WHERE train_id = %s", (train_id,), fetchone=True)
    if not existing_coaches or existing_coaches['cnt'] == 0:
        coach_classes = [('B1', '3A', 72, 1450.0), ('A1', '2A', 48, 2100.0), ('S1', 'SL', 72, 550.0)]
        for c_num, c_class, seats, fare in coach_classes:
            execute_query(
                "INSERT INTO coaches (train_id, coach_number, coach_class, total_seats, base_fare) VALUES (%s, %s, %s, %s, %s)",
                (train_id, c_num, c_class, seats, fare), commit=True
            )

    return train_id

def run_import(train_numbers=None, limit=None):
    """
    Main ingestion execution workflow.
    """
    import_limit = limit if limit is not None else Config.QRAIL_IMPORT_LIMIT
    
    if not QRailService.is_configured():
        print("\n" + "="*50)
        print("ERROR: QRAIL_API_KEY is not configured in .env!")
        print("="*50)
        print("To import real schedules from Qrail.in:")
        print("1. Obtain your API key from https://qrail.in/developers")
        print("2. Open your .env file and set: QRAIL_API_KEY=your_key_here")
        print("3. Re-run: python backend/utils/ingest_qrail_dataset.py\n")
        return False

    # Connectivity Probe
    conn_result = QRailService.test_connection()
    if not conn_result['success']:
        print(f"\nQrail connection: FAILED ({conn_result['message']})\n")
        return False

    print(f"\n{conn_result['message']}")

    # If no train numbers provided:
    # Notice: Qrail does not provide a public endpoint listing all 500+ train numbers.
    # Therefore, we require the user or system to provide candidate train numbers.
    if not train_numbers:
        # Check existing benchmark trains in database or prompt input
        existing_rows = execute_query("SELECT train_number FROM trains ORDER BY id ASC LIMIT %s", (import_limit,), fetchall=True)
        if existing_rows:
            train_numbers = [r['train_number'] for r in existing_rows]
        else:
            train_numbers = ['12952', '12015', '12951', '12016', '20977'][:import_limit]

    train_numbers = train_numbers[:import_limit]
    requested_count = len(train_numbers)
    success_count = 0
    fail_count = 0

    print(f"Beginning ingestion for {requested_count} train(s)...")

    for t_num in train_numbers:
        try:
            profile = QRailService.fetch_train_schedule(t_num)
            if profile and profile.get('stops'):
                t_id = upsert_train_and_stops(profile)
                if t_id:
                    success_count += 1
                    print(f"  [SUCCESS] Train #{profile['train_number']} ({profile['train_name']}) — {len(profile['stops'])} stops imported.")
                else:
                    fail_count += 1
                    print(f"  [FAILED] Could not persist train #{t_num}.")
            else:
                fail_count += 1
                print(f"  [FAILED] No schedule data received from Qrail for train #{t_num}.")
        except Exception as e:
            fail_count += 1
            logger.error(f"Error importing train #{t_num}: {e}")

    # Database Summary Queries
    train_count_res = execute_query("SELECT count(*) as cnt FROM trains", fetchone=True)
    st_count_res = execute_query("SELECT count(*) as cnt FROM stations", fetchone=True)
    stop_count_res = execute_query("SELECT count(*) as cnt FROM train_stops", fetchone=True)

    total_trains = train_count_res['cnt'] if train_count_res else 0
    total_stations = st_count_res['cnt'] if st_count_res else 0
    total_stops = stop_count_res['cnt'] if stop_count_res else 0

    print("\n" + "="*30)
    print("Qrail Import Report")
    print("-------------------")
    print(f"Requested: {requested_count}")
    print(f"Successfully imported: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Trains in database: {total_trains}")
    print(f"Stations in database: {total_stations}")
    print(f"Train stops in database: {total_stops}")
    print("="*30 + "\n")
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Ingest real train schedules from Qrail API.")
    parser.add_argument('--limit', type=int, default=None, help="Maximum number of trains to import (default: from QRAIL_IMPORT_LIMIT in .env)")
    parser.add_argument('--trains', type=str, default=None, help="Comma-separated train numbers (e.g. 12952,12015)")
    args = parser.parse_args()

    train_list = [t.strip() for t in args.trains.split(',')] if args.trains else None
    run_import(train_numbers=train_list, limit=args.limit)
