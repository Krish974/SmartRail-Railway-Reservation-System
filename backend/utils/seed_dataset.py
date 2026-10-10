"""
Centralized Seed Dataset for Indian Railway Reservation System.
Contains 32 verified stations across 23 cities, 30 major trains, 118 route halts/stops,
and coach configurations.
"""

STATIONS = [
    (1, 'NDLS', 'New Delhi Railway Station', 'New Delhi', 'Delhi', 28.6427, 77.2197, 'NDLS, New Delhi, Delhi, DLI, Central Delhi, Northern Railway'),
    (2, 'DLI', 'Old Delhi Railway Station', 'Delhi', 'Delhi', 28.6619, 77.2280, 'DLI, Old Delhi, Delhi Junction, Purani Dilli, Delhi'),
    (3, 'NZM', 'Hazrat Nizamuddin', 'New Delhi', 'Delhi', 28.5892, 77.2530, 'NZM, Nizamuddin, Delhi Nizamuddin, South Delhi, Delhi'),
    (4, 'ANVT', 'Anand Vihar Terminal', 'Delhi', 'Delhi', 28.6508, 77.3153, 'ANVT, Anand Vihar, East Delhi, Delhi'),
    (5, 'MMCT', 'Mumbai Central', 'Mumbai', 'Maharashtra', 18.9696, 72.8193, 'MMCT, Mumbai Central, Bombay, BCT, South Mumbai, Mumbai'),
    (6, 'CSMT', 'Chhatrapati Shivaji Maharaj Terminus', 'Mumbai', 'Maharashtra', 18.9400, 72.8353, 'CSMT, VT, Victoria Terminus, Mumbai, Bombay'),
    (7, 'BDTS', 'Bandra Terminus', 'Mumbai', 'Maharashtra', 19.0620, 72.8415, 'BDTS, Bandra, Mumbai Bandra, Western Suburbs, Mumbai'),
    (8, 'JP', 'Jaipur Junction', 'Jaipur', 'Rajasthan', 26.9196, 75.7878, 'JP, Jaipur, Pink City, Jaipur Junction, Rajasthan'),
    (9, 'DPA', 'Durgapura', 'Jaipur', 'Rajasthan', 26.8524, 75.7870, 'DPA, Durgapura, Jaipur South, Tonk Road, Jaipur'),
    (10, 'GADJ', 'Gandhinagar Jaipur', 'Jaipur', 'Rajasthan', 26.8834, 75.8010, 'GADJ, Gandhinagar Jaipur, Bajaj Nagar, Jaipur'),
    (11, 'HWH', 'Howrah Junction', 'Kolkata', 'West Bengal', 22.5850, 88.3426, 'HWH, Howrah, Kolkata, Calcutta, Eastern Railway'),
    (12, 'SDAH', 'Sealdah', 'Kolkata', 'West Bengal', 22.5670, 88.3713, 'SDAH, Sealdah, Kolkata, Calcutta'),
    (13, 'SBC', 'KSR Bengaluru City Junction', 'Bengaluru', 'Karnataka', 12.9781, 77.5696, 'SBC, Bengaluru, Bangalore, Majestic, Karnataka'),
    (14, 'YPR', 'Yesvantpur Junction', 'Bengaluru', 'Karnataka', 13.0238, 77.5501, 'YPR, Yeshwantpur, Yesvantpur, Bangalore North, Bengaluru'),
    (15, 'MAS', 'MGR Chennai Central', 'Chennai', 'Tamil Nadu', 13.0827, 80.2707, 'MAS, Chennai Central, Madras, Central Chennai, Tamil Nadu'),
    (16, 'ADI', 'Ahmedabad Junction', 'Ahmedabad', 'Gujarat', 23.0225, 72.5714, 'ADI, Ahmedabad, Kalupur, Gujarat'),
    (17, 'BPL', 'Bhopal Junction', 'Bhopal', 'Madhya Pradesh', 23.2599, 77.4126, 'BPL, Bhopal, Lake City, Madhya Pradesh'),
    (18, 'RKMP', 'Rani Kamalapati', 'Bhopal', 'Madhya Pradesh', 23.2085, 77.4390, 'RKMP, Rani Kamlapati, Habibganj, World Class Station, Bhopal'),
    (19, 'LKO', 'Lucknow Charbagh', 'Lucknow', 'Uttar Pradesh', 26.8322, 80.9220, 'LKO, Lucknow, Charbagh, Nawabs City, UP, Uttar Pradesh'),
    (20, 'CNB', 'Kanpur Central', 'Kanpur', 'Uttar Pradesh', 26.4547, 80.3507, 'CNB, Kanpur, Cawnpore, Uttar Pradesh'),
    (21, 'NGP', 'Nagpur Junction', 'Nagpur', 'Maharashtra', 21.1524, 79.0888, 'NGP, Nagpur, Orange City, Central India, Maharashtra'),
    (22, 'KOTA', 'Kota Junction', 'Kota', 'Rajasthan', 25.2138, 75.8648, 'KOTA, Kota, Coaching Capital, Rajasthan'),
    (23, 'RTM', 'Ratlam Junction', 'Ratlam', 'Madhya Pradesh', 23.3341, 75.0376, 'RTM, Ratlam, Western Railway Junction, Madhya Pradesh'),
    (24, 'BRC', 'Vadodara Junction', 'Vadodara', 'Gujarat', 22.3072, 73.1812, 'BRC, Vadodara, Baroda, Gujarat'),
    (25, 'ST', 'Surat', 'Surat', 'Gujarat', 21.1702, 72.8311, 'ST, Surat, Diamond City, Silk City, Gujarat'),
    (26, 'AGC', 'Agra Cantt', 'Agra', 'Uttar Pradesh', 27.1594, 77.9944, 'AGC, Agra Cantt, Taj Mahal, Agra, UP, Uttar Pradesh'),
    (27, 'BSB', 'Varanasi Junction', 'Varanasi', 'Uttar Pradesh', 25.3283, 82.9860, 'BSB, Varanasi, Banaras, Kashi, Uttar Pradesh'),
    (28, 'PNBE', 'Patna Junction', 'Patna', 'Bihar', 25.6022, 85.1376, 'PNBE, Patna, Pataliputra, Bihar'),
    (29, 'PUNE', 'Pune Junction', 'Pune', 'Maharashtra', 18.5284, 73.8743, 'PUNE, Pune, Poona, Oxford of the East, Maharashtra'),
    (30, 'MAO', 'Madgaon Junction', 'Goa', 'Goa', 15.2741, 73.9803, 'MAO, Madgaon, Margao, Goa, Konkan Railway'),
    (31, 'AII', 'Ajmer Junction', 'Ajmer', 'Rajasthan', 26.4526, 74.6399, 'AII, Ajmer, Dargah Sharif, Pushkar, Rajasthan'),
    (32, 'CDG', 'Chandigarh Junction', 'Chandigarh', 'Chandigarh', 30.7022, 76.8228, 'CDG, Chandigarh, City Beautiful, Punjab Haryana')
]

QUOTAS = [
    (1, 'GN', 'General', 0.00, 'Standard booking quota open for all passengers'),
    (2, 'LD', 'Ladies', 0.00, 'Reserved exclusively for solo female travelers or women with children'),
    (3, 'SS', 'Senior Citizen', -30.00, 'Discounted lower berth allocation for senior citizens (60+ M, 58+ F)'),
    (4, 'TQ', 'Tatkal', 30.00, 'Emergency short-notice travel quota with tatkal surcharge'),
    (5, 'PT', 'Premium Tatkal', 50.00, 'Dynamic pricing emergency quota with priority booking'),
    (6, 'HP', 'Divyang', -50.00, 'Concession & dedicated lower berth quota for persons with disabilities')
]

TRAINS = [
    # id, number, name, src_id, dst_id, dep, arr, dur, days, type
    (1, '12952', 'New Delhi - Mumbai Tejas Rajdhani', 1, 5, '16:55', '08:35', '15h 40m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Tejas Rajdhani'),
    (2, '12951', 'Mumbai - New Delhi Tejas Rajdhani', 5, 1, '17:00', '08:32', '15h 32m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Tejas Rajdhani'),
    (3, '12953', 'August Kranti Tejas Rajdhani', 5, 3, '17:10', '09:43', '16h 33m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Tejas Rajdhani'),
    (4, '12954', 'August Kranti Tejas Rajdhani (Up)', 3, 5, '17:15', '10:05', '16h 50m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Tejas Rajdhani'),
    (5, '12907', 'Maharashtra Sampark Kranti', 7, 3, '17:30', '10:15', '16h 45m', 'Wed,Sun', 'Sampark Kranti'),
    (6, '12908', 'Maharashtra Sampark Kranti (Up)', 3, 7, '16:30', '09:15', '16h 45m', 'Mon,Thu', 'Sampark Kranti'),
    (7, '12137', 'Punjab Mail', 6, 1, '19:35', '21:30', '25h 55m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Mail/Express'),
    (8, '12138', 'Punjab Mail (Up)', 1, 6, '05:10', '07:35', '26h 25m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Mail/Express'),
    (9, '12015', 'New Delhi - Ajmer Shatabdi Express', 1, 31, '06:10', '12:55', '6h 45m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Shatabdi Express'),
    (10, '12016', 'Ajmer - New Delhi Shatabdi Express', 31, 1, '15:55', '22:30', '6h 35m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Shatabdi Express'),
    (11, '12957', 'Swarna Jayanti Rajdhani Express', 16, 1, '17:45', '07:30', '13h 45m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Rajdhani Express'),
    (12, '12958', 'Swarna Jayanti Rajdhani Express (Up)', 1, 16, '19:55', '08:25', '12h 30m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Rajdhani Express'),
    (13, '20977', 'Ajmer - Delhi Cantt Vande Bharat', 31, 1, '06:20', '11:35', '5h 15m', 'Mon,Tue,Wed,Thu,Fri,Sun', 'Vande Bharat Express'),
    (14, '20978', 'Delhi Cantt - Ajmer Vande Bharat', 1, 31, '18:40', '23:55', '5h 15m', 'Mon,Tue,Wed,Thu,Fri,Sun', 'Vande Bharat Express'),
    (15, '12413', 'Pooja Superfast Express', 31, 2, '14:15', '21:50', '7h 35m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Superfast Express'),
    (16, '12414', 'Pooja Superfast Express (Up)', 2, 31, '04:30', '12:10', '7h 40m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Superfast Express'),
    (17, '12301', 'Howrah - New Delhi Rajdhani Express', 11, 1, '16:50', '10:05', '17h 15m', 'Mon,Tue,Wed,Fri,Sat,Sun', 'Rajdhani Express'),
    (18, '12302', 'New Delhi - Howrah Rajdhani Express', 1, 11, '16:55', '09:55', '17h 00m', 'Mon,Tue,Wed,Thu,Sat,Sun', 'Rajdhani Express'),
    (19, '12313', 'Sealdah - New Delhi Rajdhani Express', 12, 1, '16:50', '10:50', '18h 00m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Rajdhani Express'),
    (20, '12314', 'New Delhi - Sealdah Rajdhani Express', 1, 12, '16:30', '10:10', '17h 40m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Rajdhani Express'),
    (21, '22691', 'KSR Bengaluru - New Delhi Rajdhani', 13, 1, '20:00', '05:30', '33h 30m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Superfast Rajdhani'),
    (22, '22692', 'New Delhi - KSR Bengaluru Rajdhani', 1, 13, '20:45', '05:20', '32h 35m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Superfast Rajdhani'),
    (23, '12615', 'Grand Trunk Express', 15, 1, '18:50', '05:05', '34h 15m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Superfast Express'),
    (24, '12616', 'Grand Trunk Express (Up)', 1, 15, '16:10', '04:30', '36h 20m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Superfast Express'),
    (25, '20901', 'Mumbai Central - Gandhinagar Vande Bharat', 5, 16, '06:00', '11:25', '5h 25m', 'Mon,Tue,Wed,Fri,Sat,Sun', 'Vande Bharat Express'),
    (26, '20902', 'Gandhinagar - Mumbai Central Vande Bharat', 16, 5, '15:00', '20:25', '5h 25m', 'Mon,Tue,Wed,Fri,Sat,Sun', 'Vande Bharat Express'),
    (27, '12002', 'New Delhi - Bhopal Shatabdi Express', 1, 18, '06:00', '14:40', '8h 40m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Shatabdi Express'),
    (28, '12001', 'Bhopal - New Delhi Shatabdi Express', 18, 1, '15:15', '23:50', '8h 35m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Shatabdi Express'),
    (29, '12004', 'New Delhi - Lucknow Shatabdi Express', 1, 19, '06:10', '12:40', '6h 30m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Shatabdi Express'),
    (30, '12003', 'Lucknow - New Delhi Shatabdi Express', 19, 1, '15:30', '22:15', '6h 45m', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 'Shatabdi Express')
]

STOPS = [
    # 1. 12952 (NDLS -> MMCT)
    (1, 1, 1, 'START', '16:55', 0, 0), (1, 22, 2, '21:25', '21:35', 10, 465), (1, 23, 3, '00:12', '00:15', 3, 730), (1, 24, 4, '03:35', '03:45', 10, 992), (1, 25, 5, '05:10', '05:15', 5, 1122), (1, 5, 6, '08:35', 'END', 0, 1384),
    # 2. 12951 (MMCT -> NDLS)
    (2, 5, 1, 'START', '17:00', 0, 0), (2, 25, 2, '19:30', '19:35', 5, 263), (2, 24, 3, '21:00', '21:10', 10, 392), (2, 23, 4, '00:22', '00:25', 3, 653), (2, 22, 5, '03:10', '03:20', 10, 919), (2, 1, 6, '08:32', 'END', 0, 1384),
    # 3. 12953 (MMCT -> NZM)
    (3, 5, 1, 'START', '17:10', 0, 0), (3, 25, 2, '19:43', '19:48', 5, 263), (3, 24, 3, '21:18', '21:28', 10, 392), (3, 22, 4, '04:00', '04:10', 10, 919), (3, 3, 5, '09:43', 'END', 0, 1377),
    # 4. 12954 (NZM -> MMCT)
    (4, 3, 1, 'START', '17:15', 0, 0), (4, 22, 2, '22:25', '22:35', 10, 458), (4, 24, 3, '05:10', '05:20', 10, 985), (4, 25, 4, '06:50', '06:55', 5, 1114), (4, 5, 5, '10:05', 'END', 0, 1377),
    # 5. 12907 (BDTS -> NZM)
    (5, 7, 1, 'START', '17:30', 0, 0), (5, 24, 2, '22:10', '22:20', 10, 387), (5, 22, 3, '04:30', '04:40', 10, 914), (5, 3, 4, '10:15', 'END', 0, 1372),
    # 6. 12908 (NZM -> BDTS)
    (6, 3, 1, 'START', '16:30', 0, 0), (6, 22, 2, '21:50', '22:00', 10, 458), (6, 24, 3, '04:25', '04:35', 10, 985), (6, 7, 4, '09:15', 'END', 0, 1372),
    # 7. 12137 (CSMT -> NDLS)
    (7, 6, 1, 'START', '19:35', 0, 0), (7, 17, 2, '08:55', '09:05', 10, 837), (7, 26, 3, '17:45', '17:50', 5, 1349), (7, 1, 4, '21:30', 'END', 0, 1543),
    # 8. 12138 (NDLS -> CSMT)
    (8, 1, 1, 'START', '05:10', 0, 0), (8, 26, 2, '07:55', '08:00', 5, 194), (8, 17, 3, '16:30', '16:40', 10, 706), (8, 6, 4, '07:35', 'END', 0, 1543),
    # 9. 12015 (NDLS -> AII via JP)
    (9, 1, 1, 'START', '06:10', 0, 0), (9, 8, 2, '10:35', '10:40', 5, 308), (9, 31, 3, '12:55', 'END', 0, 443),
    # 10. 12016 (AII -> NDLS via JP)
    (10, 31, 1, 'START', '15:55', 0, 0), (10, 8, 2, '17:30', '17:35', 5, 135), (10, 1, 3, '22:30', 'END', 0, 443),
    # 11. 12957 (ADI -> NDLS via JP)
    (11, 16, 1, 'START', '17:45', 0, 0), (11, 8, 2, '02:35', '02:45', 10, 625), (11, 1, 3, '07:30', 'END', 0, 933),
    # 12. 12958 (NDLS -> ADI via JP)
    (12, 1, 1, 'START', '19:55', 0, 0), (12, 8, 2, '23:55', '00:05', 10, 308), (12, 16, 3, '08:25', 'END', 0, 933),
    # 13. 20977 (AII -> NDLS Vande Bharat via JP)
    (13, 31, 1, 'START', '06:20', 0, 0), (13, 8, 2, '07:40', '07:45', 5, 135), (13, 1, 3, '11:35', 'END', 0, 443),
    # 14. 20978 (NDLS -> AII Vande Bharat via JP)
    (14, 1, 1, 'START', '18:40', 0, 0), (14, 8, 2, '22:00', '22:05', 5, 308), (14, 31, 3, '23:55', 'END', 0, 443),
    # 15. 12413 (AII -> DLI via JP)
    (15, 31, 1, 'START', '14:15', 0, 0), (15, 8, 2, '15:55', '16:05', 10, 135), (15, 2, 3, '21:50', 'END', 0, 443),
    # 16. 12414 (DLI -> AII via JP)
    (16, 2, 1, 'START', '04:30', 0, 0), (16, 8, 2, '09:35', '09:45', 10, 308), (16, 31, 3, '12:10', 'END', 0, 443),
    # 17. 12301 (HWH -> NDLS)
    (17, 11, 1, 'START', '16:50', 0, 0), (17, 28, 2, '22:05', '22:15', 10, 532), (17, 20, 3, '04:35', '04:45', 10, 1012), (17, 1, 4, '10:05', 'END', 0, 1447),
    # 18. 12302 (NDLS -> HWH)
    (18, 1, 1, 'START', '16:55', 0, 0), (18, 20, 2, '21:28', '21:38', 10, 435), (18, 28, 3, '03:45', '03:55', 10, 915), (18, 11, 4, '09:55', 'END', 0, 1447),
    # 19. 12313 (SDAH -> NDLS)
    (19, 12, 1, 'START', '16:50', 0, 0), (19, 20, 2, '05:15', '05:25', 10, 1018), (19, 1, 3, '10:50', 'END', 0, 1453),
    # 20. 12314 (NDLS -> SDAH)
    (20, 1, 1, 'START', '16:30', 0, 0), (20, 20, 2, '21:05', '21:15', 10, 435), (20, 12, 3, '10:10', 'END', 0, 1453),
    # 21. 22691 (SBC -> NDLS)
    (21, 13, 1, 'START', '20:00', 0, 0), (21, 21, 2, '14:50', '15:00', 10, 1248), (21, 17, 3, '20:45', '20:55', 10, 1638), (21, 26, 4, '01:45', '01:50', 5, 2150), (21, 1, 5, '05:30', 'END', 0, 2344),
    # 22. 22692 (NDLS -> SBC)
    (22, 1, 1, 'START', '20:45', 0, 0), (22, 26, 2, '23:45', '23:50', 5, 194), (22, 17, 3, '05:20', '05:30', 10, 706), (22, 21, 4, '11:20', '11:30', 10, 1096), (22, 13, 5, '05:20', 'END', 0, 2344),
    # 23. 12615 (MAS -> NDLS)
    (23, 15, 1, 'START', '18:50', 0, 0), (23, 21, 2, '11:25', '11:35', 10, 1092), (23, 17, 3, '18:35', '18:45', 10, 1482), (23, 26, 4, '01:45', '01:50', 5, 1994), (23, 1, 5, '05:05', 'END', 0, 2188),
    # 24. 12616 (NDLS -> MAS)
    (24, 1, 1, 'START', '16:10', 0, 0), (24, 26, 2, '19:25', '19:30', 5, 194), (24, 17, 3, '02:35', '02:45', 10, 706), (24, 21, 4, '10:10', '10:20', 10, 1096), (24, 15, 5, '04:30', 'END', 0, 2188),
    # 25. 20901 (MMCT -> ADI)
    (25, 5, 1, 'START', '06:00', 0, 0), (25, 25, 2, '08:25', '08:30', 5, 263), (25, 24, 3, '09:45', '09:50', 5, 392), (25, 16, 4, '11:25', 'END', 0, 491),
    # 26. 20902 (ADI -> MMCT)
    (26, 16, 1, 'START', '15:00', 0, 0), (26, 24, 2, '16:00', '16:05', 5, 99), (26, 25, 3, '17:30', '17:35', 5, 228), (26, 5, 4, '20:25', 'END', 0, 491),
    # 27. 12002 (NDLS -> RKMP)
    (27, 1, 1, 'START', '06:00', 0, 0), (27, 26, 2, '07:45', '07:50', 5, 194), (27, 17, 3, '14:00', '14:05', 5, 706), (27, 18, 4, '14:40', 'END', 0, 712),
    # 28. 12001 (RKMP -> NDLS)
    (28, 18, 1, 'START', '15:15', 0, 0), (28, 17, 2, '15:25', '15:30', 5, 6), (28, 26, 3, '21:15', '21:20', 5, 518), (28, 1, 4, '23:50', 'END', 0, 712),
    # 29. 12004 (NDLS -> LKO)
    (29, 1, 1, 'START', '06:10', 0, 0), (29, 20, 2, '11:15', '11:20', 5, 435), (29, 19, 3, '12:40', 'END', 0, 511),
    # 30. 12003 (LKO -> NDLS)
    (30, 19, 1, 'START', '15:30', 0, 0), (30, 20, 2, '16:45', '16:50', 5, 76), (30, 1, 3, '22:15', 'END', 0, 511)
]

def generate_coaches():
    coaches = []
    c_id = 1
    for t in TRAINS:
        t_id = t[0]
        t_type = t[9]
        if 'Vande Bharat' in t_type or 'Shatabdi' in t_type:
            coaches.append((c_id, t_id, 'C1', 'CC', 75, 1280.00))
            c_id += 1
            coaches.append((c_id, t_id, 'E1', 'EC', 52, 2450.00))
            c_id += 1
        elif 'Rajdhani' in t_type:
            coaches.append((c_id, t_id, 'B1', '3A', 72, 2050.00))
            c_id += 1
            coaches.append((c_id, t_id, 'A1', '2A', 48, 2870.00))
            c_id += 1
            coaches.append((c_id, t_id, 'H1', '1A', 24, 4550.00))
            c_id += 1
        else: # Superfast, Sampark Kranti, Mail/Express
            coaches.append((c_id, t_id, 'S1', 'SL', 72, 650.00))
            c_id += 1
            coaches.append((c_id, t_id, 'B1', '3A', 72, 1750.00))
            c_id += 1
            coaches.append((c_id, t_id, 'A1', '2A', 48, 2550.00))
            c_id += 1
    return coaches

COACHES = generate_coaches()

# Operational Passing Stations / Points for Corridor Tracking Benchmarks
# (train_id, station_id, point_name, point_code, route_sequence, point_type, estimated_time, distance_km)
PASSING_POINTS = [
    # Train 1 (12952 New Delhi - Mumbai Tejas Rajdhani)
    (1, None, 'Shivaji Bridge', 'CSB', 2, 'PASSING', '16:57', 1.5),
    (1, None, 'Tilak Bridge', 'TKJ', 3, 'PASSING', '16:59', 3.0),
    (1, None, 'Pragati Maidan', 'PGMD', 4, 'PASSING', '17:02', 4.8),
    (1, 3, 'Hazrat Nizamuddin', 'NZM', 5, 'PASSING', '17:07', 7.2),
    (1, None, 'Mathura Junction', 'MTJ', 6, 'PASSING', '18:35', 141.0),
    (1, None, 'Bharatpur Junction', 'BTE', 7, 'PASSING', '19:08', 175.0),
    (1, None, 'Sawai Madhopur Junction', 'SWM', 8, 'PASSING', '20:25', 356.0),
    (1, None, 'Ramganj Mandi', 'RMA', 10, 'PASSING', '22:20', 537.0),
    (1, None, 'Shamgarh', 'SGZ', 11, 'PASSING', '23:05', 598.0),
    (1, None, 'Nagda Junction', 'NAD', 12, 'PASSING', '23:55', 690.0),
    (1, None, 'Dahod', 'DHD', 14, 'PASSING', '01:32', 844.0),
    (1, None, 'Godhra Junction', 'GDA', 15, 'PASSING', '02:30', 917.0),
    (1, None, 'Bharuch Junction', 'BH', 17, 'PASSING', '04:25', 1063.0),
    (1, None, 'Navsari', 'NVS', 19, 'PASSING', '05:38', 1151.0),
    (1, None, 'Valsad', 'BL', 20, 'PASSING', '06:12', 1190.0),
    (1, None, 'Vapi', 'VAPI', 21, 'PASSING', '06:33', 1216.0),
    (1, None, 'Palghar', 'PLG', 22, 'PASSING', '07:25', 1298.0),
    (1, None, 'Borivali', 'BVI', 23, 'PASSING', '08:05', 1354.0),

    # Train 9 (12015 New Delhi - Ajmer Shatabdi)
    (9, None, 'Palam', 'PM', 3, 'PASSING', '06:44', 19.0),
    (9, None, 'Garhi Harsaru', 'GHH', 5, 'PASSING', '07:08', 42.0),
    (9, None, 'Pataudi Road', 'PTRD', 6, 'PASSING', '07:26', 62.0),
    (9, None, 'Bawal', 'BWL', 8, 'PASSING', '08:02', 99.0),
    (9, None, 'Khairthal', 'KRH', 10, 'PASSING', '08:31', 138.0),
    (9, None, 'Rajgarh', 'RHG', 12, 'PASSING', '09:10', 187.0),
    (9, None, 'Dausa', 'DO', 14, 'PASSING', '09:56', 247.0),
    (9, 9, 'Durgapura', 'DPA', 17, 'PASSING', '10:55', 317.0),
    (9, None, 'Kishangarh', 'KSG', 19, 'PASSING', '12:28', 418.0)
]
