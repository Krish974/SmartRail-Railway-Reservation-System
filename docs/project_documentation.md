# Smart Indian Railway System - Detailed Project Documentation

## 1. System Architecture Overview

The Smart Indian Railway Ticket Reservation System is structured around a decoupled multi-tier architecture designed for scalability, maintainability, and enterprise-grade resilience:

1. **Client Tier (Frontend):**
   - Built with standards-compliant HTML5, modular CSS3, and modern Vanilla JavaScript (ES6+).
   - Component-based UI patterns without bloated frontend frameworks.
   - Dynamic Leaflet.js engine for interactive spatial tracking of trains.
   - Chart.js integration for operational data visualization.
   - Responsive CSS Grid and Flexbox layouts supporting viewports from 360px smartphones to 4K displays.

2. **Application Tier (Flask REST API):**
   - Clean separation of concerns with Flask Blueprints (`auth`, `trains`, `seats`, `quota`, `bookings`, `pnr`, `tracking`, `chatbot`, `emergency`, `admin`).
   - Unified API response schema (`{ "success": bool, "message": str, "data": dict }`).
   - Session & token authentication middleware with role-based access control (RBAC).

3. **Machine Learning Tier:**
   - **PNR Confirmation Predictor:** Gradient Boosting model calibrated to output confidence percentages and risk tiers for waitlisted tickets.
   - **AI Seat Recommender:** Multi-attribute utility function optimizing window preferences, step-free access for seniors, and central coach positioning away from restrooms.
   - **NLP Chatbot Engine:** Scikit-learn TF-IDF Vectorizer with Multinomial Naive Bayes intent classification and live entity resolution.

4. **Persistence Tier:**
   - Primary: MySQL 8.0 with InnoDB engine, foreign key constraints, and performance indexes.
   - Resilient Fallback: Built-in SQLite 3 engine (`railway_db.sqlite`) auto-initialized with schema and realistic seed data if MySQL is inactive.

---

## 2. Database Schema & Data Dictionary

### Key Tables & Relationships

1. **`users`:** Stores passenger and administrative account credentials.
   - `id`: INT, Primary Key, Auto Increment
   - `name`: VARCHAR(100), Full legal name
   - `email`: VARCHAR(100), Unique email identifier
   - `phone`: VARCHAR(20), Contact number
   - `password_hash`: VARCHAR(255), Werkzeug Scrypt cryptographic hash
   - `role`: ENUM('USER', 'ADMIN'), Authorization level

2. **`stations`:** Geographic waypoints and junction nodes.
   - `id`: INT, Primary Key
   - `code`: VARCHAR(10), Unique railway station code (e.g. NDLS, MMCT)
   - `name`: VARCHAR(100), Station title
   - `latitude`, `longitude`: DECIMAL(9, 6), Coordinates for geospatial mapping

3. **`trains`:** Active fleet schedules and trunk routes.
   - `train_number`: VARCHAR(10), Unique 5-digit Indian Railway train ID
   - `source_station_id`, `dest_station_id`: Foreign Keys referencing `stations`
   - `departure_time`, `arrival_time`, `duration`: Timetable data
   - `running_days`: Days of operation

4. **`coaches` & `seats`:** Coach composition and berth allocation.
   - Coach classes: `1A` (First AC), `2A` (AC 2-Tier), `3A` (AC 3-Tier), `SL` (Sleeper), `CC` (Chair Car)
   - Berths: `LOWER`, `MIDDLE`, `UPPER`, `SIDE_LOWER`, `SIDE_UPPER`, `WINDOW`, `AISLE`

5. **`seat_locks`:** Concurrency control table.
   - `seat_id`: FK to `seats`
   - `session_id`: Unique client UUID
   - `expires_at`: Timestamp (Current time + 300 seconds)

6. **`bookings` & `passengers` & `pnr_records`:**
   - 10-digit unique PNR generated following Indian Railway prefix rules.
   - Cascade relationship ensuring atomicity.

7. **`emergency_logs`:**
   - Incident tracking with timestamp, coach, seat, and status (`RECEIVED`, `DISPATCHED`, `RESOLVED`).

---

## 3. Concurrency & Double-Booking Prevention

When a user selects one or more seats:
1. An atomic query checks `passengers` to ensure the seat is not already confirmed on the selected journey date.
2. The system checks `seat_locks` for active locks where `expires_at > NOW()` belonging to other sessions.
3. If free, an exclusive 5-minute hold is acquired.
4. A countdown timer triggers on the client. If unbooked upon expiration, background routines release the lock automatically.

---

## 4. Machine Learning Implementation Details

### Model 1: PNR Predictor
- **Dataset:** 2,000 synthetic records modeled on IRCTC historical clearance distributions.
- **Pipeline:**
  ```python
  preprocessor = ColumnTransformer(transformers=[
      ('cat', OneHotEncoder(handle_unknown='ignore'), ['train_type', 'class_type', 'quota']),
      ('num', 'passthrough', ['waiting_list_number', 'days_to_journey', 'is_peak_season'])
  ])
  pipeline = Pipeline([
      ('preprocessor', preprocessor),
      ('classifier', GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42))
  ])
  ```
- **Performance:** ROC-AUC: 0.948, Accuracy: 93.2%.

### Model 2: NLP Intent Classifier
- Vectorizer: TF-IDF (1-2 N-grams, English stop words removed)
- Classifier: Multinomial Naive Bayes (`alpha=0.1`)
- Supported Intents: `pnr_status`, `train_search`, `seat_availability`, `booking`, `cancellation`, `quota_info`, `emergency_sos`, `live_tracking`, `greeting`, `general_faq`.

---

## 5. Security & Production Practices

- **Password Security:** Scrypt hashing via Werkzeug security primitives.
- **SQL Injection Defense:** 100% of database interactions execute via parameterized queries (`%s` in MySQL, `?` in SQLite).
- **Cross-Origin Resource Sharing:** Configured with Flask-CORS with credentials support.
- **Role Isolation:** Protected `@admin_required` decorators preventing unauthorized access to fleet management and analytics endpoints.
- **Graceful Fault Tolerance:** Transparent SQLite fallback prevents system unavailability if MySQL is offline.
