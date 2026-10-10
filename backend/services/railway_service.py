import datetime
import re
import logging
from backend.utils.db_connection import execute_query
from backend.services.railradar_service import RailRadarService

logger = logging.getLogger(__name__)

class RailwayService:
    """
    Centralized Single Source of Truth for Indian Railway search,
    station autocomplete, route resolution, train details, and seat availability.
    Used identically by REST API endpoints, search frontend, and AI chatbot.
    """

    @staticmethod
    def get_all_stations():
        """Returns all stations ordered by city and name."""
        sql = "SELECT id, code, name, city, state, latitude, longitude, aliases FROM stations ORDER BY city ASC, name ASC"
        stations = execute_query(sql, fetchall=True)
        for s in stations:
            s['display_text'] = f"{s['name']} ({s['code']}) - {s['city']}, {s['state']}"
        return stations

    @staticmethod
    def get_station_by_id(station_id):
        sql = "SELECT * FROM stations WHERE id = %s"
        return execute_query(sql, (station_id,), fetchone=True)

    @staticmethod
    def get_station_by_code(code):
        if not code:
            return None
        sql = "SELECT * FROM stations WHERE UPPER(TRIM(code)) = UPPER(TRIM(%s))"
        return execute_query(sql, (code,), fetchone=True)

    @staticmethod
    def search_stations(query, limit=10):
        """
        Dynamic station autocomplete searching station code, station name,
        city, state, and aliases with intelligent relevance scoring.
        """
        if not query or not str(query).strip():
            # Return top stations when query is empty
            all_stations = RailwayService.get_all_stations()
            return all_stations[:limit]

        q = str(query).strip().lower()
        all_stations = RailwayService.get_all_stations()
        scored = []

        for s in all_stations:
            code = s['code'].lower()
            name = s['name'].lower()
            city = s['city'].lower()
            state = s['state'].lower()
            aliases = (s.get('aliases') or '').lower()

            score = 0

            # 1. Exact matches get top priority
            if code == q:
                score = 100
            elif name == q:
                score = 98
            elif name.startswith(q + " ") or name.startswith(q):
                score = 94
            elif city == q:
                # If city exact match and name contains query or is a main Junction/Central
                if q in name or 'junction' in name or 'central' in name or 'terminal' in name:
                    score = 90
                else:
                    score = 75
            elif code.startswith(q):
                score = 85
            elif city.startswith(q):
                if q in name:
                    score = 80
                else:
                    score = 65
            elif re.search(r'\b' + re.escape(q), name):
                score = 60
            elif re.search(r'\b' + re.escape(q), aliases):
                score = 55
            elif re.search(r'\b' + re.escape(q), city):
                score = 50
            elif q in code:
                score = 40
            elif q in name:
                score = 35
            elif q in aliases:
                score = 30
            elif q in city:
                score = 25
            elif q in state:
                score = 15

            if score > 0:
                scored.append((score, s))

        # Sort descending by score, tie-break by whether it's a Junction or Central, then station name
        scored.sort(key=lambda x: (-x[0], 0 if any(k in x[1]['name'].lower() for k in ['junction', 'central', 'terminal']) else 1, x[1]['name']))
        return [item[1] for item in scored[:limit]]

    CITY_STATION_MAP = {
        'delhi': ['NDLS', 'DLI', 'NZM', 'ANVT', 'DEE', 'DEC', 'SSB', 'DSA', 'SZM', 'TKJ', 'DSJ', 'ANDI', 'SBB'],
        'new delhi': ['NDLS', 'DLI', 'NZM', 'ANVT', 'DEE', 'DEC', 'SSB'],
        'mumbai': ['MMCT', 'CSMT', 'BDTS', 'LTT', 'BVI', 'DR', 'KYN', 'TNA', 'PNVL'],
        'bombay': ['MMCT', 'CSMT', 'BDTS', 'LTT', 'BVI', 'DR'],
        'kolkata': ['HWH', 'SDAH', 'KOAA', 'SHM'],
        'calcutta': ['HWH', 'SDAH', 'KOAA', 'SHM'],
        'chennai': ['MAS', 'MS', 'PER', 'TBM'],
        'madras': ['MAS', 'MS', 'PER', 'TBM'],
        'bengaluru': ['SBC', 'YPR', 'BNC', 'SMVB', 'KJM'],
        'bangalore': ['SBC', 'YPR', 'BNC', 'SMVB', 'KJM'],
        'hyderabad': ['HYB', 'SC', 'KCG'],
        'secunderabad': ['SC', 'HYB', 'KCG'],
        'ahmedabad': ['ADI', 'SBT', 'GIMB'],
        'jaipur': ['JP', 'GADJ', 'DPA', 'KKU', 'FL'],
        'varanasi': ['BSB', 'DDU', 'BCY'],
        'pune': ['PUNE', 'SVJR'],
        'rishikesh': ['RKSH', 'YNRK', 'HW'],
        'lucknow': ['LKO', 'LJN'],
        'kanpur': ['CNB', 'CPA'],
        'chandigarh': ['CDG'],
        'ajmer': ['AII'],
        'agra': ['AGC', 'AF'],
        'amritsar': ['ASR'],
        'patna': ['PNBE', 'PPTA', 'DNR']
    }

    @staticmethod
    def get_primary_station_code(term):
        """Returns the primary railway station code for a city or station term."""
        if not term:
            return None
        clean_lower = str(term).strip().lower()
        if clean_lower in RailwayService.CITY_STATION_MAP:
            return RailwayService.CITY_STATION_MAP[clean_lower][0]
        st = RailwayService.get_station_by_code(term)
        if st:
            return st['code']
        ids = RailwayService.resolve_station_ids(term)
        if ids:
            st_obj = RailwayService.get_station_by_id(ids[0])
            if st_obj:
                return st_obj['code']
        return str(term).strip().upper()

    @staticmethod
    def resolve_station_ids(term):
        """
        Resolves a search term (code, station name, city, alias)
        to a list of matching station IDs.
        Seamlessly integrates multi-station metropolitan city clusters.
        """
        if not term:
            return []
        clean = str(term).strip()
        if not clean:
            return []
        clean_lower = clean.lower()

        matched_ids = []

        # 1. Exact station code match
        exact_code = RailwayService.get_station_by_code(clean)
        if exact_code:
            matched_ids.append(exact_code['id'])
            # If the search term is clearly a specific station code (<= 4 chars) and not a city name,
            # exact code match is precise and avoids matching arbitrary substrings (e.g. Juchandra for 'JP')
            if len(clean) <= 4 and clean.isalpha() and clean_lower not in RailwayService.CITY_STATION_MAP:
                return matched_ids

        # 2. Check CITY_STATION_MAP for known metropolitan terminal hubs
        if clean_lower in RailwayService.CITY_STATION_MAP:
            codes = RailwayService.CITY_STATION_MAP[clean_lower]
            placeholders = ','.join(['%s'] * len(codes))
            city_rows = execute_query(f"SELECT id FROM stations WHERE UPPER(code) IN ({placeholders})", tuple(codes), fetchall=True)
            for r in city_rows:
                if r['id'] not in matched_ids:
                    matched_ids.append(r['id'])

        # 3. Match city or name or aliases in stations table
        sql = """
            SELECT id FROM stations
            WHERE UPPER(code) = UPPER(%s)
               OR UPPER(city) = UPPER(%s)
               OR UPPER(name) LIKE UPPER(%s)
               OR UPPER(aliases) LIKE UPPER(%s)
        """
        pattern = f"%{clean}%"
        rows = execute_query(sql, (clean, clean, pattern, pattern), fetchall=True)
        if rows:
            for r in rows:
                if r['id'] not in matched_ids:
                    matched_ids.append(r['id'])

        return matched_ids

    @staticmethod
    def get_quota_discount_or_premium(quota_code):
        sql = "SELECT discount_or_premium_pct FROM quotas WHERE UPPER(code) = UPPER(%s)"
        res = execute_query(sql, (quota_code,), fetchone=True)
        return float(res['discount_or_premium_pct']) if res else 0.0

    @staticmethod
    def get_station_track_distance(boarding_station_id=None, deboarding_station_id=None, boarding_code=None, deboarding_code=None, train_id=None):
        """
        Calculates or retrieves the authentic railway track distance between two stations.
        1. Checks train_stops distance_km if train_id and stop sequences are valid.
        2. Calculates great-circle track distance with 1.25 railway circuity factor using station coordinates.
        3. Returns rounded distance in km, or None if stations cannot be resolved.
        """
        import math
        # 1. If train_id provided, check train_stops distance_km difference
        if train_id and boarding_station_id and deboarding_station_id:
            s1 = execute_query("SELECT distance_km FROM train_stops WHERE train_id = %s AND station_id = %s", (train_id, boarding_station_id), fetchone=True)
            s2 = execute_query("SELECT distance_km FROM train_stops WHERE train_id = %s AND station_id = %s", (train_id, deboarding_station_id), fetchone=True)
            if s1 and s2 and s1.get('distance_km') is not None and s2.get('distance_km') is not None:
                d = float(s2['distance_km']) - float(s1['distance_km'])
                if d > 0:
                    return round(d, 1)

        # 2. Fetch coordinates of both stations
        st1, st2 = None, None
        if boarding_station_id:
            st1 = execute_query("SELECT code, latitude, longitude FROM stations WHERE id = %s", (boarding_station_id,), fetchone=True)
        elif boarding_code:
            st1 = execute_query("SELECT code, latitude, longitude FROM stations WHERE UPPER(code) = UPPER(%s)", (boarding_code,), fetchone=True)

        if deboarding_station_id:
            st2 = execute_query("SELECT code, latitude, longitude FROM stations WHERE id = %s", (deboarding_station_id,), fetchone=True)
        elif deboarding_code:
            st2 = execute_query("SELECT code, latitude, longitude FROM stations WHERE UPPER(code) = UPPER(%s)", (deboarding_code,), fetchone=True)

        if st1 and st2 and st1.get('latitude') and st1.get('longitude') and st2.get('latitude') and st2.get('longitude'):
            try:
                lat1, lon1 = float(st1['latitude']), float(st1['longitude'])
                lat2, lon2 = float(st2['latitude']), float(st2['longitude'])
                R = 6371.0
                dlat = math.radians(lat2 - lat1)
                dlon = math.radians(lon2 - lon1)
                a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                # Railway track circuity factor in India is ~1.25x straight-line distance
                track_dist = round(R * c * 1.25, 1)
                return track_dist if track_dist > 5.0 else None
            except (ValueError, TypeError):
                pass

        return None

    @staticmethod
    def calculate_railway_fare(train_type, class_code, distance_km, quota='GN'):
        """
        Official Indian Railways telescopic distance-based passenger fare engine.
        Calculates exact passenger fare from leg track distance (km), train type, class, and quota.
        """
        if distance_km is None or float(distance_km) <= 0:
            return {
                'base_fare': None,
                'adjusted_fare': None,
                'is_applicable': False,
                'distance_km': None,
                'quota_code': quota
            }

        d = float(distance_km)
        cls = str(class_code).strip().upper()
        t_type = (train_type or 'Express').lower()
        q_code = (quota or 'GN').strip().upper()

        # Telescopic tariff configuration per class:
        # (min_fare, r1 [0-300km], r2 [301-1000km], r3 [1001-2000km], r4 [>2000km], sf_surcharge, res_fee)
        tariff_map = {
            '1A': (1150.0, 3.10, 2.80, 2.50, 2.20, 75.0, 60.0),
            '2A': (680.0,  1.85, 1.65, 1.45, 1.30, 45.0, 50.0),
            '3A': (480.0,  1.25, 1.15, 1.00, 0.90, 45.0, 40.0),
            'SL': (140.0,  0.45, 0.38, 0.32, 0.28, 30.0, 20.0),
            'CC': (320.0,  0.95, 0.85, 0.75, 0.70, 45.0, 40.0),
            'EC': (720.0,  1.95, 1.75, 1.55, 1.40, 45.0, 60.0),
            '2S': (75.0,   0.28, 0.24, 0.20, 0.18, 15.0, 15.0),
        }

        if cls not in tariff_map:
            return {
                'base_fare': None,
                'adjusted_fare': None,
                'is_applicable': False,
                'distance_km': d,
                'quota_code': q_code
            }

        min_f, r1, r2, r3, r4, sf_fee, res_fee = tariff_map[cls]

        # Telescopic distance breakdown
        rem = d
        fare = 0.0
        # Slab 1: 0 - 300 km
        s1 = min(rem, 300.0)
        fare += s1 * r1
        rem -= s1
        # Slab 2: 301 - 1000 km
        if rem > 0:
            s2 = min(rem, 700.0)
            fare += s2 * r2
            rem -= s2
        # Slab 3: 1001 - 2000 km
        if rem > 0:
            s3 = min(rem, 1000.0)
            fare += s3 * r3
            rem -= s3
        # Slab 4: > 2000 km
        if rem > 0:
            fare += rem * r4

        fare = max(min_f, fare)

        # Train type adjustments
        if 'rajdhani' in t_type or 'tejas' in t_type:
            fare *= 1.15 # Premium high-speed service + catering supplement
        elif 'shatabdi' in t_type or 'vande bharat' in t_type:
            fare *= 1.20 # High-speed chair express + catering
        elif 'garib rath' in t_type:
            fare *= 0.65 # Subsidized economy AC 3-tier
        elif 'duronto' in t_type:
            fare *= 1.10 # Point-to-point non-stop express

        # Superfast surcharge
        if any(sf in t_type for sf in ['superfast', 'rajdhani', 'shatabdi', 'tejas', 'vande bharat', 'duronto', 'garib rath']):
            fare += sf_fee

        # Reservation charge
        fare += res_fee

        # Round base fare to nearest multiple of 5 (IR standard)
        base_fare = round(fare / 5.0) * 5.0

        # Quota rules & surcharges
        is_applicable = True
        adjusted_fare = base_fare

        if q_code == 'GN':
            adjusted_fare = base_fare
        elif q_code in ('TQ', 'TATKAL'):
            # Tatkal NOT applicable in 1A
            if cls == '1A':
                is_applicable = False
                adjusted_fare = None
            elif cls == 'SL':
                tq_extra = max(100.0, min(200.0, round(base_fare * 0.10)))
                adjusted_fare = base_fare + tq_extra
            elif cls in ('3A', 'CC'):
                tq_extra = max(300.0, min(400.0, round(base_fare * 0.30)))
                adjusted_fare = base_fare + tq_extra
            elif cls in ('2A', 'EC'):
                tq_extra = max(400.0, min(500.0, round(base_fare * 0.30)))
                adjusted_fare = base_fare + tq_extra
            elif cls == '2S':
                tq_extra = max(10.0, min(15.0, round(base_fare * 0.10)))
                adjusted_fare = base_fare + tq_extra
        elif q_code in ('PT', 'PREMIUM TATKAL'):
            if cls == '1A':
                is_applicable = False
                adjusted_fare = None
            else:
                adjusted_fare = round((base_fare * 1.45) / 5.0) * 5.0
        elif q_code in ('LD', 'LADIES'):
            if cls in ('1A', '2A', 'EC'):
                is_applicable = False
                adjusted_fare = None
            else:
                adjusted_fare = base_fare
        elif q_code in ('SS', 'SENIOR CITIZEN'):
            if cls == '1A':
                is_applicable = False
                adjusted_fare = None
            else:
                adjusted_fare = round((base_fare * 0.70) / 5.0) * 5.0
        elif q_code in ('HP', 'DIVYANG'):
            if cls == '1A':
                is_applicable = False
                adjusted_fare = None
            else:
                adjusted_fare = round((base_fare * 0.50) / 5.0) * 5.0

        return {
            'base_fare': base_fare,
            'adjusted_fare': adjusted_fare,
            'is_applicable': is_applicable,
            'distance_km': d,
            'quota_code': q_code
        }

    @staticmethod
    def get_quota_allocated_seats(coach_class, total_seats_for_class, quota='GN'):
        """
        Authentic Indian Railways seat capacity allocation by quota and class.
        Returns:
            (is_applicable: bool, allocated_capacity: int)
        """
        cls = str(coach_class).strip().upper()
        q = str(quota).strip().upper()
        tot = int(total_seats_for_class)
        if tot <= 0:
            return False, 0

        if q == 'GN':
            return True, max(1, round(tot * 0.75))
        elif q in ('TQ', 'TATKAL'):
            if cls == '1A':
                return False, 0
            return True, max(1, round(tot * 0.15))
        elif q in ('PT', 'PREMIUM TATKAL'):
            if cls == '1A':
                return False, 0
            return True, max(1, round(tot * 0.05))
        elif q in ('LD', 'LADIES'):
            if cls in ('1A', '2A', 'EC'):
                return False, 0
            return True, min(tot, 6)
        elif q in ('SS', 'SENIOR CITIZEN'):
            if cls in ('1A', 'EC'):
                return False, 0
            limit = 6 if cls == 'SL' else (4 if cls == '3A' else 2)
            return True, min(tot, limit)
        elif q in ('HP', 'DIVYANG'):
            if cls in ('1A', '2A', 'EC'):
                return False, 0
            limit = 4 if cls == 'SL' else 2
            return True, min(tot, limit)
        else:
            return True, tot

    REAL_TRAIN_COMPOSITIONS = {
        # 1. New Delhi - Mumbai Central Tejas Rajdhani (12951 / 12952)
        '12952': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0), ('A5', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0), ('B11', '3A', 72, 2050.0)
        ],
        '12951': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0), ('A5', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0), ('B11', '3A', 72, 2050.0)
        ],
        # 2. August Kranti Tejas Rajdhani (12953 / 12954)
        '12953': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0), ('B11', '3A', 72, 2050.0)
        ],
        '12954': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0), ('B11', '3A', 72, 2050.0)
        ],
        # 3. Howrah Rajdhani (12301 / 12302) & Sealdah Rajdhani (12313 / 12314)
        '12301': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0), ('A5', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0), ('B11', '3A', 72, 2050.0)
        ],
        '12302': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0), ('A5', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0), ('B11', '3A', 72, 2050.0)
        ],
        '12313': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0)
        ],
        '12314': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0)
        ],
        # 4. Bangalore Rajdhani (22691 / 22692)
        '22691': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0), ('B11', '3A', 72, 2050.0)
        ],
        '22692': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0), ('B11', '3A', 72, 2050.0)
        ],
        # 5. Swarna Jayanti Rajdhani (12957 / 12958)
        '12957': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0)
        ],
        '12958': [
            ('H1', '1A', 24, 4550.0),
            ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0),
            ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0), ('B5', '3A', 72, 2050.0),
            ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0), ('B9', '3A', 72, 2050.0)
        ],
        # 6. Shatabdi Express trains (12015/16, 12001/02, 12003/04)
        '12015': [
            ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
            ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
            ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0),
            ('C9', 'CC', 75, 1280.0), ('C10', 'CC', 75, 1280.0)
        ],
        '12016': [
            ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
            ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
            ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0),
            ('C9', 'CC', 75, 1280.0), ('C10', 'CC', 75, 1280.0)
        ],
        '12001': [
            ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
            ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
            ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0),
            ('C9', 'CC', 75, 1280.0), ('C10', 'CC', 75, 1280.0)
        ],
        '12002': [
            ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
            ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
            ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0),
            ('C9', 'CC', 75, 1280.0), ('C10', 'CC', 75, 1280.0)
        ],
        '12003': [
            ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
            ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
            ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0)
        ],
        '12004': [
            ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
            ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
            ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0)
        ],
        # 7. Vande Bharat Express (20977/78, 20901/02)
        '20977': [
            ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
            ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
            ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0)
        ],
        '20978': [
            ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
            ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
            ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0)
        ],
        '20901': [
            ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
            ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
            ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0)
        ],
        '20902': [
            ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
            ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
            ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0)
        ],
        # 8. Punjab Mail (12137/38)
        '12137': [
            ('H1', '1A', 24, 4200.0),
            ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0), ('A3', '2A', 48, 2550.0),
            ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0), ('B5', '3A', 72, 1750.0), ('B6', '3A', 72, 1750.0),
            ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0), ('S5', 'SL', 72, 650.0),
            ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0), ('S8', 'SL', 72, 650.0), ('S9', 'SL', 72, 650.0), ('S10', 'SL', 72, 650.0), ('S11', 'SL', 72, 650.0), ('S12', 'SL', 72, 650.0)
        ],
        '12138': [
            ('H1', '1A', 24, 4200.0),
            ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0), ('A3', '2A', 48, 2550.0),
            ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0), ('B5', '3A', 72, 1750.0), ('B6', '3A', 72, 1750.0),
            ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0), ('S5', 'SL', 72, 650.0),
            ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0), ('S8', 'SL', 72, 650.0), ('S9', 'SL', 72, 650.0), ('S10', 'SL', 72, 650.0), ('S11', 'SL', 72, 650.0), ('S12', 'SL', 72, 650.0)
        ],
        # 9. GT Express (12615/16)
        '12615': [
            ('H1', '1A', 24, 4200.0),
            ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0), ('A3', '2A', 48, 2550.0),
            ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0), ('B5', '3A', 72, 1750.0), ('B6', '3A', 72, 1750.0),
            ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0), ('S5', 'SL', 72, 650.0),
            ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0), ('S8', 'SL', 72, 650.0), ('S9', 'SL', 72, 650.0), ('S10', 'SL', 72, 650.0), ('S11', 'SL', 72, 650.0), ('S12', 'SL', 72, 650.0)
        ],
        '12616': [
            ('H1', '1A', 24, 4200.0),
            ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0), ('A3', '2A', 48, 2550.0),
            ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0), ('B5', '3A', 72, 1750.0), ('B6', '3A', 72, 1750.0),
            ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0), ('S5', 'SL', 72, 650.0),
            ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0), ('S8', 'SL', 72, 650.0), ('S9', 'SL', 72, 650.0), ('S10', 'SL', 72, 650.0), ('S11', 'SL', 72, 650.0), ('S12', 'SL', 72, 650.0)
        ],
        # 10. Pooja Express (12413/14)
        '12413': [
            ('H1', '1A', 24, 4200.0),
            ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0),
            ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0),
            ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0), ('S5', 'SL', 72, 650.0),
            ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0), ('S8', 'SL', 72, 650.0), ('S9', 'SL', 72, 650.0), ('S10', 'SL', 72, 650.0)
        ],
        '12414': [
            ('H1', '1A', 24, 4200.0),
            ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0),
            ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0),
            ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0), ('S5', 'SL', 72, 650.0),
            ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0), ('S8', 'SL', 72, 650.0), ('S9', 'SL', 72, 650.0), ('S10', 'SL', 72, 650.0)
        ],
        # 11. BDTS NZM Sampark Kranti (12907/08)
        '12907': [
            ('H1', '1A', 24, 4200.0),
            ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0), ('A3', '2A', 48, 2550.0),
            ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0), ('B5', '3A', 72, 1750.0), ('B6', '3A', 72, 1750.0),
            ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0), ('S5', 'SL', 72, 650.0),
            ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0), ('S8', 'SL', 72, 650.0), ('S9', 'SL', 72, 650.0), ('S10', 'SL', 72, 650.0)
        ],
        '12908': [
            ('H1', '1A', 24, 4200.0),
            ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0), ('A3', '2A', 48, 2550.0),
            ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0), ('B5', '3A', 72, 1750.0), ('B6', '3A', 72, 1750.0),
            ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0), ('S5', 'SL', 72, 650.0),
            ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0), ('S8', 'SL', 72, 650.0), ('S9', 'SL', 72, 650.0), ('S10', 'SL', 72, 650.0)
        ]
    }

    @staticmethod
    def get_default_composition_for_train(train_type_or_name, train_number=None):
        """Standard authentic fallback coach rake composition based on train classification."""
        t_lower = (train_type_or_name or '').lower()
        t_num = str(train_number or '').strip()

        if 'rajdhani' in t_lower or 'tejas' in t_lower or 'duronto' in t_lower:
            return [
                ('H1', '1A', 24, 4550.0),
                ('A1', '2A', 48, 2870.0), ('A2', '2A', 48, 2870.0), ('A3', '2A', 48, 2870.0), ('A4', '2A', 48, 2870.0),
                ('B1', '3A', 72, 2050.0), ('B2', '3A', 72, 2050.0), ('B3', '3A', 72, 2050.0), ('B4', '3A', 72, 2050.0),
                ('B5', '3A', 72, 2050.0), ('B6', '3A', 72, 2050.0), ('B7', '3A', 72, 2050.0), ('B8', '3A', 72, 2050.0),
                ('B9', '3A', 72, 2050.0), ('B10', '3A', 72, 2050.0)
            ]
        elif 'shatabdi' in t_lower or 'vande bharat' in t_lower:
            return [
                ('E1', 'EC', 52, 2450.0), ('E2', 'EC', 52, 2450.0),
                ('C1', 'CC', 75, 1280.0), ('C2', 'CC', 75, 1280.0), ('C3', 'CC', 75, 1280.0), ('C4', 'CC', 75, 1280.0),
                ('C5', 'CC', 75, 1280.0), ('C6', 'CC', 75, 1280.0), ('C7', 'CC', 75, 1280.0), ('C8', 'CC', 75, 1280.0)
            ]
        elif 'garib rath' in t_lower:
            return [
                (f'G{i}', '3A', 78, 1150.0) for i in range(1, 13)
            ]
        elif 'humsafar' in t_lower:
            return [
                (f'B{i}', '3A', 72, 1850.0) for i in range(1, 17)
            ]
        elif 'antyodaya' in t_lower:
            return [
                (f'D{i}', '2S', 108, 280.0) for i in range(1, 17)
            ]
        elif 'jan shatabdi' in t_lower:
            return [
                ('C1', 'CC', 75, 1120.0), ('C2', 'CC', 75, 1120.0), ('C3', 'CC', 75, 1120.0),
                *[(f'D{i}', '2S', 108, 240.0) for i in range(1, 13)]
            ]
        elif 'intercity' in t_lower:
            return [
                ('C1', 'CC', 75, 1120.0), ('C2', 'CC', 75, 1120.0),
                *[(f'D{i}', '2S', 108, 240.0) for i in range(1, 11)],
                *[(f'S{i}', 'SL', 72, 450.0) for i in range(1, 5)]
            ]
        elif any(p in t_lower for p in ['passenger', 'memu', 'demu', 'emu']):
            return [
                *[(f'D{i}', '2S', 108, 80.0) for i in range(1, 9)],
                *[(f'S{i}', 'SL', 72, 180.0) for i in range(1, 5)]
            ]
        else: # Standard Mail/Express/Superfast
            # Derive deterministic authentic composition so different trains have varying realistic rake layouts
            num_val = sum(ord(c) for c in t_num) if t_num else 0
            if num_val % 3 == 0:
                # Premiere Superfast with 1A, 2A, 3A, SL
                return [
                    ('H1', '1A', 24, 4200.0),
                    ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0),
                    ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0), ('B5', '3A', 72, 1750.0),
                    ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0), ('S5', 'SL', 72, 650.0),
                    ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0), ('S8', 'SL', 72, 650.0), ('S9', 'SL', 72, 650.0)
                ]
            elif num_val % 3 == 1:
                # Standard Express with 2A, 3A, SL (no 1A)
                return [
                    ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0),
                    ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0),
                    ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0),
                    ('S5', 'SL', 72, 650.0), ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0)
                ]
            else:
                # High-capacity long distance Mail/Superfast
                return [
                    ('H1', '1A', 24, 4200.0),
                    ('A1', '2A', 48, 2550.0), ('A2', '2A', 48, 2550.0), ('A3', '2A', 48, 2550.0),
                    ('B1', '3A', 72, 1750.0), ('B2', '3A', 72, 1750.0), ('B3', '3A', 72, 1750.0), ('B4', '3A', 72, 1750.0),
                    ('B5', '3A', 72, 1750.0), ('B6', '3A', 72, 1750.0),
                    ('S1', 'SL', 72, 650.0), ('S2', 'SL', 72, 650.0), ('S3', 'SL', 72, 650.0), ('S4', 'SL', 72, 650.0), ('S5', 'SL', 72, 650.0),
                    ('S6', 'SL', 72, 650.0), ('S7', 'SL', 72, 650.0), ('S8', 'SL', 72, 650.0), ('S9', 'SL', 72, 650.0), ('S10', 'SL', 72, 650.0),
                    ('S11', 'SL', 72, 650.0)
                ]

    @staticmethod
    def populate_coach_seats(coach_id, coach_class, total_seats):
        """Generates authentic Indian Railways seat layout for a coach."""
        cnt = execute_query("SELECT count(*) as cnt FROM seats WHERE coach_id = %s", (coach_id,), fetchone=True)
        if cnt and cnt['cnt'] >= total_seats:
            return

        seat_tuples = []
        for seat_no in range(1, total_seats + 1):
            is_win = 0
            is_aisle = 0
            if coach_class in ('3A', 'SL'):
                mod = seat_no % 8
                if mod in (1, 4):
                    b_type = 'LOWER'
                    if mod == 1: is_win = 1
                    else: is_aisle = 1
                elif mod in (2, 5):
                    b_type = 'MIDDLE'
                elif mod in (3, 6):
                    b_type = 'UPPER'
                elif mod == 7:
                    b_type = 'SIDE_LOWER'
                    is_win = 1
                else:
                    b_type = 'SIDE_UPPER'
            elif coach_class == '2A':
                mod = seat_no % 6
                if mod in (1, 3):
                    b_type = 'LOWER'
                    if mod == 1: is_win = 1
                    else: is_aisle = 1
                elif mod in (2, 4):
                    b_type = 'UPPER'
                elif mod == 5:
                    b_type = 'SIDE_LOWER'
                    is_win = 1
                else:
                    b_type = 'SIDE_UPPER'
            elif coach_class == 'CC':
                mod = seat_no % 5
                if mod in (1, 0):
                    b_type = 'WINDOW'
                    is_win = 1
                elif mod in (2, 4):
                    b_type = 'AISLE'
                    is_aisle = 1
                else:
                    b_type = 'MIDDLE'
            else:  # 1A / EC
                mod = seat_no % 4
                if mod in (1, 0):
                    b_type = 'LOWER'
                    is_win = 1
                else:
                    b_type = 'UPPER'
                    is_aisle = 1

            seat_tuples.append((coach_id, seat_no, b_type, is_win, is_aisle, 'STANDARD'))

        if seat_tuples:
            placeholders = ', '.join(['(%s, %s, %s, %s, %s, %s)'] * len(seat_tuples))
            flat_params = [item for sub in seat_tuples for item in sub]
            sql = f"INSERT INTO seats (coach_id, seat_number, seat_type, is_window, is_aisle, deck_or_position) VALUES {placeholders}"
            execute_query(sql, tuple(flat_params), commit=True)

    @staticmethod
    def ensure_train_coaches(train_id):
        """
        Dynamically ensures the complete valid coach composition for the given train
        is present in the database, with full seat records created in the seats table.
        Idempotent and safe: preserves existing coaches and bookings.
        """
        train = execute_query("SELECT * FROM trains WHERE id = %s", (train_id,), fetchone=True)
        if not train:
            return []

        clean_num = str(train.get('train_number', '')).strip()
        train_type = str(train.get('train_type', '')).strip()
        train_name = str(train.get('train_name', '')).strip()

        target_composition = RailwayService.REAL_TRAIN_COMPOSITIONS.get(clean_num)
        if not target_composition:
            target_composition = RailwayService.get_default_composition_for_train(f"{train_type} {train_name}")

        existing_coaches = execute_query(
            "SELECT * FROM coaches WHERE train_id = %s ORDER BY coach_class ASC, coach_number ASC",
            (train_id,),
            fetchall=True
        )
        existing_by_num = {c['coach_number'].upper(): c for c in existing_coaches}

        # Check existing coaches' seats
        for c in existing_coaches:
            RailwayService.populate_coach_seats(c['id'], c['coach_class'], c['total_seats'])

        # Add any missing coaches from target composition
        for coach_num, c_class, total_seats, base_fare in target_composition:
            if coach_num.upper() not in existing_by_num:
                new_coach_id = execute_query(
                    """
                    INSERT INTO coaches (train_id, coach_number, coach_class, total_seats, base_fare)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (train_id, coach_num, c_class, total_seats, base_fare),
                    commit=True
                )
                if new_coach_id:
                    RailwayService.populate_coach_seats(new_coach_id, c_class, total_seats)

        all_coaches = execute_query(
            "SELECT * FROM coaches WHERE train_id = %s",
            (train_id,),
            fetchall=True
        )
        def coach_sort_key(c):
            c_num = c.get('coach_number', '') if isinstance(c, dict) else str(c)
            m = re.search(r'(\d+)', c_num)
            p = re.sub(r'\d+', '', c_num)
            return (p, int(m.group(1)) if m else 0)

        all_coaches.sort(key=coach_sort_key)
        return all_coaches

    @staticmethod
    def get_train_coach_composition(train_id, class_type=None, date=None, quota='GN', distance_km=None, train_type=None, train_obj=None, from_term=None, to_term=None, runs_on_date=None):
        """
        Returns the train's full coach rake composition, grouped by class and detailed per coach.
        Calculates authentic distance-based passenger fares and real-time seat availability for date & quota.
        """
        train = train_obj or execute_query("SELECT * FROM trains WHERE id = %s", (train_id,), fetchone=True)
        if not train:
            return None

        coaches = RailwayService.ensure_train_coaches(train_id)
        if not coaches:
            return None

        # Resolve distance for this journey / train
        eff_distance = None
        if distance_km is not None and float(distance_km) > 0:
            eff_distance = float(distance_km)
        elif from_term and to_term:
            eff_distance = RailwayService.get_station_track_distance(boarding_code=from_term, deboarding_code=to_term, train_id=train_id)
        elif train.get('boarding_km') is not None and train.get('deboarding_km') is not None and float(train.get('deboarding_km') or 0) > float(train.get('boarding_km') or 0):
            eff_distance = float(train['deboarding_km']) - float(train['boarding_km'])

        if eff_distance is None or eff_distance <= 0:
            if train.get('total_distance_km') and float(train['total_distance_km']) > 0:
                eff_distance = float(train['total_distance_km'])
            else:
                max_s = execute_query("SELECT max(distance_km) as m_km FROM train_stops WHERE train_id = %s", (train_id,), fetchone=True)
                if max_s and max_s.get('m_km') and float(max_s['m_km']) > 0:
                    eff_distance = float(max_s['m_km'])
                else:
                    eff_distance = RailwayService.get_station_track_distance(
                        boarding_station_id=train.get('source_station_id'),
                        deboarding_station_id=train.get('dest_station_id')
                    )

        # Check running status on selected date
        is_running_on_date = runs_on_date
        if date and is_running_on_date is None:
            r_st = RailwayService.get_train_running_status(train, date)
            is_running_on_date = r_st.get('runs_on_date')

        active_t_type = train.get('train_type') or train_type or 'Express'

        def coach_sort_key(c):
            c_num = c.get('coach_number', '') if isinstance(c, dict) else str(c)
            m = re.search(r'(\d+)', c_num)
            p = re.sub(r'\d+', '', c_num)
            return (p, int(m.group(1)) if m else 0)

        coaches.sort(key=coach_sort_key)

        # Group by class to calculate class total capacity and authentic fare
        class_order = ['1A', '2A', '3A', 'SL', 'EC', 'CC', '2S']
        distinct_classes = sorted(
            list(set(c['coach_class'] for c in coaches)),
            key=lambda x: class_order.index(x) if x in class_order else 99
        )

        class_fare_map = {}
        class_status_map = {}
        class_avail_map = {}

        for cls in distinct_classes:
            cls_coaches = [c for c in coaches if c['coach_class'] == cls]
            tot_s = sum(c['total_seats'] for c in cls_coaches)

            # Leg distance-based fare calculation
            fare_info = RailwayService.calculate_railway_fare(active_t_type, cls, eff_distance, quota=quota)
            class_fare_map[cls] = fare_info

            # Capacity allocation by quota
            is_q_valid, quota_cap = RailwayService.get_quota_allocated_seats(cls, tot_s, quota=quota)

            if not fare_info['is_applicable'] or not is_q_valid:
                class_status_map[cls] = "Not Applicable"
                class_avail_map[cls] = 0
            elif date is None:
                class_status_map[cls] = "Select date for live availability"
                class_avail_map[cls] = None
            elif is_running_on_date is False:
                class_status_map[cls] = "Not Running"
                class_avail_map[cls] = 0
            else:
                # Real verified booked passengers from database
                occ_sql = """
                    SELECT count(*) as cnt FROM passengers p
                    JOIN bookings b ON p.booking_id = b.id
                    JOIN coaches c ON b.coach_id = c.id
                    WHERE b.train_id = %s AND b.journey_date = %s 
                      AND c.coach_class = %s 
                      AND (b.quota_code = %s OR b.quota_code = 'GN')
                      AND b.status = 'CONFIRMED'
                """
                occ_res = execute_query(occ_sql, (train_id, date, cls, quota), fetchone=True)
                booked_cnt = occ_res['cnt'] if occ_res else 0

                # Active seat locks
                lock_sql = """
                    SELECT count(*) as cnt FROM seat_locks sl
                    JOIN seats st ON sl.seat_id = st.id
                    JOIN coaches c ON st.coach_id = c.id
                    WHERE c.train_id = %s AND sl.journey_date = %s 
                      AND c.coach_class = %s AND sl.expires_at > CURRENT_TIMESTAMP
                """
                lock_res = execute_query(lock_sql, (train_id, date, cls), fetchone=True)
                locked_cnt = lock_res['cnt'] if lock_res else 0

                total_occupied = booked_cnt + locked_cnt
                avail_seats = max(0, quota_cap - total_occupied)
                class_avail_map[cls] = avail_seats
                if avail_seats > 0:
                    class_status_map[cls] = f"AVAILABLE {avail_seats}"
                else:
                    wl_num = max(1, total_occupied - quota_cap + 1)
                    class_status_map[cls] = f"WL {wl_num}"

        # Populate detailed coaches
        detailed_coaches = []
        for c in coaches:
            cls = c['coach_class']
            f_info = class_fare_map.get(cls, {})
            b_fare = f_info.get('base_fare')
            a_fare = f_info.get('adjusted_fare')
            fare_unavail = (b_fare is None)

            # Fallback to coach base_fare only if distance calculation returned None
            if b_fare is None:
                b_fare = float(c.get('base_fare') or 0.0)
                a_fare = b_fare

            c_status = class_status_map.get(cls, 'Availability unavailable')

            # Per coach occupied seats for seat selection map
            coach_occ = 0
            if date:
                c_occ_res = execute_query("""
                    SELECT count(*) as cnt FROM passengers p
                    JOIN bookings b ON p.booking_id = b.id
                    WHERE b.coach_id = %s AND b.journey_date = %s AND b.status = 'CONFIRMED'
                """, (c['id'], date), fetchone=True)
                coach_occ = c_occ_res['cnt'] if c_occ_res else 0

            coach_avail_seats = max(0, c['total_seats'] - coach_occ) if date else c['total_seats']

            detailed_coaches.append({
                "id": c['id'],
                "coach_id": c['id'],
                "train_id": train_id,
                "coach_number": c['coach_number'],
                "coach_class": c['coach_class'],
                "total_seats": c['total_seats'],
                "available_seats": coach_avail_seats if date and is_running_on_date is not False else (0 if is_running_on_date is False else None),
                "base_fare": b_fare,
                "adjusted_fare": a_fare,
                "fare_unavailable": fare_unavail,
                "distance_km": eff_distance,
                "status": c_status,
                "quota_code": quota
            })

        # Build classes_summary
        classes_summary = []
        for cls in distinct_classes:
            cls_coaches = [c for c in detailed_coaches if c['coach_class'] == cls]
            cls_coaches.sort(key=coach_sort_key)
            tot_s = sum(c['total_seats'] for c in cls_coaches)
            first_c = cls_coaches[0]
            classes_summary.append({
                "class_code": cls,
                "coach_count": len(cls_coaches),
                "first_coach_id": first_c['id'],
                "first_coach_number": first_c['coach_number'],
                "coaches": [c['coach_number'] for c in cls_coaches],
                "base_fare": first_c['base_fare'],
                "adjusted_fare": first_c['adjusted_fare'],
                "fare_unavailable": first_c['fare_unavailable'],
                "distance_km": eff_distance,
                "total_seats": tot_s,
                "available_seats": class_avail_map.get(cls),
                "status": class_status_map.get(cls, 'Availability unavailable')
            })

        filtered_coaches = detailed_coaches
        if class_type:
            filtered_coaches = [c for c in detailed_coaches if c['coach_class'].upper() == class_type.strip().upper()]

        return {
            "train_id": train['id'],
            "train_number": train['train_number'],
            "train_name": train['train_name'],
            "train_type": active_t_type,
            "active_class": class_type or (classes_summary[0]['class_code'] if classes_summary else None),
            "distance_km": eff_distance,
            "classes": classes_summary,
            "coaches": filtered_coaches,
            "all_coaches": detailed_coaches
        }

    @staticmethod
    def _enrich_train_coaches(train_id, date=None, class_type=None, quota='GN', distance_km=None, train_type=None, train_obj=None, from_term=None, to_term=None, runs_on_date=None):
        """Fetches coach details, calculates seat availability and real distance-based fares aggregated by class."""
        RailwayService.ensure_train_coaches(train_id)
        comp = RailwayService.get_train_coach_composition(
            train_id,
            class_type=class_type,
            date=date,
            quota=quota,
            distance_km=distance_km,
            train_type=train_type,
            train_obj=train_obj,
            from_term=from_term,
            to_term=to_term,
            runs_on_date=runs_on_date
        )
        if not comp:
            return []

        classes_info = []
        for cls in comp['classes']:
            if class_type and cls['class_code'].upper() != class_type.strip().upper():
                continue
            classes_info.append({
                "coach_id": cls['first_coach_id'],
                "coach_number": cls['first_coach_number'],
                "class_code": cls['class_code'],
                "base_fare": cls['base_fare'],
                "adjusted_fare": cls['adjusted_fare'],
                "fare_unavailable": cls.get('fare_unavailable', False),
                "distance_km": cls.get('distance_km'),
                "quota_code": quota,
                "total_seats": cls['total_seats'],
                "available_seats": cls['available_seats'],
                "status": cls['status'],
                "coach_count": cls['coach_count']
            })
        return classes_info

    DAYS_META = [
        {'index': 0, 'day': 'S', 'abbr': 'Sun', 'full': 'Sunday'},
        {'index': 1, 'day': 'M', 'abbr': 'Mon', 'full': 'Monday'},
        {'index': 2, 'day': 'T', 'abbr': 'Tue', 'full': 'Tuesday'},
        {'index': 3, 'day': 'W', 'abbr': 'Wed', 'full': 'Wednesday'},
        {'index': 4, 'day': 'T', 'abbr': 'Thu', 'full': 'Thursday'},
        {'index': 5, 'day': 'F', 'abbr': 'Fri', 'full': 'Friday'},
        {'index': 6, 'day': 'S', 'abbr': 'Sat', 'full': 'Saturday'},
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

    @staticmethod
    def parse_running_days(val):
        """
        Parses running days value into a list of day indices [0..6] (0=Sun, 6=Sat).
        Returns None if missing/unavailable, without fabricating data.
        """
        if val is None:
            return None
        s = str(val).strip()
        if not s or s.lower() in ('none', 'null', 'n/a', '--', ''):
            return None
        if s.lower() in ('daily', 'all', 'everyday', 'all days'):
            return [0, 1, 2, 3, 4, 5, 6]

        tokens = [t.strip().lower() for t in s.replace(';', ',').split(',') if t.strip()]
        matched = set()
        for tok in tokens:
            if tok in RailwayService.DAY_NAME_TO_INDEX:
                matched.add(RailwayService.DAY_NAME_TO_INDEX[tok])
            elif tok.isdigit() and 0 <= int(tok) <= 6:
                matched.add(int(tok))
        if not matched:
            return None
        return sorted(list(matched))

    @staticmethod
    def get_train_running_status(train, selected_date=None):
        """
        Reliable railway helper determining train running day status.
        Supports both All Dates (selected_date=None) and Specific Date.
        Returns:
        {
            "runs_on_date": bool or None,
            "selected_day": str or None ("Sunday"),
            "selected_day_abbr": str or None ("Sun"),
            "selected_date_formatted": str or None ("04 Oct 2026"),
            "running_days": list of str (['Mon', 'Wed', 'Fri']) or None,
            "running_days_indices": list of int ([1, 3, 5]) or None,
            "running_days_display": list of 7 day dicts for S M T W T F S,
            "status_text": str ("Runs on Sun, 04 Oct 2026", "Not running on Sun, 04 Oct 2026", "Running days unavailable")
        }
        """
        raw = train.get('running_days') if isinstance(train, dict) else None
        active_indices = RailwayService.parse_running_days(raw)

        selected_day_index = None
        selected_day_full = None
        selected_day_abbr = None
        date_formatted = None

        if selected_date:
            try:
                if isinstance(selected_date, str) and selected_date.strip():
                    dt = datetime.datetime.strptime(selected_date.strip()[:10], '%Y-%m-%d').date()
                elif isinstance(selected_date, datetime.date):
                    dt = selected_date
                else:
                    dt = None
                if dt:
                    selected_day_index = (dt.weekday() + 1) % 7
                    selected_day_full = RailwayService.DAYS_META[selected_day_index]['full']
                    selected_day_abbr = RailwayService.DAYS_META[selected_day_index]['abbr']
                    date_formatted = dt.strftime('%d %b %Y')
            except Exception:
                pass

        running_days_abbrs = [RailwayService.DAYS_META[i]['abbr'] for i in active_indices] if active_indices is not None else None

        if selected_day_index is not None:
            if active_indices is None:
                runs_on_date = None
                status_text = "Running days unavailable"
            else:
                runs_on_date = (selected_day_index in active_indices)
                if runs_on_date:
                    status_text = f"Runs on {selected_day_abbr}, {date_formatted}"
                else:
                    status_text = f"Not running on {selected_day_abbr}, {date_formatted}"
        else:
            runs_on_date = None
            if active_indices is None:
                status_text = "Running days unavailable"
            elif len(active_indices) == 7:
                status_text = "Runs Daily (All 7 Days)"
            else:
                status_text = "Runs on " + ", ".join(running_days_abbrs)

        display = []
        for m in RailwayService.DAYS_META:
            runs_val = None if active_indices is None else (m['index'] in active_indices)
            is_sel = (selected_day_index == m['index']) if selected_day_index is not None else False
            display.append({
                'index': m['index'],
                'day': m['day'],
                'abbr': m['abbr'],
                'full': m['full'],
                'runs': runs_val,
                'is_selected': is_sel
            })

        return {
            'runs_on_date': runs_on_date,
            'selected_day': selected_day_full,
            'selected_day_abbr': selected_day_abbr,
            'selected_date_formatted': date_formatted,
            'running_days': running_days_abbrs,
            'running_days_indices': active_indices,
            'running_days_display': display,
            'status_text': status_text
        }

    @staticmethod
    def _normalize_train_result(train):
        """
        Guarantees consistent data structure and prevents crashes
        from missing / null / unrouted fields.
        """
        if not train:
            return None

        # String attributes with safe fallbacks
        train['train_number'] = str(train.get('train_number') or '').strip()
        train['train_name'] = str(train.get('train_name') or 'Express').strip()
        train['train_type'] = str(train.get('train_type') or 'Express').strip()

        # Check stops
        stops = train.get('stops') or []
        has_route = bool(stops and len(stops) >= 2)
        train['has_route_data'] = has_route

        # Derive source & destination from stops if not set
        if (not train.get('source_code') or train.get('source_code') == 'N/A') and stops:
            train['source_code'] = stops[0].get('station_code') or ''
            train['source_name'] = stops[0].get('station_name') or train['source_code']
            train['source_city'] = stops[0].get('station_city') or ''

        if (not train.get('dest_code') or train.get('dest_code') == 'N/A') and stops:
            train['dest_code'] = stops[-1].get('station_code') or ''
            train['dest_name'] = stops[-1].get('station_name') or train['dest_code']
            train['dest_city'] = stops[-1].get('station_city') or ''

        train['source_code'] = train.get('source_code') or 'N/A'
        train['source_name'] = train.get('source_name') or train['source_code']
        train['dest_code'] = train.get('dest_code') or 'N/A'
        train['dest_name'] = train.get('dest_name') or train['dest_code']

        # Departure and Arrival time defaults
        dep_time = train.get('departure_time')
        if (not dep_time or dep_time == 'START') and stops:
            dep_time = stops[0].get('departure_time')
        train['departure_time'] = dep_time if (dep_time and dep_time != 'START') else '--:--'

        arr_time = train.get('arrival_time')
        if (not arr_time or arr_time == 'END') and stops:
            arr_time = stops[-1].get('arrival_time')
        train['arrival_time'] = arr_time if (arr_time and arr_time != 'END') else '--:--'

        # Ensure leg times are present if not route-specific
        if not train.get('leg_departure_time') or train.get('leg_departure_time') == 'START':
            train['leg_departure_time'] = train['departure_time']
        if not train.get('leg_arrival_time') or train.get('leg_arrival_time') == 'END':
            train['leg_arrival_time'] = train['arrival_time']

        train['duration'] = train.get('duration') or 'N/A'
        # Section 23: Display 'Running days unavailable' if data is missing; never fabricate or assume 'Daily'
        train['running_days'] = train.get('running_days')

        # Always attach normalized running day status
        if 'running_status' not in train or train['running_status'] is None:
            r_info = RailwayService.get_train_running_status(train, train.get('query_date') or train.get('selected_date'))
            train['running_status'] = r_info
            train['runs_on_date'] = r_info['runs_on_date']
            train['selected_day'] = r_info['selected_day']
            train['selected_day_abbr'] = r_info['selected_day_abbr']
            train['selected_date_formatted'] = r_info['selected_date_formatted']
            train['running_days_list'] = r_info['running_days']
            train['running_days_display'] = r_info['running_days_display']
            train['status_text'] = r_info['status_text']

        # Fallback classes if none exist in DB
        classes = train.get('classes')
        if not classes:
            train['classes'] = [
                {
                    "coach_id": None,
                    "coach_number": "N/A",
                    "class_code": code,
                    "base_fare": 0.0,
                    "adjusted_fare": 0.0,
                    "quota_code": "GN",
                    "total_seats": 0,
                    "available_seats": 0,
                    "status": "Seat availability unavailable"
                }
                for code in ["SL", "3A", "2A", "1A"]
            ]

        return train

    @staticmethod
    def _upsert_station(code, name=None, lat=0.0, lng=0.0):
        """
        Retrieves existing station ID by code or inserts without creating duplicates.
        Updates coordinates if previously 0.0 or null.
        """
        if not code:
            return None
        clean_code = str(code).strip().upper()
        clean_name = str(name or clean_code).strip()

        row = execute_query("SELECT id, latitude, longitude FROM stations WHERE UPPER(code) = %s", (clean_code,), fetchone=True)
        if row:
            st_id = row['id']
            if lat != 0.0 and (row['latitude'] == 0.0 or row['latitude'] is None):
                execute_query("UPDATE stations SET latitude = %s, longitude = %s WHERE id = %s", (lat, lng, st_id), commit=True)
            return st_id

        # Insert new station safely
        aliases = f"{clean_code}, {clean_name}"
        st_id = execute_query(
            "INSERT INTO stations (code, name, city, state, latitude, longitude, aliases) VALUES (%s, %s, %s, 'India', %s, %s, %s)",
            (clean_code, clean_name, clean_name, lat, lng, aliases),
            commit=True
        )
        return st_id

    @staticmethod
    def save_train_and_route_from_railradar(data):
        """
        Atomically saves or updates a train and its route from RailRadar.
        Guarantees:
        - Never duplicates stations, trains, or stops.
        - Preserves existing valid local data.
        - Marks route_status = 'complete', route_stop_count, route_synced_at.
        """
        if not data or not isinstance(data, dict):
            return None

        t_num = str(data.get('train_number') or '').strip()
        if not t_num:
            return None

        stops = data.get('stops', [])
        # Route completeness rule: at least 2 valid stops required
        if not isinstance(stops, list) or len(stops) < 2:
            execute_query(
                "UPDATE trains SET route_status = 'failed', route_error = 'Invalid route stops count (< 2)' WHERE train_number = %s",
                (t_num,), commit=True
            )
            return None

        t_name = str(data.get('train_name') or f"Train #{t_num}").strip()
        t_type = str(data.get('train_type') or 'Express').strip()
        running_days = str(data.get('running_days') or 'Mon,Tue,Wed,Thu,Fri,Sat,Sun').strip()
        duration = str(data.get('duration') or 'N/A').strip()
        src_code = str(data.get('source_code') or stops[0]['code']).strip().upper()
        dst_code = str(data.get('dest_code') or stops[-1]['code']).strip().upper()
        dep_time = str(data.get('departure_time') or stops[0].get('departure') or '--:--').strip()
        arr_time = str(data.get('arrival_time') or stops[-1].get('arrival') or '--:--').strip()

        src_station_id = RailwayService._upsert_station(src_code, stops[0].get('name'), stops[0].get('lat', 0.0), stops[0].get('lng', 0.0))
        dst_station_id = RailwayService._upsert_station(dst_code, stops[-1].get('name'), stops[-1].get('lat', 0.0), stops[-1].get('lng', 0.0))

        # Check existing train
        train_row = execute_query("SELECT id, source_station_id, dest_station_id, departure_time, arrival_time FROM trains WHERE train_number = %s", (t_num,), fetchone=True)
        if train_row:
            train_id = train_row['id']
            execute_query("""
                UPDATE trains
                SET train_name = COALESCE(NULLIF(train_name, ''), %s),
                    train_type = COALESCE(NULLIF(train_type, ''), %s),
                    running_days = COALESCE(NULLIF(running_days, ''), %s),
                    duration = COALESCE(NULLIF(duration, ''), %s),
                    source_station_id = COALESCE(source_station_id, %s),
                    dest_station_id = COALESCE(dest_station_id, %s),
                    departure_time = CASE WHEN departure_time IS NULL OR departure_time = '' OR departure_time = '--:--' THEN %s ELSE departure_time END,
                    arrival_time = CASE WHEN arrival_time IS NULL OR arrival_time = '' OR arrival_time = '--:--' THEN %s ELSE arrival_time END,
                    route_status = 'complete',
                    route_synced_at = CURRENT_TIMESTAMP,
                    route_error = NULL,
                    route_stop_count = %s
                WHERE id = %s
            """, (t_name, t_type, running_days, duration, src_station_id, dst_station_id, dep_time, arr_time, len(stops), train_id), commit=True)
        else:
            train_id = execute_query("""
                INSERT INTO trains (train_number, train_name, train_type, running_days, duration,
                                   source_station_id, dest_station_id, departure_time, arrival_time,
                                   is_active, route_status, route_synced_at, route_stop_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 'complete', CURRENT_TIMESTAMP, %s)
            """, (t_num, t_name, t_type, running_days, duration, src_station_id, dst_station_id, dep_time, arr_time, len(stops)), commit=True)

        # Upsert commercial halts into train_stops
        new_st_ids = []
        for idx, s in enumerate(stops, 1):
            st_id = RailwayService._upsert_station(s['code'], s.get('name'), s.get('lat', 0.0), s.get('lng', 0.0))
            new_st_ids.append(st_id)
            seq = int(s.get('sequence') or idx)
            arr = str(s.get('arrival') or ('START' if idx == 1 else '--:--')).strip()
            dep = str(s.get('departure') or ('END' if idx == len(stops) else '--:--')).strip()
            halt = int(s.get('halt_minutes') or 0)
            try:
                dist = float(s.get('distance') or 0.0)
            except (ValueError, TypeError):
                dist = 0.0

            is_halt = s.get('is_halt', True) if s.get('is_halt') is not None else (1 if halt > 0 or (arr != '--:--' and dep != '--:--') else 0)
            existing_stop = execute_query("SELECT id FROM train_stops WHERE train_id = %s AND station_id = %s", (train_id, st_id), fetchone=True)
            if existing_stop:
                execute_query("""
                    UPDATE train_stops
                    SET stop_sequence = %s, arrival_time = %s, departure_time = %s, halt_minutes = %s, distance_km = %s, is_scheduled_halt = %s
                    WHERE id = %s
                """, (seq, arr, dep, halt, dist, 1 if is_halt else 0, existing_stop['id']), commit=True)
            else:
                execute_query("""
                    INSERT INTO train_stops (train_id, station_id, stop_sequence, arrival_time, departure_time, halt_minutes, distance_km, is_scheduled_halt)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (train_id, st_id, seq, arr, dep, halt, dist, 1 if is_halt else 0), commit=True)

        # Clean up any orphan stops that do not belong to the updated route
        if new_st_ids:
            st_placeholders = ','.join(['%s'] * len(new_st_ids))
            execute_query(
                f"DELETE FROM train_stops WHERE train_id = %s AND station_id NOT IN ({st_placeholders})",
                (train_id, *new_st_ids), commit=True
            )

        # Upsert operational passing points if available in data
        route_points = data.get('route_points', [])
        if route_points:
            table_check = execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='train_route_points'", fetchone=True)
            if table_check:
                execute_query("DELETE FROM train_route_points WHERE train_id = %s", (train_id,), commit=True)
                for pt in route_points:
                    st_id = RailwayService._upsert_station(pt['code'], pt.get('name'), pt.get('lat', 0.0), pt.get('lng', 0.0))
                    pt_type = 'HALT' if pt.get('is_halt') else 'PASSING'
                    est_time = pt.get('arrival') if pt.get('arrival') and pt['arrival'] != 'START' else pt.get('departure')
                    execute_query("""
                        INSERT INTO train_route_points (train_id, station_id, point_name, point_code, route_sequence, point_type, estimated_time, distance_km)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (train_id, st_id, pt['name'], pt['code'], pt['sequence'], pt_type, est_time, pt.get('distance', 0.0)), commit=True)

        return train_id

    @staticmethod
    def save_trains_between_from_railradar(between_trains):
        """
        Persists station-to-station train search results from RailRadar into the local DB.
        Ensures stations and trains are upserted without duplication.
        """
        if not between_trains or not isinstance(between_trains, list):
            return

        for item in between_trains:
            try:
                t_num = str(item.get('train_number') or '').strip()
                if not t_num:
                    continue

                t_name = str(item.get('train_name') or f"Train #{t_num}").strip()
                t_type = str(item.get('train_type') or 'Express').strip()
                run_days = str(item.get('running_days') or 'Mon,Tue,Wed,Thu,Fri,Sat,Sun').strip()
                dur = str(item.get('duration') or 'N/A').strip()
                from_code = str(item.get('from_code') or '').strip().upper()
                from_name = str(item.get('from_name') or from_code).strip()
                from_dep = str(item.get('from_departure') or '--:--').strip()
                from_seq = int(item.get('from_sequence') or 1)

                to_code = str(item.get('to_code') or '').strip().upper()
                to_name = str(item.get('to_name') or to_code).strip()
                to_arr = str(item.get('to_arrival') or '--:--').strip()
                to_seq = int(item.get('to_sequence') or 2)
                dist = float(item.get('distance_km') or 0.0)

                # Ensure from and to stations exist
                src_st_id = RailwayService._upsert_station(from_code, from_name)
                dst_st_id = RailwayService._upsert_station(to_code, to_name)

                # Check existing train
                existing = execute_query("SELECT id, source_station_id, dest_station_id FROM trains WHERE train_number = %s", (t_num,), fetchone=True)
                if existing:
                    t_id = existing['id']
                    execute_query("""
                        UPDATE trains
                        SET train_name = COALESCE(NULLIF(train_name, ''), %s),
                            train_type = COALESCE(NULLIF(train_type, ''), %s),
                            running_days = COALESCE(NULLIF(running_days, ''), %s),
                            duration = COALESCE(NULLIF(duration, ''), %s),
                            source_station_id = COALESCE(source_station_id, %s),
                            dest_station_id = COALESCE(dest_station_id, %s)
                        WHERE id = %s
                    """, (t_name, t_type, run_days, dur, src_st_id, dst_st_id, t_id), commit=True)
                else:
                    t_id = execute_query("""
                        INSERT INTO trains (train_number, train_name, train_type, running_days, duration,
                                           source_station_id, dest_station_id, departure_time, arrival_time,
                                           is_active, route_status, route_stop_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 'pending', 2)
                    """, (t_num, t_name, t_type, run_days, dur, src_st_id, dst_st_id, from_dep, to_arr), commit=True)

                # Upsert boarding and deboarding stops only if train does not already have a complete route
                existing_stops_count = execute_query("SELECT count(*) as c FROM train_stops WHERE train_id = %s", (t_id,), fetchone=True)['c']
                if existing_stops_count <= 2 and from_seq < to_seq:
                    check_s1 = execute_query("SELECT id FROM train_stops WHERE train_id = %s AND station_id = %s", (t_id, src_st_id), fetchone=True)
                    if not check_s1:
                        execute_query("""
                            INSERT INTO train_stops (train_id, station_id, stop_sequence, arrival_time, departure_time, halt_minutes, distance_km, is_scheduled_halt)
                            VALUES (%s, %s, %s, 'START', %s, 0, 0.0, 1)
                        """, (t_id, src_st_id, from_seq, from_dep), commit=True)

                    check_s2 = execute_query("SELECT id FROM train_stops WHERE train_id = %s AND station_id = %s", (t_id, dst_st_id), fetchone=True)
                    if not check_s2:
                        execute_query("""
                            INSERT INTO train_stops (train_id, station_id, stop_sequence, arrival_time, departure_time, halt_minutes, distance_km, is_scheduled_halt)
                            VALUES (%s, %s, %s, %s, 'END', 0, %s, 1)
                        """, (t_id, dst_st_id, to_seq, to_arr, dist), commit=True)

            except Exception as e:
                logger.error(f"[RAILWAY SERVICE] Error saving between train: {e}")

    @staticmethod
    def ensure_train_route_cached(train_id_or_number):
        """
        Ensures a train has a complete route in train_stops.
        If incomplete, fetches from RailRadar route API and persists.
        Returns (train, stops).
        """
        clean_num = None
        t_id = None
        row = None
        if str(train_id_or_number).isdigit() and len(str(train_id_or_number)) == 5:
            clean_num = str(train_id_or_number).strip()
            row = execute_query("SELECT id, train_number, route_status, route_stop_count FROM trains WHERE train_number = %s", (clean_num,), fetchone=True)
            if row:
                t_id = row['id']
        elif str(train_id_or_number).isdigit():
            t_id = int(train_id_or_number)
            row = execute_query("SELECT id, train_number, route_status, route_stop_count FROM trains WHERE id = %s", (t_id,), fetchone=True)
            if row:
                clean_num = row['train_number']

        if not t_id:
            if clean_num:
                train = RailwayService.search_by_train_number(clean_num)
                if train:
                    return train, train.get('stops', [])
            return None, []

        stops = RailwayService._get_train_stops(t_id)
        is_complete = (
            row and
            row.get('route_status') == 'complete' and
            (row.get('route_stop_count') or 0) > 2 and
            len(stops) > 2
        )
        if is_complete:
            train = RailwayService.search_by_train_number(clean_num)
            return train, stops

        # Route is missing or has < 2 stops: fetch from RailRadar
        if clean_num and RailRadarService.is_configured():
            full_data = RailRadarService.fetch_train_full(clean_num)
            if full_data and len(full_data.get('stops', [])) >= 2:
                RailwayService.save_train_and_route_from_railradar(full_data)
                stops = RailwayService._get_train_stops(t_id)
            else:
                if len(stops) == 0:
                    execute_query(
                        "UPDATE trains SET route_status = 'not_available', route_error = 'No route stops returned by provider' WHERE id = %s",
                        (t_id,), commit=True
                    )

        train = RailwayService.search_by_train_number(clean_num)
        return train, stops

    @staticmethod
    def _get_train_stops(train_id):
        """Fetches all stops for a train in sequence."""
        sql = """
            SELECT ts.*, s.code as station_code, s.name as station_name, s.city as station_city, s.state as station_state
            FROM train_stops ts
            JOIN stations s ON ts.station_id = s.id
            WHERE ts.train_id = %s
            ORDER BY ts.stop_sequence ASC
        """
        return execute_query(sql, (train_id,), fetchall=True)

    @staticmethod
    def search_by_train_number(train_number, date=None, class_type=None, quota='GN'):
        """
        Exact search by train number.
        Implements Level 1 & Level 2 on-demand lazy caching:
        1. Checks local database first.
        2. If present and route complete: returns local database record (0 API calls).
        3. If not in DB or route incomplete: calls RailRadar, stores in DB, returns DB record.
        """
        if not train_number:
            return None
        clean_num = str(train_number).strip()

        sql = """
            SELECT t.*, 
                   s1.code as source_code, s1.name as source_name, s1.city as source_city,
                   s2.code as dest_code, s2.name as dest_name, s2.city as dest_city
            FROM trains t
            LEFT JOIN stations s1 ON t.source_station_id = s1.id
            LEFT JOIN stations s2 ON t.dest_station_id = s2.id
            WHERE t.train_number = %s
        """
        train = execute_query(sql, (clean_num,), fetchone=True)

        is_complete = False
        if train:
            stops = RailwayService._get_train_stops(train['id'])
            if len(stops) >= 2 and train.get('route_status') == 'complete':
                is_complete = True
                train['stops'] = stops
                train['classes'] = RailwayService._enrich_train_coaches(train['id'])
                return RailwayService._normalize_train_result(train)

        # Cache Miss: train not in DB or route incomplete
        if not is_complete and RailRadarService.is_configured():
            full_data = RailRadarService.fetch_train_full(clean_num)
            if full_data and len(full_data.get('stops', [])) >= 2:
                RailwayService.save_train_and_route_from_railradar(full_data)
                train = execute_query(sql, (clean_num,), fetchone=True)

        if not train:
            return None

        train['stops'] = RailwayService._get_train_stops(train['id'])
        route_dist = float(train.get('total_distance_km') or 0.0)
        if route_dist <= 0 and train['stops']:
            route_dist = float(train['stops'][-1].get('distance_km') or 0.0)
        train['leg_distance_km'] = route_dist
        train['classes'] = RailwayService._enrich_train_coaches(
            train['id'],
            date=date,
            class_type=class_type,
            quota=quota,
            distance_km=route_dist,
            train_type=train.get('train_type'),
            train_obj=train
        )
        return RailwayService._normalize_train_result(train)

    @staticmethod
    def search_by_train_name(train_name, date=None, class_type=None, quota='GN'):
        """
        Case-insensitive partial search by train name.
        Returns list of matching trains with route summary and coaches.
        """
        if not train_name or not str(train_name).strip():
            return []
        clean_name = f"%{str(train_name).strip()}%"

        sql = """
            SELECT t.*, 
                   s1.code as source_code, s1.name as source_name, s1.city as source_city,
                   s2.code as dest_code, s2.name as dest_name, s2.city as dest_city
            FROM trains t
            LEFT JOIN stations s1 ON t.source_station_id = s1.id
            LEFT JOIN stations s2 ON t.dest_station_id = s2.id
            WHERE UPPER(t.train_name) LIKE UPPER(%s) AND t.is_active = 1
            ORDER BY t.train_number ASC
        """
        trains = execute_query(sql, (clean_name,), fetchall=True)
        for t in trains:
            t['stops'] = RailwayService._get_train_stops(t['id'])
            route_dist = float(t.get('total_distance_km') or 0.0)
            if route_dist <= 0 and t['stops']:
                route_dist = float(t['stops'][-1].get('distance_km') or 0.0)
            t['leg_distance_km'] = route_dist
            t['classes'] = RailwayService._enrich_train_coaches(
                t['id'],
                date=date,
                class_type=class_type,
                quota=quota,
                distance_km=route_dist,
                train_type=t.get('train_type'),
                train_obj=t
            )
            RailwayService._normalize_train_result(t)
        return trains

    @staticmethod
    def _init_sync_table():
        """Initializes route sync tracking table if not present."""
        execute_query("""
            CREATE TABLE IF NOT EXISTS route_searches_synced (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_term TEXT NOT NULL,
                dest_term TEXT NOT NULL,
                trains_count INTEGER DEFAULT 0,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_term, dest_term)
            )
        """, commit=True)

    @staticmethod
    def calculate_travel_duration_minutes(dep_time_str, arr_time_str):
        """
        Calculates travel duration in integer minutes.
        Accurately handles overnight journeys.
        """
        try:
            if not dep_time_str or not arr_time_str or dep_time_str in ('START', '--:--') or arr_time_str in ('END', '--:--'):
                return 9999
            d_parts = dep_time_str.split(':')
            a_parts = arr_time_str.split(':')
            dep_mins = int(d_parts[0]) * 60 + int(d_parts[1])
            arr_mins = int(a_parts[0]) * 60 + int(a_parts[1])

            diff = arr_mins - dep_mins
            if diff < 0:
                diff += 24 * 60  # Overnight arrival next day
            return diff
        except Exception:
            return 9999

    @staticmethod
    def is_confirmed_scheduled_halt(stop):
        """
        Evaluates whether a single stop node represents a confirmed scheduled halt.
        Priority:
        1. Explicit API halt/stop flag (is_scheduled_halt, is_halt, isHalt, point_type)
        2. Explicit halt duration (halt_minutes > 0)
        3. Scheduled arrival/departure timetable data
        4. Pass-through detection: stations with no scheduled stop timing are NOT halts.
        Returns:
            True: Confirmed scheduled halt
            False: Confirmed pass-through / non-halt
            None: Insufficient timetable information (unknown)
        """
        if not stop or not isinstance(stop, dict):
            return None

        # Priority 1: Explicit API halt/stop flag
        for flag in ('is_scheduled_halt', 'is_halt', 'isHalt'):
            if flag in stop and stop[flag] is not None:
                val = stop[flag]
                if isinstance(val, bool):
                    return val
                if str(val).lower() in ('1', 'true', 't', 'yes'):
                    return True
                if str(val).lower() in ('0', 'false', 'f', 'no'):
                    return False

        if 'point_type' in stop and stop['point_type']:
            pt = str(stop['point_type']).upper().strip()
            if pt in ('HALT', 'STOP', 'COMMERCIAL_HALT'):
                return True
            if pt in ('PASSING', 'NON_STOP', 'WAYPOINT', 'PASS_THROUGH'):
                return False

        # Priority 2: Explicit halt duration
        halt_mins = stop.get('halt_minutes') or stop.get('halt')
        try:
            if halt_mins is not None and int(halt_mins) > 0:
                return True
        except (ValueError, TypeError):
            pass

        # Priority 3: Scheduled arrival/departure timetable data
        arr = str(stop.get('arrival_time') or stop.get('arrival') or '').strip().upper()
        dep = str(stop.get('departure_time') or stop.get('departure') or '').strip().upper()

        # Pass-through detection (Section 6): No scheduled arrival/departure
        if (not arr or arr in ('--', '--:--', 'NONE', 'NULL')) and (not dep or dep in ('--', '--:--', 'NONE', 'NULL')):
            return False

        # Origin station (starts journey with valid departure)
        if arr in ('START', '--', '--:--', '', 'NONE', 'NULL'):
            if dep and dep not in ('--', '--:--', 'END', 'NONE', 'NULL'):
                return True

        # Destination station (ends journey with valid arrival)
        if dep in ('END', '--', '--:--', '', 'NONE', 'NULL'):
            if arr and arr not in ('--', '--:--', 'START', 'NONE', 'NULL'):
                return True

        # Intermediate station with timetable times (Section 5)
        import re
        time_pattern = re.compile(r'^\d{1,2}:\d{2}(?::\d{2})?$')
        if time_pattern.match(arr) and time_pattern.match(dep):
            return True

        if time_pattern.match(arr) or time_pattern.match(dep):
            return True

        return None

    @staticmethod
    def calculate_scheduled_halts(route):
        """
        Validates and calculates the actual scheduled halt count for a route or leg.
        Priority:
        1. Explicit API halt/stop flag
        2. Explicit scheduled arrival/departure timetable data
        3. Existing local train_stops timetable fields
        4. If neither is available: returns None (never count all route stations).
        Returns:
            int: Number of confirmed scheduled halts, or None if data is insufficient.
        """
        if not route or not isinstance(route, list):
            return None

        valid_nodes = [s for s in route if isinstance(s, dict)]
        if not valid_nodes:
            return None

        confirmed_count = 0
        has_sufficient_data = False

        for node in valid_nodes:
            is_halt = RailwayService.is_confirmed_scheduled_halt(node)
            if is_halt is True:
                confirmed_count += 1
                has_sufficient_data = True
            elif is_halt is False:
                has_sufficient_data = True

        if not has_sufficient_data:
            return None

        return confirmed_count

    @staticmethod
    def get_leg_scheduled_halts(train_id, boarding_seq, deboarding_seq):
        """
        Calculates the actual scheduled halt count between boarding and deboarding stations.
        Strictly distinguishes total_route_stations from scheduled_halt_count.
        Returns:
            (scheduled_halt_count, total_route_stations)
        """
        if not train_id or boarding_seq is None or deboarding_seq is None:
            return None, None

        try:
            b_seq = int(boarding_seq)
            d_seq = int(deboarding_seq)
        except (ValueError, TypeError):
            return None, None

        if b_seq >= d_seq:
            return 0, 0

        # Total route waypoints/stations difference (includes non-stopping stations)
        total_route_stations = max(0, d_seq - b_seq - 1)

        # If adjacent waypoints with zero gap, intermediate halts is strictly 0
        if total_route_stations == 0:
            return 0, 0

        # Query intermediate stops from train_stops
        sql = """
            SELECT ts.*, s.code as station_code, s.name as station_name
            FROM train_stops ts
            JOIN stations s ON ts.station_id = s.id
            WHERE ts.train_id = %s
              AND ts.stop_sequence > %s
              AND ts.stop_sequence < %s
            ORDER BY ts.stop_sequence ASC
        """
        intermediate_stops = execute_query(sql, (train_id, b_seq, d_seq), fetchall=True) or []

        # Check train route completeness
        train_row = execute_query("SELECT train_number, route_status, route_stop_count FROM trains WHERE id = %s", (train_id,), fetchone=True)
        is_complete = train_row and train_row.get('route_status') == 'complete' and (train_row.get('route_stop_count') or 0) > 2

        if intermediate_stops:
            halts_count = RailwayService.calculate_scheduled_halts(intermediate_stops)
            return halts_count, total_route_stations
        elif is_complete:
            # Route is confirmed complete and there are NO intermediate stops in train_stops
            return 0, total_route_stations
        else:
            # Data insufficient in local DB for this un-synced train - do NOT invent or count total_route_stations (Section 4 & 17)
            return None, total_route_stations

    @staticmethod
    def search_route(source_term, dest_term, date=None, class_type=None, quota='GN', force_refresh=False, date_mode=None, running_day=None, show_non_running=False):
        """
        Route search strictly enforcing stop sequence:
        source_sequence < dest_sequence.
        Supports station codes, station names, city names, and aliases.
        Returns all matching trains available with boarding/deboarding timings.
        Implements complete on-demand lazy caching with RailRadar provider:
        - Checks local database first.
        - If coverage incomplete or 0 trains: queries RailRadar (with byCity=True when appropriate).
        - Saves newly discovered routes into local DB.
        - Subsequent searches for the same route use the local database (0 API requests).
        - Merges, deduplicates by train number, and returns ALL available unique trains.
        """
        src_ids = RailwayService.resolve_station_ids(source_term)
        dst_ids = RailwayService.resolve_station_ids(dest_term)

        if not src_ids or not dst_ids:
            return []

        RailwayService._init_sync_table()

        src_placeholders = ','.join(['%s'] * len(src_ids))
        dst_placeholders = ','.join(['%s'] * len(dst_ids))

        sql = f"""
            SELECT 
                t.*,
                s1.station_id as boarding_station_id,
                s1.stop_sequence as boarding_sequence,
                s1.departure_time as boarding_time,
                s1.distance_km as boarding_km,
                st1.code as boarding_code,
                st1.name as boarding_name,
                st1.city as boarding_city,
                s2.station_id as deboarding_station_id,
                s2.stop_sequence as deboarding_sequence,
                s2.arrival_time as deboarding_time,
                s2.distance_km as deboarding_km,
                st2.code as deboarding_code,
                st2.name as deboarding_name,
                st2.city as deboarding_city,
                orig.code as source_code,
                orig.name as source_name,
                orig.city as source_city,
                dest.code as dest_code,
                dest.name as dest_name,
                dest.city as dest_city
            FROM train_stops s1
            JOIN train_stops s2 ON s1.train_id = s2.train_id
            JOIN trains t ON t.id = s1.train_id
            JOIN stations st1 ON s1.station_id = st1.id
            JOIN stations st2 ON s2.station_id = st2.id
            JOIN stations orig ON t.source_station_id = orig.id
            JOIN stations dest ON t.dest_station_id = dest.id
            WHERE s1.station_id IN ({src_placeholders})
              AND s2.station_id IN ({dst_placeholders})
              AND s1.stop_sequence < s2.stop_sequence
              AND t.is_active = 1
            ORDER BY s1.departure_time ASC
        """

        params = list(src_ids) + list(dst_ids)
        trains = execute_query(sql, tuple(params), fetchall=True)

        effective_date_mode = date_mode.strip().lower() if date_mode else ('specific' if (date and str(date).strip()) else 'all')
        calc_date = str(date).strip() if (effective_date_mode == 'specific' and date and str(date).strip()) else None

        # Check whether this route search has already been synced from RailRadar
        src_key = str(source_term).strip().upper()
        dst_key = str(dest_term).strip().upper()
        sync_row = execute_query(
            "SELECT trains_count FROM route_searches_synced WHERE UPPER(source_term) = %s AND UPPER(dest_term) = %s",
            (src_key, dst_key), fetchone=True
        )

        # On-demand lazy cache fetch if not yet synced (or 0 trains in DB)
        if (not sync_row or force_refresh or len(trains) == 0) and RailRadarService.is_configured():
            src_hub = RailwayService.get_primary_station_code(source_term)
            dst_hub = RailwayService.get_primary_station_code(dest_term)
            is_city = (str(source_term).strip().lower() in RailwayService.CITY_STATION_MAP or 
                       str(dest_term).strip().lower() in RailwayService.CITY_STATION_MAP or 
                       len(src_ids) > 1 or len(dst_ids) > 1)

            between_trains = []
            if is_city and src_hub and dst_hub:
                between_trains = RailRadarService.fetch_trains_between(src_hub, dst_hub, by_city=True, date=calc_date)

            # If byCity returned 0 or wasn't a city, try station-level query
            if not between_trains and src_hub and dst_hub:
                between_trains = RailRadarService.fetch_trains_between(src_hub, dst_hub, by_city=False, date=calc_date)

            # For multi-hub cities (e.g. Mumbai, Delhi, Bengaluru, Hyderabad, Kolkata), check key alternate terminals
            if src_hub and dst_hub:
                extra_pairs = []
                s_lower = str(source_term).strip().lower()
                d_lower = str(dest_term).strip().lower()
                if 'mumbai' in d_lower or 'bombay' in d_lower:
                    for alt_m in ['BDTS', 'CSMT', 'LTT']:
                        if alt_m != dst_hub: extra_pairs.append((src_hub, alt_m))
                if 'delhi' in d_lower:
                    for alt_d in ['DLI', 'NDLS', 'DEE']:
                        if alt_d != dst_hub: extra_pairs.append((src_hub, alt_d))
                if 'mumbai' in s_lower or 'bombay' in s_lower:
                    for alt_m in ['CSMT', 'BDTS', 'LTT']:
                        if alt_m != src_hub: extra_pairs.append((alt_m, dst_hub))
                if 'bengaluru' in d_lower or 'bangalore' in d_lower:
                    for alt_b in ['SBC', 'YPR']:
                        if alt_b != dst_hub: extra_pairs.append((src_hub, alt_b))
                if 'hyderabad' in s_lower or 'secunderabad' in s_lower:
                    for alt_h in ['SC', 'HYB']:
                        if alt_h != src_hub: extra_pairs.append((alt_h, dst_hub))
                if 'kolkata' in s_lower or 'calcutta' in s_lower:
                    for alt_k in ['HWH', 'SDAH']:
                        if alt_k != src_hub: extra_pairs.append((alt_k, dst_hub))
                if 'ahmedabad' in s_lower:
                    extra_pairs.append(('ADI', 'BDTS'))
                    extra_pairs.append(('ADI', 'MMCT'))

                for alt_s, alt_d in extra_pairs:
                    try:
                        more_bt = RailRadarService.fetch_trains_between(alt_s, alt_d, by_city=False, date=calc_date)
                        if more_bt:
                            between_trains.extend(more_bt)
                    except Exception:
                        pass

            if between_trains:
                # Deduplicate API response items by train_number before saving
                seen_api_nums = set()
                unique_bt = []
                for b in between_trains:
                    if b['train_number'] not in seen_api_nums:
                        seen_api_nums.add(b['train_number'])
                        unique_bt.append(b)
                RailwayService.save_trains_between_from_railradar(unique_bt)

            # Record sync completed in route_searches_synced
            execute_query("""
                INSERT OR REPLACE INTO route_searches_synced (source_term, dest_term, trains_count, synced_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """, (src_key, dst_key, len(between_trains) if between_trains else len(trains)), commit=True)

            # Re-query local database
            trains = execute_query(sql, tuple(params), fetchall=True)

        # Deduplicate trains by train_number, selecting the primary leg with strict direction validation
        unique_trains_map = {}
        for t in trains:
            b_seq = t.get('boarding_sequence')
            d_seq = t.get('deboarding_sequence')
            # Strict direction validation: boarding must precede deboarding
            if b_seq is None or d_seq is None or int(b_seq) >= int(d_seq):
                continue
            b_km = float(t.get('boarding_km') or 0.0)
            d_km = float(t.get('deboarding_km') or 0.0)
            if b_km > 0 and d_km > 0 and b_km >= d_km:
                continue

            t_num = str(t['train_number']).strip()
            if t_num not in unique_trains_map:
                unique_trains_map[t_num] = t
            else:
                existing = unique_trains_map[t_num]
                # Keep the entry with earlier boarding time or longer leg
                if (t.get('boarding_time') or '') < (existing.get('boarding_time') or ''):
                    unique_trains_map[t_num] = t

        results = []
        for t_num, t in unique_trains_map.items():
            dep_time = t['departure_time'] if t['boarding_time'] == 'START' else t['boarding_time']
            arr_time = t['arrival_time'] if t['deboarding_time'] == 'END' else t['deboarding_time']

            t['leg_departure_time'] = dep_time
            t['leg_arrival_time'] = arr_time
            try:
                b_km = float(t.get('boarding_km') or 0.0)
                d_km = float(t.get('deboarding_km') or 0.0)
                if d_km > b_km:
                    t['leg_distance_km'] = round(d_km - b_km, 1)
                else:
                    t['leg_distance_km'] = RailwayService.get_station_track_distance(
                        t.get('boarding_station_id') or t.get('source_station_id'),
                        t.get('deboarding_station_id') or t.get('dest_station_id'),
                        t.get('boarding_code'),
                        t.get('deboarding_code'),
                        t.get('id')
                    ) or 0.0
            except (ValueError, TypeError):
                t['leg_distance_km'] = 0.0

            # Calculate precise duration and duration in minutes
            t['duration'] = RailwayService.calculate_travel_duration(t['leg_departure_time'], t['leg_arrival_time'])
            t['duration_minutes'] = RailwayService.calculate_travel_duration_minutes(t['leg_departure_time'], t['leg_arrival_time'])

            # Calculate actual scheduled halts on leg vs total route stations
            halts_count, total_pts = RailwayService.get_leg_scheduled_halts(
                t['id'], t.get('boarding_sequence'), t.get('deboarding_sequence')
            )
            t['scheduled_halt_count'] = halts_count
            t['total_route_stations'] = total_pts
            t['total_halts_on_leg'] = halts_count

            # Determine running status using centralized helper
            run_status = RailwayService.get_train_running_status(t, calc_date)
            t['running_status'] = run_status
            t['runs_on_date'] = run_status['runs_on_date']
            t['selected_day'] = run_status['selected_day']
            t['selected_day_abbr'] = run_status['selected_day_abbr']
            t['selected_date_formatted'] = run_status['selected_date_formatted']
            t['running_days_list'] = run_status['running_days']
            t['running_days_display'] = run_status['running_days_display']
            t['status_text'] = run_status['status_text']

            # Filter by running day if specific day filter provided (e.g. Wednesday)
            if running_day and str(running_day).strip().lower() not in ('all', 'all days', ''):
                clean_rd = str(running_day).strip().lower()
                target_idx = RailwayService.DAY_NAME_TO_INDEX.get(clean_rd)
                if target_idx is not None:
                    active_indices = run_status.get('running_days_indices')
                    if active_indices is None or target_idx not in active_indices:
                        continue

            # In specific date mode:
            # If show_non_running is False (default): only show trains actually operating on selected date
            # (trains with runs_on_date is False are excluded; trains with runs_on_date is None are preserved with "Running days unavailable")
            if effective_date_mode == 'specific' and not show_non_running:
                if t['runs_on_date'] is False:
                    continue

            # Populate coaches & classes with leg-specific distance, running status, and quota
            t['classes'] = RailwayService._enrich_train_coaches(
                t['id'],
                date=calc_date,
                class_type=class_type,
                quota=quota,
                distance_km=t.get('leg_distance_km'),
                train_type=t.get('train_type'),
                train_obj=t,
                runs_on_date=t.get('runs_on_date')
            )

            if class_type and len(t['classes']) == 0:
                has_any_coaches = execute_query("SELECT 1 FROM coaches WHERE train_id = %s LIMIT 1", (t['id'],), fetchone=True)
                if has_any_coaches:
                    continue

            RailwayService._normalize_train_result(t)

            if class_type and not any(c.get('class_code') == class_type for c in t.get('classes', [])):
                continue

            results.append(t)

        # Sort results by leg departure time
        results.sort(key=lambda x: x.get('leg_departure_time') or '99:99')
        return results

    @staticmethod
    def unified_search(query=None, train_number=None, train_name=None, source=None, destination=None, date=None, class_type=None, quota='GN', date_mode=None, running_day=None, show_non_running=False):
        """
        Unified search dispatcher accommodating:
        1. Exact train number
        2. Train name
        3. Route search (source + destination)
        4. Generic query string (auto-detects train number or name or station)
        """
        effective_date_mode = date_mode.strip().lower() if date_mode else ('specific' if (date and str(date).strip()) else 'all')
        calc_date = str(date).strip() if (effective_date_mode == 'specific' and date and str(date).strip()) else None

        # 1. Train number explicit
        if train_number:
            single = RailwayService.search_by_train_number(train_number, date=calc_date, class_type=class_type, quota=quota)
            if single:
                r_status = RailwayService.get_train_running_status(single, calc_date)
                single['running_status'] = r_status
                single['runs_on_date'] = r_status['runs_on_date']
                single['selected_day'] = r_status['selected_day']
                single['selected_day_abbr'] = r_status['selected_day_abbr']
                single['selected_date_formatted'] = r_status['selected_date_formatted']
                single['running_days_list'] = r_status['running_days']
                single['running_days_display'] = r_status['running_days_display']
                single['status_text'] = r_status['status_text']
            return [single] if single else []

        # 2. Train name explicit
        if train_name:
            trains = RailwayService.search_by_train_name(train_name, date=calc_date, class_type=class_type, quota=quota)
            for t in trains:
                r_status = RailwayService.get_train_running_status(t, calc_date)
                t['running_status'] = r_status
                t['runs_on_date'] = r_status['runs_on_date']
                t['selected_day'] = r_status['selected_day']
                t['selected_day_abbr'] = r_status['selected_day_abbr']
                t['selected_date_formatted'] = r_status['selected_date_formatted']
                t['running_days_list'] = r_status['running_days']
                t['running_days_display'] = r_status['running_days_display']
                t['status_text'] = r_status['status_text']
            return trains

        # 3. Source + Destination route search
        if source and destination:
            return RailwayService.search_route(
                source, destination, date=date, class_type=class_type, quota=quota,
                date_mode=date_mode, running_day=running_day, show_non_running=show_non_running
            )

        # 4. Generic query string
        if query:
            clean_q = str(query).strip()
            # If 5 digits, check train number
            if re.match(r'^\d{5}$', clean_q):
                single = RailwayService.search_by_train_number(clean_q)
                if single:
                    r_status = RailwayService.get_train_running_status(single, calc_date)
                    single['running_status'] = r_status
                    single['runs_on_date'] = r_status['runs_on_date']
                    single['selected_day'] = r_status['selected_day']
                    single['selected_day_abbr'] = r_status['selected_day_abbr']
                    single['selected_date_formatted'] = r_status['selected_date_formatted']
                    single['running_days_list'] = r_status['running_days']
                    single['running_days_display'] = r_status['running_days_display']
                    single['status_text'] = r_status['status_text']
                return [single] if single else []

            # Check train name
            by_name = RailwayService.search_by_train_name(clean_q)
            if by_name:
                for t in by_name:
                    r_status = RailwayService.get_train_running_status(t, calc_date)
                    t['running_status'] = r_status
                    t['runs_on_date'] = r_status['runs_on_date']
                    t['selected_day'] = r_status['selected_day']
                    t['selected_day_abbr'] = r_status['selected_day_abbr']
                    t['selected_date_formatted'] = r_status['selected_date_formatted']
                    t['running_days_list'] = r_status['running_days']
                    t['running_days_display'] = r_status['running_days_display']
                    t['status_text'] = r_status['status_text']
                return by_name

            # Check if query contains "to" or "->" (e.g. "Delhi to Mumbai" or "JP to NDLS")
            to_match = re.search(r'^(.*?)\s+(?:to|->|-)\s+(.*)$', clean_q, re.IGNORECASE)
            if to_match:
                s_part = to_match.group(1).strip()
                d_part = to_match.group(2).strip()
                return RailwayService.search_route(
                    s_part, d_part, date=date, class_type=class_type, quota=quota,
                    date_mode=date_mode, running_day=running_day, show_non_running=show_non_running
                )

        return []

    @staticmethod
    def get_train_stops_detailed(train_id_or_number):
        """
        Returns complete ordered stops for a train from train_stops table.
        Ordered strictly by stop_sequence.
        """
        train = None
        if str(train_id_or_number).isdigit() and len(str(train_id_or_number)) == 5:
            train = RailwayService.search_by_train_number(str(train_id_or_number))
        elif str(train_id_or_number).isdigit():
            train = execute_query("SELECT * FROM trains WHERE id = %s", (int(train_id_or_number),), fetchone=True)
            if train:
                train = RailwayService.search_by_train_number(train['train_number'])

        if not train:
            return None, []

        stops = RailwayService._get_train_stops(train['id'])
        return train, stops

    @staticmethod
    def get_station_trains(station_term):
        """
        Returns all trains that stop at a given station (code, name, city, or alias).
        """
        station_ids = RailwayService.resolve_station_ids(station_term)
        if not station_ids:
            return None, []

        st = RailwayService.get_station_by_id(station_ids[0])
        placeholders = ','.join(['%s'] * len(station_ids))
        sql = f"""
            SELECT DISTINCT t.id, t.train_number, t.train_name, t.train_type,
                   ts.arrival_time, ts.departure_time, ts.stop_sequence, ts.halt_minutes, ts.distance_km,
                   s.code as station_code, s.name as station_name,
                   s1.code as source_code, s1.name as source_name,
                   s2.code as dest_code, s2.name as dest_name
            FROM train_stops ts
            JOIN trains t ON ts.train_id = t.id
            JOIN stations s ON ts.station_id = s.id
            LEFT JOIN stations s1 ON t.source_station_id = s1.id
            LEFT JOIN stations s2 ON t.dest_station_id = s2.id
            WHERE ts.station_id IN ({placeholders}) AND t.is_active = 1
            ORDER BY ts.departure_time ASC
        """
        trains = execute_query(sql, tuple(station_ids), fetchall=True)
        return st, trains

    @staticmethod
    def calculate_travel_duration(dep_time_str, arr_time_str):
        """
        Calculates travel duration in 'Xh Ym' format from departure and arrival times.
        Accurately handles overnight journeys.
        """
        try:
            if not dep_time_str or not arr_time_str or dep_time_str == 'START' or arr_time_str == 'END':
                return "N/A"
            d_parts = dep_time_str.split(':')
            a_parts = arr_time_str.split(':')
            dep_mins = int(d_parts[0]) * 60 + int(d_parts[1])
            arr_mins = int(a_parts[0]) * 60 + int(a_parts[1])

            diff = arr_mins - dep_mins
            if diff < 0:
                diff += 24 * 60  # Overnight arrival next day

            hours = diff // 60
            minutes = diff % 60
            if hours > 0 and minutes > 0:
                return f"{hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except Exception:
            return "N/A"

    @staticmethod
    def get_train_tracking_summary(train_id_or_number):
        """
        Returns live tracking telemetry summary for a train number or ID.
        Queries train_tracking and train_stops to deliver accurate real-time data.
        """
        train = None
        if str(train_id_or_number).isdigit() and len(str(train_id_or_number)) == 5:
            train = RailwayService.search_by_train_number(str(train_id_or_number))
        elif str(train_id_or_number).isdigit():
            train_row = execute_query("SELECT * FROM trains WHERE id = %s", (int(train_id_or_number),), fetchone=True)
            if train_row:
                train = RailwayService.search_by_train_number(train_row['train_number'])

        if not train:
            return None

        # Tracking telemetry record
        sql_tt = "SELECT * FROM train_tracking WHERE train_id = %s"
        tt = execute_query(sql_tt, (train['id'],), fetchone=True)

        delay_minutes = tt['delay_minutes'] if tt else 0
        speed = float(tt['current_speed']) if tt else 115.0
        delay_status = f"{delay_minutes} min late" if delay_minutes > 0 else "On Time (Right Time)"

        stops = train.get('stops', [])
        total_stops = len(stops)
        total_dist = float(stops[-1]['distance_km']) if stops else 1000.0

        # Anchor current position
        next_halt_name = tt['next_station'] if (tt and tt.get('next_station')) else None
        next_halt = None
        current_node = None

        if next_halt_name and stops:
            for idx, st in enumerate(stops):
                if st['station_code'].lower() in next_halt_name.lower() or st['station_name'].lower() in next_halt_name.lower():
                    next_halt = st
                    current_node = stops[max(0, idx - 1)]
                    break

        if not current_node and stops:
            # Default to middle stop or origin
            mid_idx = max(0, total_stops // 2 - 1)
            current_node = stops[mid_idx]
            next_halt = stops[min(total_stops - 1, mid_idx + 1)]

        curr_st_name = current_node['station_name'] if current_node else train['source_name']
        curr_st_code = current_node['station_code'] if current_node else train['source_code']
        next_st_name = next_halt['station_name'] if next_halt else train['dest_name']
        next_st_code = next_halt['station_code'] if next_halt else train['dest_code']
        next_eta = next_halt['arrival_time'] if (next_halt and next_halt['arrival_time'] != 'START') else (next_halt['departure_time'] if next_halt else '--:--')

        dist_covered = float(current_node['distance_km']) if current_node else 0.0
        pct_completed = round((dist_covered / max(1.0, total_dist)) * 100, 1)

        return {
            "train_id": train['id'],
            "train_number": train['train_number'],
            "train_name": train['train_name'],
            "source": f"{train['source_name']} ({train['source_code']})",
            "destination": f"{train['dest_name']} ({train['dest_code']})",
            "current_section": f"{curr_st_name} ({curr_st_code}) ➔ {next_st_name} ({next_st_code})",
            "current_station": f"{curr_st_name} ({curr_st_code})",
            "next_station": f"{next_st_name} ({next_st_code})",
            "eta": next_eta,
            "current_speed": speed,
            "delay_minutes": delay_minutes,
            "delay_status": delay_status,
            "distance_covered_km": dist_covered,
            "total_distance_km": total_dist,
            "percentage_completed": pct_completed
        }

