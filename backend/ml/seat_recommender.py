"""
AI Seat Recommender System
Computes intelligent personalized seat recommendations based on passenger demographic,
berth preference, coach compartment positioning, and comfort heuristics.
"""

def recommend_seats(available_seats, passenger_type='general', preference='WINDOW', coach_class='3A', count=None):
    """
    Ranks all available seats using explainable multi-attribute utility scoring.

    Parameters:
    - available_seats: list of seat dicts (id, seat_number, seat_type, is_window, is_aisle, coach_id, coach_number, etc.)
    - passenger_type: 'elderly'/'senior', 'child', 'family', 'solo', 'female', 'general'
    - preference: 'WINDOW', 'AISLE', 'LOWER', 'UPPER', 'MIDDLE', 'SIDE_LOWER', 'SIDE_UPPER'
    - coach_class: 'SL', '3A', '2A', 'CC', '1A', 'EC'
    - count: number of top seats to recommend. If None or <= 0, returns the COMPLETE ranked list.

    Returns:
    - List of recommended seat dicts sorted descending by recommendation_score (0-100) with rationale.
    """
    if not available_seats:
        return []

    scored_seats = []
    pref = (preference or 'WINDOW').upper()
    ptype = (passenger_type or 'general').lower()

    for seat in available_seats:
        seat_id = seat.get('id') or seat.get('seat_id')
        seat_no = int(seat.get('seat_number', 0))
        seat_type = str(seat.get('seat_type', '')).upper()
        is_window = bool(seat.get('is_window'))
        is_aisle = bool(seat.get('is_aisle'))
        coach_id = seat.get('coach_id')
        coach_num = seat.get('coach_number', '')
        c_class = seat.get('coach_class') or coach_class

        score = 50.0  # Base utility score
        reasons = []
        tags = []

        # 1. Direct Berth Preference Matching (Up to +40 pts)
        if pref == 'WINDOW':
            if is_window:
                score += 35
                reasons.append("matches your direct window view preference")
                tags.append("Window View")
            elif is_aisle:
                score -= 10
        elif pref == 'AISLE':
            if is_aisle:
                score += 32
                reasons.append("provides convenient aisle access for easy movement")
                tags.append("Aisle Access")
            elif is_window:
                score -= 5
        elif pref == 'LOWER':
            if seat_type == 'LOWER':
                score += 40
                reasons.append("exact Lower berth match with step-free convenience")
                tags.append("Lower Berth")
            elif seat_type == 'SIDE_LOWER':
                score += 30
                reasons.append("Side Lower berth matching your lower deck preference")
                tags.append("Side Lower")
            else:
                score -= 20
        elif pref == 'UPPER':
            if seat_type in ('UPPER', 'SIDE_UPPER'):
                score += 35
                reasons.append(f"matches your {seat_type.replace('_', ' ').title()} preference for undisturbed privacy")
                tags.append("Upper Berth")
            else:
                score -= 15
        elif pref == 'MIDDLE':
            if seat_type == 'MIDDLE':
                score += 35
                reasons.append("matches your Middle berth selection")
                tags.append("Middle Berth")
        elif pref in seat_type:
            score += 35
            reasons.append(f"exactly matches your {pref.replace('_', ' ').title()} preference")
            tags.append(pref.replace('_', ' ').title())

        # 2. Demographic & Passenger Type Optimization (Up to +35 pts)
        if ptype in ('elderly', 'senior'):
            if seat_type == 'LOWER':
                score += 35
                reasons.append("ideal step-free lower berth recommended for senior citizens")
                tags.append("Senior Friendly")
            elif seat_type == 'SIDE_LOWER':
                score += 25
                reasons.append("accessible lower level berth suitable for seniors")
                tags.append("Senior Friendly")
            elif 'UPPER' in seat_type:
                score -= 35
                reasons.append("avoids strenuous upper ladder climbing")
            elif 'MIDDLE' in seat_type:
                score -= 20
                reasons.append("avoids awkward middle berth positioning")
        elif ptype in ('child', 'family'):
            if seat_type in ('LOWER', 'MIDDLE'):
                score += 25
                reasons.append("safe clustered lower/middle cabin placement for family travel")
                tags.append("Family Friendly")
        elif ptype == 'solo':
            if 'SIDE' in seat_type or is_window:
                score += 25
                reasons.append("offers extra personal privacy for solo travelers")
                tags.append("Solo Privacy")
        elif ptype == 'female':
            if seat_type in ('LOWER', 'MIDDLE') or ('SIDE' in seat_type and is_window):
                score += 20
                reasons.append("comfortable, well-located berth for female travelers")
                tags.append("Secure Cabin")

        # 3. Coach Compartment Acoustic & Traffic Optimization (Up to +20 pts)
        # Determine whether seat is centrally located away from coach vestibules / toilets
        is_central = False
        is_near_exit = False
        if c_class in ('3A', 'SL'):
            if 17 <= seat_no <= 56:
                is_central = True
            elif seat_no in (1, 2, 3, 4, 5, 6, 7, 8, 65, 66, 67, 68, 69, 70, 71, 72):
                is_near_exit = True
        elif c_class == '2A':
            if 13 <= seat_no <= 36:
                is_central = True
            elif seat_no in (1, 2, 3, 4, 5, 6, 43, 44, 45, 46, 47, 48):
                is_near_exit = True
        elif c_class == 'CC':
            if 16 <= seat_no <= 60:
                is_central = True
            elif seat_no in (1, 2, 3, 4, 5, 71, 72, 73, 74, 75):
                is_near_exit = True
        else: # 1A / EC
            if 5 <= seat_no <= 20:
                is_central = True

        if is_central:
            score += 15
            reasons.append("located in quiet central compartment with minimal vestibule foot traffic")
            tags.append("Quiet Bay")
        elif is_near_exit:
            score -= 10
            reasons.append("near vestibule entrance and lavatories with higher transit movement")

        # 4. Emergency / Safety Proximity
        if seat_no in (7, 8, 15, 16, 23, 24, 31, 32, 39, 40, 47, 48, 55, 56):
            score += 5

        # 5. Inter-Coach Train Position Heuristic (central coaches e.g. B4-B8 have gentler suspension)
        if coach_num:
            import re
            m = re.search(r'(\d+)', coach_num)
            if m:
                c_idx = int(m.group(1))
                if 3 <= c_idx <= 8:
                    score += 3

        # Normalize score between 15% and 99%
        final_score = int(min(99, max(15, score)))
        coach_prefix = f"Coach {coach_num} - " if coach_num else ""
        explanation = f"{coach_prefix}Seat {seat_no} ({seat_type.replace('_', ' ')}): " + "; ".join(reasons) + "."

        scored_seats.append({
            "seat_id": seat_id,
            "coach_id": coach_id,
            "coach_number": coach_num,
            "coach_class": c_class,
            "seat_number": seat_no,
            "seat_type": seat_type,
            "is_window": is_window,
            "is_aisle": is_aisle,
            "recommendation_score": final_score,
            "explanation": explanation,
            "match_factors": tags
        })

    # Sort descending by recommendation score
    scored_seats.sort(key=lambda x: x['recommendation_score'], reverse=True)

    if count is not None and int(count) > 0:
        return scored_seats[:int(count)]
    return scored_seats
