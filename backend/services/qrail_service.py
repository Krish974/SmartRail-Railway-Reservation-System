"""
QRail API Service Client
------------------------
Integrates with the official Qrail.in developer API (https://api.qrail.in).
All authentication is performed via Bearer tokens configured in .env (QRAIL_API_KEY).
The API key is NEVER exposed in frontend code, logs, or API responses.
"""

import os
import requests
import logging
from backend.config import Config

logger = logging.getLogger(__name__)

class QRailService:
    BASE_URL = Config.QRAIL_BASE_URL or "https://api.qrail.in"
    TIMEOUT_SECONDS = 15

    @classmethod
    def get_api_key(cls):
        """Retrieves QRAIL_API_KEY safely from environment or Config."""
        return os.environ.get('QRAIL_API_KEY', '').strip() or Config.QRAIL_API_KEY

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
            "User-Agent": "SmartRail-Qrail-Client/2.0"
        }
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    @classmethod
    def test_connection(cls):
        """
        Tests connectivity to Qrail API without leaking any sensitive credentials.
        Returns a dict with connection status and safe summary.
        """
        if not cls.is_configured():
            return {
                "success": False,
                "status_code": 401,
                "message": "QRAIL_API_KEY is not configured in .env. Please set your key in the .env file."
            }

        url = f"{cls.BASE_URL}/api/v1/trains/details"
        try:
            # Probe with a known benchmark train
            resp = requests.get(url, headers=cls._get_headers(), params={"train": 12952}, timeout=cls.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                return {
                    "success": True,
                    "status_code": 200,
                    "message": "Qrail connection: SUCCESS"
                }
            elif resp.status_code == 401:
                return {
                    "success": False,
                    "status_code": 401,
                    "message": "Qrail connection: FAILED (Authentication failed. Invalid or expired QRAIL_API_KEY)."
                }
            elif resp.status_code == 403:
                try:
                    err_msg = resp.json().get('error') or resp.json().get('message') or "Access forbidden"
                except Exception:
                    err_msg = "Access forbidden"
                return {
                    "success": False,
                    "status_code": 403,
                    "message": f"Qrail connection: FAILED (HTTP 403: {err_msg})"
                }
            elif resp.status_code == 429:
                return {
                    "success": False,
                    "status_code": 429,
                    "message": "Qrail connection: FAILED (Rate limit exceeded. Check your Qrail daily quota)."
                }
            else:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "message": f"Qrail connection: FAILED (HTTP {resp.status_code})"
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "status_code": 0,
                "message": f"Qrail connection: FAILED (Network error connecting to {cls.BASE_URL})"
            }

    @classmethod
    def fetch_train_schedule(cls, train_number):
        """
        Fetches full train schedule and intermediate stops from Qrail API:
        GET /api/v1/trains/details?train={train_number}
        
        Returns parsed normalized dictionary or None.
        """
        if not cls.is_configured():
            logger.warning("[QRAIL] Cannot fetch schedule: QRAIL_API_KEY is not set.")
            return None

        clean_number = str(train_number).strip()
        url = f"{cls.BASE_URL}/api/v1/trains/details"
        params = {"train": clean_number}

        try:
            resp = requests.get(url, headers=cls._get_headers(), params=params, timeout=cls.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                data = resp.json()
                return cls.normalize_train_details(data, clean_number)
            elif resp.status_code == 401:
                logger.error("[QRAIL] Authentication failed. Check QRAIL_API_KEY in .env.")
                return None
            elif resp.status_code == 403:
                try:
                    err_msg = resp.json().get('error') or resp.json().get('message') or "Access forbidden"
                except Exception:
                    err_msg = "Access forbidden"
                logger.error(f"[QRAIL] 403 Forbidden for train {clean_number}: {err_msg}")
                return None
            elif resp.status_code == 404:
                logger.info(f"[QRAIL] Train {clean_number} not found in Qrail records.")
                return None
            elif resp.status_code == 429:
                logger.warning("[QRAIL] Rate limit reached on Qrail API.")
                return None
            else:
                logger.warning(f"[QRAIL] Unexpected response {resp.status_code} for train {clean_number}.")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[QRAIL] Request exception for train {clean_number}: {e}")
            return None

    @classmethod
    def fetch_trains_between(cls, from_code, to_code):
        """
        Fetches direct trains operating between two stations:
        GET /api/v1/trains/between?from={from_code}&to={to_code}
        """
        if not cls.is_configured():
            logger.warning("[QRAIL] Cannot fetch trains between: QRAIL_API_KEY is not set.")
            return []

        url = f"{cls.BASE_URL}/api/v1/trains/between"
        params = {
            "from": str(from_code).strip().upper(),
            "to": str(to_code).strip().upper()
        }

        try:
            resp = requests.get(url, headers=cls._get_headers(), params=params, timeout=cls.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                data = resp.json()
                return cls.normalize_between_response(data)
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[QRAIL] Request exception for route {from_code} -> {to_code}: {e}")
            return []

    @classmethod
    def fetch_pnr_status(cls, pnr_number):
        """
        Fetches live PNR status:
        GET /api/v1/trains/pnr/status?pnr={pnr_number}
        """
        if not cls.is_configured():
            return None

        url = f"{cls.BASE_URL}/api/v1/trains/pnr/status"
        params = {"pnr": str(pnr_number).strip()}

        try:
            resp = requests.get(url, headers=cls._get_headers(), params=params, timeout=cls.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[QRAIL] Request exception for PNR {pnr_number}: {e}")
            return None

    @classmethod
    def normalize_train_details(cls, raw_data, fallback_train_number):
        """
        Normalizes varying Qrail JSON response schemas into SmartRail standard dict:
        {
            "train_number": "...",
            "train_name": "...",
            "train_type": "...",
            "source_code": "...",
            "source_name": "...",
            "dest_code": "...",
            "dest_name": "...",
            "departure_time": "...",
            "arrival_time": "...",
            "duration": "...",
            "running_days": "...",
            "stops": [
                {
                    "stop_sequence": 1,
                    "station_code": "...",
                    "station_name": "...",
                    "city": "...",
                    "state": "...",
                    "arrival_time": "START",
                    "departure_time": "16:55",
                    "halt_minutes": 0,
                    "distance_km": 0.0
                },
                ...
            ]
        }
        """
        if not isinstance(raw_data, dict):
            return None

        # Some responses encapsulate payload in 'data'
        payload = raw_data.get('data') if isinstance(raw_data.get('data'), dict) else raw_data

        t_num = str(payload.get('train_number') or payload.get('train_no') or payload.get('number') or fallback_train_number).strip()
        t_name = str(payload.get('train_name') or payload.get('name') or f"Train #{t_num}").strip()
        t_type = str(payload.get('train_type') or payload.get('type') or "Express").strip()
        days = str(payload.get('running_days') or payload.get('days') or "Mon,Tue,Wed,Thu,Fri,Sat,Sun").strip()

        # Extract stops array from payload ('stops', 'schedule', 'route', 'stations')
        raw_stops = payload.get('stops') or payload.get('schedule') or payload.get('route') or payload.get('stations') or []
        normalized_stops = []

        for idx, s in enumerate(raw_stops, 1):
            if not isinstance(s, dict):
                continue

            st_code = str(s.get('station_code') or s.get('code') or s.get('stationCode') or '').strip().upper()
            st_name = str(s.get('station_name') or s.get('name') or s.get('stationName') or st_code).strip()
            city = str(s.get('city') or s.get('station_city') or st_name).strip()
            state = str(s.get('state') or s.get('station_state') or 'India').strip()

            arr = str(s.get('arrival_time') or s.get('arrival') or s.get('arr_time') or 'START').strip()
            dep = str(s.get('departure_time') or s.get('departure') or s.get('dep_time') or 'END').strip()

            seq = int(s.get('stop_sequence') or s.get('sequence') or s.get('seq') or idx)
            halt = int(s.get('halt_minutes') or s.get('halt') or s.get('halt_time') or 0)
            
            try:
                dist = float(s.get('distance_km') or s.get('distance') or 0.0)
            except (ValueError, TypeError):
                dist = 0.0

            normalized_stops.append({
                "stop_sequence": seq,
                "station_code": st_code,
                "station_name": st_name,
                "city": city,
                "state": state,
                "arrival_time": arr,
                "departure_time": dep,
                "halt_minutes": halt,
                "distance_km": dist
            })

        # Sort stops by sequence
        normalized_stops.sort(key=lambda x: x['stop_sequence'])

        if not normalized_stops:
            return None

        first_stop = normalized_stops[0]
        last_stop = normalized_stops[-1]

        dep_time = first_stop['departure_time'] if first_stop['departure_time'] != 'END' else first_stop['arrival_time']
        arr_time = last_stop['arrival_time'] if last_stop['arrival_time'] != 'START' else last_stop['departure_time']

        return {
            "train_number": t_num,
            "train_name": t_name,
            "train_type": t_type,
            "source_code": first_stop['station_code'],
            "source_name": first_stop['station_name'],
            "dest_code": last_stop['station_code'],
            "dest_name": last_stop['station_name'],
            "departure_time": dep_time,
            "arrival_time": arr_time,
            "duration": payload.get('duration') or "N/A",
            "running_days": days,
            "stops": normalized_stops
        }

    @classmethod
    def normalize_between_response(cls, raw_data):
        """Normalizes list of trains between stations."""
        if not isinstance(raw_data, dict):
            return []
        train_list = raw_data.get('data') or raw_data.get('trains') or []
        if not isinstance(train_list, list):
            return []
        
        normalized = []
        for t in train_list:
            if isinstance(t, dict):
                normalized.append({
                    "train_number": str(t.get('train_number') or t.get('number') or '').strip(),
                    "train_name": str(t.get('train_name') or t.get('name') or '').strip(),
                    "departure_time": str(t.get('departure_time') or t.get('departure') or '').strip(),
                    "arrival_time": str(t.get('arrival_time') or t.get('arrival') or '').strip(),
                    "duration": str(t.get('duration') or '').strip()
                })
        return normalized
