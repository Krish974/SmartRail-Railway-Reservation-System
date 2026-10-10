"""
RailRadar API Service Client
----------------------------
Integrates with the official RailRadar API (https://api.railradar.in).
Authentication is performed via Bearer tokens configured in .env (RAILRADAR_API_KEY).
The API key is NEVER exposed in frontend code, logs, terminal output, or API responses.
"""

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from backend.config import Config

logger = logging.getLogger(__name__)

class RailRadarService:
    BASE_URL = Config.RAILRADAR_BASE_URL or "https://api.railradar.in"
    TIMEOUT_SECONDS = 30

    @classmethod
    def _get_session(cls):
        """Creates a requests.Session with connection pooling and retries."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    @classmethod
    def get_api_key(cls):
        """Retrieves RAILRADAR_API_KEY safely from environment or Config."""
        return os.environ.get('RAILRADAR_API_KEY', '').strip() or Config.RAILRADAR_API_KEY

    @classmethod
    def is_configured(cls):
        """Checks if a non-empty API key is present."""
        return bool(cls.get_api_key())

    @classmethod
    def _get_headers(cls):
        """Builds standard headers with Bearer token authentication."""
        key = cls.get_api_key()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "SmartRail-RailRadar-Client/1.0"
        }
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    @classmethod
    def test_connection(cls):
        """
        Tests connectivity to RailRadar station lookup endpoint:
        GET /v1/lookup/stations
        Returns a dict with connection status and safe summary without leaking credentials.
        """
        if not cls.is_configured():
            return {
                "success": False,
                "status_code": 401,
                "message": "RAILRADAR_API_KEY is not configured in .env. Please add your key to .env.",
                "stations_count": 0
            }

        url = f"{cls.BASE_URL}/v1/lookup/stations"
        try:
            resp = cls._get_session().get(url, headers=cls._get_headers(), timeout=cls.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                data = resp.json()
                raw_data = data.get('data') if isinstance(data, dict) else data
                count = len(raw_data) if isinstance(raw_data, (dict, list)) else 0
                return {
                    "success": True,
                    "status_code": 200,
                    "message": "Connection: SUCCESS",
                    "stations_count": count,
                    "meta": data.get('meta', {}) if isinstance(data, dict) else {}
                }
            elif resp.status_code == 401:
                return {
                    "success": False,
                    "status_code": 401,
                    "message": "Authentication failure (HTTP 401: Invalid or missing API Key)",
                    "stations_count": 0
                }
            elif resp.status_code == 403:
                return {
                    "success": False,
                    "status_code": 403,
                    "message": "API access/permission failure (HTTP 403: Access forbidden or subscription expired)",
                    "stations_count": 0
                }
            elif resp.status_code == 404:
                return {
                    "success": False,
                    "status_code": 404,
                    "message": "Endpoint not found (HTTP 404: Please verify endpoint in documentation)",
                    "stations_count": 0
                }
            elif resp.status_code == 429:
                return {
                    "success": False,
                    "status_code": 429,
                    "message": "Rate limit exceeded (HTTP 429: Please wait before retrying)",
                    "stations_count": 0
                }
            elif resp.status_code >= 500:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "message": f"Server error (HTTP {resp.status_code})",
                    "stations_count": 0
                }
            else:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "message": f"Unexpected status (HTTP {resp.status_code})",
                    "stations_count": 0
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "status_code": 0,
                "message": f"Network error connecting to {cls.BASE_URL}: {str(e)}",
                "stations_count": 0
            }

    @classmethod
    def fetch_stations(cls):
        """
        Fetches the complete station directory:
        GET /v1/lookup/stations
        Returns a list of parsed station dictionaries or empty list on error.
        """
        if not cls.is_configured():
            logger.warning("[RAILRADAR] Cannot fetch stations: RAILRADAR_API_KEY is not set.")
            return []

        url = f"{cls.BASE_URL}/v1/lookup/stations"
        try:
            resp = cls._get_session().get(url, headers=cls._get_headers(), timeout=cls.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                data = resp.json()
                raw_data = data.get('data') if isinstance(data, dict) else data
                return cls.normalize_stations(raw_data)
            else:
                logger.error(f"[RAILRADAR] Failed to fetch stations: HTTP {resp.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[RAILRADAR] Request exception fetching stations: {e}")
            return []

    @classmethod
    def fetch_trains_ntes(cls):
        """
        Fetches NTES train directory:
        GET /v1/lookup/trains/ntes
        """
        if not cls.is_configured():
            logger.warning("[RAILRADAR] Cannot fetch trains: RAILRADAR_API_KEY is not set.")
            return []

        url = f"{cls.BASE_URL}/v1/lookup/trains/ntes"
        try:
            resp = cls._get_session().get(url, headers=cls._get_headers(), timeout=cls.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                data = resp.json()
                raw_data = data.get('data') if isinstance(data, dict) and 'data' in data else data
                return cls.normalize_trains_ntes(raw_data)
            else:
                logger.error(f"[RAILRADAR] Failed to fetch NTES trains: HTTP {resp.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[RAILRADAR] Request exception fetching trains: {e}")
            return []

    @classmethod
    def fetch_train_route(cls, train_number):
        """
        Fetches full timetable route for a train:
        GET /v1/trains/{train_number}/route
        """
        if not cls.is_configured():
            logger.warning("[RAILRADAR] Cannot fetch train route: RAILRADAR_API_KEY is not set.")
            return None

        clean_num = str(train_number).strip()
        url = f"{cls.BASE_URL}/v1/trains/{clean_num}/route?stops=true"
        try:
            resp = cls._get_session().get(url, headers=cls._get_headers(), timeout=cls.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                data = resp.json()
                return cls.normalize_train_route(data, clean_num)
            elif resp.status_code == 429:
                logger.warning(f"[RAILRADAR] Rate limit reached while fetching route for {clean_num}.")
                return None
            else:
                logger.error(f"[RAILRADAR] Route request failed for {clean_num}: HTTP {resp.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[RAILRADAR] Request exception for route {clean_num}: {e}")
            return None

    @classmethod
    def fetch_train_full(cls, train_number):
        """
        Fetches complete train definition and halts:
        GET /v1/trains/{train_number}
        """
        if not cls.is_configured():
            logger.warning("[RAILRADAR] Cannot fetch train: RAILRADAR_API_KEY is not set.")
            return None

        clean_num = str(train_number).strip()
        url = f"{cls.BASE_URL}/v1/trains/{clean_num}"
        try:
            resp = cls._get_session().get(url, headers=cls._get_headers(), timeout=cls.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                data = resp.json()
                return cls.normalize_full_train(data, clean_num)
            elif resp.status_code == 429:
                logger.warning(f"[RAILRADAR] Rate limit reached fetching train {clean_num}.")
                return None
            else:
                logger.info(f"[RAILRADAR] Train full lookup HTTP {resp.status_code} for {clean_num}, trying route endpoint...")
                # Fallback to route endpoint
                return cls.fetch_train_route(clean_num)
        except requests.exceptions.RequestException as e:
            logger.error(f"[RAILRADAR] Request exception for train {clean_num}: {e}")
            return None

    @classmethod
    def fetch_trains_between(cls, source_code, dest_code, by_city=False, date=None):
        """
        Fetches direct trains between two stations or city clusters:
        GET /v1/trains/between/{from}/{to}
        Supports byCity=true and date parameters.
        """
        if not cls.is_configured():
            logger.warning("[RAILRADAR] Cannot fetch trains between: RAILRADAR_API_KEY is not set.")
            return []

        src = str(source_code).strip().upper()
        dst = str(dest_code).strip().upper()
        url = f"{cls.BASE_URL}/v1/trains/between/{src}/{dst}"
        params = {}
        if by_city:
            params['byCity'] = 'true'
        if date:
            params['date'] = str(date).strip()

        try:
            resp = cls._get_session().get(url, headers=cls._get_headers(), params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return cls.normalize_between_trains(data)
            elif resp.status_code == 429:
                logger.warning(f"[RAILRADAR] Rate limit reached on between search {src} -> {dst}.")
                return []
            else:
                logger.info(f"[RAILRADAR] Between search {src} -> {dst} returned HTTP {resp.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[RAILRADAR] Request exception for between search {src} -> {dst}: {e}")
            return []

    @classmethod
    def fetch_train_live(cls, train_number):
        """
        Fetches real-time running status with a strict 5s finite timeout:
        GET /v1/trains/{train_number}/live
        """
        if not cls.is_configured():
            return None

        clean_num = str(train_number).strip()
        url = f"{cls.BASE_URL}/v1/trains/{clean_num}/live"
        try:
            resp = cls._get_session().get(url, headers=cls._get_headers(), timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return cls.normalize_live_telemetry(data)
            else:
                return None
        except Exception as e:
            logger.info(f"[RAILRADAR] Live status fetch exception for {clean_num}: {e}")
            return None

    @classmethod
    def _extract_list_from_response(cls, data, candidate_keys):
        """Extracts list of records from varied API response envelopes."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in candidate_keys:
                if k in data and isinstance(data[k], list):
                    return data[k]
            # Check nested 'data' dict
            if 'data' in data and isinstance(data['data'], dict):
                for k in candidate_keys:
                    if k in data['data'] and isinstance(data['data'][k], list):
                        return data['data'][k]
        return []

    @classmethod
    def normalize_stations(cls, raw_input):
        """
        Normalizes station objects into standard SmartRail dictionary.
        Supports:
        1. Dict map: {"NDLS": "New Delhi", "JP": "Jaipur Jn", ...}
        2. List of dicts: [{"code": "NDLS", "name": "New Delhi", ...}, ...]
        """
        normalized = []
        if isinstance(raw_input, dict):
            for code, name in raw_input.items():
                c = str(code).strip().upper()
                n = str(name).strip()
                if c:
                    normalized.append({
                        "code": c,
                        "name": n,
                        "city": n,
                        "state": "India",
                        "latitude": 0.0,
                        "longitude": 0.0,
                        "aliases": f"{c}, {n}"
                    })
        elif isinstance(raw_input, list):
            for item in raw_input:
                if not isinstance(item, dict):
                    continue
                code = str(item.get('code') or item.get('station_code') or item.get('stationCode') or '').strip().upper()
                if not code:
                    continue
                name = str(item.get('name') or item.get('station_name') or item.get('stationName') or code).strip()
                city = str(item.get('city') or item.get('cityName') or name).strip()
                state = str(item.get('state') or item.get('stateName') or 'India').strip()
                try:
                    lat = float(item.get('latitude') or item.get('lat') or 0.0)
                    lng = float(item.get('longitude') or item.get('lng') or item.get('lon') or 0.0)
                except (ValueError, TypeError):
                    lat, lng = 0.0, 0.0
                aliases = str(item.get('aliases') or f"{code}, {name}, {city}, {state}").strip()
                normalized.append({
                    "code": code,
                    "name": name,
                    "city": city,
                    "state": state,
                    "latitude": lat,
                    "longitude": lng,
                    "aliases": aliases
                })
        return normalized

    @classmethod
    def infer_train_type(cls, train_name):
        """Infers train type category from the official train name."""
        upper = str(train_name).upper()
        if "VANDE BHARAT" in upper:
            return "Vande Bharat Express"
        elif "TEJAS" in upper:
            return "Tejas Express"
        elif "RAJDHANI" in upper:
            return "Rajdhani Express"
        elif "SHATABDI" in upper:
            return "Shatabdi Express"
        elif "GARIB RATH" in upper:
            return "Garib Rath Express"
        elif "DURONTO" in upper:
            return "Duronto Express"
        elif "HUMSAFAR" in upper:
            return "Humsafar Express"
        elif "JAN SHATABDI" in upper:
            return "Jan Shatabdi Express"
        elif "ANTYODAYA" in upper:
            return "Antyodaya Express"
        elif "MEMU" in upper:
            return "MEMU"
        elif "DEMU" in upper:
            return "DEMU"
        elif "EMU" in upper:
            return "EMU"
        elif "PASSENGER" in upper or " PASS" in upper:
            return "Passenger"
        elif "SUPERFAST" in upper or " SF " in f" {upper} " or upper.endswith(" SF"):
            return "Superfast Express"
        elif "MAIL" in upper:
            return "Mail Express"
        elif "EXPRESS" in upper or " EXP" in upper:
            return "Express"
        else:
            return "Express"

    @classmethod
    def normalize_trains_ntes(cls, raw_input):
        """
        Normalizes train directory items into standard SmartRail dictionary.
        Supports:
        1. Dict map: {"10103": "CSMT-MAO MANDOVI EXPRESS", ...}
        2. List of dicts: [{"train_number": "10103", "train_name": "CSMT-MAO MANDOVI EXPRESS", ...}, ...]
        """
        normalized = []
        if isinstance(raw_input, dict):
            for num, name in raw_input.items():
                t_num = str(num).strip()
                t_name = str(name).strip()
                if t_num:
                    t_type = cls.infer_train_type(t_name)
                    normalized.append({
                        "train_number": t_num,
                        "train_name": t_name,
                        "source_code": None,
                        "dest_code": None,
                        "train_type": t_type
                    })
        elif isinstance(raw_input, list):
            for item in raw_input:
                if not isinstance(item, dict):
                    continue
                num = str(item.get('train_number') or item.get('number') or item.get('trainNumber') or '').strip()
                if not num:
                    continue

                name = str(item.get('train_name') or item.get('name') or item.get('trainName') or f"Train #{num}").strip()
                src = str(item.get('from') or item.get('source') or item.get('source_code') or '').strip().upper() or None
                dst = str(item.get('to') or item.get('destination') or item.get('dest_code') or '').strip().upper() or None
                t_type = str(item.get('type') or item.get('train_type') or cls.infer_train_type(name)).strip()

                normalized.append({
                    "train_number": num,
                    "train_name": name,
                    "source_code": src,
                    "dest_code": dst,
                    "train_type": t_type
                })
        return normalized

    @classmethod
    def normalize_train_route(cls, data, fallback_num):
        """
        Normalizes train route/stops payload.
        """
        payload = data.get('data') if isinstance(data.get('data'), dict) else data
        if not isinstance(payload, dict):
            return None

        t_num = str(payload.get('train_number') or payload.get('number') or fallback_num).strip()
        t_name = str(payload.get('train_name') or payload.get('name') or f"Train #{t_num}").strip()
        t_type = str(payload.get('train_type') or payload.get('type') or 'Express').strip()

        raw_stops = cls._extract_list_from_response(payload, ['stops', 'route', 'schedule', 'stations'])
        normalized_stops = []

        for idx, s in enumerate(raw_stops, 1):
            if not isinstance(s, dict):
                continue
            st_code = str(s.get('station_code') or s.get('code') or '').strip().upper()
            if not st_code:
                continue
            st_name = str(s.get('station_name') or s.get('name') or st_code).strip()
            arr = str(s.get('arrival_time') or s.get('arrival') or 'START').strip()
            dep = str(s.get('departure_time') or s.get('departure') or 'END').strip()
            seq = int(s.get('stop_sequence') or s.get('sequence') or idx)
            halt = int(s.get('halt_minutes') or s.get('halt') or 0)
            try:
                dist = float(s.get('distance_km') or s.get('distance') or 0.0)
            except (ValueError, TypeError):
                dist = 0.0

            normalized_stops.append({
                "stop_sequence": seq,
                "station_code": st_code,
                "station_name": st_name,
                "arrival_time": arr,
                "departure_time": dep,
                "halt_minutes": halt,
                "distance_km": dist
            })

        normalized_stops.sort(key=lambda x: x['stop_sequence'])
        if not normalized_stops:
            return None

        return {
            "train_number": t_num,
            "train_name": t_name,
            "train_type": t_type,
            "source_code": normalized_stops[0]['station_code'],
            "dest_code": normalized_stops[-1]['station_code'],
            "departure_time": normalized_stops[0]['departure_time'],
            "arrival_time": normalized_stops[-1]['arrival_time'],
            "stops": normalized_stops
        }

    @classmethod
    def normalize_full_train(cls, data, fallback_num):
        """
        Normalizes response from GET /v1/trains/{train_number}.
        Returns structured dict with train header, commercial stops, and passing waypoints.
        """
        payload = data.get('data') if isinstance(data, dict) and 'data' in data else data
        if not isinstance(payload, dict):
            return None

        train_obj = payload.get('train', {}) if isinstance(payload.get('train'), dict) else {}
        t_num = str(train_obj.get('number') or payload.get('trainNumber') or fallback_num).strip()
        t_name = str(train_obj.get('name') or payload.get('trainName') or f"Train #{t_num}").strip()
        t_type = str(train_obj.get('type') or payload.get('trainType') or cls.infer_train_type(t_name)).strip()

        # Running days
        run_days = train_obj.get('runDays') or payload.get('runDays') or []
        if isinstance(run_days, list) and run_days:
            days_str = ",".join([d.strip().capitalize() for d in run_days])
        else:
            days_str = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"

        # Duration
        dur_mins = train_obj.get('duration') or payload.get('duration')
        if isinstance(dur_mins, (int, float)) and dur_mins > 0:
            h = int(dur_mins) // 60
            m = int(dur_mins) % 60
            duration_str = f"{h}h {m}m"
        else:
            duration_str = "N/A"

        # Source & Dest
        src_obj = train_obj.get('source', {}) if isinstance(train_obj.get('source'), dict) else {}
        dst_obj = train_obj.get('destination', {}) if isinstance(train_obj.get('destination'), dict) else {}
        source_code = str(src_obj.get('code') or '').strip().upper() or None
        dest_code = str(dst_obj.get('code') or '').strip().upper() or None

        raw_route = payload.get('route') or payload.get('stops') or []
        stops = []
        route_points = []

        if isinstance(raw_route, list):
            for idx, node in enumerate(raw_route, 1):
                if not isinstance(node, dict):
                    continue
                st_obj = node.get('station', {}) if isinstance(node.get('station'), dict) else {}
                st_code = str(st_obj.get('code') or node.get('stationCode') or node.get('code') or '').strip().upper()
                if not st_code:
                    continue
                st_name = str(st_obj.get('name') or node.get('stationName') or node.get('name') or st_code).strip()
                try:
                    lat = float(st_obj.get('lat') or node.get('lat') or 0.0)
                    lng = float(st_obj.get('lng') or node.get('lng') or 0.0)
                except (ValueError, TypeError):
                    lat, lng = 0.0, 0.0

                seq = int(node.get('sequence') or idx)
                arr = str(node.get('arrival') or ('START' if idx == 1 else '--:--')).strip()
                dep = str(node.get('departure') or ('END' if idx == len(raw_route) else '--:--')).strip()
                try:
                    dist = float(node.get('distance') or 0.0)
                except (ValueError, TypeError):
                    dist = 0.0

                is_halt = bool(node.get('isHalt', True))
                halt_mins = int(node.get('halt') or node.get('halt_minutes') or 0)

                # Keep all route waypoints for timeline/passing points
                route_points.append({
                    "sequence": seq,
                    "code": st_code,
                    "name": st_name,
                    "lat": lat,
                    "lng": lng,
                    "arrival": arr,
                    "departure": dep,
                    "distance": dist,
                    "is_halt": is_halt,
                    "halt_minutes": halt_mins
                })

                # Commercial halts only for train_stops table
                if is_halt or idx == 1 or idx == len(raw_route):
                    stops.append({
                        "sequence": seq,
                        "code": st_code,
                        "name": st_name,
                        "lat": lat,
                        "lng": lng,
                        "arrival": arr,
                        "departure": dep,
                        "distance": dist,
                        "halt_minutes": halt_mins
                    })

        stops.sort(key=lambda x: x['sequence'])
        if stops and not source_code:
            source_code = stops[0]['code']
        if stops and not dest_code:
            dest_code = stops[-1]['code']

        dep_time = stops[0]['departure'] if stops and stops[0]['departure'] != 'END' else '--:--'
        arr_time = stops[-1]['arrival'] if stops and stops[-1]['arrival'] != 'START' else '--:--'

        return {
            "train_number": t_num,
            "train_name": t_name,
            "train_type": t_type,
            "running_days": days_str,
            "duration": duration_str,
            "source_code": source_code,
            "dest_code": dest_code,
            "departure_time": dep_time,
            "arrival_time": arr_time,
            "stops": stops,
            "route_points": route_points
        }

    @classmethod
    def normalize_between_trains(cls, data):
        """
        Normalizes response from GET /v1/trains/between/{from}/{to}.
        Returns list of standardized train search result items.
        """
        payload = data.get('data') if isinstance(data, dict) and 'data' in data else data
        if not isinstance(payload, dict):
            return []

        raw_trains = payload.get('trains') or []
        results = []

        for item in raw_trains:
            if not isinstance(item, dict):
                continue
            tr = item.get('train', {}) if isinstance(item.get('train'), dict) else {}
            fr = item.get('from', {}) if isinstance(item.get('from'), dict) else {}
            to = item.get('to', {}) if isinstance(item.get('to'), dict) else {}

            t_num = str(tr.get('number') or '').strip()
            if not t_num:
                continue

            t_name = str(tr.get('name') or f"Train #{t_num}").strip()
            t_type = str(tr.get('type') or cls.infer_train_type(t_name)).strip()

            run_days = tr.get('runDays') or []
            if isinstance(run_days, list) and run_days:
                days_str = ",".join([d.strip().capitalize() for d in run_days])
            else:
                days_str = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"

            dur_mins = item.get('duration') or 0
            if dur_mins:
                h = int(dur_mins) // 60
                m = int(dur_mins) % 60
                duration_str = f"{h}h {m}m"
            else:
                duration_str = "N/A"

            from_code = str(fr.get('code') or '').strip().upper()
            from_name = str(fr.get('name') or from_code).strip()
            from_dep = str(fr.get('departure') or '--:--').strip()
            from_seq = int(fr.get('sequence') or 1)

            to_code = str(to.get('code') or '').strip().upper()
            to_name = str(to.get('name') or to_code).strip()
            to_arr = str(to.get('arrival') or '--:--').strip()
            to_seq = int(to.get('sequence') or 2)

            try:
                dist = float(item.get('distance') or 0.0)
            except (ValueError, TypeError):
                dist = 0.0

            results.append({
                "train_number": t_num,
                "train_name": t_name,
                "train_type": t_type,
                "running_days": days_str,
                "duration": duration_str,
                "distance_km": dist,
                "from_code": from_code,
                "from_name": from_name,
                "from_departure": from_dep,
                "from_sequence": from_seq,
                "to_code": to_code,
                "to_name": to_name,
                "to_arrival": to_arr,
                "to_sequence": to_seq
            })

        return results

    @classmethod
    def normalize_live_telemetry(cls, data):
        """
        Normalizes response from GET /v1/trains/{train_number}/live.
        Returns clean, standardized real-time tracking telemetry.
        """
        payload = data.get('data') if isinstance(data, dict) and 'data' in data else data
        if not isinstance(payload, dict):
            return None

        t_num = str(payload.get('trainNumber') or '').strip()
        t_name = str(payload.get('trainName') or f"Train #{t_num}").strip()
        status = str(payload.get('status') or 'running').strip().lower()
        delay_mins = int(payload.get('delayMinutes') or 0)
        delay_status = f"{delay_mins} min late" if delay_mins > 0 else "On Time (Right Time)"

        curr_loc = payload.get('currentLocation') or {}
        curr_code = str(curr_loc.get('stationCode') or '').strip().upper() or None
        curr_name = str(curr_loc.get('stationName') or curr_code or 'In Transit').strip()
        curr_pos_status = str(curr_loc.get('status') or 'in-transit').strip().lower()
        platform = str(curr_loc.get('platform') or '').strip() or None

        # Speed Extraction Hierarchy:
        # 1. Direct positive speed reported in currentLocation or payload
        raw_speed = None
        for candidate in [
            curr_loc.get('speedKmh'),
            curr_loc.get('speed'),
            curr_loc.get('speed_kmh'),
            payload.get('speedKmh'),
            payload.get('speed'),
            payload.get('currentSpeed')
        ]:
            if candidate is not None:
                try:
                    val = float(candidate)
                    if val > 0:
                        raw_speed = val
                        break
                except (ValueError, TypeError):
                    continue

        # 2. Check if train is genuinely halted at a commercial halt
        # Only report 0.0 km/h when train is confirmed stopped/halted at a scheduled stop
        is_scheduled_halt = bool(curr_loc.get('isHalt', False))
        is_halted_status = curr_pos_status in ('at-station', 'halt', 'halted', 'stopped', 'at_station')
        is_genuinely_halted = is_halted_status and is_scheduled_halt

        curr_speed = None
        if raw_speed is not None and raw_speed > 0:
            curr_speed = round(raw_speed, 1)
        elif is_genuinely_halted:
            curr_speed = 0.0
        else:
            # 3. For running/in-transit trains, look up segment speed from route nodes
            raw_route = payload.get('route') or payload.get('stops') or []
            curr_seq = curr_loc.get('sequence')
            route_speed = None

            if isinstance(raw_route, list):
                # First try matching by sequence or station code
                for r_node in raw_route:
                    if not isinstance(r_node, dict):
                        continue
                    n_seq = r_node.get('sequence')
                    n_code = str(r_node.get('stationCode') or (r_node.get('station') or {}).get('code') or '').strip().upper()
                    if (curr_seq is not None and n_seq == curr_seq) or (curr_code and n_code == curr_code):
                        s_val = r_node.get('speedToNextStationKmph') or r_node.get('speedKmph') or r_node.get('speed')
                        if s_val is not None:
                            try:
                                sv = float(s_val)
                                if sv > 0:
                                    route_speed = sv
                                    break
                            except (ValueError, TypeError):
                                pass

                # If still not found, check the latest departed node
                if route_speed is None:
                    departed_nodes = [
                        n for n in raw_route
                        if isinstance(n, dict) and str(n.get('status') or '').lower() == 'departed'
                    ]
                    if departed_nodes:
                        last_dep = departed_nodes[-1]
                        s_val = last_dep.get('speedToNextStationKmph') or last_dep.get('speedKmph') or last_dep.get('speed')
                        if s_val is not None:
                            try:
                                sv = float(s_val)
                                if sv > 0:
                                    route_speed = sv
                            except (ValueError, TypeError):
                                pass

            if route_speed is not None and route_speed > 0:
                curr_speed = round(route_speed, 1)
            elif is_halted_status:
                curr_speed = 0.0
            else:
                curr_speed = None

        next_halt = payload.get('nextHalt') or {}
        next_code = str(next_halt.get('stationCode') or '').strip().upper() or None
        next_name = str(next_halt.get('stationName') or next_code or 'Terminus').strip()
        next_eta = str(next_halt.get('eta') or next_halt.get('expectedArrival') or '--:--').strip()

        return {
            "train_number": t_num,
            "train_name": t_name,
            "running_status": status,
            "delay_minutes": delay_mins,
            "delay_status": delay_status,
            "current_station": f"{curr_name} ({curr_code})" if curr_code else curr_name,
            "current_station_name": curr_name,
            "current_station_code": curr_code,
            "current_speed": curr_speed,
            "current_position": curr_pos_status,
            "is_halted": is_genuinely_halted,
            "platform": platform,
            "next_station": f"{next_name} ({next_code})" if next_code else next_name,
            "next_station_name": next_name,
            "next_station_code": next_code,
            "next_eta": next_eta,
            "last_updated_at": payload.get('lastUpdatedAt')
        }
