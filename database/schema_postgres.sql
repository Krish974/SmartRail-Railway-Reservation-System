-- SMART INDIAN RAILWAY TICKET RESERVATION SYSTEM
-- Database Schema for PostgreSQL 14+ (Production Ready)
-- Run this script on your PostgreSQL database (e.g., Render Postgres, Railway Postgres, Supabase, Neon)

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'USER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 2. STATIONS TABLE
CREATE TABLE IF NOT EXISTS stations (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    aliases TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_stations_code ON stations(code);
CREATE INDEX IF NOT EXISTS idx_stations_city ON stations(city);

-- 3. TRAINS TABLE
CREATE TABLE IF NOT EXISTS trains (
    id SERIAL PRIMARY KEY,
    train_number VARCHAR(10) NOT NULL UNIQUE,
    train_name VARCHAR(150) NOT NULL,
    source_station_id INT REFERENCES stations(id) ON DELETE CASCADE,
    dest_station_id INT REFERENCES stations(id) ON DELETE CASCADE,
    departure_time VARCHAR(10) NOT NULL,
    arrival_time VARCHAR(10) NOT NULL,
    duration VARCHAR(20) NOT NULL,
    running_days VARCHAR(50) NOT NULL,
    train_type VARCHAR(50) DEFAULT 'Superfast Express',
    is_active INT DEFAULT 1,
    route_status VARCHAR(20) DEFAULT 'complete',
    route_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    route_error TEXT,
    route_stop_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_trains_number ON trains(train_number);

-- 4. TRAIN STOPS TABLE
CREATE TABLE IF NOT EXISTS train_stops (
    id SERIAL PRIMARY KEY,
    train_id INT NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    station_id INT NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    stop_sequence INT NOT NULL,
    arrival_time VARCHAR(10) NOT NULL,
    departure_time VARCHAR(10) NOT NULL,
    halt_minutes INT DEFAULT 0,
    distance_km DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(train_id, station_id)
);
CREATE INDEX IF NOT EXISTS idx_stops_train ON train_stops(train_id);

-- 5. TRAIN ROUTE PASSING POINTS
CREATE TABLE IF NOT EXISTS train_route_points (
    id SERIAL PRIMARY KEY,
    train_id INT NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    station_id INT REFERENCES stations(id) ON DELETE SET NULL,
    point_name VARCHAR(255) NOT NULL,
    point_code VARCHAR(50),
    route_sequence INT NOT NULL,
    point_type VARCHAR(50) DEFAULT 'PASSING',
    estimated_time VARCHAR(50),
    distance_km DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_route_points_train ON train_route_points(train_id);

-- 6. COACHES TABLE
CREATE TABLE IF NOT EXISTS coaches (
    id SERIAL PRIMARY KEY,
    train_id INT NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    coach_number VARCHAR(10) NOT NULL,
    coach_class VARCHAR(10) NOT NULL,
    total_seats INT NOT NULL DEFAULT 72,
    base_fare DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_coaches_train ON coaches(train_id);

-- 7. SEATS TABLE
CREATE TABLE IF NOT EXISTS seats (
    id SERIAL PRIMARY KEY,
    coach_id INT NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    seat_number INT NOT NULL,
    seat_type VARCHAR(20) NOT NULL,
    is_window INT DEFAULT 0,
    is_aisle INT DEFAULT 0,
    deck_or_position VARCHAR(20) DEFAULT 'STANDARD',
    UNIQUE(coach_id, seat_number)
);
CREATE INDEX IF NOT EXISTS idx_seats_coach ON seats(coach_id);

-- 8. QUOTAS TABLE
CREATE TABLE IF NOT EXISTS quotas (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    discount_or_premium_pct DOUBLE PRECISION DEFAULT 0.0,
    description TEXT
);

-- 9. BOOKINGS TABLE
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    booking_reference VARCHAR(50) NOT NULL UNIQUE,
    pnr VARCHAR(10) NOT NULL UNIQUE,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    train_id INT NOT NULL REFERENCES trains(id),
    coach_id INT NOT NULL REFERENCES coaches(id),
    journey_date VARCHAR(20) NOT NULL,
    quota_code VARCHAR(10) DEFAULT 'GN',
    base_fare DOUBLE PRECISION NOT NULL,
    tax_amount DOUBLE PRECISION DEFAULT 0.0,
    convenience_fee DOUBLE PRECISION DEFAULT 17.70,
    total_fare DOUBLE PRECISION NOT NULL,
    status VARCHAR(20) DEFAULT 'CONFIRMED',
    chart_prepared INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bookings_pnr ON bookings(pnr);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);

-- 10. PASSENGERS TABLE
CREATE TABLE IF NOT EXISTS passengers (
    id SERIAL PRIMARY KEY,
    booking_id INT NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    seat_id INT REFERENCES seats(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(10) NOT NULL,
    id_type VARCHAR(50) NOT NULL,
    id_number VARCHAR(100) NOT NULL,
    seat_number_assigned VARCHAR(20),
    berth_type VARCHAR(20),
    status VARCHAR(20) DEFAULT 'CONFIRMED'
);
CREATE INDEX IF NOT EXISTS idx_passengers_booking ON passengers(booking_id);

-- 11. PNR RECORDS TABLE
CREATE TABLE IF NOT EXISTS pnr_records (
    id SERIAL PRIMARY KEY,
    pnr VARCHAR(10) NOT NULL UNIQUE,
    booking_id INT NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    chart_status VARCHAR(50) DEFAULT 'Chart Not Prepared',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. SEAT LOCKS TABLE
CREATE TABLE IF NOT EXISTS seat_locks (
    id SERIAL PRIMARY KEY,
    seat_id INT NOT NULL REFERENCES seats(id) ON DELETE CASCADE,
    journey_date VARCHAR(20) NOT NULL,
    user_id INT,
    session_id VARCHAR(100) NOT NULL,
    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_locks_session ON seat_locks(session_id);

-- 13. TRAIN TRACKING TABLE
CREATE TABLE IF NOT EXISTS train_tracking (
    id SERIAL PRIMARY KEY,
    train_id INT NOT NULL UNIQUE REFERENCES trains(id) ON DELETE CASCADE,
    current_latitude DOUBLE PRECISION NOT NULL,
    current_longitude DOUBLE PRECISION NOT NULL,
    current_speed DOUBLE PRECISION NOT NULL,
    delay_minutes INT DEFAULT 0,
    next_station VARCHAR(100) NOT NULL,
    eta VARCHAR(20) NOT NULL,
    distance_travelled_km DOUBLE PRECISION NOT NULL,
    route_coordinates_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 14. EMERGENCY LOGS TABLE
CREATE TABLE IF NOT EXISTS emergency_logs (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) NOT NULL UNIQUE,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    user_name VARCHAR(100) NOT NULL,
    user_phone VARCHAR(20) NOT NULL,
    emergency_type VARCHAR(100) NOT NULL,
    train_number VARCHAR(20) NOT NULL,
    coach VARCHAR(20) NOT NULL,
    seat VARCHAR(20) NOT NULL,
    description TEXT,
    status VARCHAR(30) DEFAULT 'RECEIVED',
    response_note TEXT DEFAULT 'Alert logged. RPF Control Room notified.',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. CLEANING REQUESTS TABLE
CREATE TABLE IF NOT EXISTS cleaning_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(50) NOT NULL UNIQUE,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    passenger_name VARCHAR(255) NOT NULL,
    contact_mobile VARCHAR(50) NOT NULL,
    train_number VARCHAR(50) NOT NULL,
    coach_number VARCHAR(50) NOT NULL,
    seat_number VARCHAR(50),
    issue_type VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 16. TTE ASSISTANCE REQUESTS TABLE
CREATE TABLE IF NOT EXISTS tte_assistance_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(50) NOT NULL UNIQUE,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    train_number VARCHAR(50) NOT NULL,
    train_name VARCHAR(255),
    journey_date VARCHAR(50) NOT NULL,
    coach VARCHAR(50),
    berth VARCHAR(50),
    pnr VARCHAR(50),
    assistance_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 17. LEFT LUGGAGE REQUESTS TABLE
CREATE TABLE IF NOT EXISTS left_luggage_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(50) NOT NULL UNIQUE,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    passenger_name VARCHAR(255) NOT NULL,
    contact_mobile VARCHAR(50) NOT NULL,
    train_number VARCHAR(50) NOT NULL,
    pnr VARCHAR(50),
    station_name VARCHAR(255),
    coach VARCHAR(50),
    seat VARCHAR(50),
    item_category VARCHAR(100),
    item_description TEXT,
    status VARCHAR(50) DEFAULT 'REPORTED',
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 18. FOOD PARTNERS TABLE
CREATE TABLE IF NOT EXISTS food_partners (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    tagline VARCHAR(255),
    description TEXT,
    logo_icon VARCHAR(100),
    website_url VARCHAR(500) NOT NULL,
    cuisines VARCHAR(255),
    is_featured INT DEFAULT 0,
    is_official INT DEFAULT 1,
    active INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 19. FOOD RESTAURANTS TABLE
CREATE TABLE IF NOT EXISTS food_restaurants (
    id SERIAL PRIMARY KEY,
    station_id INT NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    cuisine VARCHAR(255),
    rating NUMERIC(3,1) DEFAULT 4.2,
    image_url VARCHAR(500),
    prep_time VARCHAR(50) DEFAULT '20-25 min',
    min_order NUMERIC(10,2) DEFAULT 100.0,
    is_veg_only INT DEFAULT 0,
    active INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 20. FOOD MENU ITEMS TABLE
CREATE TABLE IF NOT EXISTS food_menu_items (
    id SERIAL PRIMARY KEY,
    restaurant_id INT NOT NULL REFERENCES food_restaurants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    is_veg INT DEFAULT 1,
    image_url VARCHAR(500),
    rating NUMERIC(3,1) DEFAULT 4.5,
    available INT DEFAULT 1,
    active INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 21. FOOD ORDERS TABLE
CREATE TABLE IF NOT EXISTS food_orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    passenger_name VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50) NOT NULL,
    pnr VARCHAR(50),
    train_id INT REFERENCES trains(id) ON DELETE SET NULL,
    train_number VARCHAR(50) NOT NULL,
    delivery_station_id INT NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    delivery_station_name VARCHAR(255) NOT NULL,
    coach VARCHAR(50) NOT NULL,
    seat VARCHAR(50) NOT NULL,
    delivery_eta VARCHAR(50),
    subtotal NUMERIC(10,2) NOT NULL,
    delivery_fee NUMERIC(10,2) DEFAULT 20.0,
    total_amount NUMERIC(10,2) NOT NULL,
    payment_method VARCHAR(50) DEFAULT 'UPI',
    payment_status VARCHAR(50) DEFAULT 'PAID',
    order_status VARCHAR(50) DEFAULT 'Placed',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 22. FOOD ORDER ITEMS TABLE
CREATE TABLE IF NOT EXISTS food_order_items (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES food_orders(id) ON DELETE CASCADE,
    menu_item_id INT REFERENCES food_menu_items(id) ON DELETE SET NULL,
    item_name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    total_price NUMERIC(10,2) NOT NULL
);

-- 23. FOOD ORDER STATUS HISTORY TABLE
CREATE TABLE IF NOT EXISTS food_order_status_history (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES food_orders(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note TEXT
);
