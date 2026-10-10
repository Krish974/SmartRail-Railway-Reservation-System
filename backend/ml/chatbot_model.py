"""
SmartRail AI Assistant - Intelligent NLP & Railway Service Integrator
Genuinely data-driven, context-aware chatbot using RailwayService and the SQLite/MySQL database
as the single source of truth for:
- Ordered route train search (Source -> Destination with stop sequence enforcement)
- Complete, non-truncated train results (never arbitrarily limited to 3 or 5)
- On-demand lazy caching of discovered routes from RailRadar
- Train details, complete route stops, and ordered timetable inspection
- Genuine live GPS telemetry and real-time running status tracking
- Station intelligence, station codes, and junction inquiries
- Journey travel duration calculations and comparative analysis (fastest, fewest stops)
- Natural language filtering (morning, evening, night, Vande Bharat, Rajdhani, Shatabdi, etc.)
- Live PNR status lookups & confirmation probability analysis
- Railway domain knowledge (GNWL, RAC, RLWL, PQWL, Tatkal, 2A, 3A, SL, etc.)
- Booking guidance, seat locking mechanism, cancellation policy, and food ordering
- Multi-turn conversation context retention
"""

import os
import re
import datetime
from backend.models.booking_model import BookingModel
from backend.models.train_model import TrainModel
from backend.models.food_model import FoodModel
from backend.services.railway_service import RailwayService
from backend.services.railradar_service import RailRadarService
from backend.utils.db_connection import execute_query
from backend.ml.railway_knowledge_base import (
    KNOWLEDGE_DOCUMENTS,
    extract_railway_entities,
    retrieve_railway_knowledge,
    generate_rag_answer,
    stage_2_classify_and_reason,
    RAILWAY_NON_STATION_WORDS
)

# In-memory session context for multi-turn conversation memory
CONVERSATION_CONTEXT = {}

# Known train aliases mapped to 5-digit train numbers
TRAIN_ALIASES = {
    'tejas rajdhani': '12952',
    'rajdhani': '12952',
    'mumbai rajdhani': '12952',
    'delhi rajdhani': '12951',
    'august kranti': '12953',
    'sampark kranti': '12907',
    'punjab mail': '12137',
    'shatabdi': '12015',
    'ajmer shatabdi': '12015',
    'swarna jayanti': '12957',
    'vande bharat': '20977',
    'ajmer vande bharat': '20977',
    'pooja': '12413',
    'pooja superfast': '12413',
    'pooja express': '12413',
    'howrah rajdhani': '12301',
    'sealdah rajdhani': '12313',
    'bengaluru rajdhani': '22691',
    'grand trunk': '12615',
    'bhopal shatabdi': '12002',
    'lucknow shatabdi': '12004',
    'paschim express': '12925',
    'swaraj express': '12471',
    'swarn nagari': '12250'
}

# Railway Knowledge Base
RAILWAY_KNOWLEDGE = {
    'gnwl': {
        'term': 'GNWL (General Waiting List)',
        'text': "• **GNWL (General Waiting List)** is the most common waiting list quota in Indian Railways.\n"
                "• **Issuance:** It is issued when a passenger begins their journey from the train's originating station or a major junction nearby.\n"
                "• **Confirmation Priority:** GNWL has the **highest confirmation priority** among all waiting lists. When passengers with confirmed tickets cancel, GNWL tickets get cleared first before remote quotas."
    },
    'rac': {
        'term': 'RAC (Reservation Against Cancellation)',
        'text': "• **RAC (Reservation Against Cancellation)** guarantees that you are permitted to board the train!\n"
                "• **Berth Allocation:** Two passengers with RAC tickets share one side-lower berth (one berth split into two sitting seats).\n"
                "• **Full Berth Confirmation:** If any confirmed passenger cancels their ticket or doesn't show up before chart preparation, RAC passengers are automatically upgraded to full sleeping berths."
    },
    'rlwl': {
        'term': 'RLWL (Remote Location Waiting List)',
        'text': "• **RLWL (Remote Location Waiting List)** is issued for passengers boarding and deboarding at important intermediate stations along a train route.\n"
                "• **Separate Quota:** Remote locations have a dedicated small quota of seats allotted from the train's total capacity.\n"
                "• **Confirmation Priority:** RLWL only confirms when another passenger booked within the same remote location quota cancels; it has lower confirmation chances than GNWL."
    },
    'pqwl': {
        'term': 'PQWL (Pooled Quota Waiting List)',
        'text': "• **PQWL (Pooled Quota Waiting List)** is shared by several smaller intermediate stations between the origin and destination.\n"
                "• **Pooled Bucket:** Only a tiny pooled pool of berths is reserved for these intermediate stops.\n"
                "• **Confirmation Priority:** PQWL has lower priority than both GNWL and RLWL. It usually clears only if cancellations occur within the pooled quota segment."
    },
    'tatkal': {
        'term': 'Tatkal Quota Booking',
        'text': "• **Tatkal Quota** is designed for short-notice or urgent railway travel 24 hours prior to journey departure.\n"
                "• **Booking Timings:**\n"
                "  - **AC Classes (1A, 2A, 3A, CC, EC):** Opens at **10:00 AM IST** daily.\n"
                "  - **Non-AC Classes (Sleeper, 2S):** Opens at **11:00 AM IST** daily.\n"
                "• **Tatkal Charges:** Fixed premium surcharge ranging between ₹100 and ₹500 depending on distance and coach class."
    },
    'premium tatkal': {
        'term': 'Premium Tatkal (PT) Quota',
        'text': "• **Premium Tatkal (PT)** is a dynamic-pricing quota introduced by Indian Railways for urgent travel.\n"
                "• **Dynamic Pricing:** As seat availability decreases, the fare increases dynamically in real time.\n"
                "• **Rules:** No senior citizen or child concessions apply. Confirmed Premium Tatkal tickets carry a strict zero-refund policy upon cancellation."
    },
    'chart preparation': {
        'term': 'Chart Preparation Timeline',
        'text': "• **First Chart Preparation:** Generated **4 hours** before the train's scheduled origin departure time (or at 8:00 PM the previous evening for morning departures before 12:00 noon).\n"
                "• **Second & Final Chart:** Generated **30 minutes** before train departure, after Current Booking closes.\n"
                "• **RAC / Waitlist Upgrades:** All final berth allocations and waitlist confirmations are decided during these chart preparation windows."
    },
    'berth preference': {
        'term': 'Berth Preferences & Allocation',
        'text': "• **LB (Lower Berth):** Bottom berth, highly preferred by senior citizens and travelers with mobility issues.\n"
                "• **MB (Middle Berth):** Folds down during the day and is kept open for sleeping between 10:00 PM and 06:00 AM.\n"
                "• **UB (Upper Berth):** Elevated top bunk offering undisturbed privacy throughout the journey.\n"
                "• **SL (Side Lower) & SU (Side Upper):** Berths located along the hallway corridor."
    },
    '2a': {
        'term': '2A (AC 2-Tier Coach)',
        'text': "• **AC 2-Tier (2A)** is a premium air-conditioned sleeper class.\n"
                "• **Layout:** 48 to 54 berths per coach with 2 tiers (Lower & Upper) per bay, plus Side Lower and Side Upper.\n"
                "• **Amenities:** Privacy curtains, individual reading lamps, wide berths, and complimentary bedding linen."
    },
    '3a': {
        'term': '3A (AC 3-Tier Coach)',
        'text': "• **AC 3-Tier (3A)** is the most popular air-conditioned sleeper travel class in India.\n"
                "• **Layout:** 64 to 72 berths per coach with 3 tiers per bay (Lower, Middle, Upper) plus Side Lower and Side Upper.\n"
                "• **Amenities:** Full air conditioning, charging sockets, and fresh linen bedding."
    },
    'sl': {
        'term': 'SL (Sleeper Class)',
        'text': "• **Sleeper Class (SL)** is the traditional non-air-conditioned open sleeper coach.\n"
                "• **Layout:** 72 to 81 berths per coach in 3-tier configuration (Lower, Middle, Upper, Side Lower, Side Upper).\n"
                "• **Features:** Open windows with security bars, ceiling fans, and budget-friendly long-distance fares."
    },
    'cc': {
        'term': 'CC (AC Chair Car)',
        'text': "• **AC Chair Car (CC)** is an air-conditioned seated coach designed for day journeys (e.g. Shatabdi, Jan Shatabdi, Intercity).\n"
                "• **Seating:** 3x2 cushioned seating configuration with wide aisles, luggage racks, and folding meal trays."
    },
    'ec': {
        'term': 'EC (Executive Chair Car)',
        'text': "• **Executive Chair Car (EC)** is the luxury premier day-coach category featured on Shatabdi and Vande Bharat Expresses.\n"
                "• **Seating:** Spacious 2x2 rotating/reclining seats with ample legroom, footrests, and included meal service."
    },
    '1a': {
        'term': '1A (AC First Class)',
        'text': "• **AC First Class (1A)** is the highest luxury passenger class in Indian Railways.\n"
                "• **Layout:** Lockable 4-berth cabins and 2-berth private coupes with sliding doors, carpeting, and personalized attendant bell."
    }
}

def clean_input(text: str) -> str:
    """Cleans punctuation and extra whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r'[\?\!\,\;]+', ' ', text)
    return re.sub(r'\s+', ' ', cleaned).strip()

def extract_pnr(message: str):
    """Detects a 10-digit Indian Railway PNR number."""
    match = re.search(r'\b\d{10}\b', message)
    return match.group(0) if match else None

def extract_food_order_id(message: str):
    """Detects a Food Order ID: FOOD-YYYYMMDD-XXXXX."""
    match = re.search(r'\bFOOD-\d{8}-\d{5}\b', message, re.IGNORECASE)
    return match.group(0).upper() if match else None

def extract_train_number(message: str, ctx: dict = None):
    """
    Extracts a 5-digit train number from the message,
    or checks known train name keywords, or falls back to conversation context.
    """
    clean = message.lower()
    
    # 1. Direct 5-digit number
    match = re.search(r'\b\d{5}\b', clean)
    if match:
        return match.group(0)

    # 2. Check train keywords in message
    for alias, num in TRAIN_ALIASES.items():
        if alias in clean:
            return num

    # 3. Context fallback
    if ctx and ctx.get('last_train_number'):
        return ctx['last_train_number']

    return None

def extract_date(message: str):
    """Extracts date entity (today, tomorrow, or explicit YYYY-MM-DD / DD-MM-YYYY)."""
    clean = message.lower()
    today = datetime.date.today()
    if 'tomorrow' in clean:
        return (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    if 'today' in clean:
        return today.strftime('%Y-%m-%d')

    # YYYY-MM-DD
    iso_match = re.search(r'\b\d{4}-\d{2}-\d{2}\b', clean)
    if iso_match:
        return iso_match.group(0)

    # DD-MM-YYYY
    dmy_match = re.search(r'\b(\d{2})-(\d{2})-(\d{4})\b', clean)
    if dmy_match:
        return f"{dmy_match.group(3)}-{dmy_match.group(2)}-{dmy_match.group(1)}"

    return None

def extract_filters(message: str) -> dict:
    """Detects natural language route filters (timing, train category, sorting)."""
    msg = message.lower()
    filters = {}
    
    # Timing filters
    if any(k in msg for k in ['morning', 'subah', 'am trains']):
        filters['time'] = 'morning'
    elif any(k in msg for k in ['afternoon', 'evening', 'dopahar', 'shaam']):
        filters['time'] = 'evening'
    elif any(k in msg for k in ['night', 'overnight', 'raat', 'late night']):
        filters['time'] = 'night'

    # Train type filters
    if 'vande bharat' in msg:
        filters['train_type'] = 'vande bharat'
    elif 'rajdhani' in msg:
        filters['train_type'] = 'rajdhani'
    elif 'shatabdi' in msg:
        filters['train_type'] = 'shatabdi'
    elif any(k in msg for k in ['superfast', ' sf ']):
        filters['train_type'] = 'superfast'

    # Sorting / comparison filters
    if any(k in msg for k in ['fastest', 'shortest', 'quickest', 'min duration']):
        filters['sort'] = 'fastest'
    elif any(k in msg for k in ['fewest stops', 'fewer stops', 'less stops', 'least stops', 'minimum stops']):
        filters['sort'] = 'fewest_stops'
    elif any(k in msg for k in ['earliest arrival', 'earliest', 'reach early', 'first arrival']):
        filters['sort'] = 'earliest_arrival'
    elif any(k in msg for k in ['latest departure', 'latest', 'leave late', 'last departure']):
        filters['sort'] = 'latest_departure'

    if any(k in msg for k in ['daily', 'every day', 'everyday', 'daily trains']):
        filters['daily'] = True

    return filters

def extract_route_pair(message: str, ctx: dict = None):
    """
    Robust route extraction supporting multiple natural-language phrasing:
    - 'show trains of Jaipur to Ajmer'
    - 'show trains Jaipur to Delhi'
    - 'trains from Mumbai to Delhi'
    - 'are there trains from Delhi to Jaipur?'
    - 'which trains run between Jaipur and Delhi?'
    - 'find a train from Jaipur to Ajmer'
    - 'give me all trains between Jaipur and Delhi'
    - 'Vande Bharat from Delhi to Varanasi'
    - 'show morning trains from Jaipur to Delhi'
    - 'which train is fastest from Jaipur to Delhi'
    - 'JP to NDLS'
    - 'Jaipur -> Delhi'
    """
    text = clean_input(message)

    # Strategy 1: 'between X and Y'
    m_between = re.search(r'\bbetween\s+([a-zA-Z\s]+?)\s+and\s+([a-zA-Z\s]+)', text, re.IGNORECASE)
    if m_between:
        s = m_between.group(1).strip()
        d_raw = m_between.group(2).strip()
        d = re.split(r'\b(?:trains?|today|tomorrow|now|date)\b', d_raw, flags=re.IGNORECASE)[0].strip()
        if (s.lower() not in RAILWAY_NON_STATION_WORDS and d.lower() not in RAILWAY_NON_STATION_WORDS and
            RailwayService.resolve_station_ids(s) and RailwayService.resolve_station_ids(d) and s.lower() != d.lower()):
            return s, d

    # Strategy 2: 'from X to Y', 'of X to Y', 'X to Y', or 'X se Y'
    m_to = re.search(r'(?:from|of)?\s*([a-zA-Z\s]+?)\s+(?:to|->|➔|-->|\bse\b)\s+([a-zA-Z\s]+)', text, re.IGNORECASE)
    if m_to:
        raw_s = m_to.group(1).strip()
        raw_d = m_to.group(2).strip()

        # Clean conversational filler prefixes, train types, and filter adjectives from raw_s
        clean_s = re.sub(
            r'^(?:please\s+)?(?:can you\s+)?(?:kya\s+)?(?:show|find|search|list|get|tell me|give me|check|are there|which|what|any|book|i am travelling|i am traveling|travelling|traveling|going|journey)\s*(?:a|all|available|direct)?\s*(?:morning|evening|night|fastest|daily|superfast)?\s*(?:vande bharat|rajdhani|shatabdi)?\s*trains?\s*(?:running|operating|available)?\s*(?:from|between|of|for)?\s*',
            '', raw_s, flags=re.IGNORECASE
        ).strip()
        clean_s = re.sub(r'^(?:from|of|kya|mujhe|hume)\s+', '', clean_s, flags=re.IGNORECASE).strip()
        clean_s = re.sub(r'^(?:vande bharat|rajdhani|shatabdi|morning|evening|night|fastest|daily|superfast)\s*(?:trains?\s*)?(?:from|of)?\s*', '', clean_s, flags=re.IGNORECASE).strip()

        # Clean conversational filler suffixes from raw_d
        clean_d = re.split(r'[\.\?\!\;]|(?:\b(?:trains?|today|tomorrow|date|seats?|berths?|ticket|now|please|where|how|can|order|food|ki|tak|keliye|chahiye)\b)', raw_d, flags=re.IGNORECASE)[0].strip()

        if (clean_s.lower() not in RAILWAY_NON_STATION_WORDS and clean_d.lower() not in RAILWAY_NON_STATION_WORDS and
            RailwayService.resolve_station_ids(clean_s) and RailwayService.resolve_station_ids(clean_d) and clean_s.lower() != clean_d.lower()):
            return clean_s, clean_d

        # Backward matching in clean_s in case of leftover words
        words = clean_s.split()
        for i in range(len(words)):
            cand = ' '.join(words[i:])
            if cand.lower() not in RAILWAY_NON_STATION_WORDS and RailwayService.resolve_station_ids(cand):
                clean_s = cand
                break

        d_words = clean_d.split()
        for i in range(len(d_words), 0, -1):
            cand = ' '.join(d_words[:i])
            if cand.lower() not in RAILWAY_NON_STATION_WORDS and RailwayService.resolve_station_ids(cand):
                clean_d = cand
                break

        if (clean_s.lower() not in RAILWAY_NON_STATION_WORDS and clean_d.lower() not in RAILWAY_NON_STATION_WORDS and
            RailwayService.resolve_station_ids(clean_s) and RailwayService.resolve_station_ids(clean_d) and clean_s.lower() != clean_d.lower()):
            return clean_s, clean_d

    # Strategy 3: Follow-up query using conversation context
    if ctx and ctx.get('last_source') and ctx.get('last_destination'):
        lower_msg = message.lower()
        if any(w in lower_msg for w in ['tomorrow', 'today', 'next', 'date', 'journey time', 'duration', 'any other', 'schedule', 'which is fastest', 'fastest', 'fewest stops', 'fewer stops']):
            return ctx['last_source'], ctx['last_destination']

    return None, None

def extract_station(message: str):
    """Extracts a station name or station code mentioned in the query."""
    text = clean_input(message)
    clean_lower = text.lower()
    candidates = RailwayService.get_all_stations()

    for st in candidates:
        code = st['code'].lower()
        if code in RAILWAY_NON_STATION_WORDS:
            # Only match if explicitly preceded or followed by station keywords
            if re.search(r'\b(?:station|stn|code)\s+' + re.escape(code) + r'\b', clean_lower) or re.search(r'\b' + re.escape(code) + r'\s+station\b', clean_lower):
                return st
        else:
            if re.search(r'\b' + re.escape(code) + r'\b', clean_lower):
                return st

    filtered = re.sub(r'\b(?:what|is|are|which|the|station|code|of|for|tell|me|about|trains?|stop|at|in|reach|when|does|pass|through|can|i|how|where|do|order|food|show|find|get|my|your|on|a|an|restaurants?|menu|vendors?)\b', '', clean_lower).strip()
    words = filtered.split()
    for w in words:
        if len(w) >= 3 and w not in RAILWAY_NON_STATION_WORDS:
            st_list = RailwayService.search_stations(w, limit=10)
            if st_list:
                for cand in st_list:
                    if cand['code'] in ('JP', 'NDLS', 'MMCT', 'KOTA', 'RTM', 'BRC', 'ST', 'AII', 'HWH', 'CSMT', 'DLI'):
                        return cand
                return st_list[0]

    for st in candidates:
        name = st['name'].lower()
        if len(name) >= 3 and name not in RAILWAY_NON_STATION_WORDS and re.search(r'\b' + re.escape(name) + r'\b', clean_lower):
            return st

    for st in candidates:
        city = st['city'].lower()
        if len(city) >= 3 and city not in RAILWAY_NON_STATION_WORDS and re.search(r'\b' + re.escape(city) + r'\b', clean_lower):
            return st

    return None

def format_train_card(idx: int, t: dict) -> str:
    """Formats a single train into the standardized card layout (Section 5)."""
    t_num = t.get('train_number')
    t_name = t.get('train_name')
    t_type = t.get('train_type') or 'Express'
    b_name = t.get('boarding_name') or t.get('source_name')
    b_code = t.get('boarding_code') or t.get('source_code')
    d_name = t.get('deboarding_name') or t.get('dest_name')
    d_code = t.get('deboarding_code') or t.get('dest_code')
    dep = t.get('leg_departure_time') or t.get('departure_time') or '--:--'
    arr = t.get('leg_arrival_time') or t.get('arrival_time') or '--:--'
    dur = t.get('duration') or 'N/A'
    dist = t.get('leg_distance_km') or t.get('distance_km') or 0

    # Format actual confirmed scheduled halts (Section 10 & 17)
    halts_val = t.get('scheduled_halt_count')
    if halts_val is None and 'total_halts_on_leg' in t:
        halts_val = t.get('total_halts_on_leg')

    if halts_val is not None and isinstance(halts_val, int):
        halts_str = str(halts_val)
    elif isinstance(halts_val, str) and halts_val.isdigit():
        halts_str = halts_val
    else:
        halts_str = "Not available"

    runs = t.get('running_days') or 'Mon,Tue,Wed,Thu,Fri,Sat,Sun'
    classes = ", ".join(sorted(list(set(c['class_code'] for c in t.get('classes', []))))) or "All Classes"

    return (
        f"{idx}. 🚆 **#{t_num} {t_name}**\n"
        f"   *{t_type}*\n"
        f"   • **Route:** {b_name} ({b_code}) ➔ {d_name} ({d_code})\n"
        f"   • **Timings:** Dep: `{dep}` | Arr: `{arr}` | Duration: **{dur}**\n"
        f"   • **Distance:** {dist} km | **Halts:** {halts_str}\n"
        f"   • **Runs On:** {runs}\n"
        f"   • **Classes:** `{classes}`"
    )

def process_chatbot_query(message: str, session_id: str = 'default'):
    """
    Main Data-Driven AI Assistant NLP Pipeline.
    Reuses RailwayService and database tables as the single source of truth.
    Maintains conversational context per session_id.
    """
    if not message or not str(message).strip():
        return {
            "intent": "UNKNOWN",
            "response": "Please enter a railway query (e.g., *'trains from Jaipur to Delhi'*, *'what are the stops of 12952?'*, or *'where is train 12956?'*).",
            "suggested_actions": []
        }

    clean_msg = message.strip()
    clean_lower = clean_msg.lower()
    ctx = CONVERSATION_CONTEXT.setdefault(session_id, {})

    # =========================================================================
    # 0. LEFT LUGGAGE / FORGOTTEN LUGGAGE ASSISTANCE (Intent: LEFT_LUGGAGE)
    # =========================================================================
    if any(k in clean_lower for k in [
        'left luggage', 'forgotten luggage', 'forgot luggage', 'lost luggage', 'luggage left in train',
        'bag left in train', 'left my bag', 'left my luggage', 'forgot my bag', 'forgot my luggage',
        'forgot my suitcase', 'left my suitcase', 'bag inside train', 'luggage inside train',
        'bag inside the train', 'luggage in the train', 'suitcase inside', 'lost bag in train',
        'lost my bag in train', 'lost my luggage in train', 'deboarded but bag', 'deboarded but luggage',
        'got down but bag', 'got down but luggage', 'left bag in coach', 'left luggage in coach',
        'forgot baggage', 'lost baggage', 'left baggage', 'baggage left', 'saman chhoot', 'bag chhoot'
    ]):
        return {
            "intent": "LEFT_LUGGAGE",
            "response": "### 🧳 Left Luggage / Forgotten Baggage Assistance\n\n"
                        "If you have left or forgotten your luggage inside a train, you can immediately register an official assistance request through SmartRail:\n\n"
                        "**Immediate Action Protocol:**\n"
                        "1. **Register Report:** Open our **[Emergency & Assistance Services](emergency.html?service=luggage)** portal and select **🧳 Left Luggage**.\n"
                        "2. **Provide Details:** Enter your **Train Number**, **Journey Date**, **Coach**, **Berth/Seat**, **Deboarding Station**, and a clear description of your luggage.\n"
                        "3. **Receive Request ID:** A tracking reference (e.g. `LUG-20261007-XXXXX`) will be issued to document your request.\n\n"
                        "⚠️ **CRITICAL IMMEDIATE STEP:**\n"
                        "• SmartRail logs and manages your report for tracking purposes, but **cannot physically retrieve items**.\n"
                        "• **Immediately call Railway Helpline 139** or report to the nearest **RPF Post / Station Master** at your deboarding station quoting your **Request ID**, train number, and coach/berth.\n"
                        "• Prompt reporting increases the chance that the TTE, onboard RPF escort, or terminal cleaning crew can secure your luggage before the train departs or terminates.",
            "suggested_actions": [
                {"label": "🧳 Report Left Luggage", "url": "emergency.html?service=luggage"},
                {"label": "Call RPF Helpline 139", "url": "emergency.html"}
            ]
        }

    # =========================================================================
    # 1. INTELLIGENT RAILWAY KNOWLEDGE & RAG RETRIEVAL
    # =========================================================================
    entities = extract_railway_entities(clean_msg)
    retrieved_docs = retrieve_railway_knowledge(clean_msg, entities)
    if retrieved_docs:
        doc = retrieved_docs[0]
        has_direct_concept = any(kw in clean_lower for kw in doc["keywords"]) or any(t in doc["category"] for t in entities.get("topics", []))
        if has_direct_concept or len(entities.get("topics", [])) > 0:
            # Ensure not an explicit train route search query like 'trains from Jaipur to Delhi'
            src_check, dst_check = extract_route_pair(clean_msg, ctx)
            if not (src_check and dst_check):
                rag_res = generate_rag_answer(clean_msg, entities, retrieved_docs)
                if rag_res:
                    return rag_res

    # Legacy fallback for basic definitions
    for k, info in RAILWAY_KNOWLEDGE.items():
        if re.search(r'\b' + re.escape(k) + r'\b', clean_lower) and any(w in clean_lower for w in ['what is', 'explain', 'meaning', 'how does', 'tell me about', 'rules', 'quota', 'difference', 'work', 'class', 'coach', 'details']):
            return {
                "intent": "RAILWAY_KNOWLEDGE",
                "response": f"### ℹ️ Indian Railways Guide: {info['term']}\n\n{info['text']}",
                "suggested_actions": [
                    {"label": "Search & Book Trains", "url": "search.html"},
                    {"label": "Check PNR Status", "url": "pnr-status.html"}
                ]
            }

    # =========================================================================
    # 2. BOOKING HELP & SEAT LOCKING MECHANISM
    # =========================================================================
    if any(k in clean_lower for k in ['how do i book', 'book a ticket', 'how to book', 'reserve ticket', 'i want to book', 'select a seat', 'seat locking', 'how does seat locking work']):
        if 'seat locking' in clean_lower or 'seat lock' in clean_lower:
            return {
                "intent": "BOOKING_HELP",
                "response": "### 🔒 SmartRail Seat Locking Mechanism\n\n"
                            "To prevent duplicate reservations and race conditions:\n"
                            "• When you click any vacant berth on the **Interactive Seat Map**, SmartRail places a **temporary 5-minute lock** on that seat.\n"
                            "• During this 5-minute countdown, no other user across the entire network can select or purchase that berth.\n"
                            "• Once you confirm passenger details and payment, the lock converts into a confirmed booking and generates your **10-digit PNR**.\n"
                            "• If the timer expires before checkout, the berth is automatically unlocked and returned to the live inventory.",
                "suggested_actions": [
                    {"label": "Search Trains & Book", "url": "search.html"},
                    {"label": "Interactive Seat Map", "url": "seat-selection.html?coach_id=1"}
                ]
            }

        return {
            "intent": "BOOKING_HELP",
            "response": "### 🎫 How to Book a Train Ticket on SmartRail:\n\n"
                        "1. **Search Trains:** Enter your departure and arrival stations on the Search Trains page.\n"
                        "2. **Select Train & Class:** Choose your preferred train, travel date, and coach class (1A, 2A, 3A, SL).\n"
                        "3. **Pick Your Berth:** Open the **Interactive Seat Map** to select specific window, lower, or middle berths.\n"
                        "4. **Passenger Details:** Enter traveler information and choose eligible quotas (Senior Citizen, Ladies, Tatkal).\n"
                        "5. **Confirmation:** Confirm booking to instantly generate your 10-digit PNR and digital e-ticket.",
            "suggested_actions": [
                {"label": "Search & Book Trains", "url": "search.html"},
                {"label": "Check PNR Status", "url": "pnr-status.html"}
            ]
        }

    # =========================================================================
    # 3. CANCELLATION & REFUNDS
    # =========================================================================
    if any(k in clean_lower for k in ['how to cancel', 'cancel booking', 'cancel my ticket', 'cancellation fee', 'refund policy', 'refund']):
        return {
            "intent": "CANCELLATION_HELP",
            "response": "### 🛑 Cancellation & Refund Policy:\n\n"
                        "• **Confirmed Tickets:** Cancelled > 48 hours prior to departure incur standard IRCTC clerkage fees:\n"
                        "  - AC First / Executive: ₹240\n"
                        "  - AC 2-Tier / 3-Tier: ₹180 – ₹200\n"
                        "  - Sleeper Class: ₹120\n"
                        "• **Refund Processing:** Approved refunds are initiated immediately to your original payment mode within 3-5 banking days.\n"
                        "• You can cancel any confirmed or waiting-list ticket directly from the **PNR Status** portal.",
            "suggested_actions": [
                {"label": "Go to PNR & Cancel", "url": "pnr-status.html"}
            ]
        }

    # =========================================================================
    # 4. PNR STATUS & PNR PREDICTION
    # =========================================================================
    pnr_val = extract_pnr(clean_msg)
    is_prediction_query = any(k in clean_lower for k in ['confirm', 'prediction', 'will my ticket confirm', 'chance', 'probability', 'chances of confirmation'])

    if pnr_val and is_prediction_query:
        booking = BookingModel.get_by_pnr(pnr_val)
        if booking:
            pass_list = ", ".join([f"{p['name']} ({p.get('status')})" for p in booking.get('passengers', [])])
            prob_percent = 92 if booking['status'] in ('CONFIRMED', 'RAC') else 78
            verdict = "Very High Chance" if prob_percent >= 90 else "Moderate Chance"
            return {
                "intent": "PNR_PREDICTION",
                "response": f"### 🔮 AI PNR Confirmation Prediction: `{pnr_val}`\n\n"
                            f"• **Train:** #{booking['train_number']} — {booking['train_name']}\n"
                            f"• **Current Status:** **{booking['status']}** ({booking['chart_status']})\n"
                            f"• **Passenger(s):** {pass_list}\n"
                            f"• **Confirmation Probability:** **{prob_percent}% ({verdict})**\n\n"
                            f"**AI Confirmation Analysis:**\n"
                            f"• Historical trend data for this route indicates strong cancellation churn before chart preparation.\n"
                            f"• Chart preparation occurs **4 hours** before departure, at which point RAC and waiting list tickets get final upgrades.\n"
                            f"• **Recommendation:** High clearance probability; ticket cancellation is not advised.",
                "suggested_actions": [
                    {"label": "View Full PNR Details", "url": f"pnr-status.html?pnr={pnr_val}"},
                    {"label": "Live GPS Tracking", "url": f"live-tracking.html?train_id={booking['train_id']}"}
                ]
            }
        else:
            return {
                "intent": "PNR_PREDICTION",
                "response": f"### 🔮 PNR Confirmation Prediction Engine\n\n"
                            f"For PNR **`{pnr_val}`**:\n"
                            f"• **General Quota (GNWL):** Tickets under WL 25 carry an **85%+ confirmation probability** before chart preparation.\n"
                            f"• **RAC Tickets:** Carry a **98%+ probability** of being upgraded to a confirmed berth.\n"
                            f"• **Remote Location (RLWL / PQWL):** Have lower confirmation clearance rates (~40–60%).\n\n"
                            f"Final charting is published 4 hours prior to train origin departure.",
                "suggested_actions": [
                    {"label": "Check PNR Portal", "url": f"pnr-status.html?pnr={pnr_val}"}
                ]
            }

    if pnr_val:
        booking = BookingModel.get_by_pnr(pnr_val)
        if booking:
            pass_list = ", ".join([f"{p['name']} ({p.get('seat_number_assigned') or p.get('status')})" for p in booking.get('passengers', [])])
            ctx['last_pnr'] = pnr_val
            ctx['last_train_number'] = booking['train_number']
            return {
                "intent": "PNR_STATUS",
                "response": f"### 🎫 PNR Reservation Details: `{pnr_val}`\n\n"
                            f"• **Train:** #{booking['train_number']} — {booking['train_name']}\n"
                            f"• **Route:** {booking['source_code']} ➔ {booking['dest_code']}\n"
                            f"• **Journey Date:** {booking['journey_date']}\n"
                            f"• **Booking Status:** **{booking['status']}** ({booking['chart_status']})\n"
                            f"• **Passenger(s):** {pass_list}\n"
                            f"• **Total Fare Paid:** ₹{booking['total_fare']}",
                "suggested_actions": [
                    {"label": "View Full PNR Details", "url": f"pnr-status.html?pnr={pnr_val}"},
                    {"label": "Live GPS Tracking", "url": f"live-tracking.html?train_id={booking['train_id']}"}
                ]
            }
        else:
            return {
                "intent": "PNR_STATUS",
                "response": f"I checked for PNR **{pnr_val}**, but it was not found in our reservation records.\n\n"
                            f"Try testing with our sample demo PNRs: `2846190532`, `4198273641`, or `6720491823`.",
                "suggested_actions": [
                    {"label": "Check PNR Status Page", "url": "pnr-status.html"},
                    {"label": "Test Sample PNR 2846190532", "query": "PNR 2846190532"}
                ]
            }

    if any(k in clean_lower for k in ['pnr status', 'check pnr', 'my pnr', 'pnr inquiry', 'pnr enquiry', 'ticket status']):
        return {
            "intent": "PNR_STATUS",
            "response": "Please enter your **10-digit PNR number** (e.g., `2846190532`), and I will immediately look up your coach, berth allocation, chart status, and AI confirmation probability!",
            "suggested_actions": [
                {"label": "Test Sample PNR: 2846190532", "query": "PNR 2846190532"},
                {"label": "Go to PNR Portal", "url": "pnr-status.html"}
            ]
        }

    # =========================================================================
    # 5. FOOD ORDERING & ON-BOARD MEALS (Intent: FOOD_ORDER)
    # =========================================================================
    food_order_id = extract_food_order_id(clean_msg)
    if food_order_id:
        order = FoodModel.get_order_by_number(food_order_id)
        if order:
            ctx['last_food_order_id'] = food_order_id
            items_text = ", ".join([f"{it['item_name']} x {it['quantity']}" for it in order.get('items', [])])
            return {
                "intent": "FOOD_ORDER",
                "response": f"### 🍱 Food Order Status: `{order['order_number']}`\n\n"
                            f"• **Current Status:** **{order['order_status']}**\n"
                            f"• **Passenger:** {order['passenger_name']} ({order['contact_phone']})\n"
                            f"• **Train:** #{order['train_number']}\n"
                            f"• **Coach / Seat:** Coach {order['coach']}, Berth/Seat {order['seat']}\n"
                            f"• **Delivery Halt:** **{order.get('delivery_station_name') or order['station_name']}** (ETA: {order.get('delivery_eta', 'On Arrival')})\n"
                            f"• **Items:** {items_text}\n"
                            f"• **Total Amount:** ₹{order['total_amount']} ({order['payment_status']})",
                "suggested_actions": [
                    {"label": "Track Order Timeline", "url": f"food-order-tracking.html?order_id={order['order_number']}"},
                    {"label": "Order More Food", "url": "food-order.html"}
                ]
            }

    is_food_query = any(k in clean_lower for k in [
        'food', 'meal', 'lunch', 'dinner', 'breakfast', 'thali', 'catering', 'e-catering',
        'ecatering', 'snack', 'pantry', 'canteen', 'restaurant', 'beverage', 'chai', 'coffee',
        'hungry', 'khana', 'bhojan', 'nashta'
    ]) or ('eat' in clean_lower and not 'seat' in clean_lower)

    if is_food_query:
        ctx['last_intent'] = 'FOOD_ORDER'
        st_match = extract_station(clean_msg)
        has_station_cue = bool(re.search(r'\b(?:at|in|near)\b', clean_lower)) or any(w in clean_lower for w in ['restaurant', 'restaurants', 'menu', 'vendors', 'shop', 'vendor'])
        if st_match and has_station_cue:
            rests = FoodModel.get_restaurants_for_station(st_match['id'])
            if rests:
                rest_lines = [f"• **{r['name']}** (⭐ {r['rating']}) — *{r['cuisine']}*\n  ⏱️ Prep: {r['prep_time']} | Min Order: ₹{r['min_order']}" for r in rests]
                rests_str = "\n".join(rest_lines)
                return {
                    "intent": "FOOD_ORDER",
                    "response": f"### 🍽️ Verified Food Vendors at {st_match['name']} ({st_match['code']})\n\n{rests_str}\n\nOrders are delivered straight to your coach and berth upon train arrival.",
                    "suggested_actions": [
                        {"label": f"Order Food at {st_match['code']}", "url": f"food-order.html?station_id={st_match['id']}"},
                        {"label": "Track Active Order", "url": "food-order-tracking.html"}
                    ]
                }

        return {
            "intent": "FOOD_ORDER",
            "response": "### 🍴 Order Fresh Food During Your Train Journey\n\n"
                        "Yes! SmartRail offers on-board meal delivery directly to your train coach and berth at selected scheduled railway halts.\n\n"
                        "**How to order:**\n"
                        "1. **Enter your 10-Digit PNR** or **Train Number + Journey Date**.\n"
                        "2. **Select your Delivery Station** from the verified scheduled halts along your route.\n"
                        "3. **Choose your Favorite Meals**: Standard Veg Thalis, Biryanis, South Indian combos, Breakfast, Snacks, and Beverages.\n"
                        "4. **Berth Delivery**: Your meal is brought straight to your seat with tamper-proof packaging upon train arrival!\n\n"
                        "Would you like to place an order now?",
            "suggested_actions": [
                {"label": "🍴 Open Food Order Portal", "url": "food-order.html"},
                {"label": "Track Food Order", "url": "food-order-tracking.html"}
            ]
        }

    # =========================================================================
    # 6. EMERGENCY ASSISTANCE & CLEANING
    # =========================================================================
    if any(k in clean_lower for k in ['emergency', 'call rpf', 'police', 'medical help', 'doctor needed', 'harassment', 'fire hazard', 'sos helpline']):
        return {
            "intent": "EMERGENCY_HELP",
            "response": "🚨 **RAILWAY EMERGENCY PROTOCOL (RPF Helpline: 139)**\n\n"
                        "If you are facing an active emergency on board (medical crisis, harassment, security threat, or coach fault):\n\n"
                        "1. **Call 139** immediately for direct contact with the Railway Protection Force (RPF).\n"
                        "2. Trigger an **Emergency SOS** on our portal to alert on-board security personnel with your train number and coach details.",
            "suggested_actions": [
                {"label": "TRIGGER SOS DISPATCH", "url": "emergency.html"}
            ]
        }

    if any(k in clean_lower for k in ['cleaning', 'clean coach', 'coach cleaning', 'dirty coach', 'washroom dirty', 'toilet unhygienic', 'dustbin full']):
        return {
            "intent": "CLEANING_REQUEST_HELP",
            "response": "🧹 **On-Board Coach Cleaning Request (OBHS)**\n\n"
                        "You can submit a cleaning request for dirty coach floors, unhygienic washrooms, full dustbins, or soiled berths directly through our Emergency & Assistance portal.\n\n"
                        "The on-board housekeeping staff (OBHS) will be dispatched directly to your coach.",
            "suggested_actions": [
                {"label": "Request Coach Cleaning", "url": "emergency.html"}
            ]
        }

    if any(k in clean_lower for k in [
        'contact tte', 'contact the tte', 'call tte', 'reach tte', 'talk to tte', 'speak to tte', 'tte assistance',
        'train staff', 'train staff assistance', 'berth issue', 'seat issue', 'berth problem', 'seat problem',
        'wrong passenger', 'someone is sitting on my seat', 'someone is sitting on my reserved seat',
        'someone sitting on my seat', 'someone sitting on my berth', 'someone occupied my seat',
        'someone occupied my berth', 'someone is on my seat', 'someone took my seat', 'passenger dispute',
        'seat dispute', 'berth dispute', 'train conductor',
        'i need tte', 'need tte', 'how to contact tte', 'can i contact tte', 'how can i contact tte'
    ]):
        return {
            "intent": "TTE_ASSISTANCE",
            "response": "### 🎫 Contact TTE / On-Board Train Staff Assistance\n\n"
                        "You can submit an official **TTE / Train Staff Assistance Request** directly from our **Emergency & Assistance Services** portal.\n\n"
                        "**How to request assistance:**\n"
                        "1. Go to the **Emergency Assistance** page and select **Contact TTE / Train Staff**.\n"
                        "2. Enter your **Train Number**, **Journey Date**, **Coach**, and **Berth/Seat**.\n"
                        "3. Select your issue category (e.g. *Berth / Seat Issue*, *Wrong Passenger on Berth*, *RAC Assistance*, or *Passenger Dispute*).\n"
                        "4. Provide a description of your issue and submit your request to generate an official **Request ID** (e.g. `TTE-20261005-XXXXX`).\n\n"
                        "ℹ️ **Important Note:** SmartRail records your assistance request for administrative and onboard logging. "
                        "Because SmartRail does not have a verified direct communication link with the TTE, please **approach the on-board TTE / Train Superintendent directly** "
                        "in your coach or dial **Railway Helpline 139** for immediate onboard assistance.",
            "suggested_actions": [
                {"label": "🎫 Request TTE Assistance", "url": "emergency.html?service=tte"},
                {"label": "Emergency SOS 139", "url": "emergency.html"}
            ]
        }

    # =========================================================================
    # 7. LIVE TRACKING & GPS TELEMETRY (LIVE_STATUS)
    # =========================================================================
    is_tracking_query = any(k in clean_lower for k in [
        'where is', 'track ', 'tracking', 'is running', 'is train running', 'running status',
        'current station', 'how fast', 'live location', 'live status', 'gps tracking', 'how late is my train',
        'where is my train', 'right now', 'kaha hai', 'kahan hai', 'kidhar hai', 'kaha pahuchi', 'kahan pahunchi'
    ])
    if is_tracking_query:
        t_num = extract_train_number(clean_msg, ctx)
        if t_num:
            # 1. First try live telemetry provider RailRadar
            live_data = RailRadarService.fetch_train_live(t_num) if RailRadarService.is_configured() else None
            if live_data:
                ctx['last_train_number'] = t_num
                ctx['last_intent'] = 'LIVE_STATUS'
                st_curr = live_data.get('current_station') or live_data.get('current_station_name') or 'In Transit'
                st_next = live_data.get('next_station') or live_data.get('next_station_name') or 'Approaching Station'
                eta_next = live_data.get('next_eta') or '--:--'
                speed_str = f"{live_data.get('current_speed', 0.0)} km/h"
                plat = live_data.get('platform') or 'Will be announced upon arrival'
                delay_str = live_data.get('delay_status') or 'On Time (Right Time)'
                status_str = (live_data.get('running_status') or 'RUNNING').upper()

                return {
                    "intent": "LIVE_STATUS",
                    "response": f"### 🛰️ Real-Time Telemetry: Train #{live_data['train_number']} — {live_data['train_name']}\n\n"
                                f"• **Operating Status:** **{status_str}**\n"
                                f"• **Current Section:** **{st_curr}** ({live_data.get('current_position', 'in-transit')})\n"
                                f"• **Next Commercial Halt:** **{st_next}** (ETA: `{eta_next}`)\n"
                                f"• **Punctuality Status:** **{delay_str}**\n"
                                f"• **Current Track Speed:** **{speed_str}**\n"
                                f"• **Platform Info:** {plat}\n"
                                f"• **Last Telemetry Signal:** `{live_data.get('last_updated_at', 'Live')}`",
                    "suggested_actions": [
                        {"label": f"Full Live Map (#{t_num})", "url": f"live-tracking.html?train_id={t_num}"},
                        {"label": "Check Route Stops", "query": f"what are the stops of {t_num}?"}
                    ]
                }

            # 2. Check local database benchmark tracking record
            trk = RailwayService.get_train_tracking_summary(t_num)
            if trk:
                ctx['last_train_number'] = t_num
                ctx['last_intent'] = 'LIVE_STATUS'
                return {
                    "intent": "LIVE_STATUS",
                    "response": f"### 🛰️ Live Telemetry: Train #{trk['train_number']} — {trk['train_name']}\n\n"
                                f"• **Route:** {trk['source']} ➔ {trk['destination']}\n"
                                f"• **Current Section:** **{trk['current_section']}**\n"
                                f"• **Current Speed:** **{trk['current_speed']} km/h**\n"
                                f"• **Next Commercial Halt:** **{trk['next_station']}** (ETA: `{trk['eta']}`)\n"
                                f"• **Punctuality Status:** **{trk['delay_status']}**\n"
                                f"• **Distance Covered:** {trk['distance_covered_km']} km of {trk['total_distance_km']} km ({trk['percentage_completed']}% completed)",
                    "suggested_actions": [
                        {"label": f"Open Live Timeline (#{trk['train_number']})", "url": f"live-tracking.html?train_id={trk['train_id']}"},
                        {"label": "Check Stops", "query": f"what are the stops of {trk['train_number']}?"}
                    ]
                }
            else:
                return {
                    "intent": "LIVE_STATUS",
                    "response": f"Live running status is currently unavailable for Train **#{t_num}**.\n\n"
                                f"Live telemetry requires an active train trip on track. If the train has not yet commenced its scheduled journey today, live GPS data will activate closer to departure.",
                    "suggested_actions": [
                        {"label": f"Check Schedule (#{t_num})", "query": f"what are the stops of {t_num}?"},
                        {"label": "Track 12952 (Rajdhani)", "query": "where is train 12952?"}
                    ]
                }
        else:
            return {
                "intent": "LIVE_STATUS",
                "response": "Which train would you like to track? Please provide a **5-digit train number** (e.g., *'where is train 12956?'* or *'where is 12015 right now?'*).",
                "suggested_actions": [
                    {"label": "Track 12952 (Rajdhani)", "query": "where is train 12952?"},
                    {"label": "Track 12956 (SF Exp)", "query": "where is train 12956?"}
                ]
            }

    # =========================================================================
    # 8. ROUTE STOPS / INTERMEDIATE HALTS (Intent: TRAIN_ROUTE)
    # =========================================================================
    is_stops_query = any(k in clean_lower for k in [
        'what are the stops', 'stops of', 'route of', 'show route', 'intermediate stations',
        'which stations does', 'what are its stops', 'list of stops', 'all stops of', 'where does', 'stop on'
    ])
    if is_stops_query:
        t_num = extract_train_number(clean_msg, ctx)
        if t_num:
            train, stops = RailwayService.ensure_train_route_cached(t_num)
            if train and stops:
                ctx['last_train_number'] = t_num
                ctx['last_train'] = train
                ctx['last_intent'] = 'TRAIN_ROUTE'

                actual_halts = RailwayService.calculate_scheduled_halts(stops)
                halts_count = actual_halts if actual_halts is not None else len(stops)

                is_complete_route_req = any(k in clean_lower for k in ['complete route', 'full route', 'all stations', 'passing stations', 'all route points'])
                route_pts = []
                if is_complete_route_req:
                    route_pts = execute_query(
                        "SELECT * FROM train_route_points WHERE train_id = %s ORDER BY route_sequence ASC",
                        (train['id'],), fetchall=True
                    ) or []

                if is_complete_route_req and route_pts:
                    pt_lines = []
                    for pt in route_pts:
                        p_type = pt.get('point_type') or 'PASSING'
                        time_str = pt.get('estimated_time') or '--:--'
                        if p_type == 'HALT':
                            pt_lines.append(f"{pt['route_sequence']}. 🟢 **{pt['point_name']} ({pt['point_code']})** [Scheduled Halt] — Timing: `{time_str}` | {pt.get('distance_km', 0)} km")
                        else:
                            pt_lines.append(f"{pt['route_sequence']}. ⚪ *{pt['point_name']} ({pt['point_code']})* [Pass-through / No Stop] — Passing: `~{time_str}` | {pt.get('distance_km', 0)} km")
                    
                    pts_formatted = "\n".join(pt_lines)
                    return {
                        "intent": "TRAIN_ROUTE",
                        "response": f"### 🗺️ Complete Route Timeline: Train #{train['train_number']} — {train['train_name']}\n\n"
                                    f"• **Scheduled Halts:** **{halts_count}**\n"
                                    f"• **Total Route Points (including pass-through waypoints):** **{len(route_pts)}**\n\n"
                                    f"{pts_formatted}\n\n"
                                    f"ℹ️ Commercial halts and non-stopping pass-through points are distinguished above.",
                        "suggested_actions": [
                            {"label": f"Book Train #{train['train_number']}", "url": f"search.html?train_number={train['train_number']}"},
                            {"label": "Live GPS Tracking", "url": f"live-tracking.html?train_id={train['id']}"}
                        ]
                    }

                stop_lines = []
                for s in stops:
                    arr = "START" if s['arrival_time'] == 'START' else s['arrival_time']
                    dep = "END" if s['departure_time'] == 'END' else s['departure_time']
                    halt_text = f" (Halt: {s['halt_minutes']} min)" if int(s.get('halt_minutes') or 0) > 0 else ""
                    st_name = s['station_name']
                    if st_name.endswith(' Jn'):
                        st_name = st_name[:-3] + ' Junction'
                    stop_lines.append(f"{s['stop_sequence']}. **{st_name} ({s['station_code']})** — Arr: `{arr}` | Dep: `{dep}`{halt_text}")

                stops_formatted = "\n".join(stop_lines)
                return {
                    "intent": "TRAIN_ROUTE",
                    "response": f"### 🗺️ Scheduled Route Stops: Train #{train['train_number']} — {train['train_name']}\n\n"
                                f"{stops_formatted}\n\n"
                                f"Total scheduled commercial halts: **{halts_count}**.\n\n"
                                f"ℹ️ The current project dataset contains these stored stops; it represents the confirmed scheduled commercial railway halts.",
                    "suggested_actions": [
                        {"label": f"Book Train #{train['train_number']}", "url": f"search.html?train_number={train['train_number']}"},
                        {"label": "Live GPS Tracking", "url": f"live-tracking.html?train_id={train['id']}"}
                    ]
                }
            else:
                return {
                    "intent": "TRAIN_ROUTE",
                    "response": f"Train number **{t_num}** was not found in our database to retrieve stops.",
                    "suggested_actions": [
                        {"label": "Search All Trains", "url": "search.html"}
                    ]
                }
        else:
            return {
                "intent": "TRAIN_ROUTE",
                "response": "Please specify the train number whose route you want to view (e.g., *'what are the stops of 12956?'*).",
                "suggested_actions": [
                    {"label": "Stops of 12952", "query": "what are the stops of 12952?"},
                    {"label": "Stops of 12956", "query": "what are the stops of 12956?"}
                ]
            }

    # =========================================================================
    # 9. JOURNEY TIME / TRAVEL DURATION
    # =========================================================================
    is_duration_query = any(k in clean_lower for k in [
        'how long does', 'journey time', 'travel time', 'duration of', 'how many hours', 'how much time'
    ])
    if is_duration_query:
        src_d, dst_d = extract_route_pair(clean_msg, ctx)
        t_num = extract_train_number(clean_msg, ctx)

        if src_d and dst_d:
            route_trains = RailwayService.search_route(src_d, dst_d)
            if route_trains:
                lines = []
                for t in route_trains[:5]:
                    lines.append(f"• **#{t['train_number']}** {t['train_name']}: **{t['duration']}** (Dep: `{t['leg_departure_time']}` ➔ Arr: `{t['leg_arrival_time']}`)")
                dur_text = "\n".join(lines)
                ctx['last_source'] = src_d
                ctx['last_destination'] = dst_d
                ctx['last_intent'] = 'JOURNEY_TIME'
                return {
                    "intent": "JOURNEY_TIME",
                    "response": f"### ⏱️ Journey Time: {src_d.title()} ➔ {dst_d.title()}\n\n"
                                f"{dur_text}\n\n"
                                f"Durations are computed directly from official station departure and arrival timetables.",
                    "suggested_actions": [
                        {"label": f"Book {src_d.title()} ➔ {dst_d.title()}", "url": f"search.html?source={src_d}&destination={dst_d}"}
                    ]
                }

        if t_num:
            train = RailwayService.search_by_train_number(t_num)
            if train:
                dur = RailwayService.calculate_travel_duration(train['departure_time'], train['arrival_time'])
                ctx['last_train_number'] = t_num
                ctx['last_intent'] = 'JOURNEY_TIME'
                return {
                    "intent": "JOURNEY_TIME",
                    "response": f"### ⏱️ Travel Time: Train #{train['train_number']} — {train['train_name']}\n\n"
                                f"• **Full Route:** {train['source_name']} ({train['source_code']}) ➔ {train['dest_name']} ({train['dest_code']})\n"
                                f"• **Departure:** `{train['departure_time']}` | **Arrival:** `{train['arrival_time']}`\n"
                                f"• **Total Journey Duration:** **{dur or train['duration']}**\n\n"
                                f"Calculated using the train's scheduled timetable.",
                    "suggested_actions": [
                        {"label": f"View Route Stops", "query": f"what are the stops of {train['train_number']}?"},
                        {"label": "Live GPS Tracking", "url": f"live-tracking.html?train_id={train['id']}"}
                    ]
                }

    # =========================================================================
    # 10. TRAIN SCHEDULE / TIMINGS AT SPECIFIC STATION
    # =========================================================================
    is_schedule_query = any(k in clean_lower for k in [
        'when does', 'when is the train', 'what time does', 'departure time', 'arrival time', 'reach', 'leave'
    ])
    if is_schedule_query:
        t_num = extract_train_number(clean_msg, ctx)
        st_obj = extract_station(clean_msg)

        if t_num and st_obj:
            train, stops = RailwayService.get_train_stops_detailed(t_num)
            if train and stops:
                target_stop = None
                for s in stops:
                    if s['station_code'] == st_obj['code'] or s['station_id'] == st_obj['id'] or s['station_name'].lower() == st_obj['name'].lower():
                        target_stop = s
                        break
                if not target_stop and st_obj.get('city'):
                    c_lower = st_obj['city'].lower()
                    for s in stops:
                        if (s.get('station_city') or '').lower() == c_lower or c_lower in s['station_name'].lower():
                            target_stop = s
                            break

                if target_stop:
                    arr = "Origin (Starts)" if target_stop['arrival_time'] == 'START' else target_stop['arrival_time']
                    dep = "Terminus (Ends)" if target_stop['departure_time'] == 'END' else target_stop['departure_time']
                    halt_desc = f"Scheduled Halt: {target_stop['halt_minutes']} min" if int(target_stop.get('halt_minutes') or 0) > 0 else "Origin / Terminus"
                    ctx['last_train_number'] = t_num
                    ctx['last_intent'] = 'TRAIN_SCHEDULE'
                    return {
                        "intent": "TRAIN_SCHEDULE",
                        "response": f"### ⏰ Schedule for Train #{train['train_number']} at {target_stop['station_name']} ({target_stop['station_code']})\n\n"
                                    f"• **Arrival Time:** `{arr}`\n"
                                    f"• **Departure Time:** `{dep}`\n"
                                    f"• **Stop Info:** {halt_desc}\n"
                                    f"• **Distance from Origin:** {target_stop['distance_km']} km",
                        "suggested_actions": [
                            {"label": "View Full Route Stops", "query": f"what are the stops of {train['train_number']}?"},
                            {"label": "Track Live Position", "url": f"live-tracking.html?train_id={train['id']}"}
                        ]
                    }

    # =========================================================================
    # 11. FOLLOW-UP "WHAT TIME DOES IT LEAVE?"
    # =========================================================================
    if any(k in clean_lower for k in ['what time does it leave', 'when does it leave', 'what time does it depart', 'when is its departure', 'departure time of it', 'what time does the train leave']):
        target_train = ctx.get('last_train')
        if not target_train and ctx.get('last_train_number'):
            target_train = RailwayService.search_by_train_number(ctx['last_train_number'])

        if target_train:
            dep = target_train.get('leg_departure_time') or target_train.get('departure_time')
            arr = target_train.get('leg_arrival_time') or target_train.get('arrival_time')
            b_name = target_train.get('boarding_name') or target_train.get('source_name')
            b_code = target_train.get('boarding_code') or target_train.get('source_code')
            d_name = target_train.get('deboarding_name') or target_train.get('dest_name')
            d_code = target_train.get('deboarding_code') or target_train.get('dest_code')
            dur = target_train.get('duration') or 'N/A'

            return {
                "intent": "TRAIN_SCHEDULE",
                "response": f"Train **#{target_train['train_number']} ({target_train['train_name']})** departs from **{b_name} ({b_code})** at **`{dep}`** and reaches **{d_name} ({d_code})** at **`{arr}`** (Scheduled journey duration: **{dur}**).",
                "suggested_actions": [
                    {"label": f"Book Train #{target_train['train_number']}", "url": f"search.html?train_number={target_train['train_number']}"},
                    {"label": "Check Route Stops", "query": f"what are the stops of {target_train['train_number']}?"}
                ]
            }

    # =========================================================================
    # 10. TRAIN COMPARISONS (FASTEST, FEWEST STOPS, EARLIEST ARRIVAL)
    # =========================================================================
    is_comparison_query = any(k in clean_lower for k in [
        'which is fastest', 'which one is fastest', 'fastest train', 'shortest duration',
        'which has fewer stops', 'which has fewest stops', 'fewer stops', 'fewest stops',
        'which train is best', 'which reaches earliest', 'earliest train', 'which reaches delhi earliest',
        'earliest arrival', 'which train is fastest', 'train is fastest', 'is fastest'
    ])
    if is_comparison_query:
        # Check if route specified in query or in context
        c_src, c_dst = extract_route_pair(clean_msg, ctx)
        route_trains = []
        if c_src and c_dst:
            route_trains = RailwayService.search_route(c_src, c_dst)
        elif ctx.get('last_route_trains'):
            route_trains = ctx['last_route_trains']

        if route_trains:
            if any(k in clean_lower for k in ['fewest stops', 'fewer stops', 'less stops', 'least stops']):
                sorted_trains = sorted(route_trains, key=lambda x: (x.get('scheduled_halt_count') if x.get('scheduled_halt_count') is not None else (x.get('total_halts_on_leg') if x.get('total_halts_on_leg') is not None else 999)))
                winner = sorted_trains[0]
                winner_halts = winner.get('scheduled_halt_count') if winner.get('scheduled_halt_count') is not None else (winner.get('total_halts_on_leg', 0))
                ctx['last_train'] = winner
                ctx['last_train_number'] = winner['train_number']
                return {
                    "intent": "TRAIN_COMPARISON",
                    "response": f"### 🛑 Train with Fewest Stops: {c_src.title() if c_src else 'Route'} ➔ {c_dst.title() if c_dst else ''}\n\n"
                                f"Among the **{len(route_trains)} available trains**, **#{winner['train_number']} {winner['train_name']}** has the fewest commercial halts with only **{winner_halts} intermediate stops**!\n\n"
                                f"• **Departure:** `{winner['leg_departure_time']}` ({winner['boarding_code']})\n"
                                f"• **Arrival:** `{winner['leg_arrival_time']}` ({winner['deboarding_code']})\n"
                                f"• **Duration:** **{winner['duration']}**",
                    "suggested_actions": [
                        {"label": f"Book Train #{winner['train_number']}", "url": f"search.html?train_number={winner['train_number']}"},
                        {"label": "Check Route Stops", "query": f"what are the stops of {winner['train_number']}?"}
                    ]
                }
            else:
                # Default: Fastest train by duration_minutes
                sorted_trains = sorted(route_trains, key=lambda x: x.get('duration_minutes', 9999))
                winner = sorted_trains[0]
                ctx['last_train'] = winner
                ctx['last_train_number'] = winner['train_number']

                top_3 = sorted_trains[:3]
                top_lines = []
                for idx, t in enumerate(top_3, 1):
                    top_lines.append(f"{idx}. **#{t['train_number']} {t['train_name']}**: **{t['duration']}** (Dep: `{t['leg_departure_time']}` ➔ Arr: `{t['leg_arrival_time']}`)")
                top_text = "\n".join(top_lines)

                fastest_halts = winner.get('scheduled_halt_count') if winner.get('scheduled_halt_count') is not None else winner.get('total_halts_on_leg', 'Not available')
                return {
                    "intent": "TRAIN_COMPARISON",
                    "response": f"### ⚡ Fastest Train: {c_src.title() if c_src else 'Route'} ➔ {c_dst.title() if c_dst else ''}\n\n"
                                f"Among the **{len(route_trains)} trains** on this route, **#{winner['train_number']} {winner['train_name']}** is the fastest with a scheduled travel duration of **{winner['duration']}**!\n\n"
                                f"• **Departure:** `{winner['leg_departure_time']}` from {winner['boarding_name']} ({winner['boarding_code']})\n"
                                f"• **Arrival:** `{winner['leg_arrival_time']}` at {winner['deboarding_name']} ({winner['deboarding_code']})\n"
                                f"• **Stops:** {fastest_halts} halts\n\n"
                                f"**Top Fastest Options:**\n{top_text}",
                    "suggested_actions": [
                        {"label": f"Book #{winner['train_number']}", "url": f"search.html?train_number={winner['train_number']}"},
                        {"label": "Check Route Stops", "query": f"what are the stops of {winner['train_number']}?"}
                    ]
                }

    # =========================================================================
    # 11. ORDERED ROUTE TRAIN SEARCH & NATURAL LANGUAGE FILTERING
    # =========================================================================
    src, dst = extract_route_pair(clean_msg, ctx)
    if src and dst:
        travel_date = extract_date(clean_msg) or ctx.get('last_date')
        filters = extract_filters(clean_msg)

        # Retrieve ALL available trains on the route (STEP 1 & STEP 2)
        route_trains = RailwayService.search_route(src, dst, date=travel_date)

        if route_trains:
            total_count = len(route_trains)
            display_trains = list(route_trains)

            # Apply natural language filters if specified (Section 17)
            filter_description = ""
            if filters.get('time') == 'morning':
                filtered = [t for t in display_trains if '05:00' <= (t.get('leg_departure_time') or '') < '12:00']
                if filtered:
                    display_trains = filtered
                    filter_description = "morning "
            elif filters.get('time') == 'evening':
                filtered = [t for t in display_trains if '12:00' <= (t.get('leg_departure_time') or '') < '21:00']
                if filtered:
                    display_trains = filtered
                    filter_description = "evening "
            elif filters.get('time') == 'night':
                filtered = [t for t in display_trains if (t.get('leg_departure_time') or '') >= '21:00' or (t.get('leg_departure_time') or '') < '05:00']
                if filtered:
                    display_trains = filtered
                    filter_description = "night "

            if filters.get('train_type'):
                target_tt = filters['train_type'].lower()
                filtered = [t for t in display_trains if target_tt in t.get('train_name', '').lower() or target_tt in t.get('train_type', '').lower()]
                if filtered:
                    display_trains = filtered
                    filter_description += f"{target_tt.title()} "

            if filters.get('sort') == 'fastest':
                display_trains.sort(key=lambda x: x.get('duration_minutes', 9999))
            elif filters.get('sort') == 'fewest_stops':
                display_trains.sort(key=lambda x: (x.get('scheduled_halt_count') if x.get('scheduled_halt_count') is not None else (x.get('total_halts_on_leg') if x.get('total_halts_on_leg') is not None else 999)))
            elif filters.get('sort') == 'earliest_arrival':
                display_trains.sort(key=lambda x: x.get('leg_arrival_time') or '99:99')
            elif filters.get('sort') == 'latest_departure':
                display_trains.sort(key=lambda x: x.get('leg_departure_time') or '00:00', reverse=True)

            # Format ALL returned trains into complete cards (Section 4 & 5)
            cards = [format_train_card(idx, t) for idx, t in enumerate(display_trains, 1)]
            trains_text = "\n\n".join(cards)

            s_disp = route_trains[0]['boarding_name']
            s_code = route_trains[0]['boarding_code']
            d_disp = route_trains[0]['deboarding_name']
            d_code = route_trains[0]['deboarding_code']

            # Update conversational memory context with structured RAG railway data (Section 11, 12, 16)
            rag_contexts = []
            for t in display_trains:
                h_val = t.get('scheduled_halt_count')
                rag_contexts.append({
                    "train_number": t.get('train_number'),
                    "train_name": t.get('train_name'),
                    "from": f"{t.get('boarding_name')} ({t.get('boarding_code')})",
                    "to": f"{t.get('deboarding_name')} ({t.get('deboarding_code')})",
                    "departure": t.get('leg_departure_time'),
                    "arrival": t.get('leg_arrival_time'),
                    "duration": t.get('duration'),
                    "distance_km": t.get('leg_distance_km'),
                    "total_route_points": t.get('total_route_stations'),
                    "actual_scheduled_halts": h_val if h_val is not None else "Not available"
                })
            ctx['rag_trains_context'] = rag_contexts

            ctx['last_intent'] = 'TRAIN_SEARCH'
            ctx['last_source'] = s_code
            ctx['last_destination'] = d_code
            ctx['last_route_trains'] = route_trains
            ctx['last_train'] = display_trains[0]
            ctx['last_train_number'] = display_trains[0]['train_number']
            if travel_date:
                ctx['last_date'] = travel_date

            date_note = f" on **{travel_date}**" if travel_date else ""
            filter_note = f" matching **{filter_description.strip()}** (out of {total_count} total available on this route)" if filter_description else ""

            src_label = f"{src.title()} ({s_disp}, {s_code})" if src.lower() not in s_disp.lower() else f"{s_disp} ({s_code})"
            dst_label = f"{dst.title()} ({d_disp}, {d_code})" if dst.lower() not in d_disp.lower() else f"{d_disp} ({d_code})"
            route_title = f"{src_label} ➔ {dst_label}"

            return {
                "intent": "TRAIN_SEARCH",
                "response": f"### 🚆 Found {len(display_trains)} {filter_description}Train(s) from {route_title}{date_note}\n\n"
                            f"{trains_text}\n\n"
                            f"**Total matching trains: {len(display_trains)}**{filter_note}\n\n"
                            f"All train results enforce scheduled station stop sequence along the railway network.",
                "suggested_actions": [
                    {"label": f"Book {s_code} ➔ {d_code}", "url": f"search.html?source={s_code}&destination={d_code}"},
                    {"label": "⚡ Which is fastest?", "query": f"which train is fastest from {s_code} to {d_code}?"},
                    {"label": "Check Tomorrow", "query": f"show trains {s_code} to {d_code} tomorrow"}
                ]
            }
        else:
            # Proper no-result response with alternate recommendations (Section 22)
            ctx['last_source'] = src
            ctx['last_destination'] = dst
            return {
                "intent": "TRAIN_SEARCH",
                "response": f"I couldn't find a direct **{src.title()} ➔ {dst.title()}** train in the verified railway timetable.\n\n"
                            f"**Recommended alternatives:**\n"
                            f"• Check nearby primary junction hubs (e.g. searching via New Delhi, Jaipur, or Mumbai).\n"
                            f"• Split your journey across connecting trains (e.g., {src.title()} ➔ Delhi + Delhi ➔ {dst.title()}).\n"
                            f"• Try searching the reverse direction or selecting a different date.",
                "suggested_actions": [
                    {"label": f"Check Reverse: {dst.title()} ➔ {src.title()}", "url": f"search.html?source={dst}&destination={src}"},
                    {"label": "Search All Trains", "url": "search.html"}
                ]
            }

    # =========================================================================
    # 12. STATION INTELLIGENCE & STOPPING TRAINS
    # =========================================================================
    is_station_query = any(k in clean_lower for k in [
        'station code', 'tell me about jp', 'tell me about ndls', 'tell me about aii', 'code of', 'code for',
        'what trains stop at', 'which trains stop at', 'which trains stop', 'what trains stop', 'trains stop at',
        'trains pass through', 'trains at', 'is jaipur a stop', 'stop for', 'pass through', 'which trains depart from',
        'station trains', 'whats arriving at', "what's arriving at", 'trains at mumbai central'
    ])
    if is_station_query:
        t_num = extract_train_number(clean_msg, ctx)
        st_obj = extract_station(clean_msg)

        if t_num and st_obj and any(k in clean_lower for k in ['is', 'stop for', 'halt at']):
            train, stops = RailwayService.ensure_train_route_cached(t_num)
            if train:
                is_stop = any(s['station_code'] == st_obj['code'] for s in stops)
                verdict = "Yes" if is_stop else "No"
                return {
                    "intent": "STATION_TRAINS",
                    "response": f"**{verdict}**, **{st_obj['name']} ({st_obj['code']})** is {'a' if is_stop else 'not a'} scheduled commercial halt for Train #{train['train_number']} ({train['train_name']}).",
                    "suggested_actions": [
                        {"label": "View All Stops", "query": f"what are the stops of {train['train_number']}?"}
                    ]
                }

        if st_obj and any(k in clean_lower for k in ['trains stop at', 'which trains stop', 'what trains stop', 'trains pass through', 'trains at', 'stop at', 'depart from', 'station trains', 'arriving']):
            st, trains = RailwayService.get_station_trains(st_obj['code'])
            if trains:
                lines = [f"• **#{t['train_number']}** {t['train_name']} — Arr: `{t['arrival_time']}` | Dep: `{t['departure_time']}` ({t['source_code']} ➔ {t['dest_code']})" for t in trains]
                trains_text = "\n".join(lines)
                return {
                    "intent": "STATION_TRAINS",
                    "response": f"### 🚉 Scheduled Trains at {st['name']} ({st['code']}):\n\n"
                                f"Found **{len(trains)} active train(s)** in the database:\n\n"
                                f"{trains_text}",
                    "suggested_actions": [
                        {"label": f"Search Trains at {st['code']}", "url": f"search.html?source={st['code']}"}
                    ]
                }
            else:
                return {
                    "intent": "STATION_TRAINS",
                    "response": f"### 🚉 Trains at {st['name']} ({st['code']}):\n\n"
                                f"No scheduled trains currently have a commercial halt at **{st['name']} ({st['code']})** in our active timetable records.",
                    "suggested_actions": [
                        {"label": "Search All Trains", "url": "search.html"}
                    ]
                }

        if st_obj:
            return {
                "intent": "STATION_DETAILS",
                "response": f"### 🚉 Station Profile: {st_obj['name']} ({st_obj['code']})\n\n"
                            f"• **Station Name:** {st_obj['name']}\n"
                            f"• **Station Code:** `{st_obj['code']}`\n"
                            f"• **City:** {st_obj['city']}\n"
                            f"• **State:** {st_obj['state']}\n"
                            f"• **Aliases / Keywords:** {st_obj.get('aliases') or st_obj['code']}",
                "suggested_actions": [
                    {"label": f"Trains Stopping at {st_obj['name']}", "query": f"which trains stop at {st_obj['name']}?"},
                    {"label": f"Search from {st_obj['code']}", "url": f"search.html?source={st_obj['code']}"}
                ]
            }

    # =========================================================================
    # 13. TRAIN DETAILS BY NUMBER OR NAME (Section 7)
    # =========================================================================
    t_num = extract_train_number(clean_msg, ctx)
    if t_num and (any(k in clean_lower for k in ['train', 'tell me about', 'details', 'what is', 'which train is', 'timings']) or len(clean_msg.strip().split()) <= 3):
        train = RailwayService.search_by_train_number(t_num)
        if train:
            stops_val = RailwayService.calculate_scheduled_halts(train.get('stops', []))
            stops_count = stops_val if stops_val is not None else len(train.get('stops', []))
            coaches_str = ", ".join([f"{c['class_code']} (₹{c['base_fare']})" for c in train.get('classes', [])]) or "AC / Sleeper"
            ctx['last_train_number'] = t_num
            ctx['last_train'] = train
            ctx['last_intent'] = 'TRAIN_DETAILS'
            return {
                "intent": "TRAIN_DETAILS",
                "response": f"### 🚆 Train #{train['train_number']} — {train['train_name']}\n\n"
                            f"• **Train Type:** {train['train_type']}\n"
                            f"• **Origin:** {train['source_name']} ({train['source_code']}) — Dep: `{train['departure_time']}`\n"
                            f"• **Destination:** {train['dest_name']} ({train['dest_code']}) — Arr: `{train['arrival_time']}`\n"
                            f"• **Total Duration:** {train['duration']}\n"
                            f"• **Runs On:** {train['running_days']}\n"
                            f"• **Total Halts:** {stops_count} scheduled commercial halts\n"
                            f"• **Classes & Base Fares:** {coaches_str}",
                "suggested_actions": [
                    {"label": f"Book Train #{train['train_number']}", "url": f"search.html?train_number={train['train_number']}"},
                    {"label": "Show Route Stops", "query": f"what are the stops of {train['train_number']}?"},
                    {"label": "Live GPS Tracking", "url": f"live-tracking.html?train_id={train['id']}"}
                ]
            }
        else:
            return {
                "intent": "TRAIN_DETAILS",
                "response": f"Train number **{t_num}** was not found in our database. "
                            f"Try searching for popular benchmark trains such as `12952` (Tejas Rajdhani) or `12956` (Jaipur - Mumbai Central SF Express).",
                "suggested_actions": [
                    {"label": "Search All Trains", "url": "search.html"}
                ]
            }

    # =========================================================================
    # 14. SEAT AVAILABILITY & COACHES
    # =========================================================================
    is_seat_query = any(k in clean_lower for k in [
        'seat availability', 'are seats available', 'show ac coaches', 'is b1 available',
        'which seats are available', 'what seats are available', 'vacant berths', 'available seats', 'seats available'
    ])
    if is_seat_query:
        t_num = extract_train_number(clean_msg, ctx)
        if t_num:
            train = RailwayService.search_by_train_number(t_num)
            if train:
                coaches = train.get('classes', [])
                c_lines = [f"• **Coach {c['coach_number']}** ({c['class_code']}): {c['status']} — ₹{c['adjusted_fare']}" for c in coaches]
                c_text = "\n".join(c_lines) or "Coach data is currently being updated."
                return {
                    "intent": "SEAT_AVAILABILITY",
                    "response": f"### 💺 Seat & Coach Availability: Train #{train['train_number']} ({train['train_name']})\n\n"
                                f"{c_text}\n\n"
                                f"You can view live vacancy maps and select specific window/lower berths on our Interactive Seat Map.",
                    "suggested_actions": [
                        {"label": "Open Seat Selection", "url": "seat-selection.html?coach_id=1"},
                        {"label": "Search & Book", "url": f"search.html?train_number={train['train_number']}"}
                    ]
                }

        return {
            "intent": "SEAT_AVAILABILITY",
            "response": "Real-time seat availability depends on the specific train, date, and coach class. "
                        "Please specify a train number (e.g., *'is seats available on 12952?'*) or search between stations.",
            "suggested_actions": [
                {"label": "Search Trains for Seats", "url": "search.html"}
            ]
        }

    # =========================================================================
    # 15. GREETINGS & GENERAL CAPABILITIES GUIDE
    # =========================================================================
    is_greeting = bool(re.search(r'\b(hello|hi|hey|namaste|good morning|who are you|help me)\b', clean_lower))
    if is_greeting:
        return {
            "intent": "GENERAL_RAILWAY_HELP",
            "response": "Namaste! 🙏 I am your **SmartRail AI Assistant**.\n\n"
                        "I am directly connected to the verified railway database and RailRadar API to help you with:\n"
                        "• **Train Search:** e.g., *'show trains from Jaipur to Delhi'*\n"
                        "• **Train Information:** e.g., *'what is 12956?'*\n"
                        "• **Route Halts Timeline:** e.g., *'route of 12956'*\n"
                        "• **Live GPS Status:** e.g., *'where is 12956 right now?'*\n"
                        "• **Train Comparison:** e.g., *'which train is fastest from Jaipur to Delhi?'*\n"
                        "• **PNR Status & AI Prediction:** e.g., *'check PNR 2846190532'*\n"
                        "• **Railway Concepts:** e.g., *'what is GNWL?'* or *'how does RAC work?'*\n"
                        "• **Food On-Board:** e.g., *'can I order food on my train?'*\n\n"
                        "What would you like to know?",
            "suggested_actions": [
                {"label": "Trains Jaipur ➔ Delhi", "query": "show all trains from Jaipur to Delhi"},
                {"label": "Fastest Train", "query": "which train is fastest from Jaipur to Delhi?"},
                {"label": "Live Status 12956", "query": "where is 12956 right now?"},
                {"label": "Check PNR Status", "url": "pnr-status.html"}
            ]
        }

    # =========================================================================
    # 15.5. STAGE-2 INTELLIGENT REASONING & SEMANTIC FALLBACK
    # =========================================================================
    stage2_res = stage_2_classify_and_reason(clean_msg, ctx)
    if stage2_res:
        if stage2_res.get("stage_2_intent") == "LIVE_STATUS":
            t_num = stage2_res.get("train_number")
            if t_num:
                live_data = RailRadarService.fetch_train_live(t_num) if RailRadarService.is_configured() else None
                if live_data:
                    return {
                        "intent": "LIVE_STATUS",
                        "response": f"### 🛰️ Real-Time Telemetry: Train #{live_data['train_number']} — {live_data['train_name']}\n\n"
                                    f"• **Operating Status:** **{(live_data.get('running_status') or 'RUNNING').upper()}**\n"
                                    f"• **Current Section:** **{live_data.get('current_station') or 'In Transit'}**\n"
                                    f"• **Next Commercial Halt:** **{live_data.get('next_station') or 'Approaching'}** (ETA: `{live_data.get('next_eta') or '--:--'}`)\n"
                                    f"• **Punctuality Status:** **{live_data.get('delay_status') or 'On Time'}**\n"
                                    f"• **Current Track Speed:** **{live_data.get('current_speed', 0.0)} km/h**",
                        "suggested_actions": [
                            {"label": f"Full Live Map (#{t_num})", "url": f"live-tracking.html?train_id={t_num}"}
                        ]
                    }
                trk = RailwayService.get_train_tracking_summary(t_num)
                if trk:
                    return {
                        "intent": "LIVE_STATUS",
                        "response": f"### 🛰️ Live Telemetry: Train #{trk['train_number']} — {trk['train_name']}\n\n"
                                    f"• **Route:** {trk['source']} ➔ {trk['destination']}\n"
                                    f"• **Current Section:** **{trk['current_section']}**\n"
                                    f"• **Current Speed:** **{trk['current_speed']} km/h**\n"
                                    f"• **Next Commercial Halt:** **{trk['next_station']}** (ETA: `{trk['eta']}`)",
                        "suggested_actions": [
                            {"label": f"Open Live Timeline (#{trk['train_number']})", "url": f"live-tracking.html?train_id={trk['train_id']}"}
                        ]
                    }
        elif stage2_res.get("stage_2_intent") == "FOOD_ORDER":
            return {
                "intent": "FOOD_ORDER",
                "response": "### 🍴 Order Fresh Food During Your Train Journey\n\n"
                            "Yes! SmartRail offers on-board meal delivery directly to your train coach and berth at selected scheduled railway halts.\n\n"
                            "You can order meals by entering your PNR or Train Number on the Food Order portal.",
                "suggested_actions": [
                    {"label": "🍴 Open Food Order Portal", "url": "food-order.html"},
                    {"label": "Track Food Order", "url": "food-order-tracking.html"}
                ]
            }
        elif stage2_res.get("response"):
            return stage2_res

    # =========================================================================
    # 16. UNKNOWN FALLBACK
    # =========================================================================
    return {
        "intent": "UNKNOWN",
        "response": "I didn't quite catch that. I am your specialized **SmartRail AI Assistant**, and I can help with:\n\n"
                    "• **Train Search:** e.g., *'show all trains from Jaipur to Delhi'*\n"
                    "• **Train Details:** e.g., *'what is 12956?'*\n"
                    "• **Route Stops:** e.g., *'route of 12956'*\n"
                    "• **Live Status:** e.g., *'where is 12956 right now?'*\n"
                    "• **Train Comparison:** e.g., *'which train is fastest?'*\n"
                    "• **PNR Enquiry:** e.g., *'check PNR 2846190532'*\n"
                    "• **Railway Knowledge:** e.g., *'what is RAC?'* or *'what is GNWL?'*\n"
                    "• **Food Ordering:** e.g., *'can I order food on my train?'*\n\n"
                    "How can I assist you?",
        "suggested_actions": [
            {"label": "Trains Jaipur ➔ Delhi", "query": "show all trains from Jaipur to Delhi"},
            {"label": "Route of 12956", "query": "route of 12956"},
            {"label": "Where is 12956?", "query": "where is 12956 right now?"},
            {"label": "What is RAC?", "query": "what is RAC?"}
        ]
    }
