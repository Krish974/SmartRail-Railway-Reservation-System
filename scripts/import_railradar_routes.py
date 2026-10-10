"""
RailRadar Bulk Route Importer Script
------------------------------------
Production-safe, resumable importer for train routes and station stops from RailRadar API.
Supports rate-limiting, progress checkpoints, and graceful error handling.

Usage:
  python scripts/import_railradar_routes.py --limit 10
  python scripts/import_railradar_routes.py --limit 100 --delay 1
  python scripts/import_railradar_routes.py --resume
  python scripts/import_railradar_routes.py --train 12952
"""

import sys
import os
import time
import argparse
import json
import logging
from datetime import datetime

# Add project root to sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import Config
from backend.utils.db_connection import execute_query, get_connection, get_db_type
from backend.services.railradar_service import RailRadarService

PROGRESS_FILE = os.path.join(PROJECT_ROOT, 'database', 'route_import_progress.json')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RouteImporter")

def load_progress():
    """Loads route import progress from JSON file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load progress file ({e}), starting fresh.")
    return {
        "last_processed_train_id": 0,
        "last_processed_train_number": None,
        "successful_routes": [],
        "failed_routes": {},
        "skipped_routes": [],
        "total_stops_inserted": 0,
        "total_stops_updated": 0,
        "updated_at": None
    }

def save_progress(progress):
    """Saves progress checkpoint atomically to JSON file."""
    progress['updated_at'] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    temp_file = f"{PROGRESS_FILE}.tmp"
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        if os.path.exists(PROGRESS_FILE):
            os.replace(temp_file, PROGRESS_FILE)
        else:
            os.rename(temp_file, PROGRESS_FILE)
    except Exception as e:
        logger.error(f"Error saving progress checkpoint: {e}")

def is_route_complete(train_id):
    """
    Checks if a train already has a complete route in the database.
    A complete route has >= 2 train_stops and non-null source/dest station references.
    """
    t_row = execute_query("SELECT source_station_id, dest_station_id FROM trains WHERE id = %s", (train_id,), fetchone=True)
    if not t_row or t_row['source_station_id'] is None or t_row['dest_station_id'] is None:
        return False

    stops_res = execute_query("SELECT count(*) as count FROM train_stops WHERE train_id = %s", (train_id,), fetchone=True)
    stops_count = stops_res['count'] if stops_res else 0
    return stops_count >= 2

def upsert_station_from_stop(cursor, db_type, stop):
    """
    Resolves or inserts station using real data from the route stop.
    Updates coordinates if existing record has 0.0 coordinates.
    Returns (station_id, is_new).
    """
    placeholder = '?' if db_type == 'sqlite' else '%s'
    code = str(stop.get('code') or '').strip().upper()
    name = str(stop.get('name') or code).strip()
    try:
        lat = float(stop.get('lat') or 0.0)
        lng = float(stop.get('lng') or 0.0)
    except (ValueError, TypeError):
        lat, lng = 0.0, 0.0

    check_sql = f"SELECT id, latitude, longitude FROM stations WHERE UPPER(code) = UPPER({placeholder})"
    cursor.execute(check_sql, (code,))
    row = cursor.fetchone()
    if row:
        st_id = row['id']
        cur_lat = row['latitude']
        if lat != 0.0 and (cur_lat == 0.0 or cur_lat is None):
            update_sql = f"UPDATE stations SET latitude = {placeholder}, longitude = {placeholder} WHERE id = {placeholder}"
            cursor.execute(update_sql, (lat, lng, st_id))
        return st_id, False
    else:
        aliases = f"{code}, {name}"
        insert_sql = f"""
            INSERT INTO stations (code, name, city, state, latitude, longitude, aliases)
            VALUES ({placeholder}, {placeholder}, {placeholder}, 'India', {placeholder}, {placeholder}, {placeholder})
        """
        cursor.execute(insert_sql, (code, name, name, lat, lng, aliases))
        st_id = cursor.lastrowid
        return st_id, True

def run_route_importer(limit=None, offset=0, train_number=None, resume=False, delay=None):
    """
    Executes the bulk route importer with rate-limiting, progress checkpoints, and reporting.
    """
    if delay is None:
        delay = getattr(Config, 'RAILRADAR_ROUTE_DELAY', 1.0)

    progress = load_progress()
    db_type = get_db_type()
    placeholder = '?' if db_type == 'sqlite' else '%s'

    # Determine candidate trains
    if train_number:
        query_sql = f"SELECT id, train_number, train_name, source_station_id, dest_station_id FROM trains WHERE train_number = {placeholder}"
        candidate_trains = execute_query(query_sql, (str(train_number).strip(),), fetchall=True)
    elif resume:
        last_id = progress.get('last_processed_train_id', 0)
        query_sql = f"SELECT id, train_number, train_name, source_station_id, dest_station_id FROM trains WHERE id > {placeholder} ORDER BY id ASC"
        candidate_trains = execute_query(query_sql, (last_id,), fetchall=True)
        if offset > 0:
            candidate_trains = candidate_trains[offset:]
    else:
        query_sql = "SELECT id, train_number, train_name, source_station_id, dest_station_id FROM trains ORDER BY id ASC"
        candidate_trains = execute_query(query_sql, fetchall=True)
        if offset > 0:
            candidate_trains = candidate_trains[offset:]

    if not candidate_trains:
        print("No candidate trains found to process.")
        return

    # Statistics
    requested_count = 0  # Number of trains where API request was made
    successful_count = 0
    skipped_count = 0
    failed_count = 0
    stops_inserted = 0
    stops_updated = 0
    api_requests_made = 0
    api_failures = 0
    http_429_count = 0

    print("="*55)
    print("Starting RailRadar Route Importer")
    print(f"Target limit (API requests): {limit if limit else 'All candidate trains'}")
    print(f"Request delay: {delay}s | Database engine: {db_type}")
    print("="*55)

    conn = get_connection()
    cursor = conn.cursor() if db_type == 'sqlite' else conn.cursor(dictionary=True)

    try:
        for t in candidate_trains:
            t_id = t['id']
            t_num = str(t['train_number']).strip()
            t_name = str(t['train_name']).strip()

            # Check if route is already complete in database
            if not train_number and is_route_complete(t_id):
                skipped_count += 1
                if t_num not in progress['skipped_routes']:
                    progress['skipped_routes'].append(t_num)
                progress['last_processed_train_id'] = t_id
                progress['last_processed_train_number'] = t_num
                continue

            # Check if we have fulfilled the limit for API requests
            if limit and requested_count >= limit:
                break

            # Need to request route from RailRadar
            requested_count += 1
            api_requests_made += 1

            url = f"{RailRadarService.BASE_URL}/v1/trains/{t_num}/route?stops=true"
            try:
                resp = RailRadarService._get_session().get(url, headers=RailRadarService._get_headers(), timeout=30)
                status_code = resp.status_code

                if status_code == 429:
                    http_429_count += 1
                    logger.warning(f"HTTP 429: Rate limit encountered on train #{t_num}. Pausing importer.")
                    save_progress(progress)
                    break

                if status_code == 401:
                    api_failures += 1
                    logger.error("HTTP 401: Invalid or missing API key. Stopping importer.")
                    save_progress(progress)
                    break

                if status_code == 403:
                    api_failures += 1
                    logger.error("HTTP 403: Forbidden/Subscription error. Stopping importer.")
                    save_progress(progress)
                    break

                if status_code == 404:
                    api_failures += 1
                    failed_count += 1
                    progress['failed_routes'][t_num] = "HTTP 404: Route not found"
                    progress['last_processed_train_id'] = t_id
                    progress['last_processed_train_number'] = t_num
                    save_progress(progress)
                    time.sleep(delay)
                    continue

                if status_code >= 500:
                    api_failures += 1
                    failed_count += 1
                    progress['failed_routes'][t_num] = f"HTTP {status_code}: Provider server error"
                    progress['last_processed_train_id'] = t_id
                    progress['last_processed_train_number'] = t_num
                    save_progress(progress)
                    time.sleep(delay)
                    continue

                if status_code != 200:
                    api_failures += 1
                    failed_count += 1
                    progress['failed_routes'][t_num] = f"HTTP {status_code}: Unexpected response"
                    progress['last_processed_train_id'] = t_id
                    progress['last_processed_train_number'] = t_num
                    save_progress(progress)
                    time.sleep(delay)
                    continue

                # 200 OK: Parse stops
                data = resp.json()
                raw_data = data.get('data', {}) if isinstance(data, dict) else {}
                raw_stops = raw_data.get('stops', []) if isinstance(raw_data, dict) else []

                # Route validation: at least 2 stops required
                if not isinstance(raw_stops, list) or len(raw_stops) < 2:
                    api_failures += 1
                    failed_count += 1
                    progress['failed_routes'][t_num] = f"Invalid route: only {len(raw_stops)} stops returned"
                    progress['last_processed_train_id'] = t_id
                    progress['last_processed_train_number'] = t_num
                    save_progress(progress)
                    time.sleep(delay)
                    continue

                # Process stops in a single transaction
                t_inserted = 0
                t_updated = 0
                first_st_id = None
                last_st_id = None
                first_dep = 'START'
                last_arr = 'END'

                for idx, s in enumerate(raw_stops, 1):
                    st_id, _ = upsert_station_from_stop(cursor, db_type, s)
                    if idx == 1:
                        first_st_id = st_id
                    if idx == len(raw_stops):
                        last_st_id = st_id

                    seq = int(s.get('sequence') or idx)
                    arr = str(s.get('arrival') or ('START' if idx == 1 else '--:--')).strip()
                    dep = str(s.get('departure') or ('END' if idx == len(raw_stops) else '--:--')).strip()
                    if idx == 1 and dep != '--:--':
                        first_dep = dep
                    if idx == len(raw_stops) and arr != '--:--':
                        last_arr = arr

                    halt = int(s.get('halt') or 0)
                    try:
                        dist = float(s.get('distance') or 0.0)
                    except (ValueError, TypeError):
                        dist = 0.0

                    # Check existing stop
                    check_stop_sql = f"SELECT id FROM train_stops WHERE train_id = {placeholder} AND station_id = {placeholder}"
                    cursor.execute(check_stop_sql, (t_id, st_id))
                    existing_stop = cursor.fetchone()

                    if existing_stop:
                        stop_id = existing_stop['id']
                        upd_stop_sql = f"""
                            UPDATE train_stops
                            SET stop_sequence = {placeholder}, arrival_time = {placeholder},
                                departure_time = {placeholder}, halt_minutes = {placeholder}, distance_km = {placeholder}
                            WHERE id = {placeholder}
                        """
                        cursor.execute(upd_stop_sql, (seq, arr, dep, halt, dist, stop_id))
                        t_updated += 1
                    else:
                        ins_stop_sql = f"""
                            INSERT INTO train_stops (train_id, station_id, stop_sequence, arrival_time, departure_time, halt_minutes, distance_km)
                            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                        """
                        cursor.execute(ins_stop_sql, (t_id, st_id, seq, arr, dep, halt, dist))
                        t_inserted += 1

                # Update train's source and destination station references
                update_train_sql = f"""
                    UPDATE trains
                    SET source_station_id = {placeholder}, dest_station_id = {placeholder},
                        departure_time = CASE WHEN departure_time IS NULL OR departure_time = '' THEN {placeholder} ELSE departure_time END,
                        arrival_time = CASE WHEN arrival_time IS NULL OR arrival_time = '' THEN {placeholder} ELSE arrival_time END
                    WHERE id = {placeholder}
                """
                cursor.execute(update_train_sql, (first_st_id, last_st_id, first_dep, last_arr, t_id))
                conn.commit()

                successful_count += 1
                stops_inserted += t_inserted
                stops_updated += t_updated
                progress['total_stops_inserted'] += t_inserted
                progress['total_stops_updated'] += t_updated

                if t_num not in progress['successful_routes']:
                    progress['successful_routes'].append(t_num)

                progress['last_processed_train_id'] = t_id
                progress['last_processed_train_number'] = t_num
                save_progress(progress)

                logger.info(f"Train #{t_num} ({t_name}): {len(raw_stops)} stops imported (+{t_inserted} new, {t_updated} updated).")

            except Exception as e:
                conn.rollback()
                api_failures += 1
                failed_count += 1
                progress['failed_routes'][t_num] = str(e)
                progress['last_processed_train_id'] = t_id
                progress['last_processed_train_number'] = t_num
                save_progress(progress)
                logger.error(f"Error importing route for train #{t_num}: {e}")

            time.sleep(delay)

    finally:
        cursor.close()
        conn.close()

    # Query current totals from database
    total_stations = execute_query("SELECT count(*) as count FROM stations", fetchone=True)['count']
    total_trains = execute_query("SELECT count(*) as count FROM trains", fetchone=True)['count']
    total_stops = execute_query("SELECT count(*) as count FROM train_stops", fetchone=True)['count']

    # Generate Report
    print("\n" + "="*40)
    print("RailRadar Route Import Report")
    print("------------------------------")
    print(f"Requested: {requested_count}")
    print(f"Successful: {successful_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Failed: {failed_count}")
    print(f"Stops inserted: {stops_inserted}")
    print(f"Stops updated: {stops_updated}")
    print("")
    print("Database totals:")
    print(f"Stations: {total_stations:,}")
    print(f"Trains: {total_trains:,}")
    print(f"Train stops: {total_stops:,}")
    print("")
    print("Also show:")
    print(f"- API requests made: {api_requests_made}")
    print(f"- API failures: {api_failures}")
    print(f"- HTTP 429 occurrences: {http_429_count}")
    print("="*40 + "\n")

    return {
        "requested": requested_count,
        "successful": successful_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "stops_inserted": stops_inserted,
        "stops_updated": stops_updated,
        "total_stations": total_stations,
        "total_trains": total_trains,
        "total_stops": total_stops,
        "api_requests_made": api_requests_made,
        "api_failures": api_failures,
        "http_429_count": http_429_count
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="RailRadar Bulk Route Importer")
    parser.add_argument('--limit', type=int, default=None, help="Maximum number of route API requests to make")
    parser.add_argument('--offset', type=int, default=0, help="Offset into candidates list")
    parser.add_argument('--train', type=str, default=None, help="Specific train number to import route for")
    parser.add_argument('--resume', action='store_true', help="Resume from last processed checkpoint")
    parser.add_argument('--delay', type=float, default=None, help="Delay between API requests in seconds")

    args = parser.parse_args()
    run_route_importer(
        limit=args.limit,
        offset=args.offset,
        train_number=args.train,
        resume=args.resume,
        delay=args.delay
    )
