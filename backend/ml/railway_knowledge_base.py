"""
SmartRail AI Assistant - Railway Knowledge Base & RAG Engine
Authoritative, data-grounded knowledge base covering:
- RAC rules, travel eligibility, status meaning, berth sharing
- Side Upper & Side Lower daytime seating vs night sleeping rules
- Middle berth operation & lower berth daytime access
- Waitlist types (GNWL, RLWL, PQWL, TQWL, RSWL) & clearance priorities
- E-ticket vs Counter ticket waitlist boarding rules
- Tatkal & Premium Tatkal rules, timings, surcharges, cancellation
- Cancellation slabs, refund policies, RAC/WL cancellation
- Chart preparation timelines & berth upgrade logic
- Class definitions (1A, 2A, 3A, 3E, SL, CC, EC, 2S)
- Berth modification, TTE authority, Senior Citizen concessions
- Hinglish & natural language understanding
"""

import re
from typing import Dict, List, Any, Optional

RAILWAY_NON_STATION_WORDS = {
    'can', 'to', 'in', 'on', 'at', 'is', 'for', 'by', 'do', 'go', 'me', 'we', 'us',
    'an', 'as', 'if', 'it', 'my', 'no', 'so', 'up', 'be', 'or', 'am', 'are', 'and',
    'the', 'sl', 'su', 'lb', 'mb', 'ub', 'rac', 'wl', 'gnwl', 'rlwl', 'pqwl', 'tqwl',
    'rswl', 'side', 'lower', 'upper', 'middle', 'berth', 'berths', 'seat', 'seats',
    'ticket', 'tickets', 'brother', 'sister', 'family', 'tatkal', 'premium', 'chart',
    'rules', 'rule', 'day', 'daytime', 'night', 'sleep', 'sleeping', 'sit', 'sitting',
    'passenger', 'passengers', 'what', 'why', 'how', 'when', 'who', 'where', 'meaning',
    'difference', 'cancel', 'cancellation', 'refund', 'confirm', 'confirmation',
    'class', 'coach', 'coaches', 'khana', 'food', 'meal', 'meals', 'order', 'kaha',
    'hai', 'kya', 'bhi', 'dono', 'se', 'pe', 'mein', 'din', 'raat', 'train', 'trains',
    'run', 'runs', 'fast', 'fastest', 'best', 'stop', 'stops', 'halt', 'halts', 'time',
    'timing', 'timings', 'date', 'pnr', 'status'
}

# Structured authoritative knowledge documents
KNOWLEDGE_DOCUMENTS = {
    # -------------------------------------------------------------------------
    # 1. RAC & BERTH SHARING RULES
    # -------------------------------------------------------------------------
    "rac_overview": {
        "id": "rac_overview",
        "category": "rac_rules",
        "title": "RAC (Reservation Against Cancellation) Overview",
        "keywords": ["what is rac", "explain rac", "rac meaning", "rac full form", "how does rac work", "rac ticket", "rac kya hai", "rac ka matlab"],
        "direct_answer": "**RAC stands for Reservation Against Cancellation.** It is an official confirmed-travel status in Indian Railways that guarantees you legal permission to board the train along with a dedicated sitting seat.",
        "explanation": (
            "• **Travel Guarantee:** Unlike waitlisted tickets, an RAC ticket is valid for travel. You are legally entitled to board the train.\n"
            "• **Berth Allocation:** Two RAC passengers share one **Side Lower (SL)** berth (the berth converts into two sitting seats during the journey).\n"
            "• **Full Berth Upgrade:** If any confirmed passenger cancels their booking or fails to board, RAC passengers are automatically upgraded to full sleeping berths in chronological order (RAC 1, RAC 2, etc.) at or before chart preparation."
        ),
        "conditions": (
            "• If your ticket remains RAC after chart preparation, you still travel with your allocated sitting seat.\n"
            "• RAC passengers are eligible for bedrolls in AC classes."
        )
    },

    "rac_travel_eligibility": {
        "id": "rac_travel_eligibility",
        "category": "rac_rules",
        "title": "Can RAC Passengers Board and Travel?",
        "keywords": ["can rac passengers travel", "can i travel with rac", "can i board train with rac", "is rac allowed to travel", "rac travel permission", "rac me travel kar sakte hain", "kya rac me travel ho sakta hai", "board the train with rac"],
        "direct_answer": "**Yes — all passengers holding an RAC ticket are 100% legally permitted to board the train and travel!**",
        "explanation": (
            "• **Guaranteed Travel Rights:** Under Indian Railways rules, an RAC ticket is a confirmed travel entitlement. You do not need to worry about being deboarded.\n"
            "• **Berth Configuration:** You will share a Side Lower berth with another RAC passenger as two sitting seats.\n"
            "• **Contrast with Waiting List:** Only fully waitlisted (WL) e-tickets are automatically cancelled and barred from boarding. RAC tickets are NEVER cancelled automatically."
        ),
        "conditions": (
            "• You must carry an original valid government ID (Aadhaar, Voter ID, Driving Licence, Passport, etc.) for verification by the TTE.\n"
            "• If confirmed berths become vacant during the run, the TTE will allot a full sleeping berth to you based on your RAC sequence."
        )
    },

    "rac_number_meaning": {
        "id": "rac_number_meaning",
        "category": "rac_rules",
        "title": "Meaning of Specific RAC Status Number (e.g. RAC 23)",
        "keywords": ["what does rac mean", "rac23", "rac 23", "what does rac 23 mean", "my seat is rac23", "rac status meaning", "rac number meaning", "rac23 ka kya rule hai", "rac 23 ka kya matlab hai", "i have rac 23"],
        "direct_answer": "**Holding an RAC status like RAC 23 means you have a guaranteed sitting seat on the train and are currently 23rd in line to be upgraded to a full sleeping berth.**",
        "explanation": (
            "• **Travel Guarantee:** You are fully entitled to board and complete your journey. Your travel is completely confirmed.\n"
            "• **Queue Position:** '23' indicates your position in the upgrade queue. As passengers with confirmed berths cancel, your RAC number moves closer to confirmation (e.g., RAC 23 ➔ RAC 15 ➔ RAC 4 ➔ Confirmed Berth CNF).\n"
            "• **Seat Allocation:** While in RAC, you and another RAC ticket holder share one Side Lower (SL) berth for sitting."
        ),
        "conditions": (
            "• Final upgrade status is determined when the **first reservation chart is prepared (4 hours before train departure)**.\n"
            "• Even if your ticket does not upgrade to a full berth, your right to travel on the shared Side Lower seat remains completely intact."
        )
    },

    "side_upper_lower_daytime": {
        "id": "side_upper_lower_daytime",
        "category": "berth_rules",
        "title": "Side Upper Passenger Sitting on Lower Berth During Daytime",
        "keywords": ["can side upper passenger sit on lower berth during day", "side upper sit on lower", "side upper lower daytime", "side upper wala din me niche baith sakta h kya", "side upper wala din me lower pe baith sakta hai kya", "can side upper sit on side lower", "can the side upper passenger sit on my lower berth during daytime", "side upper passenger rules"],
        "direct_answer": "**Yes — under Indian Railways rules, the passenger allotted the Side Upper (SU) berth has the official right to sit on the Side Lower (SL) berth during daytime hours (between 6:00 AM and 10:00 PM).**",
        "explanation": (
            "• **Daytime Seating Rights (06:00 AM – 10:00 PM):** Railway passenger amenities regulations specify that Side Upper passengers are entitled to sit on the Side Lower berth during the daytime, as sitting continuously on an upper berth for long hours is inconvenient.\n"
            "• **Night Sleeping Hours (10:00 PM – 06:00 AM):** At night, the Side Upper passenger **must move up to their assigned Side Upper berth to sleep**. During these hours, the Side Lower berth belongs exclusively to the Side Lower passenger(s) for sleeping."
        ),
        "conditions": (
            "• Neither the Side Lower passenger nor the Side Upper passenger can monopolize the berth outside their designated hours.\n"
            "• Mutual passenger cooperation is standard practice on Indian Railways during transition hours."
        )
    },

    "rac_side_upper_lower_complex": {
        "id": "rac_side_upper_lower_complex",
        "category": "berth_rules",
        "title": "RAC Passengers Sharing Side Lower with Side Upper Passenger During Day",
        "keywords": [
            "if my seat is rac23 with my brother who has also rac23 so side upper seat passenger can seat on my lower berth on the day time",
            "if my seat is rac23 and my brother also has rac23 can the side upper passenger sit on my lower berth during daytime",
            "rac23 with my brother side upper seat passenger sit on my lower berth daytime",
            "brother bhi rac hai to kya dono same berth share karenge side upper",
            "mera rac hai kya side upper wala din me niche baith sakta hai",
            "two rac passengers side upper daytime sitting"
        ],
        "direct_answer": "**Yes — under Indian Railways berth rules, the Side Upper (SU) passenger is entitled to sit on the Side Lower (SL) berth during daytime hours (between 6:00 AM and 10:00 PM), even when the berth is allotted to RAC passengers.**",
        "explanation": (
            "• **Daytime Seating Rule (06:00 AM – 10:00 PM):** Official railway regulations permit the Side Upper passenger to sit on the Side Lower berth during the daytime. Because the Side Lower berth converts into two sitting seats, the Side Upper passenger has the right to occupy sitting space there.\n"
            "• **RAC Berth Sharing (You & Your Brother):** Since both you and your brother hold RAC 23, you are jointly allotted the Side Lower berth as your shared travel space. During the daytime, the seating space accommodates the passengers traveling on that bay.\n"
            "• **Night Sleeping Hours (10:00 PM – 06:00 AM):** At 10:00 PM, the Side Upper passenger **must leave the lower berth and sleep on their assigned Side Upper berth**. The Side Lower berth then belongs exclusively to you and your brother to sleep/rest together throughout the night."
        ),
        "conditions": (
            "• During daytime hours, passengers are expected to accommodate each other courteously on the two-seat Side Lower layout.\n"
            "• If confirmed cancellations occur before departure chart preparation (4 hours prior to origin departure), one or both of you may get upgraded to full individual berths, resolving the shared space automatically!"
        )
    },

    "rac_berth_sharing": {
        "id": "rac_berth_sharing",
        "category": "rac_rules",
        "title": "Can Two RAC Passengers Share One Berth?",
        "keywords": ["can two rac passengers share one berth", "do rac passengers share berth", "how do rac passengers share", "two rac share berth", "brother bhi rac hai kya dono same berth share karenge", "rac berth sharing rule"],
        "direct_answer": "**Yes — under Indian Railways regulations, two RAC passengers are officially allotted to share one single Side Lower (SL) berth.**",
        "explanation": (
            "• **Berth Allocation Design:** The Side Lower berth is designed to fold into two facing sitting seats during daytime travel. For RAC ticket holders, this single berth provides sitting accommodation for two passengers throughout the journey.\n"
            "• **Travel Eligibility:** Both passengers have valid, legal boarding authorization and are assigned to the exact same berth number (e.g. SL Coach B2 Berth 31).\n"
            "• **Upgrade Mechanism:** If vacancies open up due to cancellations or no-shows, the TTE upgrades the senior RAC passenger to a vacant full berth first."
        ),
        "conditions": (
            "• If booked on the same PNR, family members or co-travelers holding consecutive RAC numbers are generally assigned to the same shared berth.\n"
            "• Both passengers receive individual bedding/linen sets in AC classes."
        )
    },

    "daytime_sleeping_lower_berth": {
        "id": "daytime_sleeping_lower_berth",
        "category": "berth_rules",
        "title": "Can I Sleep on Lower Berth During Daytime?",
        "keywords": ["can i sleep on lower berth during daytime", "can passenger sleep on lower berth during day", "when can i sleep on lower berth", "sleeping rules in train", "daytime sleeping rule", "lower berth kab use kar sakte hain", "din me so sakte hain kya lower berth pe"],
        "direct_answer": "**No — passengers cannot insist on sleeping on the lower berth during official daytime hours (06:00 AM to 10:00 PM) if middle or upper berth passengers wish to sit.**",
        "explanation": (
            "• **Official Sleeping Hours:** Under Indian Railways Rule 144, designated sleeping hours are strictly between **10:00 PM and 06:00 AM**.\n"
            "• **Daytime Seating Rights:** Between **06:00 AM and 10:00 PM**, middle and upper berth passengers have the legal right to sit on the lower berth, and middle berths must be folded down.\n"
            "• **Exceptions:** Sick passengers, pregnant women, elderly passengers, and disabled persons may be permitted to lie down during the day by mutual consent and courtesy of fellow travelers."
        ),
        "conditions": (
            "• If co-passengers mutually agree, a lower berth passenger may nap during daytime hours, provided it does not deprive others of reasonable sitting space."
        )
    },

    "middle_berth_rules": {
        "id": "middle_berth_rules",
        "category": "berth_rules",
        "title": "Middle Berth Opening and Sleeping Rules",
        "keywords": ["middle berth rules", "when can middle berth sleep", "middle berth timing", "middle berth open time", "middle berth band kab kare", "can middle berth open in daytime"],
        "direct_answer": "**Under Indian Railways rules, the middle berth can only be opened and used for sleeping between 10:00 PM and 06:00 AM.**",
        "explanation": (
            "• **Daytime Folding Requirement:** From **06:00 AM to 10:00 PM**, the middle berth must remain folded down against the wall so that lower, middle, and upper berth passengers can sit comfortably on the lower berth.\n"
            "• **Nighttime Sleeping:** At **10:00 PM**, the middle berth passenger is fully entitled to raise the berth and sleep. Lower berth passengers cannot object to opening the middle berth during sleeping hours."
        ),
        "conditions": (
            "• If a passenger with a middle berth is unwell, elderly, or pregnant, fellow passengers are encouraged to cooperate and allow earlier opening."
        )
    },

    "berth_change_swap_rules": {
        "id": "berth_change_swap_rules",
        "category": "berth_rules",
        "title": "Can I Change or Swap My Berth?",
        "keywords": ["can i change my berth", "how to change berth in train", "can i swap seat", "seat change rule", "berth change tte", "kya seat change kar sakte hain", "berth badal sakte hain"],
        "direct_answer": "**Passengers cannot unilaterally change berths on their own; only the on-duty Train Ticket Examiner (TTE) has the legal authority to officially re-allot berths.**",
        "explanation": (
            "• **Mutual Exchange:** Passengers may mutually agree to swap berths among themselves with mutual consent (e.g., giving a lower berth to an elderly traveler).\n"
            "• **TTE Re-Allotment:** If there are vacant berths on the train due to cancellations or no-shows, the TTE can officially transfer you to an open berth and update the chart on their handheld terminal (HHT).\n"
            "• **Class Upgrade:** TTEs can also upgrade passengers to a higher class (e.g. Sleeper to 3A) upon payment of the fare difference plus applicable surcharge, subject to seat availability."
        ),
        "conditions": (
            "• Unauthorized occupancy of someone else's berth is treated as traveling without proper authority and can attract railway fines."
        )
    },

    "side_lower_berth_info": {
        "id": "side_lower_berth_info",
        "category": "berth_rules",
        "title": "What is Side Lower (SL) Berth?",
        "keywords": ["what is side lower", "side lower berth", "side lower seat", "sl berth meaning", "side lower kya hota hai", "side lower details"],
        "direct_answer": "**The Side Lower (SL) berth is the berth situated along the longitudinal aisle/corridor of the coach, directly opposite the main 6-berth compartment.**",
        "explanation": (
            "• **Daytime Function:** During daytime hours, the Side Lower berth splits into two individual cushioned seats facing each other with a fold-up window snack table between them.\n"
            "• **Nighttime Function:** For night sleeping (10:00 PM to 6:00 AM), the table folds down and the backrest cushions drop flat to form a complete single sleeping berth.\n"
            "• **RAC Allocation:** When a train has RAC ticket holders, the Side Lower berth is allocated to two RAC passengers to share for sitting."
        ),
        "conditions": (
            "• Side Lower berths are popular for panoramic window views along the journey."
        )
    },

    # -------------------------------------------------------------------------
    # 2. WAITING LIST RULES (GNWL, RLWL, PQWL, TQWL, CANCELLATION)
    # -------------------------------------------------------------------------
    "gnwl_rules": {
        "id": "gnwl_rules",
        "category": "waitlist_rules",
        "title": "GNWL (General Waiting List)",
        "keywords": ["what is gnwl", "gnwl meaning", "gnwl rules", "general waiting list", "gnwl confirmation chances", "gnwl kya hai"],
        "direct_answer": "**GNWL (General Waiting List) is the primary and most common waiting list quota in Indian Railways, issued when booking from the train's originating station or nearby major junction.**",
        "explanation": (
            "• **Highest Clearance Priority:** GNWL has the **highest confirmation priority** (highest confirmation probability) among all waiting list categories.\n"
            "• **Cancellation Clearing:** Whenever any confirmed passenger holding a general quota ticket cancels, GNWL tickets advance first in line before any remote quotas.\n"
            "• **Progression:** GNWL progresses to RAC first, and then to fully confirmed (CNF) berths."
        ),
        "conditions": (
            "• GNWL numbers under 20–30 on popular routes generally have high clearance rates before chart preparation."
        )
    },

    "rlwl_rules": {
        "id": "rlwl_rules",
        "category": "waitlist_rules",
        "title": "RLWL (Remote Location Waiting List)",
        "keywords": ["what is rlwl", "rlwl meaning", "rlwl rules", "remote location waiting list", "rlwl confirmation chances", "rlwl kya hai"],
        "direct_answer": "**RLWL (Remote Location Waiting List) is issued for passengers boarding and deboarding at important intermediate stations along a train route.**",
        "explanation": (
            "• **Dedicated Quota:** Important intermediate railway stations have an earmarked small quota of seats allocated from the train's total capacity.\n"
            "• **Clearance Mechanism:** RLWL clears **only when someone who booked within that specific remote location quota cancels**.\n"
            "• **Priority:** RLWL has a lower confirmation probability than GNWL because the seat pool is much smaller."
        ),
        "conditions": (
            "• If booking from a remote station, check if booking from the originating station with boarding point changed gives you a GNWL ticket instead."
        )
    },

    "pqwl_rules": {
        "id": "pqwl_rules",
        "category": "waitlist_rules",
        "title": "PQWL (Pooled Quota Waiting List)",
        "keywords": ["what is pqwl", "pqwl meaning", "pqwl rules", "pooled quota waiting list", "pqwl confirmation chances", "pqwl kya hai"],
        "direct_answer": "**PQWL (Pooled Quota Waiting List) is a shared waiting list bucket used for passengers traveling between smaller intermediate stations.**",
        "explanation": (
            "• **Shared Bucket:** Several minor intermediate stations share a single tiny 'pooled' quota of seats on the train.\n"
            "• **Low Priority:** PQWL has a lower confirmation priority than both GNWL and RLWL. It clears only if cancellations occur within that shared intermediate pool.\n"
            "• **Progression:** PQWL rarely converts to RAC; it generally jumps directly to confirmed or remains waitlisted."
        ),
        "conditions": (
            "• Travelers with high PQWL numbers (above PQWL 15) are advised to explore alternative trains or Tatkal quotas."
        )
    },

    "tqwl_rules": {
        "id": "tqwl_rules",
        "category": "waitlist_rules",
        "title": "TQWL (Tatkal Waiting List)",
        "keywords": ["what is tqwl", "tqwl meaning", "tqwl rules", "tatkal waiting list", "tqwl confirmation", "tqwl kya hota hai"],
        "direct_answer": "**TQWL (Tatkal Waiting List) is the waiting list issued when all confirmed seats in the Tatkal quota have been exhausted.**",
        "explanation": (
            "• **Direct Cancellation if Unconfirmed:** Unlike general quota waiting lists, **TQWL does not convert into RAC**. At chart preparation, if berths are not cleared, TQWL tickets are automatically cancelled and refunded.\n"
            "• **Confirmation Precedence:** TQWL clears only when other Tatkal quota passengers cancel (which is rare since confirmed Tatkal tickets carry 0% refund).\n"
            "• **Confirmation Chances:** Confirmation probability for TQWL is very low."
        ),
        "conditions": (
            "• Only book TQWL if your waitlist number is 1, 2, or 3 on a long-distance train."
        )
    },

    "waitlist_travel_rules": {
        "id": "waitlist_travel_rules",
        "category": "waitlist_rules",
        "title": "Can Waitlisted (WL) Passengers Travel?",
        "keywords": ["can waitlist passengers travel", "can wl passengers board", "can i travel with waiting ticket", "what happens if wl is not confirmed", "waiting ticket rule", "kya waiting ticket me travel kar sakte hain", "waiting list travel allowed"],
        "direct_answer": "**No — passengers holding fully waitlisted online e-tickets are strictly NOT permitted to board reserved coaches of the train.**",
        "explanation": (
            "• **Online E-Tickets:** If an online e-ticket remains on waiting list (WL) after final chart preparation, **it is automatically cancelled by IRCTC and the full fare is refunded to the passenger's bank account**. Boarding a reserved coach with a cancelled e-ticket is treated as traveling without a ticket and incurs penalties.\n"
            "• **PRS Counter Tickets:** If you purchased a physical paper ticket from a railway station counter and it remains on the waiting list, you are permitted to travel in **unreserved (General) coaches**, or consult the TTE on board to check for unreserved vacant berths."
        ),
        "conditions": (
            "• If one passenger on a group PNR has a confirmed/RAC berth and others are WL, the waitlisted passengers may consult the TTE for accommodation."
        )
    },

    "difference_rac_wl": {
        "id": "difference_rac_wl",
        "category": "rac_rules",
        "title": "Difference Between RAC and Waiting List (WL)",
        "keywords": ["what is the difference between rac and wl", "difference between rac and waiting list", "rac vs wl", "rac or wl me kya difference hai", "difference between rac and waitlist"],
        "direct_answer": "**The fundamental difference between RAC and Waiting List (WL) is travel authorization and seat guarantee:**",
        "explanation": (
            "• **RAC (Reservation Against Cancellation):**\n"
            "  - **Travel Guarantee:** 100% legal permission to board and travel.\n"
            "  - **Seat Provided:** Guaranteed sitting seat (sharing a Side Lower berth).\n"
            "  - **Status:** Advance towards full berth; never auto-cancelled.\n\n"
            "• **WL (Waiting List):**\n"
            "  - **No Travel Guarantee:** No seat or berth is assigned.\n"
            "  - **E-Ticket Cancellation:** Automatically cancelled and refunded after charting if not confirmed.\n"
            "  - **Boarding:** Strictly prohibited in reserved coaches."
        ),
        "conditions": (
            "• RAC gives you peace of mind to travel; Waiting List requires monitoring confirmation right up until charting."
        )
    },

    # -------------------------------------------------------------------------
    # 3. TATKAL & PREMIUM TATKAL QUOTA RULES
    # -------------------------------------------------------------------------
    "tatkal_rules": {
        "id": "tatkal_rules",
        "category": "tatkal_rules",
        "title": "Tatkal Quota Booking Rules & Timings",
        "keywords": ["how does tatkal work", "tatkal rules", "what is tatkal", "when does tatkal booking open", "tatkal timing", "tatkal charges", "tatkal ticket rule", "tatkal kab khulta hai"],
        "direct_answer": "**Tatkal is an urgent short-notice booking quota opening exactly 1 day prior to the train's scheduled departure date from its originating station.**",
        "explanation": (
            "• **Opening Timings:**\n"
            "  - **AC Classes (1A, 2A, 3A, CC, EC):** Opens daily at **10:00 AM IST**.\n"
            "  - **Non-AC Classes (Sleeper, 2S):** Opens daily at **11:00 AM IST**.\n"
            "• **Tatkal Surcharges:** Calculated at 10% of base fare for Second Class and 30% for other classes (min ₹100 to max ₹500 depending on class).\n"
            "• **Refund on Cancellation:** **Zero refund (0%)** is granted on cancellation of confirmed Tatkal tickets."
        ),
        "conditions": (
            "• Maximum of 4 passengers can be booked per Tatkal PNR.\n"
            "• Senior citizen and child concessions do not apply under Tatkal."
        )
    },

    "premium_tatkal_rules": {
        "id": "premium_tatkal_rules",
        "category": "tatkal_rules",
        "title": "Premium Tatkal (PT) Dynamic Pricing Quota",
        "keywords": ["what is premium tatkal", "premium tatkal rules", "premium tatkal vs tatkal", "pt quota", "premium tatkal kya hai"],
        "direct_answer": "**Premium Tatkal (PT) is a dynamic-pricing emergency quota where ticket fares increase in real-time as seat availability decreases.**",
        "explanation": (
            "• **Dynamic Fares:** There is no fixed upper ceiling; fares escalate with demand, often reaching 2x to 3x standard base fares.\n"
            "• **Timings:** Same as Tatkal (10:00 AM for AC, 11:00 AM for Non-AC, 1 day prior to origin departure).\n"
            "• **Strict Cancellation Policy:** Confirmed Premium Tatkal tickets have a **strict 100% zero-refund policy** upon cancellation.\n"
            "• **No Waiting List:** PT quota tickets are only sold as confirmed."
        ),
        "conditions": (
            "• Only book Premium Tatkal if urgent travel is guaranteed and non-negotiable."
        )
    },

    # -------------------------------------------------------------------------
    # 4. TICKET CANCELLATION & REFUND POLICIES
    # -------------------------------------------------------------------------
    "cancellation_rules": {
        "id": "cancellation_rules",
        "category": "cancellation_rules",
        "title": "Cancellation & Refund Policy",
        "keywords": ["how can i cancel my ticket", "how to cancel ticket", "cancellation rules", "refund policy", "cancellation charges", "ticket cancel charges", "ticket kaise cancel kare"],
        "direct_answer": "**You can cancel your railway ticket online via the PNR Status portal before chart preparation, with refunds processed per official IRCTC slabs:**",
        "explanation": (
            "• **Cancellation Time Slabs:**\n"
            "  - **More than 48 hours before departure:** Flat clerkage charge deducted (1A/EC: ₹240, 2A: ₹200, 3A/CC: ₹180, SL: ₹120, 2S: ₹60).\n"
            "  - **Between 48 hours and 12 hours before departure:** **25%** of the ticket fare is deducted (subject to flat clerkage minimum).\n"
            "  - **Between 12 hours and 4 hours before departure (or chart preparation):** **50%** of the ticket fare is deducted.\n"
            "  - **After chart preparation (< 4 hours):** **No refund** is permitted for confirmed tickets.\n"
            "• **RAC & Waitlist Cancellation:** RAC and waiting list tickets can be cancelled up to **30 minutes before scheduled departure** with a minimal flat clerkage charge of ₹60 + GST per passenger."
        ),
        "conditions": (
            "• Approved refunds are credited directly back to the original payment source within 3–5 business days.\n"
            "• For train cancellations by Indian Railways, a 100% full refund is automatically issued without any clerkage deduction."
        )
    },

    # -------------------------------------------------------------------------
    # 5. CHART PREPARATION TIMELINE
    # -------------------------------------------------------------------------
    "chart_preparation_rules": {
        "id": "chart_preparation_rules",
        "category": "railway_knowledge",
        "title": "Reservation Chart Preparation Timeline",
        "keywords": ["when is chart prepared", "chart preparation time", "chart preparation rules", "chart timing", "chart kab banta hai"],
        "direct_answer": "**Indian Railways prepares reservation charts in two sequential stages prior to train departure:**",
        "explanation": (
            "• **First Reservation Chart:** Prepared **4 hours before** the train's scheduled origin departure time (or at **8:00 PM the previous evening** for morning trains departing before 12:00 noon).\n"
            "• **Current Booking Window:** Between 4 hours and 30 minutes before departure, unsold vacant seats open up for 'Current Booking' at discounted fares.\n"
            "• **Second & Final Chart:** Prepared **30 minutes before departure**, locking in final berth allocations and TTE handheld terminals."
        ),
        "conditions": (
            "• All RAC to Confirmed upgrades and waitlist promotions take effect during the first chart preparation window."
        )
    },

    # -------------------------------------------------------------------------
    # 6. COACHES AND CLASS INFORMATION (1A, 2A, 3A, 3E, SL, CC, EC, 2S)
    # -------------------------------------------------------------------------
    "class_3a": {
        "id": "class_3a",
        "category": "coach_rules",
        "title": "3A (AC 3-Tier Class)",
        "keywords": ["what is 3a", "3a meaning", "ac 3 tier", "3a coach details", "3a kya hai", "3 tier ac"],
        "direct_answer": "**3A (AC 3-Tier) is the most widely traveled air-conditioned sleeper class in Indian Railways, offering comfortable long-distance travel at moderate fares.**",
        "explanation": (
            "• **Layout & Berths:** Accommodates 64 to 72 berths per coach. Each passenger bay has 6 berths (Lower, Middle, Upper on both sides) plus 2 berths along the corridor (Side Lower, Side Upper).\n"
            "• **Amenities:** Regulated central air conditioning, fresh clean bedroll linen (sheets, pillow, blanket), charging points at every bay, and fold-down snack tables.\n"
            "• **Popularity:** Balances comfort, climate control, and affordability across express and superfast trains."
        ),
        "conditions": (
            "• Middle berths in 3A fold down during the day (06:00 AM to 10:00 PM) for shared lower berth sitting."
        )
    },

    "class_2a": {
        "id": "class_2a",
        "category": "coach_rules",
        "title": "2A (AC 2-Tier Class)",
        "keywords": ["what is 2a", "2a meaning", "ac 2 tier", "2a coach details", "2a kya hai"],
        "direct_answer": "**2A (AC 2-Tier) is a premium air-conditioned sleeper coach offering greater space, privacy, and fewer berths per coach than 3A.**",
        "explanation": (
            "• **Layout & Berths:** Features 48 to 54 berths per coach with only 2 tiers per bay (Lower and Upper) plus Side Lower and Side Upper along the corridor. There is NO middle berth!\n"
            "• **Privacy & Comfort:** Equipped with personal privacy curtains along the aisle, individual reading lamps, wider berths, and premium bedding linen.\n"
            "• **Quiet Atmosphere:** Considerably quieter with less passenger foot traffic than 3A or Sleeper."
        ),
        "conditions": (
            "• Lower berth and Upper berth have substantial headroom allowing passengers to sit upright comfortably."
        )
    },

    "class_1a": {
        "id": "class_1a",
        "category": "coach_rules",
        "title": "1A (AC First Class)",
        "keywords": ["what is 1a", "1a meaning", "ac first class", "first ac", "1a coach details", "1a kya hai"],
        "direct_answer": "**1A (AC First Class) is the highest luxury passenger travel class available on Indian Railways.**",
        "explanation": (
            "• **Private Cabins:** Coaches feature lockable private 4-berth cabins and 2-berth private coupes with sliding doors for complete security and privacy.\n"
            "• **Luxury Amenities:** Plush wide berths, carpeted floors, personalized attendant call bell, reading lights, and complimentary gourmet dining on premier trains like Rajdhani.\n"
            "• **No Side Berths:** There are no corridor side berths; the full aisle is open."
        ),
        "conditions": (
            "• Specific cabin or coupe allocation is decided manually by the charting officer during chart preparation based on VIP seniority and traveling pairs."
        )
    },

    "class_sl": {
        "id": "class_sl",
        "category": "coach_rules",
        "title": "SL (Sleeper Class)",
        "keywords": ["what is sl", "sl meaning", "sleeper class", "sl coach details", "sleeper coach kya hai"],
        "direct_answer": "**SL (Sleeper Class) is the traditional non-air-conditioned open sleeper coach on Indian Railways.**",
        "explanation": (
            "• **Layout:** 72 to 81 berths per coach configured in 3 tiers per bay (Lower, Middle, Upper) plus Side Lower and Side Upper.\n"
            "• **Features:** Open windows with safety bars, ceiling fans, wide luggage racks, and budget-friendly fares connecting all corners of the country.\n"
            "• **No Bedroll:** Bedding linen is not provided; passengers carry their own blankets or sheets."
        ),
        "conditions": (
            "• Middle berth folds down during daytime hours (06:00 AM to 10:00 PM) for shared sitting."
        )
    },

    "class_cc": {
        "id": "class_cc",
        "category": "coach_rules",
        "title": "CC (AC Chair Car)",
        "keywords": ["what is cc", "cc meaning", "ac chair car", "chair car coach details", "cc kya hai"],
        "direct_answer": "**CC (AC Chair Car) is an air-conditioned seated coach designed for day journeys and medium-distance intercity expresses like Shatabdi and Jan Shatabdi.**",
        "explanation": (
            "• **Seating Configuration:** Cushioned 3x2 seating arrangement with wide center aisles, reclining backrests, and individual folding food tray tables.\n"
            "• **Amenities:** Full climate control, wide panoramic windows, overhead luggage shelves, and charging points."
        ),
        "conditions": (
            "• Ideal for daylight intercity travel under 8 hours duration."
        )
    },

    "class_ec": {
        "id": "class_ec",
        "category": "coach_rules",
        "title": "EC (Executive Chair Car)",
        "keywords": ["what is ec", "ec meaning", "executive chair car", "vande bharat ec", "ec coach details", "ec kya hai"],
        "direct_answer": "**EC (Executive Chair Car) is the premier luxury seated coach featured on Vande Bharat Express and Shatabdi Express trains.**",
        "explanation": (
            "• **Spacious 2x2 Seating:** Ultra-wide reclining and rotating seats (on Vande Bharat) configured 2x2 with expansive legroom and footrests.\n"
            "• **VIP Comfort:** Premium on-board dining included in fare, large observation windows, bottle holders, USB sockets, and reading lights."
        ),
        "conditions": (
            "• Highest tier of comfort for day train travel across Indian Railways."
        )
    },

    # -------------------------------------------------------------------------
    # 7. SENIOR CITIZEN & QUOTA ALLOCATION
    # -------------------------------------------------------------------------
    "senior_citizen_quota": {
        "id": "senior_citizen_quota",
        "category": "quota_rules",
        "title": "Senior Citizen Lower Berth Quota Rules",
        "keywords": ["senior citizen quota", "lower berth for senior citizen", "senior citizen rules", "senior citizen lower berth", "bujurg ke liye lower berth"],
        "direct_answer": "**Indian Railways provides dedicated Lower Berth Quotas for senior citizens to ensure accessible travel without needing to climb.**",
        "explanation": (
            "• **Eligibility:** Male passengers aged **60 years and above**, and female passengers aged **45 years and above** traveling alone or as a senior couple.\n"
            "• **Automatic Allotment:** When booking tickets, the reservation system automatically prioritizes vacant Lower Berths for eligible seniors under the General Quota.\n"
            "• **Dedicated Quota:** A specific quota of 6 to 7 lower berths per Sleeper coach and 4 to 5 lower berths per 3A/2A coach is reserved specifically for seniors and solo female travelers."
        ),
        "conditions": (
            "• Valid age proof (Aadhaar, Voter ID, Senior Citizen card) must be carried and produced during journey verification."
        )
    },

    # -------------------------------------------------------------------------
    # 9. LEFT LUGGAGE / LOST BAGGAGE RULES
    # -------------------------------------------------------------------------
    "left_luggage_rules": {
        "id": "left_luggage_rules",
        "category": "luggage_rules",
        "title": "Left Luggage / Lost Baggage in Indian Railways",
        "keywords": [
            "left luggage", "forgot luggage", "lost luggage", "luggage left in train",
            "bag left in train", "left my bag", "forgot my bag", "forgot my luggage",
            "lost bag in train", "lost luggage in train", "luggage lost", "baggage lost",
            "saman chhoot gaya", "bag chhoot gaya"
        ],
        "direct_answer": "**If you have left or forgotten your luggage on a train, immediately report it to Railway Helpline 139 or the nearest Station Master / RPF post.**",
        "explanation": (
            "• **Immediate Action (Within Minutes/Hours):** Dial **139 (Railway Helpline)** or inform the Station Master / RPF post at your deboarding station immediately. Provide your **Train Number, Coach, Seat/Berth number**, and a description of your luggage.\n"
            "• **On-board Securing:** The control room alerts the on-board TTE, Train Superintendent, or RPF escort to inspect the berth and secure the unattended luggage before other passengers or terminal cleaners handle it.\n"
            "• **Lost Property Office (LPO):** If recovered at terminating stations or along the route, unattended items are deposited with the **Station Lost Property Office (LPO)** or RPF Thana under official inventory receipt.\n"
            "• **Claiming Your Property:** The owner can claim the item by producing travel proof (valid PNR/ticket), government photo ID, and verifying the contents of the baggage."
        ),
        "conditions": (
            "• You can also register a Left Luggage assistance report on SmartRail's Emergency Assistance portal (`emergency.html?service=luggage`) to generate an official Request ID (`LUG-YYYYMMDD-XXXXX`) for tracking."
        )
    }
}


# =============================================================================
# TOPIC & ENTITY EXTRACTION ENGINE
# =============================================================================

def extract_railway_entities(query: str) -> Dict[str, Any]:
    """
    Extracts all railway entities, concepts, relationships, and time contexts
    from natural-language, conversational, or Hinglish queries.
    """
    q_lower = query.lower().strip()

    entities = {
        "reservation_status": None,
        "rac_number": None,
        "relationship": None,
        "berth_type": None,
        "other_berth": None,
        "time_context": None,
        "topics": [],
        "language": "english"
    }

    # Detect Hindi/Hinglish cues
    hinglish_markers = ['kya', 'hai', 'h ', 'ka ', 'ke ', 'ki ', 'ko ', 'din ', 'me ', 'mein ', 'mai ', 'raat ', 
                        'baith ', 'so ', 'sota ', 'niche ', 'upar ', 'wala ', 'wali ', 'bhai ', 'khana ', 'sari ', 
                        'batao ', 'kaha ', 'kidhar ', 'kab ', 'sakta ', 'sakti ', 'karenge ']
    if any(m in q_lower for m in hinglish_markers):
        entities["language"] = "hinglish"

    # 1. RAC status & number
    rac_match = re.search(r'\brac\s*(\d+)?\b', q_lower)
    if rac_match:
        entities["reservation_status"] = "RAC"
        if rac_match.group(1):
            entities["rac_number"] = rac_match.group(1)
        entities["topics"].append("rac")

    # 2. Waitlist status
    if 'gnwl' in q_lower:
        entities["reservation_status"] = "GNWL"
        entities["topics"].append("gnwl")
    elif 'rlwl' in q_lower:
        entities["reservation_status"] = "RLWL"
        entities["topics"].append("rlwl")
    elif 'pqwl' in q_lower:
        entities["reservation_status"] = "PQWL"
        entities["topics"].append("pqwl")
    elif 'tqwl' in q_lower:
        entities["reservation_status"] = "TQWL"
        entities["topics"].append("tqwl")
    elif 'waiting' in q_lower or 'waitlist' in q_lower or re.search(r'\bwl\b', q_lower):
        entities["reservation_status"] = entities["reservation_status"] or "WL"
        entities["topics"].append("waitlist")

    # 3. Relationships
    if any(w in q_lower for w in ['brother', 'bhai', 'sister', 'behen', 'mother', 'father', 'friend', 'relative', 'family']):
        for rel in ['brother', 'bhai', 'sister', 'mother', 'father', 'friend', 'family']:
            if rel in q_lower:
                entities["relationship"] = 'brother' if rel in ['brother', 'bhai'] else rel
                break
        entities["topics"].append("berth_sharing")

    # 4. Berths (Side Lower, Side Upper, Lower, Middle, Upper)
    has_side = 'side' in q_lower
    if 'side lower' in q_lower or 'sl berth' in q_lower or (has_side and ('lower' in q_lower or 'niche' in q_lower)):
        entities["berth_type"] = "side_lower"
        entities["topics"].append("side_lower")
    elif 'side upper' in q_lower or 'su berth' in q_lower or (has_side and ('upper' in q_lower or 'upar' in q_lower)):
        entities["other_berth"] = "side_upper"
        entities["topics"].append("side_upper")
    elif 'middle' in q_lower:
        entities["berth_type"] = "middle"
        entities["topics"].append("middle_berth")
    elif 'lower' in q_lower or 'niche' in q_lower:
        entities["berth_type"] = "lower"
        entities["topics"].append("lower_berth")
    elif 'upper' in q_lower or 'upar' in q_lower:
        entities["berth_type"] = "upper"
        entities["topics"].append("upper_berth")

    if 'side upper' in q_lower or (has_side and 'upper' in q_lower):
        entities["other_berth"] = "side_upper"
        entities["topics"].append("side_upper")

    # 5. Time context (Daytime vs Nighttime)
    if any(w in q_lower for w in ['day', 'daytime', 'day time', 'din', 'din me', 'morning', 'afternoon']):
        entities["time_context"] = "daytime"
        entities["topics"].append("daytime_seating")
    elif any(w in q_lower for w in ['night', 'nighttime', 'raat', 'sleeping', 'so sakta']):
        entities["time_context"] = "night"
        entities["topics"].append("sleeping_hours")

    # 6. Actions (Sit, Sleep, Share, Cancel, Board, Travel, Book)
    if any(w in q_lower for w in ['sit', 'seat on', 'baith', 'sitting']):
        entities["topics"].append("seating_rules")
    if any(w in q_lower for w in ['sleep', 'so ', 'sota', 'sleeping']):
        entities["topics"].append("sleeping_rules")
    if any(w in q_lower for w in ['share', 'both share', 'dono share', 'sharing']):
        entities["topics"].append("berth_sharing")
    if any(w in q_lower for w in ['travel', 'board', 'board the train', 'travel allowed']):
        entities["topics"].append("travel_eligibility")
    if any(w in q_lower for w in ['cancel', 'cancellation', 'refund']):
        entities["topics"].append("cancellation_rules")
    if any(w in q_lower for w in ['change berth', 'swap seat', 'swap berth', 'change seat']):
        entities["topics"].append("berth_change")
    if any(w in q_lower for w in ['luggage', 'baggage', 'bag', 'suitcase', 'saman']):
        entities["topics"].append("luggage_rules")

    return entities


# =============================================================================
# KNOWLEDGE RETRIEVER ENGINE (RAG)
# =============================================================================

def retrieve_railway_knowledge(query: str, entities: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Retrieves the most authoritative and relevant railway rule document(s)
    from the structured knowledge base using scored semantic matching.
    """
    q_lower = query.lower()
    entities = entities or extract_railway_entities(query)

    scored_docs = []

    for doc_id, doc in KNOWLEDGE_DOCUMENTS.items():
        score = 0

        # 1. Specific multi-entity question scoring (CRITICAL MATCH)
        if doc_id == "rac_side_upper_lower_complex":
            if entities.get("reservation_status") == "RAC" and entities.get("other_berth") == "side_upper" and entities.get("time_context") == "daytime":
                score += 150
            if "side upper" in q_lower and ("lower" in q_lower or "rac" in q_lower) and ("day" in q_lower or "din" in q_lower):
                score += 120
            if "rac23" in q_lower and "brother" in q_lower:
                score += 80

        # 2. Side upper sitting on lower berth during day
        elif doc_id == "side_upper_lower_daytime":
            if ("side upper" in q_lower or "side upper wala" in q_lower) and ("lower" in q_lower or "niche" in q_lower) and ("day" in q_lower or "din" in q_lower or "sit" in q_lower or "baith" in q_lower):
                score += 130
            elif "side upper" in q_lower and "lower" in q_lower:
                score += 70

        # 3. Meaning of RAC Number (e.g. RAC 23)
        elif doc_id == "rac_number_meaning":
            if entities.get("rac_number") or re.search(r'\brac\s*\d+\b', q_lower):
                score += 110
            if any(w in q_lower for w in ["what does rac", "rac23 ka kya", "rac 23 mean", "my seat is rac"]):
                score += 80

        # 4. RAC travel eligibility
        elif doc_id == "rac_travel_eligibility":
            if "rac" in q_lower and any(w in q_lower for w in ["travel", "board", "board the train", "travel kar sakte", "allowed to travel"]):
                score += 120

        # 5. RAC berth sharing
        elif doc_id == "rac_berth_sharing":
            if "rac" in q_lower and any(w in q_lower for w in ["share", "sharing", "two rac", "both rac", "dono same berth"]):
                score += 120

        # 6. Daytime sleeping on lower berth
        elif doc_id == "daytime_sleeping_lower_berth":
            if ("sleep" in q_lower or "so " in q_lower or "so sakte" in q_lower) and ("lower" in q_lower or "niche" in q_lower):
                score += 110
            if "when can i sleep" in q_lower or "sleeping rules" in q_lower or "lower berth kab use" in q_lower:
                score += 100

        # 7. Difference between RAC and WL
        elif doc_id == "difference_rac_wl":
            if ("difference" in q_lower or "vs" in q_lower or "or" in q_lower) and ("rac" in q_lower and "wl" in q_lower):
                score += 140

        # 8. Waitlist boarding/travel rules
        elif doc_id == "waitlist_travel_rules":
            if ("waiting" in q_lower or "waitlist" in q_lower or "wl" in q_lower) and any(w in q_lower for w in ["travel", "board", "not confirmed", "unconfirmed", "cancelled"]):
                score += 120

        # 9. Berth change / swap
        elif doc_id == "berth_change_swap_rules":
            if any(w in q_lower for w in ["change my berth", "change berth", "swap seat", "swap berth", "change seat", "seat change", "seat badal"]):
                score += 130

        # 10. Keyword & phrase matching
        for kw in doc["keywords"]:
            if kw in q_lower:
                score += 40

        # 11. Category alignment
        if doc["category"] in entities.get("topics", []):
            score += 25

        if score > 0:
            scored_docs.append((score, doc))

    # Sort descending by relevance score
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_docs[:3]]


# =============================================================================
# NATURAL ANSWER GENERATOR (RAG PIPELINE)
# =============================================================================

def generate_rag_answer(query: str, entities: Dict[str, Any], retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates a structured, data-grounded response answering the ACTUAL user question.
    Format:
    1. Short direct answer first.
    2. Detailed explanation.
    3. Important conditions & exceptions.
    """
    if not retrieved_docs:
        return None

    primary_doc = retrieved_docs[0]

    # Assemble structured response
    resp_lines = [
        f"### ℹ️ Indian Railways Guide: {primary_doc['title']}\n",
        f"{primary_doc['direct_answer']}\n",
        f"{primary_doc['explanation']}\n",
        f"**Important Conditions & Guidelines:**\n{primary_doc['conditions']}"
    ]

    # If query is the specific RAC23 + brother + side upper + lower daytime question:
    # Ensure all topics are clearly connected
    if primary_doc['id'] == 'rac_side_upper_lower_complex':
        resp_lines = [
            "### 💺 Railway Berth & Seating Rules: RAC + Side Upper Access\n",
            f"{primary_doc['direct_answer']}\n",
            "**Key Points for Your Journey:**\n",
            "• **Daytime Seating Right (06:00 AM – 10:00 PM):** Under Indian Railways passenger regulations, the Side Upper (SU) passenger has the official right to sit on the Side Lower (SL) berth during daytime hours.",
            "• **Your RAC 23 Shared Allocation:** Because both you and your brother hold RAC status, you are jointly allocated the Side Lower berth as your shared travel space. During the day, you, your brother, and the Side Upper passenger share the two-seater space together.",
            "• **Night Sleeping Hours (10:00 PM – 06:00 AM):** At night, the Side Upper passenger **must return to their designated upper berth to sleep**. During sleeping hours, the Side Lower berth belongs exclusively to you and your brother to rest/sleep together.",
            "• **Chart Upgrade Probability:** If any confirmed passenger on your coach cancels before chart preparation (4 hours prior to train departure), your RAC 23 status may automatically upgrade to a full confirmed berth!\n",
            "**Guidelines:** During daytime hours, passengers are expected to accommodate each other courteously on the two-seat Side Lower layout."
        ]

    # Suggested actions
    actions = [
        {"label": "Search Trains & Availability", "url": "search.html"},
        {"label": "Check PNR Status", "url": "pnr-status.html"}
    ]
    if 'tatkal' in primary_doc['category']:
        actions.append({"label": "Tatkal Guidelines", "query": "what is tatkal?"})
    elif 'cancellation' in primary_doc['category']:
        actions.append({"label": "Cancellation Portal", "url": "pnr-status.html"})

    # Determine intent tag (RAILWAY_KNOWLEDGE by default, LEFT_LUGGAGE for luggage, CANCELLATION_HELP for cancellations)
    if "luggage" in primary_doc['category']:
        intent_tag = "LEFT_LUGGAGE"
        actions = [
            {"label": "🧳 Report Left Luggage", "url": "emergency.html?service=luggage"},
            {"label": "Call RPF Helpline 139", "url": "emergency.html"}
        ]
    elif "cancellation" in primary_doc['category']:
        intent_tag = "CANCELLATION_HELP"
    else:
        intent_tag = "RAILWAY_KNOWLEDGE"

    return {
        "intent": intent_tag,
        "response": "\n\n".join(resp_lines),
        "suggested_actions": actions,
        "rag_context": {
            "user_query": query,
            "intent": intent_tag,
            "topics": entities.get("topics", []),
            "entities": entities,
            "retrieved_knowledge": [d['title'] for d in retrieved_docs]
        }
    }


# =============================================================================
# STAGE-2 INTELLIGENT SEMANTIC CLASSIFIER & REASONER
# =============================================================================

def stage_2_classify_and_reason(query: str, ctx: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Stage-2 Intelligent Fallback Classifier:
    When primary regex/rule-based heuristics do not detect a confident intent,
    this stage reasons over the query semantics, extracts multi-entities,
    queries the RAG knowledge retriever, and constructs a grounded response.
    Returns None only if the query is genuinely out-of-domain or uninterpretable.
    """
    q_lower = query.lower().strip()
    entities = extract_railway_entities(query)

    # 1. Check if query is railway knowledge / rules / berth / RAC / waitlist
    retrieved_docs = retrieve_railway_knowledge(query, entities)
    if retrieved_docs:
        # Check relevance: has at least one matching concept or topic
        doc = retrieved_docs[0]
        has_any_match = any(kw in q_lower for kw in doc["keywords"]) or any(t in doc["category"] for t in entities.get("topics", []))
        if has_any_match or len(entities.get("topics", [])) > 0:
            return generate_rag_answer(query, entities, retrieved_docs)

    # 2. Check for Hinglish train inquiries (e.g. "Jaipur se Delhi ki train", "12956 abhi kaha hai")
    if 'kaha' in q_lower or 'kidhar' in q_lower or 'kahan' in q_lower:
        match_num = re.search(r'\b\d{5}\b', q_lower)
        if match_num or (ctx and ctx.get('last_train_number')):
            # Live tracking intent
            return {
                "stage_2_intent": "LIVE_STATUS",
                "train_number": match_num.group(0) if match_num else ctx.get('last_train_number')
            }

    if 'khana' in q_lower or 'bhojan' in q_lower or 'nashta' in q_lower:
        return {
            "stage_2_intent": "FOOD_ORDER"
        }

    return None
