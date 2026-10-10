/**
 * SMART RAILWAY - PNR STATUS, E-TICKET PDF & CANCELLATION CONTROLLER
 * Compliant with Indian Railways / IRCTC rules (IRCTC-REFUND-RULES-2026.1)
 */

let currentBooking = null;

document.addEventListener('DOMContentLoaded', () => {
  const pnrParam = getQueryParam('pnr');
  if (pnrParam) {
    const input = document.getElementById('input-pnr-search');
    if (input) input.value = pnrParam;
    fetchPnrStatus(pnrParam);
  }

  setupEventListeners();
});

function setupEventListeners() {
  const form = document.getElementById('pnr-search-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const pnrVal = document.getElementById('input-pnr-search')?.value.trim();
      if (pnrVal) {
        fetchPnrStatus(pnrVal);
      }
    });
  }

  const confirmCancelBtn = document.getElementById('btn-confirm-cancellation');
  if (confirmCancelBtn) {
    confirmCancelBtn.addEventListener('click', executeTicketCancellation);
  }
}

async function fetchPnrStatus(pnr) {
  const container = document.getElementById('pnr-result-card');
  if (container) {
    container.innerHTML = `
      <div class="state-box">
        <div class="spinner"></div>
        <h3>Fetching PNR Status from Railway Database...</h3>
        <p>Checking chart allocation, coach composition, and reservation status.</p>
      </div>
    `;
    container.style.display = 'block';
  }

  const res = await fetchApi(`/pnr/${pnr}`);

  if (!res.success) {
    if (container) {
      container.innerHTML = `
        <div class="state-box">
          <i class="fa-solid fa-file-circle-xmark" style="color: var(--accent-red);"></i>
          <h3>PNR Not Found</h3>
          <p>${res.message}</p>
          <p style="font-size: 0.85rem; color: var(--text-muted);">Demo Tip: Try sample PNRs: <strong>2846190532</strong>, <strong>4198273641</strong>, or <strong>6720491823</strong></p>
        </div>
      `;
    }
    return;
  }

  currentBooking = res.data;
  renderBoardingPass(currentBooking);
}

function renderBoardingPass(booking) {
  const container = document.getElementById('pnr-result-card');
  if (!container) return;

  const isCancelled = booking.status === 'CANCELLED';
  const isPartialCancelled = booking.status === 'PARTIALLY_CANCELLED';
  const isConfirmed = booking.status === 'CONFIRMED';
  const isWL = booking.status === 'WAITLIST' || (booking.pnr_status && booking.pnr_status.includes('WL'));

  let statusBadge = '';
  if (isCancelled) {
    statusBadge = '<span class="badge badge-cancelled" style="font-size: 0.95rem; padding: 0.45rem 0.9rem;"><i class="fa-solid fa-ban"></i> CANCELLED</span>';
  } else if (isPartialCancelled) {
    statusBadge = '<span class="badge" style="background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; font-size: 0.95rem; padding: 0.45rem 0.9rem; font-weight: 700;"><i class="fa-solid fa-user-xmark"></i> PARTIALLY CANCELLED</span>';
  } else if (isConfirmed) {
    statusBadge = '<span class="badge badge-confirmed" style="font-size: 0.95rem; padding: 0.45rem 0.9rem;"><i class="fa-solid fa-check"></i> CONFIRMED</span>';
  } else {
    statusBadge = '<span class="badge badge-wl" style="font-size: 0.95rem; padding: 0.45rem 0.9rem;"><i class="fa-solid fa-clock"></i> ' + (booking.pnr_status || booking.status) + '</span>';
  }

  // Generate QR Code SVG with authentic verification payload
  let qrCodeSvg = '';
  let barcodeSvg = '';
  if (window.SmartRailQR) {
    const qrPayload = `SMARTRAIL|PNR:${booking.pnr}|TRAIN:${booking.train_number}|DATE:${booking.journey_date}|CLASS:${booking.coach_class}|STATUS:${booking.status}`;
    qrCodeSvg = window.SmartRailQR.createQRCodeSVG(qrPayload, 88);
    barcodeSvg = window.SmartRailQR.createBarcodeSVG('PNR-' + booking.pnr, 200, 36);
  }

  // Passenger Rows
  const passengerRows = (booking.passengers || []).map((p, idx) => {
    const pIsCancelled = p.status === 'CANCELLED';
    const pBadgeClass = pIsCancelled ? 'badge-cancelled' : (p.status === 'CONFIRMED' ? 'badge-confirmed' : 'badge-wl');
    const pStatusIcon = pIsCancelled ? 'fa-ban' : (p.status === 'CONFIRMED' ? 'fa-check' : 'fa-clock');
    return `
      <tr style="${pIsCancelled ? 'background: #fffbfb; color: #64748b;' : ''}">
        <td style="text-align: center;"><strong>${idx + 1}</strong></td>
        <td>
          <strong style="${pIsCancelled ? 'text-decoration: line-through; color: #94a3b8;' : 'color: #0f172a;'}">${p.name}</strong>
          <span style="font-size: 0.8rem; color: #64748b; margin-left: 4px;">(${p.age} yrs, ${p.gender})</span>
        </td>
        <td>${p.id_type || 'Aadhaar'}: ${p.id_number || 'Verified'}</td>
        <td style="font-weight: 700;">${pIsCancelled ? '<span style="color: #ef4444;">Cancelled</span>' : (p.seat_number_assigned || 'WL')}</td>
        <td>${pIsCancelled ? '-' : (p.berth_type || 'N/A')}</td>
        <td>
          <span class="badge ${pBadgeClass}">
            <i class="fa-solid ${pStatusIcon}"></i> ${p.status}
          </span>
        </td>
      </tr>
    `;
  }).join('');

  // Fare calculations
  const totalFare = parseFloat(booking.total_fare || 0);
  const convFee = parseFloat(booking.convenience_fee || 17.70);
  const baseFare = parseFloat(booking.base_fare || (totalFare - convFee));
  const taxAmount = parseFloat(booking.tax_amount || 0);

  // Cancellation Audit History Card (if ticket was cancelled or partially cancelled)
  let cancellationReceiptHtml = '';
  const latestCancellation = (booking.cancellations && booking.cancellations.length > 0) ? booking.cancellations[0] : null;

  if (latestCancellation || isCancelled || isPartialCancelled) {
    const canRef = latestCancellation?.cancellation_reference || `CAN-2026-${booking.id || '98101'}`;
    const canCharge = latestCancellation?.cancellation_charge ?? (120 * (booking.passengers || []).length);
    const refundAmt = latestCancellation?.refund_amount ?? Math.max(0, totalFare - canCharge);
    const refundStatus = latestCancellation?.refund_status || 'Refund Processed';
    const canTime = latestCancellation?.created_at || 'Recent';

    cancellationReceiptHtml = `
      <div class="ticket-cancellation-receipt">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #fca5a5; padding-bottom: 0.5rem; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem;">
          <h4 style="margin: 0; font-size: 1.05rem;">
            <i class="fa-solid fa-receipt"></i> Cancellation &amp; Refund Receipt
          </h4>
          <span class="badge" style="background: #fee2e2; color: #991b1b; font-weight: 700; font-size: 0.8rem;">
            Ref: ${canRef}
          </span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; font-size: 0.85rem;">
          <div>
            <span style="color: #64748b; display: block; font-size: 0.75rem;">Cancellation Type</span>
            <strong>${isPartialCancelled ? 'Partial Passenger Cancellation' : 'Full Ticket Cancellation'}</strong>
          </div>
          <div>
            <span style="color: #64748b; display: block; font-size: 0.75rem;">IRCTC Cancellation Charges</span>
            <strong style="color: #dc2626;">- ${formatINR(canCharge)}</strong>
          </div>
          <div>
            <span style="color: #64748b; display: block; font-size: 0.75rem;">Refund Credited / Initiated</span>
            <strong style="color: #15803d; font-size: 1.05rem;">${formatINR(refundAmt)}</strong>
          </div>
          <div>
            <span style="color: #64748b; display: block; font-size: 0.75rem;">Refund Status</span>
            <span class="badge" style="background: #ecfdf5; color: #047857; font-weight: 700;">${refundStatus}</span>
          </div>
        </div>
        <div style="margin-top: 0.65rem; font-size: 0.75rem; color: #64748b; font-style: italic;">
          Processed on: ${canTime} &bull; Refund will be credited to source payment method within 3–5 business days.
        </div>
      </div>
    `;
  }

  // AI Prediction Card (WL / RAC only - screen view only)
  let aiPredictionHtml = '';
  if (booking.ai_prediction && !isCancelled) {
    const pred = booking.ai_prediction;
    const catClass = pred.category === 'High' ? 'text-success' : (pred.category === 'Moderate' ? 'text-warning' : 'text-danger');
    const gaugeColor = pred.category === 'High' ? '#2a9d8f' : (pred.category === 'Moderate' ? '#f77f00' : '#e63946');

    aiPredictionHtml = `
      <div class="card ai-prediction-card no-print" style="margin-top: 1.5rem; background: linear-gradient(135deg, rgba(121, 40, 202, 0.04) 0%, rgba(255, 0, 128, 0.04) 100%); border: 1.5px solid rgba(121, 40, 202, 0.25);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <div style="width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, #7928ca, #ff0080); color: white; display: flex; align-items: center; justify-content: center;">
              <i class="fa-solid fa-wand-magic-sparkles"></i>
            </div>
            <div>
              <h4 style="font-size: 1.05rem; color: var(--primary-navy); margin: 0;">AI Confirmation Probability Predictor</h4>
              <span style="font-size: 0.75rem; color: var(--text-muted);">Machine Learning analysis based on historical train booking trends</span>
            </div>
          </div>
          <span class="badge badge-ai">SCIKIT-LEARN ML</span>
        </div>

        <div style="display: grid; grid-template-columns: 140px 1fr; gap: 1.5rem; align-items: center;">
          <div style="text-align: center; padding: 1rem; background: white; border-radius: var(--radius-md); border: 2px solid ${gaugeColor};">
            <div style="font-size: 2.2rem; font-weight: 800; color: ${gaugeColor};">${pred.probability}%</div>
            <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase;" class="${catClass}">${pred.category} Chance</div>
          </div>
          <div>
            <p style="font-size: 0.95rem; color: var(--text-primary); margin-bottom: 0.5rem; line-height: 1.5;">${pred.explanation}</p>
            <span style="font-size: 0.75rem; color: var(--text-muted); font-style: italic;">⚠️ ${pred.disclaimer}</span>
          </div>
        </div>
      </div>
    `;
  }

  // Count active passengers to control cancel button
  const activePassengers = (booking.passengers || []).filter(p => p.status !== 'CANCELLED');
  const canCancel = activePassengers.length > 0 && !isCancelled;

  container.innerHTML = `
    <div class="card boarding-pass-card printable-ticket" style="box-shadow: var(--shadow-lg); border-top: 5px solid var(--primary-navy); padding: 2rem;">
      
      <!-- Official E-Ticket Header Strip -->
      <div class="ticket-header-strip">
        <div class="ticket-branding-area">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <div style="width: 44px; height: 44px; border-radius: 8px; background: var(--primary-navy); color: white; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">
              <i class="fa-solid fa-train-subway"></i>
            </div>
            <div>
              <div style="font-size: 1.4rem; font-weight: 800; color: var(--primary-navy); line-height: 1.1;">
                Smart<span style="color: var(--accent-saffron);">Rail</span>
              </div>
              <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; letter-spacing: 0.5px; text-transform: uppercase;">
                Indian Railway Electronic Reservation Slip (ERS)
              </div>
            </div>
          </div>
        </div>

        <div class="ticket-pnr-status-area">
          <div style="text-align: right;">
            <span style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; display: block;">Passenger Name Record (PNR)</span>
            <div style="font-size: 1.85rem; font-weight: 800; color: var(--primary-navy); letter-spacing: 1.5px; line-height: 1.1;">
              ${booking.pnr}
            </div>
            <div style="margin-top: 4px;">${statusBadge}</div>
          </div>
          <div style="border-left: 1px solid #e2e8f0; padding-left: 1rem; display: flex; flex-direction: column; align-items: center;">
            <div style="background: white; padding: 2px; border: 1px solid #cbd5e1; border-radius: 4px;">
              ${qrCodeSvg}
            </div>
            <span style="font-size: 0.65rem; color: #64748b; margin-top: 2px;">Scan to Verify</span>
          </div>
        </div>
      </div>

      <!-- Ticket Journey Metadata Grid -->
      <div class="ticket-meta-grid">
        <div class="meta-col">
          <span class="meta-label">Train No. &amp; Name</span>
          <span class="meta-val">${booking.train_number} - ${booking.train_name}</span>
        </div>
        <div class="meta-col">
          <span class="meta-label">Booking Reference / Txn ID</span>
          <span class="meta-val">${booking.booking_reference}</span>
        </div>
        <div class="meta-col">
          <span class="meta-label">Journey Date</span>
          <span class="meta-val">${booking.journey_date}</span>
        </div>
        <div class="meta-col">
          <span class="meta-label">Class &amp; Quota</span>
          <span class="meta-val">${booking.coach_class} (Coach ${booking.coach_number}) &bull; Quota: ${booking.quota_code}</span>
        </div>
        <div class="meta-col">
          <span class="meta-label">From Station (Boarding)</span>
          <span class="meta-val">${booking.source_name} (${booking.source_code}) &bull; ${booking.departure_time}</span>
        </div>
        <div class="meta-col">
          <span class="meta-label">To Station (Destination)</span>
          <span class="meta-val">${booking.dest_name} (${booking.dest_code}) &bull; ${booking.arrival_time}</span>
        </div>
        <div class="meta-col">
          <span class="meta-label">Duration &amp; Distance</span>
          <span class="meta-val">${booking.duration}</span>
        </div>
        <div class="meta-col">
          <span class="meta-label">Charting Status</span>
          <span class="meta-val">${booking.chart_status}</span>
        </div>
      </div>

      <!-- Passenger Details Table -->
      <div class="ticket-section-title">
        <i class="fa-solid fa-users"></i> Passenger Details &amp; Berth Allocation
      </div>
      <div class="data-table-wrapper" style="margin-bottom: 1rem;">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 40px; text-align: center;">#</th>
              <th>Passenger Name</th>
              <th>Govt ID Proof</th>
              <th>Allocated Coach / Berth</th>
              <th>Berth Type</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${passengerRows}
          </tbody>
        </table>
      </div>

      <!-- Fare Breakdown & Payment Summary -->
      <div class="ticket-section-title" style="margin-top: 1rem;">
        <i class="fa-solid fa-file-invoice-dollar"></i> Fare Breakdown &amp; Payment Details
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: var(--radius-md); padding: 0.85rem 1.15rem; margin-bottom: 1rem; font-size: 0.88rem;">
        <div>
          <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; display: block;">Ticket Base Fare:</span>
          <strong>${formatINR(baseFare)}</strong>
        </div>
        <div>
          <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; display: block;">Convenience Fee (IRCTC):</span>
          <strong>${formatINR(convFee)}</strong>
        </div>
        <div>
          <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; display: block;">Taxes / GST:</span>
          <strong>${formatINR(taxAmount)}</strong>
        </div>
        <div>
          <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; display: block;">Total Fare Paid:</span>
          <strong style="font-size: 1.15rem; color: var(--primary-navy);">${formatINR(totalFare)}</strong>
        </div>
      </div>

      ${cancellationReceiptHtml}

      <!-- Important Boarding & Travel Instructions -->
      <div class="ticket-instructions-box">
        <strong style="color: #0f172a; display: block; margin-bottom: 4px;">
          <i class="fa-solid fa-circle-info" style="color: var(--primary-navy); margin-right: 4px;"></i> Important Passenger Instructions:
        </strong>
        <ol>
          <li>At least one passenger must carry a valid original Government Photo Identity Card (Aadhaar, Passport, PAN Card, Voter ID, Driving License) during the journey.</li>
          <li>E-ticket holders with fully confirmed or RAC status are authorized to board. Passengers with fully waitlisted e-tickets are not permitted to travel.</li>
          <li>Check scheduled departure time and coach position at the station before boarding.</li>
          <li>In case of train cancellation due to operational reasons, a full refund of fare is credited automatically.</li>
        </ol>
      </div>

      <!-- Official Cancellation & Refund Policy Notice -->
      <div class="ticket-instructions-box" style="margin-top: 0.5rem; background: #fafafa;">
        <strong style="color: #0f172a; display: block; margin-bottom: 4px;">
          <i class="fa-solid fa-scale-balanced" style="color: var(--accent-orange); margin-right: 4px;"></i> Cancellation &amp; Refund Rules (IRCTC-REFUND-RULES-2026.1):
        </strong>
        <div style="font-size: 0.78rem; color: #475569; line-height: 1.4;">
          &bull; <strong>> 48 hrs:</strong> Flat clerkage (1A/EC ₹240, 2A ₹200, 3A/CC ₹180, SL ₹120, 2S ₹60) &bull; <strong>48h–12h:</strong> 25% min clerkage &bull; <strong>12h–4h:</strong> 50% min clerkage &bull; <strong>&lt; 4 hrs:</strong> No refund &bull; <strong>RAC/WL:</strong> Cancelled &ge; 30 mins before departure: ₹60 clerkage &bull; <strong>Tatkal (Confirmed):</strong> No refund &bull; IRCTC Convenience fee is non-refundable.
        </div>
      </div>

      <!-- Barcode Strip -->
      <div style="display: flex; justify-content: center; margin-top: 0.85rem; margin-bottom: 0.5rem;">
        ${barcodeSvg}
      </div>

      <!-- Platform Disclaimer -->
      <div class="ticket-disclaimer-note">
        <strong>Disclaimer:</strong> SmartRail is an intelligent railway passenger services simulation and testing platform. This Electronic Reservation Slip is generated for demonstrated railway bookings and does not represent an official Indian Railways / IRCTC ticket unless booked via authorized CRIS / IRCTC integration.
      </div>

      ${aiPredictionHtml}

      <!-- Screen-Only Bottom Actions -->
      <div class="ticket-screen-actions no-print" style="display: flex; align-items: center; justify-content: space-between; margin-top: 1.75rem; border-top: 1px solid var(--border-light); padding-top: 1.5rem; flex-wrap: wrap; gap: 1rem;">
        <div>
          <span style="font-size: 0.85rem; color: var(--text-muted); display: block;">Total Fare Paid</span>
          <strong style="font-size: 1.6rem; color: var(--primary-navy);">${formatINR(booking.total_fare)}</strong>
        </div>

        <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
          <a href="live-tracking.html?train_id=${booking.train_id}" class="btn btn-outline">
            <i class="fa-solid fa-satellite-dish" style="color: var(--accent-orange);"></i> Live Train Tracking
          </a>
          <button onclick="printTicket()" class="btn btn-primary">
            <i class="fa-solid fa-print"></i> Print Ticket (PDF)
          </button>
          ${canCancel ? `
            <button onclick="openCancelModal()" class="btn btn-danger">
              <i class="fa-solid fa-ban"></i> Cancel Ticket
            </button>
          ` : `
            <span class="badge badge-cancelled" style="font-size: 0.9rem; padding: 0.5rem 0.9rem;">
              <i class="fa-solid fa-ban"></i> ${isCancelled ? 'Ticket Cancelled' : 'No Active Berths'}
            </span>
          `}
        </div>
      </div>
    </div>
  `;
}

/**
 * Clean Print Action: Sets clean A4 title and invokes browser print dialog
 */
function printTicket() {
  if (!currentBooking) return;
  const originalTitle = document.title;
  document.title = `SmartRail_Ticket_${currentBooking.pnr}_${currentBooking.train_number}`;
  window.print();
  setTimeout(() => {
    document.title = originalTitle;
  }, 1200);
}

/**
 * Interactive Cancellation Modal Controller
 */
function openCancelModal() {
  if (!currentBooking) return;
  const modal = document.getElementById('cancel-modal');
  if (!modal) return;

  document.getElementById('cancel-pnr-display').textContent = currentBooking.pnr;
  document.getElementById('cancel-train-display').textContent = `${currentBooking.train_number} - ${currentBooking.train_name}`;

  // Populate Passenger Checklists
  const listContainer = document.getElementById('cancel-passenger-list');
  const passengers = currentBooking.passengers || [];

  let html = '';
  passengers.forEach(p => {
    const isAlreadyCancelled = p.status === 'CANCELLED';
    html += `
      <div class="cancel-passenger-item ${isAlreadyCancelled ? 'disabled' : ''}">
        <label style="display: flex; align-items: center; gap: 0.6rem; cursor: ${isAlreadyCancelled ? 'not-allowed' : 'pointer'}; margin: 0; font-size: 0.9rem;">
          <input type="checkbox" class="passenger-cancel-chk" value="${p.id}" ${isAlreadyCancelled ? 'disabled' : 'checked'} onchange="updateRefundEstimate()">
          <div>
            <strong>${p.name}</strong> <span style="font-size: 0.8rem; color: #64748b;">(${p.age}, ${p.gender})</span>
            <div style="font-size: 0.75rem; color: #64748b;">Allocated: ${p.seat_number_assigned || 'WL'} &bull; ${p.berth_type || 'N/A'}</div>
          </div>
        </label>
        <div>
          ${isAlreadyCancelled 
            ? '<span class="badge badge-cancelled" style="font-size: 0.7rem;">Already Cancelled</span>' 
            : `<span class="badge ${p.status === 'CONFIRMED' ? 'badge-confirmed' : 'badge-wl'}" style="font-size: 0.75rem;">${p.status}</span>`}
        </div>
      </div>
    `;
  });

  listContainer.innerHTML = html;

  // Initial calculation
  updateRefundEstimate();
  modal.classList.add('active');
}

function closeCancelModal() {
  const modal = document.getElementById('cancel-modal');
  if (modal) modal.classList.remove('active');
}

function toggleSelectAllPassengers(isChecked) {
  const checkboxes = document.querySelectorAll('.passenger-cancel-chk:not(:disabled)');
  checkboxes.forEach(cb => { cb.checked = isChecked; });
  updateRefundEstimate();
}

/**
 * Queries real-time refund estimation from backend API
 */
async function updateRefundEstimate() {
  if (!currentBooking) return;
  const selectedCheckboxes = document.querySelectorAll('.passenger-cancel-chk:checked:not(:disabled)');
  const selectedIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));

  const confirmBtn = document.getElementById('btn-confirm-cancellation');
  const ruleText = document.getElementById('cancel-rule-text');

  if (selectedIds.length === 0) {
    document.getElementById('cancel-selected-fare').textContent = '₹0.00';
    document.getElementById('cancel-charge').textContent = '- ₹0.00';
    document.getElementById('cancel-refund-est').textContent = '₹0.00';
    ruleText.textContent = 'Please select at least one active passenger to cancel.';
    if (confirmBtn) confirmBtn.disabled = true;
    return;
  }

  if (confirmBtn) confirmBtn.disabled = false;

  ruleText.textContent = 'Calculating verified IRCTC refund rules...';

  const res = await fetchApi(`/bookings/${currentBooking.id}/refund-quote`, {
    method: 'POST',
    body: JSON.stringify({ passenger_ids: selectedIds })
  });

  if (!res.success) {
    // Fallback to client-side rule estimation if offline
    estimateRefundClientSide(selectedIds.length);
    return;
  }

  const quote = res.data;
  document.getElementById('cancel-selected-fare').textContent = formatINR(quote.selected_fare);
  document.getElementById('cancel-charge').textContent = '- ' + formatINR(quote.cancellation_charge);
  document.getElementById('cancel-conv-fee').textContent = '- ' + formatINR(quote.convenience_fee);
  document.getElementById('cancel-refund-est').textContent = formatINR(quote.estimated_refund);

  const primaryRule = quote.passengers_to_cancel[0]?.rule_description || quote.time_window_label;
  ruleText.innerHTML = `<strong>${quote.time_window_label}:</strong> ${primaryRule}`;
}

function estimateRefundClientSide(selectedCount) {
  const totalFare = parseFloat(currentBooking.total_fare || 0);
  const convFee = 17.70;
  const eligible = Math.max(0, totalFare - convFee);
  const totalCount = (currentBooking.passengers || []).length || 1;
  const selectedFare = (eligible / totalCount) * selectedCount;
  const charge = 180 * selectedCount;
  const refund = Math.max(0, selectedFare - charge);

  document.getElementById('cancel-selected-fare').textContent = formatINR(selectedFare);
  document.getElementById('cancel-charge').textContent = '- ' + formatINR(charge);
  document.getElementById('cancel-conv-fee').textContent = '- ' + formatINR(convFee);
  document.getElementById('cancel-refund-est').textContent = formatINR(refund);
  document.getElementById('cancel-rule-text').textContent = `Standard IRCTC cancellation rules applied for ${selectedCount} passenger(s).`;
}

/**
 * Executes cancellation transaction atomically on backend
 */
async function executeTicketCancellation() {
  if (!currentBooking) return;
  const selectedCheckboxes = document.querySelectorAll('.passenger-cancel-chk:checked:not(:disabled)');
  const selectedIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));

  if (selectedIds.length === 0) {
    showToast('Please select at least one passenger to cancel.', 'warning', 'No Passengers Selected');
    return;
  }

  const btn = document.getElementById('btn-confirm-cancellation');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing Cancellation...`;
  }

  const res = await fetchApi(`/bookings/${currentBooking.id}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ passenger_ids: selectedIds })
  });

  closeCancelModal();

  if (btn) {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-ban"></i> Confirm Cancellation`;
  }

  if (!res.success) {
    showToast(res.message, 'error', 'Cancellation Failed');
    return;
  }

  const cData = res.data;
  showToast(
    `Cancellation successful! Reference: ${cData.cancellation_reference}. Refund of ${formatINR(cData.refund_amount)} initiated.`,
    'success',
    'Ticket Cancelled'
  );

  // Refresh PNR status immediately to display updated ticket
  fetchPnrStatus(currentBooking.pnr);
}
