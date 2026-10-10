-- SMART INDIAN RAILWAY TICKET RESERVATION SYSTEM
-- Database Schema for MySQL 8.0+

CREATE DATABASE IF NOT EXISTS railway_db;
USE railway_db;

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('USER', 'ADMIN') DEFAULT 'USER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. STATIONS TABLE
CREATE TABLE IF NOT EXISTS stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    latitude DECIMAL(9, 6) NOT NULL,
    longitude DECIMAL(9, 6) NOT NULL,
    aliases TEXT NULL,
    INDEX idx_station_code (code),
    INDEX idx_station_city (city)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. TRAINS TABLE
CREATE TABLE IF NOT EXISTS trains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_number VARCHAR(10) NOT NULL UNIQUE,
    train_name VARCHAR(150) NOT NULL,
    source_station_id INT NOT NULL,
    dest_station_id INT NOT NULL,
    departure_time VARCHAR(10) NOT NULL,
    arrival_time VARCHAR(10) NOT NULL,
    duration VARCHAR(20) NOT NULL,
    running_days VARCHAR(50) NOT NULL,
    train_type VARCHAR(50) DEFAULT 'Superfast Express',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_station_id) REFERENCES stations(id) ON DELETE CASCADE,
    FOREIGN KEY (dest_station_id) REFERENCES stations(id) ON DELETE CASCADE,
    INDEX idx_train_number (train_number),
    INDEX idx_train_route (source_station_id, dest_station_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. TRAIN STOPS TABLE (Route Sequence & Halts)
CREATE TABLE IF NOT EXISTS train_stops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL,
    station_id INT NOT NULL,
    stop_sequence INT NOT NULL,
    arrival_time VARCHAR(10) NOT NULL,
    departure_time VARCHAR(10) NOT NULL,
    halt_minutes INT DEFAULT 2,
    distance_km DECIMAL(8, 2) DEFAULT 0.0,
    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
    FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE CASCADE,
    UNIQUE KEY uq_train_stop (train_id, stop_sequence),
    INDEX idx_stop_station (station_id),
    INDEX idx_stop_train (train_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. COACHES TABLE
CREATE TABLE IF NOT EXISTS coaches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL,
    coach_number VARCHAR(10) NOT NULL,
    coach_class VARCHAR(10) NOT NULL, -- 'SL', '3A', '2A', '1A', 'CC', 'EC'
    total_seats INT NOT NULL DEFAULT 72,
    base_fare DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
    INDEX idx_coach_train (train_id),
    INDEX idx_coach_class (coach_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. SEATS TABLE
CREATE TABLE IF NOT EXISTS seats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    coach_id INT NOT NULL,
    seat_number INT NOT NULL,
    seat_type VARCHAR(20) NOT NULL, -- 'LOWER', 'MIDDLE', 'UPPER', 'SIDE_LOWER', 'SIDE_UPPER', 'WINDOW', 'AISLE'
    is_window BOOLEAN DEFAULT FALSE,
    is_aisle BOOLEAN DEFAULT FALSE,
    deck_or_position VARCHAR(20) DEFAULT 'STANDARD',
    FOREIGN KEY (coach_id) REFERENCES coaches(id) ON DELETE CASCADE,
    UNIQUE KEY uq_coach_seat (coach_id, seat_number),
    INDEX idx_seat_type (seat_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. QUOTAS TABLE
CREATE TABLE IF NOT EXISTS quotas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL,
    discount_or_premium_pct DECIMAL(5, 2) DEFAULT 0.00,
    description VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. BOOKINGS TABLE
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_reference VARCHAR(50) NOT NULL UNIQUE,
    pnr VARCHAR(10) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    train_id INT NOT NULL,
    coach_id INT NOT NULL,
    journey_date DATE NOT NULL,
    quota_code VARCHAR(10) DEFAULT 'GN',
    base_fare DECIMAL(10, 2) NOT NULL,
    tax_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    convenience_fee DECIMAL(10, 2) NOT NULL DEFAULT 17.70,
    total_fare DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'CONFIRMED', -- 'CONFIRMED', 'RAC', 'WAITLIST', 'CANCELLED', 'COMPLETED'
    chart_prepared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
    FOREIGN KEY (coach_id) REFERENCES coaches(id) ON DELETE CASCADE,
    INDEX idx_booking_pnr (pnr),
    INDEX idx_booking_user (user_id),
    INDEX idx_booking_date (journey_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. PASSENGERS TABLE
CREATE TABLE IF NOT EXISTS passengers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    seat_id INT NULL,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(10) NOT NULL,
    id_type VARCHAR(30) NOT NULL,
    id_number VARCHAR(50) NOT NULL,
    seat_number_assigned VARCHAR(20),
    berth_type VARCHAR(20),
    status VARCHAR(20) DEFAULT 'CONFIRMED',
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    FOREIGN KEY (seat_id) REFERENCES seats(id) ON DELETE SET NULL,
    INDEX idx_passenger_booking (booking_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. PNR RECORDS TABLE
CREATE TABLE IF NOT EXISTS pnr_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pnr VARCHAR(10) NOT NULL UNIQUE,
    booking_id INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    chart_status VARCHAR(50) DEFAULT 'Chart Not Prepared',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    INDEX idx_pnr (pnr)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. SEAT LOCKS TABLE (For Concurrency & Temporary Hold)
CREATE TABLE IF NOT EXISTS seat_locks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    seat_id INT NOT NULL,
    journey_date DATE NOT NULL,
    user_id INT NULL,
    session_id VARCHAR(100) NOT NULL,
    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (seat_id) REFERENCES seats(id) ON DELETE CASCADE,
    INDEX idx_lock_expiry (expires_at),
    INDEX idx_lock_seat (seat_id, journey_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 12. TRAIN TRACKING TABLE (Live GPS / Simulated Telemetry)
CREATE TABLE IF NOT EXISTS train_tracking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL UNIQUE,
    current_latitude DECIMAL(9, 6) NOT NULL,
    current_longitude DECIMAL(9, 6) NOT NULL,
    current_speed DECIMAL(5, 2) NOT NULL,
    delay_minutes INT DEFAULT 0,
    next_station VARCHAR(100) NOT NULL,
    eta VARCHAR(20) NOT NULL,
    distance_travelled_km DECIMAL(8, 2) NOT NULL,
    route_coordinates_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 13. EMERGENCY LOGS TABLE (RPF / SOS Incidents)
CREATE TABLE IF NOT EXISTS emergency_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    incident_id VARCHAR(30) NOT NULL UNIQUE,
    user_id INT NULL,
    user_name VARCHAR(100) NOT NULL,
    user_phone VARCHAR(20) NOT NULL,
    emergency_type VARCHAR(50) NOT NULL,
    train_number VARCHAR(20) NOT NULL,
    coach VARCHAR(10) NOT NULL,
    seat VARCHAR(10) NOT NULL,
    description TEXT,
    status VARCHAR(30) DEFAULT 'RECEIVED', -- 'RECEIVED', 'DISPATCHED', 'RESOLVED'
    response_note VARCHAR(255) DEFAULT 'Alert logged. RPF Control Room notified.',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_incident_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 14. CLEANING REQUESTS TABLE (Coach Cleaning / Housekeeping Service)
CREATE TABLE IF NOT EXISTS cleaning_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL UNIQUE,
    user_id INT NULL,
    passenger_name VARCHAR(100) NOT NULL,
    contact_mobile VARCHAR(20) NOT NULL,
    train_number VARCHAR(20) NOT NULL,
    coach_number VARCHAR(10) NOT NULL,
    seat_number VARCHAR(10) NULL,
    issue_type VARCHAR(50) NOT NULL,
    description TEXT,
    status VARCHAR(30) DEFAULT 'PENDING', -- 'PENDING', 'ASSIGNED', 'CLEANING IN PROGRESS', 'RESOLVED', 'CANCELLED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_cleaning_train (train_number),
    INDEX idx_cleaning_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 15. TTE / TRAIN STAFF ASSISTANCE REQUESTS TABLE (On-Board Passenger & Ticket Assistance)
CREATE TABLE IF NOT EXISTS tte_assistance_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id VARCHAR(50) NOT NULL UNIQUE,
    user_id INT NULL,
    train_number VARCHAR(20) NOT NULL,
    train_name VARCHAR(150) NULL,
    journey_date VARCHAR(30) NOT NULL,
    coach VARCHAR(20) NULL,
    berth VARCHAR(20) NULL,
    pnr VARCHAR(20) NULL,
    assistance_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(30) DEFAULT 'Pending', -- 'Pending', 'Submitted', 'Resolved', 'Cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_tte_train (train_number),
    INDEX idx_tte_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 16. TRAIN ROUTE POINTS TABLE (Operational Passing Points / Waypoints Without Scheduled Halts)
CREATE TABLE IF NOT EXISTS train_route_points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_id INT NOT NULL,
    station_id INT NULL,
    point_name VARCHAR(100) NOT NULL,
    point_code VARCHAR(20) NULL,
    route_sequence INT NOT NULL,
    point_type VARCHAR(20) DEFAULT 'PASSING', -- 'PASSING'
    estimated_time VARCHAR(10) NULL,
    distance_km DECIMAL(8, 2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
    FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE SET NULL,
    INDEX idx_trp_train (train_id),
    INDEX idx_trp_seq (train_id, route_sequence)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


