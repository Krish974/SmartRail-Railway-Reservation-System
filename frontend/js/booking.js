/**
 * SMART RAILWAY - BOOKING & DEMO PAYMENT CONTROLLER
 */

let bookingData = null;
let currentPassengers = [];

document.addEventListener('DOMContentLoaded', () => {
  loadBookingIntent();
  setupEventListeners();
});

// Load booking payload from sessionStorage or provide realistic fallback
function loadBookingIntent() {
  const intentStr = sessionStorage.getItem('current_booking_intent');
  if (intentStr) {
    try {
      bookingData = JSON.parse(intentStr);
    } catch (e) {
      console.error(e);
    }
  }

  // Fallback defaults if accessed directly
  if (!bookingData) {
    bookingData = {
      train_id: 1,
      train_number: '12952',
      train_name: 'New Delhi - Mumbai Tejas Rajdhani',
      coach_id: 3,
      coach_number: 'B1',
      coach_class: '3A',
      base_fare: 2050.00,
      journey_date: new Date().toISOString().split('T')[0],
      quota_code: 'GN',
      selected_seats: [
        { seat_id: 1, seat_number: 1, seat_type: 'LOWER' },
        { seat_id: 4, seat_number: 4, seat_type: 'LOWER' }
      ]
    };
  }

  renderTrainSummary();
  renderPassengerForms();
  recalculateFare();
}

function renderTrainSummary() {
  const trainInfoEl = document.getElementById('summary-train-info');
  const dateEl = document.getElementById('summary-journey-date');
  const coachEl = document.getElementById('summary-coach-info');
  const quotaSelect = document.getElementById('select-booking-quota');

  if (trainInfoEl) trainInfoEl.textContent = `${bookingData.train_number} - ${bookingData.train_name}`;
  if (dateEl) dateEl.textContent = bookingData.journey_date;
  if (coachEl) coachEl.textContent = `${bookingData.coach_number} (${bookingData.coach_class})`;
  if (quotaSelect) quotaSelect.value = bookingData.quota_code || 'GN';
}

// Generate passenger input fields matching selected seats
function renderPassengerForms() {
  const container = document.getElementById('passengers-form-container');
  if (!container) return;

  const seats = bookingData.selected_seats || [];
  let html = '';

  seats.forEach((s, idx) => {
    html += `
      <div class="card passenger-card" style="margin-bottom: 1.25rem;" id="passenger-card-${idx}">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; border-bottom: 1px solid var(--border-light); padding-bottom: 0.5rem;">
          <h4 style="font-size: 1rem; color: var(--primary-navy);">
            <i class="fa-solid fa-user" style="color: var(--accent-saffron); margin-right: 6px;"></i> Passenger ${idx + 1}
          </h4>
          <span class="badge badge-available">Seat: ${bookingData.coach_number}-${s.seat_number} (${s.seat_type})</span>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr 1.2fr; gap: 1rem; margin-bottom: 1rem;">
          <div class="form-group">
            <label>Full Name *</label>
            <input type="text" class="form-control pass-name" required placeholder="e.g. Ramesh Kumar" data-idx="${idx}" value="${idx === 0 ? 'Rahul Sharma' : 'Sunita Sharma'}">
          </div>
          <div class="form-group">
            <label>Age *</label>
            <input type="number" class="form-control pass-age" min="1" max="110" required data-idx="${idx}" value="${idx === 0 ? '32' : '29'}">
          </div>
          <div class="form-group">
            <label>Gender *</label>
            <select class="form-control pass-gender" data-idx="${idx}">
              <option value="Male" ${idx === 0 ? 'selected' : ''}>Male</option>
              <option value="Female" ${idx === 1 ? 'selected' : ''}>Female</option>
              <option value="Transgender">Transgender</option>
            </select>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1.5fr; gap: 1rem;">
          <div class="form-group">
            <label>Govt ID Type *</label>
            <select class="form-control pass-id-type" data-idx="${idx}">
              <option value="Aadhaar Card">Aadhaar Card</option>
              <option value="PAN Card">PAN Card</option>
              <option value="Passport">Passport</option>
              <option value="Voter ID">Voter ID</option>
              <option value="UDID Disability Card">UDID Disability Card</option>
            </select>
          </div>
          <div class="form-group">
            <label>ID Number *</label>
            <input type="text" class="form-control pass-id-num" required placeholder="e.g. 1234-5678-9012" data-idx="${idx}" value="XXXX-XXXX-9821">
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;

  // Add listeners to input changes to recalculate and validate
  document.querySelectorAll('.pass-name, .pass-age, .pass-gender').forEach(el => {
    el.addEventListener('change', recalculateFare);
  });
}

function setupEventListeners() {
  const quotaSelect = document.getElementById('select-booking-quota');
  if (quotaSelect) {
    quotaSelect.addEventListener('change', async (e) => {
      bookingData.quota_code = e.target.value;
      await validateQuotaEligibility();
      recalculateFare();
    });
  }

  const payBtn = document.getElementById('btn-open-payment-modal');
  if (payBtn) {
    payBtn.addEventListener('click', openPaymentModal);
  }

  const confirmPayBtn = document.getElementById('btn-confirm-demo-payment');
  if (confirmPayBtn) {
    confirmPayBtn.addEventListener('click', executeBooking);
  }

  // Payment method tab switching inside demo payment modal
  document.querySelectorAll('.pay-method-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.pay-method-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.pay-method-pane').forEach(p => p.style.display = 'none');
      tab.classList.add('active');
      const targetPane = document.getElementById(tab.getAttribute('data-target'));
      if (targetPane) targetPane.style.display = 'block';
    });
  });
}

// Collect passenger form data
function collectPassengers() {
  const seats = bookingData.selected_seats || [];
  const passengers = [];

  seats.forEach((s, idx) => {
    const card = document.getElementById(`passenger-card-${idx}`);
    if (card) {
      const name = card.querySelector('.pass-name')?.value || `Passenger ${idx + 1}`;
      const age = parseInt(card.querySelector('.pass-age')?.value || '30', 10);
      const gender = card.querySelector('.pass-gender')?.value || 'Male';
      const idType = card.querySelector('.pass-id-type')?.value || 'Aadhaar Card';
      const idNumber = card.querySelector('.pass-id-num')?.value || 'NA';

      passengers.push({
        seat_id: s.seat_id,
        seat_number: s.seat_number,
        berth_preference: s.seat_type,
        name: name,
        age: age,
        gender: gender,
        id_type: idType,
        id_number: idNumber
      });
    }
  });

  return passengers;
}

// Dynamic Fare Recalculation
function recalculateFare() {
  const count = (bookingData.selected_seats || []).length;
  const baseFarePerTicket = bookingData.base_fare || 2000;
  const totalBase = baseFarePerTicket * count;

  const quota = bookingData.quota_code || 'GN';
  let quotaAdjustment = 0;

  if (quota === 'TQ') quotaAdjustment = totalBase * 0.30;
  else if (quota === 'PT') quotaAdjustment = totalBase * 0.50;
  else if (quota === 'SS') quotaAdjustment = -(totalBase * 0.30);
  else if (quota === 'HP') quotaAdjustment = -(totalBase * 0.50);

  const subtotal = totalBase + quotaAdjustment;
  const gst = Math.round(subtotal * 0.05 * 100) / 100;
  const convenienceFee = 17.70;
  const grandTotal = Math.round((subtotal + gst + convenienceFee) * 100) / 100;

  // Update UI Elements
  document.getElementById('fare-base-amount').textContent = formatINR(totalBase);
  document.getElementById('fare-quota-code').textContent = quota;
  document.getElementById('fare-quota-amount').textContent = (quotaAdjustment >= 0 ? '+' : '-') + formatINR(Math.abs(quotaAdjustment));
  document.getElementById('fare-gst-amount').textContent = formatINR(gst);
  document.getElementById('fare-convenience-amount').textContent = formatINR(convenienceFee);
  document.getElementById('fare-grand-total').textContent = formatINR(grandTotal);
  
  const modalTotal = document.getElementById('payment-modal-amount');
  if (modalTotal) modalTotal.textContent = formatINR(grandTotal);

  bookingData.calculated_total = grandTotal;
}

// Check Quota Validation with Backend API
async function validateQuotaEligibility() {
  const passengers = collectPassengers();
  const res = await fetchApi('/quota/validate', {
    method: 'POST',
    body: JSON.stringify({
      quota_code: bookingData.quota_code,
      passengers: passengers
    })
  });

  const feedbackEl = document.getElementById('quota-validation-msg');
  if (feedbackEl) {
    feedbackEl.textContent = res.message;
    feedbackEl.className = res.success ? 'quota-valid-msg' : 'quota-invalid-msg';
    feedbackEl.style.display = 'block';
  }

  if (!res.success) {
    showToast(res.message, 'warning', 'Quota Restriction');
  }
}

// Open Payment Gateway Modal
function openPaymentModal() {
  const passengers = collectPassengers();
  if (passengers.some(p => !p.name.trim())) {
    showToast('Please enter full names for all passengers.', 'warning');
    return;
  }

  const modal = document.getElementById('payment-modal');
  if (modal) modal.classList.add('active');
}

function closePaymentModal() {
  const modal = document.getElementById('payment-modal');
  if (modal) modal.classList.remove('active');
}

// Submit Booking Transaction to API
async function executeBooking() {
  const btn = document.getElementById('btn-confirm-demo-payment');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing Payment...`;
  }

  const passengers = collectPassengers();
  const user = getCurrentUser();

  const payload = {
    user_id: user ? user.id : 2,
    train_id: bookingData.train_id,
    coach_id: bookingData.coach_id,
    journey_date: bookingData.journey_date,
    quota_code: bookingData.quota_code,
    base_fare: bookingData.base_fare,
    from_station: bookingData.from_station,
    to_station: bookingData.to_station,
    passengers: passengers,
    session_id: getSessionId()
  };

  // Simulate 1.2 second processing latency
  await new Promise(r => setTimeout(r, 1200));

  const res = await fetchApi('/bookings', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  if (!res.success) {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-lock"></i> Pay Now (Demo)`;
    }
    showToast(res.message, 'error', 'Payment Failed');
    return;
  }

  showToast(`Booking Successful! PNR: ${res.data.pnr}`, 'success', 'Confirmed');
  sessionStorage.removeItem('current_booking_intent');

  setTimeout(() => {
    window.location.href = `pnr-status.html?pnr=${res.data.pnr}`;
  }, 1000);
}
