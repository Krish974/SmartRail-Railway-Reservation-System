import json
import time
import datetime
import re
import logging
from flask import Blueprint, request
from backend.utils.db_connection import execute_query
from backend.utils.helpers import api_response
from backend.services.railradar_service import RailRadarService
from backend.services.railway_service import RailwayService

logger = logging.getLogger(__name__)

tracking_bp = Blueprint('tracking_bp', __name__)

IST_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

DAYS_META = [
    {'abbr': 'Sun', 'full': 'Sunday'},
    {'abbr': 'Mon', 'full': 'Monday'},
    {'abbr': 'Tue', 'full': 'Tuesday'},
    {'abbr': 'Wed', 'full': 'Wednesday'},
    {'abbr': 'Thu', 'full': 'Thursday'},
    {'abbr': 'Fri', 'full': 'Friday'},
    {'abbr': 'Sat', 'full': 'Saturday'}
]

DAY_NAME_TO_INDEX = {
    'sun': 0, 'sunday': 0, 's': 0, '0': 0,
    'mon': 1, 'monday': 1, 'm': 1, '1': 1,
    'tue': 2, 'tues': 2, 'tuesday': 2, '2': 2,
    'wed': 3, 'wednesday': 3, 'w': 3, '3': 3,
    'thu': 4, 'thur': 4, 'thurs': 4, 'thursday': 4, 'th': 4, '4': 4,
    'fri': 5, 'friday': 5, 'f': 5, '5': 5,
    'sat': 6, 'saturday': 6, 'sa': 6, '6': 6,
}

def parse_running_days(val):
    """
    Parses running days string into list of weekday indices [0..6] (0=Sun, 6=Sat).
    Returns None if missing/unavailable.
    """
    if not val:
        return None
    s = str(val).strip().lower()
    if not s or s in ('none', 'null', 'n/a', '--', ''):
        return None
    if s in ('daily', 'all', 'everyday', 'all days'):
        return [0, 1, 2, 3, 4, 5, 6]
    tokens = [t.strip().lower() for t in s.replace(';', ',').split(',') if t.strip()]
    matched = set()
    for tok in tokens:
        if tok in DAY_NAME_TO_INDEX:
            matched.add(DAY_NAME_TO_INDEX[tok])
        elif tok[:3] in DAY_NAME_TO_INDEX:
            matched.add(DAY_NAME_TO_INDEX[tok[:3]])
        elif tok.isdigit() and 0 <= int(tok) <= 6:
            matched.add(int(tok))
    return sorted(list(matched)) if matched else None

def parse_time_str(time_str):
    """Parses 'HH:MM' or 'HH:MM:SS' into (hours, minutes) tuple."""
    if not time_str or not isinstance(time_str, str):
        return None
    match = re.match(r'^(\d{1,2}):(\d{2})', time_str.strip())
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        if 0 <= h < 24 and 0 <= m < 60:
            return (h, m)
    return None

def parse_duration_minutes(duration_str, dep_tuple, arr_tuple):
    """Computes total journey duration in minutes."""
    if duration_str and isinstance(duration_str, str):
        match = re.search(r'(\d+)\s*h(?:ours?)?(?:\s*(\d+)\s*m(?:in)?)?', duration_str, re.IGNORECASE)
        if match:
            h = int(match.group(1))
            m = int(match.group(2) or 0)
            return h * 60 + m
    if dep_tuple and arr_tuple:
        dep_m = dep_tuple[0] * 60 + dep_tuple[1]
        arr_m = arr_tuple[0] * 60 + arr_tuple[1]
        if arr_m >= dep_m:
            return arr_m - dep_m
        else:
            return (24 * 60 - dep_m) + arr_m
    return None

def determine_train_operating_status(train, now_ist=None):
    """
    Determines train operational status based on real IST date/time, running days,
    and scheduled journey window (including overnight & multi-day journeys).
    Returns dict with status_code, is_running, status_message, active_cycle, etc.
    """
    if now_ist is None:
        now_ist = datetime.datetime.now(IST_TZ)

    today_date = now_ist.date()
    today_day_idx = (today_date.weekday() + 1) % 7
    today_day_name = DAYS_META[today_day_idx]['full']

    raw_rd = train.get('running_days')
    running_days_indices = parse_running_days(raw_rd)
    if running_days_indices is None:
        running_days_indices = [0, 1, 2, 3, 4, 5, 6]

    dep_tuple = parse_time_str(train.get('departure_time'))
    arr_tuple = parse_time_str(train.get('arrival_time'))

    if not dep_tuple or not arr_tuple:
        return {
            'status_code': 'NOT_RUNNING_TODAY',
            'is_running': False,
            'status_message': 'Train timetable schedule unavailable',
            'active_cycle': None,
            'today_day_name': today_day_name,
            'runs_today': False
        }

    dur_minutes = parse_duration_minutes(train.get('duration'), dep_tuple, arr_tuple)
    if not dur_minutes or dur_minutes <= 0:
        dur_minutes = 120

    # Check past journey origin dates that could still be in transit
    max_days_back = max(1, (dur_minutes // 1440) + 1)
    active_cycle = None

    for days_ago in range(max_days_back, -1, -1):
        origin_date = today_date - datetime.timedelta(days=days_ago)
        origin_day_idx = (origin_date.weekday() + 1) % 7

        if origin_day_idx in running_days_indices:
            dep_dt = datetime.datetime.combine(
                origin_date,
                datetime.time(dep_tuple[0], dep_tuple[1]),
                tzinfo=IST_TZ
            )
            arr_dt = dep_dt + datetime.timedelta(minutes=dur_minutes)

            if dep_dt <= now_ist <= arr_dt:
                active_cycle = {
                    'origin_date': origin_date,
                    'dep_dt': dep_dt,
                    'arr_dt': arr_dt,
                    'dur_minutes': dur_minutes,
                    'days_ago': days_ago
                }
                break

    if active_cycle:
        dep_str = active_cycle['dep_dt'].strftime('%d %b %H:%M')
        return {
            'status_code': 'IN_WINDOW',
            'is_running': True,
            'status_message': f'Train in transit (Departed {dep_str} IST)',
            'active_cycle': active_cycle,
            'today_day_name': today_day_name,
            'runs_today': (today_day_idx in running_days_indices)
        }

    runs_today = today_day_idx in running_days_indices
    if runs_today:
        today_dep_dt = datetime.datetime.combine(
            today_date,
            datetime.time(dep_tuple[0], dep_tuple[1]),
            tzinfo=IST_TZ
        )
        today_arr_dt = today_dep_dt + datetime.timedelta(minutes=dur_minutes)

        if now_ist < today_dep_dt:
            t_str = today_dep_dt.strftime('%H:%M')
            return {
                'status_code': 'SCHEDULED_NOT_STARTED',
                'is_running': False,
                'status_message': f'Scheduled to depart today at {t_str} IST',
                'active_cycle': None,
                'today_day_name': today_day_name,
                'runs_today': True
            }
        elif now_ist > today_arr_dt:
            t_str = today_arr_dt.strftime('%H:%M')
            return {
                'status_code': 'COMPLETED',
                'is_running': False,
                'status_message': f'Journey completed today at {t_str} IST',
                'active_cycle': None,
                'today_day_name': today_day_name,
                'runs_today': True
            }

    return {
        'status_code': 'NOT_RUNNING_TODAY',
        'is_running': False,
        'status_message': f'Train is not scheduled to run today ({today_day_name})',
        'active_cycle': None,
        'today_day_name': today_day_name,
        'runs_today': False
    }

class LiveTrackingCache:
    """
    Level 4 Short-lived in-memory cache for live train running status.
    Default TTL: 120 seconds (2 minutes).
    Ensures live delays are never permanently stored as static timetables.
    """
    _cache = {}
    TTL_SECONDS = 120

    @classmethod
    def get(cls, train_number):
        key = str(train_number).strip()
        item = cls._cache.get(key)
        if item and (time.time() - item['timestamp'] < cls.TTL_SECONDS):
            return item['data']
        return None

    @classmethod
    def set(cls, train_number, data):
        key = str(train_number).strip()
        cls._cache[key] = {
            'timestamp': time.time(),
            'data': data
        }

@tracking_bp.route('/tracking/<int:train_id>', methods=['GET'])
def get_live_tracking(train_id):
    """
    Live Train Telemetry & Route Progression API.
    Combines scheduled commercial halts (train_stops) with operational non-stopping
    passing points (train_route_points) into a single ordered timeline.
    Validates operating status against current real-world IST date/time.
    """
    filter_mode = request.args.get('filter', 'all').strip().lower()

    # 1. Fetch train core info including running_days
    sql_train = """
        SELECT t.id, t.train_number, t.train_name, t.train_type, t.running_days,
               t.departure_time, t.arrival_time, t.duration,
               s1.name as source_station, s1.code as source_code,
               s2.name as dest_station, s2.code as dest_code
        FROM trains t
        JOIN stations s1 ON t.source_station_id = s1.id
        JOIN stations s2 ON t.dest_station_id = s2.id
        WHERE t.id = %s
    """
    train = execute_query(sql_train, (train_id,), fetchone=True)
    if not train:
        return api_response(False, f"Train with ID {train_id} not found.", None, 404)

    # 2. Check and eagerly ensure complete route + passing points are cached
    sql_pts_count = "SELECT count(*) as c FROM train_route_points WHERE train_id = %s"
    pts_count = execute_query(sql_pts_count, (train_id,), fetchone=True)
    c_pts = pts_count['c'] if pts_count else 0
    sql_stops_count = "SELECT count(*) as c FROM train_stops WHERE train_id = %s"
    stops_count = execute_query(sql_stops_count, (train_id,), fetchone=True)
    c_stops = stops_count['c'] if stops_count else 0

    if (c_pts < 2 or c_stops < 3) and RailRadarService.is_configured():
        clean_num = train['train_number']
        try:
            full_data = RailRadarService.fetch_train_full(clean_num)
            if full_data and len(full_data.get('stops', [])) >= 2:
                RailwayService.save_train_and_route_from_railradar(full_data)
        except Exception as e:
            logger.warning(f"Failed to fetch complete route from RailRadar for {clean_num}: {e}")

    # 3. Fetch scheduled commercial halts from train_stops
    sql_stops = """
        SELECT ts.stop_sequence, ts.arrival_time, ts.departure_time, ts.halt_minutes, ts.distance_km,
               s.id as station_id, s.code as station_code, s.name as station_name, s.city as station_city, s.state as station_state,
               s.latitude, s.longitude
        FROM train_stops ts
        JOIN stations s ON ts.station_id = s.id
        WHERE ts.train_id = %s
        ORDER BY ts.stop_sequence ASC
    """
    raw_stops = execute_query(sql_stops, (train_id,), fetchall=True) or []

    # Fallback if no stops are populated
    if not raw_stops:
        raw_stops = [
            {
                "stop_sequence": 1,
                "arrival_time": "START",
                "departure_time": train['departure_time'],
                "halt_minutes": 0,
                "distance_km": 0,
                "station_id": 1,
                "station_code": train['source_code'],
                "station_name": train['source_station'],
                "station_city": train['source_station'],
                "station_state": ""
            },
            {
                "stop_sequence": 2,
                "arrival_time": train['arrival_time'],
                "departure_time": "END",
                "halt_minutes": 0,
                "distance_km": 1000,
                "station_id": 2,
                "station_code": train['dest_code'],
                "station_name": train['dest_station'],
                "station_city": train['dest_station'],
                "station_state": ""
            }
        ]

    # 4. Fetch operational non-stopping passing points from train_route_points
    sql_points = """
        SELECT trp.id, trp.train_id, trp.station_id, trp.point_name, trp.point_code,
               trp.route_sequence, trp.point_type, trp.estimated_time, trp.distance_km,
               s.city as station_city, s.state as station_state, s.latitude, s.longitude
        FROM train_route_points trp
        LEFT JOIN stations s ON trp.station_id = s.id
        WHERE trp.train_id = %s
        ORDER BY trp.route_sequence ASC
    """
    raw_points = execute_query(sql_points, (train_id,), fetchall=True) or []

    # 5. Normalize and merge Halts and Passing Points (Zero Duplicates, Strict Route Sequence)
    combined = []
    stops_by_seq = {s['stop_sequence']: s for s in raw_stops}
    stops_by_code = {s['station_code'].upper(): s for s in raw_stops}
    used_halts = set()

    if raw_points:
        for pt in raw_points:
            pt_seq = pt['route_sequence']
            pt_code = (pt.get('point_code') or '').upper()
            st = stops_by_seq.get(pt_seq)
            if not st and pt.get('point_type') == 'HALT':
                st = stops_by_code.get(pt_code)

            if st:
                used_halts.add(st['stop_sequence'])
                combined.append({
                    "is_scheduled_halt": True,
                    "orig_sequence": pt_seq,
                    "station_id": st['station_id'],
                    "station_code": st['station_code'],
                    "station_name": st['station_name'],
                    "city": st.get('station_city', ''),
                    "state": st.get('station_state', ''),
                    "arrival_time": st['arrival_time'],
                    "departure_time": st['departure_time'],
                    "halt_minutes": int(st.get('halt_minutes') or 0),
                    "distance_km": float(st.get('distance_km') or pt.get('distance_km') or 0.0),
                    "latitude": st.get('latitude') or pt.get('latitude'),
                    "longitude": st.get('longitude') or pt.get('longitude'),
                    "estimated_time": None,
                    "is_estimated": False,
                    "raw_stop_seq": st['stop_sequence']
                })
            else:
                combined.append({
                    "is_scheduled_halt": False,
                    "orig_sequence": pt_seq,
                    "point_type": "PASSING",
                    "station_id": pt.get('station_id'),
                    "station_code": pt.get('point_code') or "--",
                    "station_name": pt['point_name'],
                    "city": pt.get('station_city') or "",
                    "state": pt.get('station_state') or "",
                    "arrival_time": None,
                    "departure_time": None,
                    "halt_minutes": 0,
                    "halt_desc": "No Halt / Pass-through",
                    "distance_km": float(pt.get('distance_km') or 0.0),
                    "latitude": pt.get('latitude'),
                    "longitude": pt.get('longitude'),
                    "estimated_time": pt['estimated_time'],
                    "is_estimated": True,
                    "raw_stop_seq": None
                })
    else:
        for idx, st in enumerate(raw_stops):
            combined.append({
                "is_scheduled_halt": True,
                "orig_sequence": st['stop_sequence'],
                "station_id": st['station_id'],
                "station_code": st['station_code'],
                "station_name": st['station_name'],
                "city": st.get('station_city', ''),
                "state": st.get('station_state', ''),
                "arrival_time": st['arrival_time'],
                "departure_time": st['departure_time'],
                "halt_minutes": int(st.get('halt_minutes') or 0),
                "distance_km": float(st.get('distance_km') or 0.0),
                "latitude": st.get('latitude'),
                "longitude": st.get('longitude'),
                "estimated_time": None,
                "is_estimated": False,
                "raw_stop_seq": st['stop_sequence']
            })

    # Append any remaining halts from raw_stops not matched in raw_points
    for st in raw_stops:
        if st['stop_sequence'] not in used_halts and raw_points:
            combined.append({
                "is_scheduled_halt": True,
                "orig_sequence": st['stop_sequence'],
                "station_id": st['station_id'],
                "station_code": st['station_code'],
                "station_name": st['station_name'],
                "city": st.get('station_city', ''),
                "state": st.get('station_state', ''),
                "arrival_time": st['arrival_time'],
                "departure_time": st['departure_time'],
                "halt_minutes": int(st.get('halt_minutes') or 0),
                "distance_km": float(st.get('distance_km') or 0.0),
                "latitude": st.get('latitude'),
                "longitude": st.get('longitude'),
                "estimated_time": None,
                "is_estimated": False,
                "raw_stop_seq": st['stop_sequence']
            })

    # Sort combined route strictly by route sequence and distance
    combined.sort(key=lambda x: (x['orig_sequence'], x['distance_km']))

    # Label halts and assign halt sequence
    num_halts = sum(1 for n in combined if n['is_scheduled_halt'])
    cur_halt_num = 0
    for item in combined:
        if item['is_scheduled_halt']:
            cur_halt_num += 1
            item['halt_sequence'] = cur_halt_num
            halt_mins = item['halt_minutes']
            if cur_halt_num == 1:
                item['point_type'] = "ORIGIN"
                item['halt_desc'] = "Journey Origin"
            elif cur_halt_num == num_halts:
                item['point_type'] = "DESTINATION"
                item['halt_desc'] = "Destination Terminus"
            else:
                item['point_type'] = "HALT"
                item['halt_desc'] = f"Halt: {halt_mins} min{'s' if halt_mins != 1 else ''}"
        else:
            item['halt_sequence'] = None

    # Assign unified strictly-increasing sequence
    for i, item in enumerate(combined):
        item['sequence'] = i + 1

    total_combined = len(combined)
    total_route_distance = float(combined[-1]['distance_km']) if combined else 0.0

    # 5. Evaluate real-world operational status using India Standard Time (IST / Asia/Kolkata)
    now_ist = datetime.datetime.now(IST_TZ)
    op_status = determine_train_operating_status(train, now_ist)

    # Check Level 4 Live Tracking Cache / RailRadar Live API
    clean_num = train['train_number']
    live_info = LiveTrackingCache.get(clean_num)
    if not live_info and RailRadarService.is_configured():
        live_info = RailRadarService.fetch_train_live(clean_num)
        if live_info:
            LiveTrackingCache.set(clean_num, live_info)

    has_live_data = bool(live_info)

    # Resolve Explicit Operational State Model:
    # NOT_RUNNING_TODAY | SCHEDULED_NOT_STARTED | RUNNING | COMPLETED | LIVE_DATA_UNAVAILABLE
    if op_status['status_code'] == 'IN_WINDOW':
        if has_live_data:
            status_code = 'RUNNING'
            is_running = True
            status_message = op_status['status_message']
        else:
            status_code = 'LIVE_DATA_UNAVAILABLE'
            is_running = False
            status_message = "Live telemetry is currently unavailable for this train."
    elif op_status['status_code'] == 'SCHEDULED_NOT_STARTED':
        status_code = 'SCHEDULED_NOT_STARTED'
        is_running = False
        status_message = op_status['status_message']
    elif op_status['status_code'] == 'COMPLETED':
        status_code = 'COMPLETED'
        is_running = False
        status_message = op_status['status_message']
    else:
        status_code = 'NOT_RUNNING_TODAY'
        is_running = False
        status_message = op_status['status_message']

    # 6. Build telemetry fields strictly based on verified operational state (No fake speed, no modulo cycling)
    if status_code == 'RUNNING':
        live_spd = live_info.get('current_speed') if live_info else None
        if live_spd is not None:
            sim_speed = float(live_spd)
            speed_display = f"{sim_speed}"
        else:
            sim_speed = None
            speed_display = "Speed unavailable"
        delay_minutes = int(live_info.get('delay_minutes', 0))
        delay_status = live_info.get('delay_status') or (f"{delay_minutes} min late" if delay_minutes > 0 else "On Time (Right Time)")

        # Anchor current position based on live verified station codes or timetable progress
        current_idx = None
        if live_info.get('current_station_code'):
            c_code = live_info['current_station_code'].upper()
            for i, node in enumerate(combined):
                if (node.get('station_code') or '').upper() == c_code:
                    current_idx = i
                    break
        if current_idx is None and live_info.get('next_station_code'):
            n_code = live_info['next_station_code'].upper()
            for i, node in enumerate(combined):
                if (node.get('station_code') or '').upper() == n_code:
                    current_idx = max(0, i - 1)
                    break
        if current_idx is None and op_status.get('active_cycle'):
            cycle = op_status['active_cycle']
            elapsed = (now_ist - cycle['dep_dt']).total_seconds()
            total_dur = (cycle['arr_dt'] - cycle['dep_dt']).total_seconds()
            ratio = max(0.0, min(1.0, elapsed / total_dur)) if total_dur > 0 else 0.0
            target_dist = ratio * total_route_distance
            best_idx = 0
            best_diff = float('inf')
            for i, n in enumerate(combined):
                d = abs(float(n.get('distance_km', 0.0)) - target_dist)
                if d < best_diff:
                    best_diff = d
                    best_idx = i
            current_idx = best_idx
        if current_idx is None:
            current_idx = 0

        current_node = combined[current_idx]
        prev_node = combined[current_idx - 1] if current_idx > 0 else None
        next_node = combined[current_idx + 1] if current_idx + 1 < total_combined else None

        # Next commercial halt
        next_halt = None
        for h in combined[current_idx + 1:]:
            if h['is_scheduled_halt']:
                next_halt = h
                break
        if not next_halt and current_idx < total_combined:
            next_halt = combined[-1]

        distance_covered = float(current_node['distance_km'])
        if total_route_distance > 0:
            pct_completed = round((distance_covered / total_route_distance) * 100, 1)
        else:
            pct_completed = round((current_idx / max(1, total_combined - 1)) * 100, 1)
        pct_completed = max(0.0, min(100.0, pct_completed))

        if current_idx == total_combined - 1:
            next_station_str = f"Destination Reached — {current_node['station_name']}"
            eta_str = "Arrived"
        elif live_info.get('next_station'):
            next_station_str = live_info['next_station']
            eta_str = live_info.get('next_eta') or "--:--"
        elif next_halt:
            next_station_str = f"{next_halt['station_name']} ({next_halt['station_code']})"
            if next_halt.get('arrival_time') and next_halt['arrival_time'] != 'START':
                eta_str = next_halt['arrival_time']
            elif next_halt.get('departure_time') and next_halt['departure_time'] != 'END':
                eta_str = next_halt['departure_time']
            else:
                eta_str = "--:--"
        else:
            next_station_str = f"Destination Reached — {current_node['station_name']}"
            eta_str = "Arrived"

        if current_node['point_type'] == 'PASSING':
            pos_mode = "PASSING_POINT"
            pos_text = f"Passing: {current_node['station_name']} ({current_node['station_code']})"
            between_from = prev_node['station_name'] if prev_node else current_node['station_name']
            between_to = next_node['station_name'] if next_node else current_node['station_name']
        elif current_idx == total_combined - 1:
            pos_mode = "AT_DESTINATION"
            pos_text = f"Arrived at Destination: {current_node['station_name']}"
            between_from = current_node['station_name']
            between_to = current_node['station_name']
        elif current_idx == 0:
            pos_mode = "AT_ORIGIN"
            pos_text = f"Origin: {current_node['station_name']} (Scheduled Dep: {current_node['departure_time']})"
            between_from = current_node['station_name']
            between_to = next_node['station_name'] if next_node else current_node['station_name']
        else:
            pos_mode = "BETWEEN_STATIONS"
            between_from = current_node['station_name']
            between_to = next_node['station_name'] if next_node else current_node['station_name']
            pos_text = f"Between {between_from} → {between_to}"

        current_position_data = {
            "mode": pos_mode,
            "current_node_index": current_idx,
            "from_station": between_from,
            "to_station": between_to,
            "status_text": pos_text,
            "speed": sim_speed
        }
        cur_station_str = live_info.get('current_station') or f"{current_node['station_name']} ({current_node['station_code']})"
        prev_station_str = f"{prev_node['station_name']} ({prev_node['station_code']})" if prev_node else "Journey Origin"

    elif status_code == 'COMPLETED':
        current_idx = total_combined - 1 if total_combined > 0 else 0
        current_node = combined[current_idx] if combined else {}
        prev_node = combined[current_idx - 1] if current_idx > 0 else None
        sim_speed = 0.0
        speed_display = "Completed"
        delay_minutes = 0
        delay_status = "Journey Completed"
        next_station_str = f"Destination Reached — {current_node.get('station_name', train['dest_station'])}"
        eta_str = "Arrived"
        distance_covered = total_route_distance
        pct_completed = 100.0
        cur_station_str = f"{train['dest_station']} ({train['dest_code']})"
        prev_station_str = f"{prev_node['station_name']} ({prev_node['station_code']})" if prev_node else "Journey Origin"
        current_position_data = {
            "mode": "AT_DESTINATION",
            "current_node_index": current_idx,
            "from_station": cur_station_str,
            "to_station": cur_station_str,
            "status_text": f"Arrived at Destination: {train['dest_station']}",
            "speed": 0.0
        }

    elif status_code == 'SCHEDULED_NOT_STARTED':
        current_idx = 0
        current_node = combined[0] if combined else {}
        next_node = combined[1] if total_combined > 1 else None
        sim_speed = None
        speed_display = "Not Started"
        delay_minutes = 0
        delay_status = "Scheduled"
        first_halt = None
        for h in combined[1:]:
            if h['is_scheduled_halt']:
                first_halt = h
                break
        next_station_str = f"{first_halt['station_name']} ({first_halt['station_code']})" if first_halt else train['dest_station']
        eta_str = f"Departs {train['departure_time']}"
        distance_covered = 0.0
        pct_completed = 0.0
        cur_station_str = f"{train['source_station']} ({train['source_code']})"
        prev_station_str = "Journey Origin"
        current_position_data = {
            "mode": "SCHEDULED",
            "current_node_index": 0,
            "from_station": cur_station_str,
            "to_station": next_station_str,
            "status_text": f"Scheduled to depart at {train['departure_time']} IST",
            "speed": None
        }

    elif status_code == 'LIVE_DATA_UNAVAILABLE':
        current_idx = None
        current_node = combined[0] if combined else {}
        prev_node = None
        next_node = None
        sim_speed = None
        speed_display = "Unavailable"
        delay_minutes = 0
        delay_status = "Live Data Unavailable"
        next_station_str = "Unavailable"
        eta_str = "Not Available"
        distance_covered = 0.0
        pct_completed = 0.0
        cur_station_str = "Live Data Unavailable"
        prev_station_str = f"{train['source_station']} ({train['source_code']})"
        current_position_data = {
            "mode": "UNAVAILABLE",
            "current_node_index": None,
            "from_station": f"{train['source_station']} ({train['source_code']})",
            "to_station": f"{train['dest_station']} ({train['dest_code']})",
            "status_text": "Live telemetry is currently unavailable for this train.",
            "speed": None
        }

    else:  # 'NOT_RUNNING_TODAY'
        current_idx = None
        current_node = combined[0] if combined else {}
        prev_node = None
        next_node = None
        sim_speed = None
        speed_display = "Not Running"
        delay_minutes = 0
        delay_status = "Not Running Today"
        next_station_str = "Not Available"
        eta_str = "Not Available"
        distance_covered = 0.0
        pct_completed = 0.0
        cur_station_str = "Not Running Today"
        prev_station_str = f"{train['source_station']} ({train['source_code']})"
        current_position_data = {
            "mode": "NOT_RUNNING",
            "current_node_index": None,
            "from_station": f"{train['source_station']} ({train['source_code']})",
            "to_station": f"{train['dest_station']} ({train['dest_code']})",
            "status_text": op_status['status_message'],
            "speed": None
        }

    # 7. Enrich all nodes with status and labels based on operating status
    enriched_nodes = []
    for idx, node in enumerate(combined):
        if status_code == 'RUNNING':
            if idx < current_idx:
                node_status = "COMPLETED"
                node_status_label = "Passed" if node['point_type'] == 'PASSING' else "Departed"
                passing_label = f"Passed at {node['estimated_time']}" if node['estimated_time'] else "Passed (No Halt)"
            elif idx == current_idx:
                node_status = "CURRENT"
                node_status_label = "Current Location"
                passing_label = f"Passing now (~{node['estimated_time']})" if node['estimated_time'] else "Passing now (No Halt)"
            else:
                node_status = "UPCOMING"
                node_status_label = "Upcoming"
                passing_label = f"Est. Passing: {node['estimated_time']}" if node['estimated_time'] else "No Halt / Pass-through"
            is_node_current = (idx == current_idx)
        elif status_code == 'COMPLETED':
            node_status = "COMPLETED"
            node_status_label = "Departed" if idx < total_combined - 1 else "Arrived"
            if node['point_type'] == 'PASSING':
                passing_label = f"Passed: {node['estimated_time']}" if node['estimated_time'] else "Passed (No Halt)"
            elif node['point_type'] == 'DESTINATION':
                passing_label = f"Arrived: {node['arrival_time']}"
            else:
                passing_label = f"Departed: {node['departure_time']}"
            is_node_current = False
        else:  # NOT_RUNNING_TODAY, SCHEDULED_NOT_STARTED, LIVE_DATA_UNAVAILABLE
            node_status = "UPCOMING"
            node_status_label = "Scheduled"
            if node['point_type'] == 'PASSING':
                passing_label = f"Pass-through: {node['estimated_time']}" if node['estimated_time'] else "No Halt / Pass-through"
            elif node['point_type'] == 'ORIGIN':
                passing_label = f"Origin Dep: {node['departure_time']}"
            elif node['point_type'] == 'DESTINATION':
                passing_label = f"Destination Arr: {node['arrival_time']}"
            else:
                passing_label = f"Arr: {node['arrival_time']} | Dep: {node['departure_time']}"
            is_node_current = False

        enriched_nodes.append({
            "sequence": node['sequence'],
            "halt_sequence": node['halt_sequence'],
            "is_scheduled_halt": node['is_scheduled_halt'],
            "point_type": node['point_type'],
            "station_id": node['station_id'],
            "station_code": node['station_code'],
            "station_name": node['station_name'],
            "city": node['city'],
            "state": node['state'],
            "arrival_time": node['arrival_time'],
            "departure_time": node['departure_time'],
            "halt_minutes": node['halt_minutes'],
            "halt_desc": node['halt_desc'],
            "distance_km": node['distance_km'],
            "estimated_time": node['estimated_time'],
            "is_estimated": node['is_estimated'],
            "passing_label": passing_label,
            "status": node_status,
            "status_label": node_status_label,
            "is_current": is_node_current
        })

    # 8. Build Level 1 Halts and Level 2 Inter-Halt Sections strictly by sequence
    halts = [n for n in enriched_nodes if n['is_scheduled_halt']]
    sections = []
    for k in range(len(halts) - 1):
        h_from = halts[k]
        h_to = halts[k + 1]
        sec_pts = [
            n for n in enriched_nodes
            if not n['is_scheduled_halt'] and (h_from['sequence'] < n['sequence'] < h_to['sequence'])
        ]

        # Determine if train is actively in this leg:
        # only active when train is in verified RUNNING status
        is_cur_sec = False
        if status_code == 'RUNNING' and current_node:
            if current_node['sequence'] == h_from['sequence'] and current_idx < total_combined - 1:
                is_cur_sec = True
            elif h_from['sequence'] < current_node['sequence'] < h_to['sequence']:
                is_cur_sec = True

        sections.append({
            "section_id": f"sec-{k}-{k+1}",
            "section_index": k,
            "from_station_code": h_from['station_code'],
            "from_station_name": h_from['station_name'],
            "to_station_code": h_to['station_code'],
            "to_station_name": h_to['station_name'],
            "section_title": f"{h_from['station_name']} ➔ {h_to['station_name']}",
            "distance_km": round(h_to['distance_km'] - h_from['distance_km'], 1),
            "intermediate_count": len(sec_pts),
            "intermediate_points": sec_pts,
            "is_current_section": is_cur_sec
        })

    # Apply filter if requested
    if filter_mode == 'halts':
        final_stops = halts
    else:
        final_stops = enriched_nodes

    return api_response(True, "Live tracking telemetry retrieved.", {
        "train_id": train['id'],
        "train_number": train['train_number'],
        "train_name": train['train_name'],
        "train_type": train['train_type'],
        "running_days": train.get('running_days'),
        "source": f"{train['source_station']} ({train['source_code']})",
        "destination": f"{train['dest_station']} ({train['dest_code']})",
        "departure_time": train.get('departure_time'),
        "arrival_time": train.get('arrival_time'),
        "duration": train.get('duration'),
        "status_code": status_code,
        "status_message": status_message,
        "is_running": is_running,
        "speed_display": speed_display,
        "latitude": current_node.get('latitude', 28.6427) if current_node else 28.6427,
        "longitude": current_node.get('longitude', 77.2197) if current_node else 77.2197,
        "current_speed": sim_speed,
        "delay_minutes": delay_minutes,
        "delay_status": delay_status,
        "previous_station": prev_station_str,
        "current_station": cur_station_str,
        "next_station": next_station_str,
        "eta": eta_str,
        "distance_travelled_km": distance_covered,
        "total_distance_km": total_route_distance,
        "percentage_completed": pct_completed,
        "current_stop_sequence": current_node.get('sequence') if (is_running and current_node) else None,
        "current_stop_index": current_idx if is_running else None,
        "current_position": current_position_data,
        "total_halts": num_halts,
        "total_passing_points": len(enriched_nodes) - len(halts),
        "total_stops": len(final_stops),
        "filter": filter_mode,
        "is_live_data": has_live_data,
        "running_status": live_info['running_status'] if has_live_data else ('In Transit' if is_running else status_code),
        "platform": live_info.get('platform') if has_live_data else None,
        "halts": halts,
        "sections": sections,
        "stops": final_stops
    })


