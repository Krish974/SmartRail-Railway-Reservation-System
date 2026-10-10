/**
 * SMART RAILWAY - EMERGENCY SOS & COACH CLEANING CONTROLLER
 */

let selectedEmergencyType = 'Medical Emergency';
let currentMode = 'emergency'; // 'emergency', 'cleaning', or 'tte'

document.addEventListener('DOMContentLoaded', () => {
  setupEmergencyTypeCards();
  setupEmergencyForm();
  prefillUserInfo();

  // Set default journey date for TTE form if present
  const tteDateInput = document.getElementById('input-tte-date');
  if (tteDateInput && !tteDateInput.value) {
    tteDateInput.value = new Date().toISOString().split('T')[0];
  }

  // Set default journey date for Left Luggage form if present
  const lugDateInput = document.getElementById('input-luggage-date');
  if (lugDateInput && !lugDateInput.value) {
    lugDateInput.value = new Date().toISOString().split('T')[0];
  }

  // Auto-activate service if requested via query param (e.g. ?service=tte or ?service=luggage)
  const urlParams = new URLSearchParams(window.location.search);
  const serviceParam = (urlParams.get('service') || urlParams.get('type') || '').toLowerCase();
  if (serviceParam === 'tte') {
    const tteCard = document.querySelector('.emergency-type-card[data-mode="tte"]');
    if (tteCard) tteCard.click();
  } else if (serviceParam === 'cleaning') {
    const clrCard = document.querySelector('.emergency-type-card[data-mode="cleaning"]');
    if (clrCard) clrCard.click();
  } else if (serviceParam === 'luggage' || serviceParam === 'left_luggage' || serviceParam === 'lost_luggage') {
    const lugCard = document.querySelector('.emergency-type-card[data-mode="luggage"]');
    if (lugCard) lugCard.click();
  }
});

function prefillUserInfo() {
  const user = typeof getCurrentUser === 'function' ? getCurrentUser() : null;
  if (user) {
    const nameInput = document.getElementById('input-sos-name');
    const phoneInput = document.getElementById('input-sos-phone');
    const lugMobileInput = document.getElementById('input-luggage-mobile');
    if (nameInput && user.name) nameInput.value = user.name;
    if (phoneInput && user.phone) phoneInput.value = user.phone;
    if (lugMobileInput && user.phone && !lugMobileInput.value) lugMobileInput.value = user.phone;
  }
}

function setupEmergencyTypeCards() {
  document.querySelectorAll('.emergency-type-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.emergency-type-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      
      const mode = card.getAttribute('data-mode') || 'emergency';
      selectedEmergencyType = card.getAttribute('data-type') || 'Emergency Assistance';
      currentMode = mode;

      applyFormMode(mode, selectedEmergencyType);
    });
  });
}

function applyFormMode(mode, typeName) {
  const displayType = document.getElementById('display-selected-type');
  const badge = document.getElementById('display-priority-badge');
  const emergencyFormContainer = document.getElementById('emergency-form-container');
  const tteFormContainer = document.getElementById('tte-form-container');
  const luggageFormContainer = document.getElementById('luggage-form-container');
  const cleaningGroup = document.getElementById('cleaning-issue-group');
  const seatLabel = document.getElementById('lbl-sos-seat');
  const descLabel = document.getElementById('lbl-sos-desc');
  const descInput = document.getElementById('input-sos-desc');
  const triggerBtn = document.getElementById('btn-trigger-sos');
  const noticeText = document.getElementById('notice-protocol-text');

  if (mode === 'luggage') {
    if (emergencyFormContainer) emergencyFormContainer.style.display = 'none';
    if (tteFormContainer) tteFormContainer.style.display = 'none';
    if (luggageFormContainer) luggageFormContainer.style.display = 'block';

    if (displayType) {
      displayType.textContent = 'Left Luggage / Forgotten Luggage';
      displayType.style.color = '#2563eb';
    }
    if (badge) {
      badge.textContent = 'PASSENGER ASSISTANCE';
      badge.className = 'badge';
      badge.style.background = 'rgba(37, 99, 235, 0.15)';
      badge.style.color = '#1d4ed8';
    }

    const lugDateInput = document.getElementById('input-luggage-date');
    if (lugDateInput && !lugDateInput.value) {
      lugDateInput.value = new Date().toISOString().split('T')[0];
    }

    const lugTrainInput = document.getElementById('input-luggage-train');
    if (lugTrainInput && lugTrainInput.value) {
      lookupLuggageTrain(lugTrainInput.value.trim());
    }
    return;
  }

  if (mode === 'tte') {
    if (emergencyFormContainer) emergencyFormContainer.style.display = 'none';
    if (luggageFormContainer) luggageFormContainer.style.display = 'none';
    if (tteFormContainer) tteFormContainer.style.display = 'block';

    if (displayType) {
      displayType.textContent = 'Contact TTE / Train Staff';
      displayType.style.color = 'var(--accent-saffron, #f77f00)';
    }
    if (badge) {
      badge.textContent = 'PASSENGER ASSISTANCE';
      badge.className = 'badge';
      badge.style.background = 'rgba(247, 127, 0, 0.15)';
      badge.style.color = '#c05621';
    }

    const tteDateInput = document.getElementById('input-tte-date');
    if (tteDateInput && !tteDateInput.value) {
      tteDateInput.value = new Date().toISOString().split('T')[0];
    }

    const tteTrainInput = document.getElementById('input-tte-train');
    if (tteTrainInput && tteTrainInput.value) {
      lookupTteTrain(tteTrainInput.value.trim());
    }
    return;
  }

  // For emergency or cleaning modes:
  if (tteFormContainer) tteFormContainer.style.display = 'none';
  if (luggageFormContainer) luggageFormContainer.style.display = 'none';
  if (emergencyFormContainer) emergencyFormContainer.style.display = 'block';

  if (mode === 'cleaning') {
    if (displayType) {
      displayType.textContent = 'Coach Cleaning Request';
      displayType.style.color = '#2a9d8f';
    }
    if (badge) {
      badge.textContent = 'SERVICE REQUEST (NON-EMERGENCY)';
      badge.className = 'badge';
      badge.style.background = 'rgba(42, 157, 143, 0.15)';
      badge.style.color = '#1b685f';
    }
    if (cleaningGroup) cleaningGroup.style.display = 'block';
    if (seatLabel) seatLabel.textContent = 'Seat Number (Optional)';
    if (descLabel) descLabel.textContent = 'Additional Notes / Instructions (Optional)';
    if (descInput) {
      descInput.required = false;
      descInput.placeholder = 'Provide specific location or details (e.g. Near washroom, seat 14, floor dirty)...';
      descInput.value = 'Please clean the coach floor and washroom promptly.';
    }
    if (triggerBtn) {
      triggerBtn.className = 'btn btn-lg';
      triggerBtn.style.background = '#2a9d8f';
      triggerBtn.style.borderColor = '#2a9d8f';
      triggerBtn.style.color = 'white';
      triggerBtn.innerHTML = '<i class="fa-solid fa-broom"></i> REQUEST COACH CLEANING';
    }
    if (noticeText) {
      noticeText.innerHTML = '* Housekeeping Notice: This is an onboard passenger service request. It alerts the coach cleaning supervisor and does not dispatch emergency armed forces.';
    }
  } else {
    if (displayType) {
      displayType.textContent = typeName;
      displayType.style.color = 'var(--accent-red)';
    }
    if (badge) {
      badge.textContent = 'HIGH PRIORITY TICKET';
      badge.className = 'badge badge-cancelled';
      badge.style.background = '';
      badge.style.color = '';
    }
    if (cleaningGroup) cleaningGroup.style.display = 'none';
    if (seatLabel) seatLabel.textContent = 'Seat Number *';
    if (descLabel) descLabel.textContent = 'Describe the Emergency Situation *';
    if (descInput) {
      descInput.required = true;
      descInput.placeholder = 'Provide key details so attending staff can arrive prepared...';
      descInput.value = 'Passenger feeling severe dizziness and requiring immediate doctor assistance at next halt.';
    }
    if (triggerBtn) {
      triggerBtn.className = 'btn btn-danger btn-lg';
      triggerBtn.style.background = '';
      triggerBtn.style.borderColor = '';
      triggerBtn.style.color = '';
      triggerBtn.innerHTML = '<i class="fa-solid fa-bullhorn"></i> DISPATCH EMERGENCY SOS (RPF 139)';
    }
    if (noticeText) {
      noticeText.innerHTML = '* Demo Notice: Alerts generated here are logged to MySQL/SQLite and simulated for demonstration purposes without contacting real police authorities.';
    }
  }
}

function setupEmergencyForm() {
  const actionBtn = document.getElementById('btn-trigger-sos');
  if (actionBtn) {
    actionBtn.addEventListener('click', () => {
      if (currentMode === 'cleaning') {
        executeCleaningDispatch();
      } else {
        openSosModal();
      }
    });
  }

  const confirmBtn = document.getElementById('btn-confirm-sos-dispatch');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', executeSosDispatch);
  }

  // TTE train lookup listener
  const tteTrainInput = document.getElementById('input-tte-train');
  if (tteTrainInput) {
    let debounceTimer;
    tteTrainInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        lookupTteTrain(tteTrainInput.value.trim());
      }, 300);
    });
    tteTrainInput.addEventListener('blur', () => {
      lookupTteTrain(tteTrainInput.value.trim());
    });
  }

  // TTE submit button listener
  const tteSubmitBtn = document.getElementById('btn-submit-tte');
  if (tteSubmitBtn) {
    tteSubmitBtn.addEventListener('click', executeTteDispatch);
  }

  // Left Luggage train lookup listener
  const lugTrainInput = document.getElementById('input-luggage-train');
  if (lugTrainInput) {
    let debounceTimer;
    lugTrainInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        lookupLuggageTrain(lugTrainInput.value.trim());
      }, 300);
    });
    lugTrainInput.addEventListener('blur', () => {
      lookupLuggageTrain(lugTrainInput.value.trim());
    });
  }

  // Left Luggage PNR lookup listener
  const lugPnrInput = document.getElementById('input-luggage-pnr');
  if (lugPnrInput) {
    let pnrTimer;
    lugPnrInput.addEventListener('input', () => {
      clearTimeout(pnrTimer);
      const val = lugPnrInput.value.trim();
      if (val.length === 10) {
        pnrTimer = setTimeout(() => {
          lookupLuggagePnr(val);
        }, 300);
      }
    });
    lugPnrInput.addEventListener('blur', () => {
      const val = lugPnrInput.value.trim();
      if (val.length === 10) {
        lookupLuggagePnr(val);
      }
    });
  }

  // Left Luggage submit button listener
  const lugSubmitBtn = document.getElementById('btn-submit-luggage');
  if (lugSubmitBtn) {
    lugSubmitBtn.addEventListener('click', executeLuggageDispatch);
  }

  // Incident tracker form
  const trackForm = document.getElementById('track-incident-form');
  if (trackForm) {
    trackForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const incId = document.getElementById('input-incident-id').value.trim();
      if (incId) trackIncidentStatus(incId);
    });
  }
}

function openSosModal() {
  const trainNo = document.getElementById('input-sos-train').value.trim();
  const coach = document.getElementById('input-sos-coach').value.trim();
  const seat = document.getElementById('input-sos-seat').value.trim();

  if (!trainNo || !coach || !seat) {
    showToast('Please fill in your Train Number, Coach and Seat to dispatch help.', 'warning');
    return;
  }

  document.getElementById('sos-modal-type').textContent = selectedEmergencyType;
  document.getElementById('sos-modal-train').textContent = trainNo;
  document.getElementById('sos-modal-seat').textContent = `Coach ${coach}, Seat ${seat}`;

  const modal = document.getElementById('sos-confirm-modal');
  if (modal) modal.classList.add('active');
}

function closeSosModal() {
  const modal = document.getElementById('sos-confirm-modal');
  if (modal) modal.classList.remove('active');
}

async function executeSosDispatch() {
  const trainNo = document.getElementById('input-sos-train').value.trim();
  const coach = document.getElementById('input-sos-coach').value.trim();
  const seat = document.getElementById('input-sos-seat').value.trim();
  const desc = document.getElementById('input-sos-desc').value.trim();
  const name = document.getElementById('input-sos-name').value.trim() || 'Passenger';
  const phone = document.getElementById('input-sos-phone').value.trim() || '139-RPF';

  const btn = document.getElementById('btn-confirm-sos-dispatch');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Dispatched to Control Room...`;
  }

  const res = await fetchApi('/emergency/sos', {
    method: 'POST',
    body: JSON.stringify({
      emergency_type: selectedEmergencyType,
      train_number: trainNo,
      coach: coach,
      seat: seat,
      description: desc || `Urgent assistance required in Coach ${coach} Seat ${seat}.`,
      user_name: name,
      user_phone: phone
    })
  });

  closeSosModal();

  if (!res.success) {
    showToast(res.message, 'error', 'SOS Dispatch Failed');
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'DISPATCH EMERGENCY TEAM';
    }
    return;
  }

  const incident = res.data;
  showToast(`Emergency Broadcast Received! Incident ID: ${incident.incident_id}`, 'error', 'SOS DISPATCHED');
  renderIncidentReceipt(incident);
}

async function executeCleaningDispatch() {
  const trainNo = document.getElementById('input-sos-train').value.trim();
  const coach = document.getElementById('input-sos-coach').value.trim();
  const seat = document.getElementById('input-sos-seat').value.trim();
  const issue = document.getElementById('input-cleaning-issue').value.trim();
  const name = document.getElementById('input-sos-name').value.trim() || 'Passenger';
  const phone = document.getElementById('input-sos-phone').value.trim();
  const desc = document.getElementById('input-sos-desc').value.trim();

  if (!trainNo) {
    showToast('Please enter the Train Number.', 'warning');
    return;
  }
  if (!coach) {
    showToast('Please enter your Coach Number (e.g. B1, S3).', 'warning');
    return;
  }
  if (!phone) {
    showToast('Please enter your Contact Mobile number.', 'warning');
    return;
  }

  const btn = document.getElementById('btn-trigger-sos');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Submitting Request...`;
  }

  const res = await fetchApi('/emergency/cleaning', {
    method: 'POST',
    body: JSON.stringify({
      train_number: trainNo,
      coach_number: coach,
      seat_number: seat || null,
      issue_type: issue,
      passenger_name: name,
      contact_mobile: phone,
      description: desc
    })
  });

  if (btn) {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-broom"></i> REQUEST COACH CLEANING';
  }

  if (!res.success) {
    showToast(res.message, 'error', 'Cleaning Request Failed');
    return;
  }

  const req = res.data;
  showToast(`Coach Cleaning Request Logged! Request ID: ${req.request_id}`, 'success', 'REQUEST REGISTERED');
  renderCleaningReceipt(req);
}

function renderIncidentReceipt(incident) {
  const card = document.getElementById('sos-receipt-container');
  if (!card) return;

  card.innerHTML = `
    <div class="card" style="border-left: 6px solid var(--accent-red); background: white; box-shadow: var(--shadow-xl); padding: 2rem; margin-top: 2rem;">
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.25rem;">
        <div>
          <span class="badge" style="background: rgba(230, 57, 70, 0.15); color: var(--accent-red); font-size: 0.85rem;">
            <i class="fa-solid fa-tower-broadcast fa-fade"></i> ACTIVE SOS INCIDENT
          </span>
          <h2 style="font-size: 1.8rem; color: var(--primary-navy); margin-top: 0.5rem;">Incident ID: ${incident.incident_id}</h2>
        </div>
        <span class="badge badge-wl" style="font-size: 0.9rem; padding: 0.4rem 1rem;">STATUS: ${incident.status}</span>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; background: var(--bg-slate); padding: 1.25rem; border-radius: var(--radius-md); margin-bottom: 1.5rem;">
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Emergency Type</span>
          <strong style="display: block; font-size: 1rem; color: var(--accent-red);">${incident.emergency_type}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Train & Location</span>
          <strong style="display: block; font-size: 1rem;">Train ${incident.train_number} (${incident.coach}-${incident.seat})</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Passenger</span>
          <strong style="display: block; font-size: 1rem;">${incident.user_name} (${incident.user_phone})</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Timestamp</span>
          <strong style="display: block; font-size: 0.95rem;">${incident.created_at || 'Just now'}</strong>
        </div>
      </div>

      <div style="background: rgba(42, 157, 143, 0.08); border-left: 4px solid var(--accent-green); padding: 1rem 1.25rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
        <h4 style="font-size: 0.95rem; color: #1b685f; margin-bottom: 0.25rem;"><i class="fa-solid fa-headset"></i> Control Room Response Note:</h4>
        <p style="font-size: 0.9rem; color: var(--text-primary);">${incident.response_note}</p>
      </div>

      <p style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">
        * Notice: This is a verified simulated log. In a live system, this protocol signals the Railway Protection Force (RPF) and Train Superintendent at 139.
      </p>
    </div>
  `;
  card.scrollIntoView({ behavior: 'smooth' });
}

function renderCleaningReceipt(req) {
  const card = document.getElementById('sos-receipt-container');
  if (!card) return;

  const statusClass = req.status === 'RESOLVED' ? 'badge-confirmed' : (req.status === 'CANCELLED' ? 'badge-cancelled' : 'badge-available');

  card.innerHTML = `
    <div class="card" style="border-left: 6px solid #2a9d8f; background: white; box-shadow: var(--shadow-xl); padding: 2rem; margin-top: 2rem;">
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.25rem;">
        <div>
          <span class="badge" style="background: rgba(42, 157, 143, 0.15); color: #1b685f; font-size: 0.85rem;">
            <i class="fa-solid fa-broom"></i> ONBOARD COACH CLEANING SERVICE
          </span>
          <h2 style="font-size: 1.8rem; color: var(--primary-navy); margin-top: 0.5rem;">Request ID: ${req.request_id}</h2>
        </div>
        <span class="badge ${statusClass}" style="font-size: 0.9rem; padding: 0.4rem 1rem;">STATUS: ${req.status}</span>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; background: var(--bg-slate); padding: 1.25rem; border-radius: var(--radius-md); margin-bottom: 1.5rem;">
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Issue Reported</span>
          <strong style="display: block; font-size: 1rem; color: #2a9d8f;">${req.issue_type}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Train & Coach</span>
          <strong style="display: block; font-size: 1rem;">Train ${req.train_number} (Coach ${req.coach_number}${req.seat_number ? ', Seat ' + req.seat_number : ''})</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Passenger</span>
          <strong style="display: block; font-size: 1rem;">${req.passenger_name} (${req.contact_mobile})</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Submitted At</span>
          <strong style="display: block; font-size: 0.95rem;">${req.created_at || 'Just now'}</strong>
        </div>
      </div>

      ${req.description ? `
        <div style="background: #f8fafc; border: 1px solid var(--border-light); padding: 1rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
          <strong style="font-size: 0.85rem; color: var(--text-secondary); display: block; margin-bottom: 0.25rem;">Passenger Notes:</strong>
          <p style="font-size: 0.9rem; margin: 0; color: var(--text-primary);">${req.description}</p>
        </div>
      ` : ''}

      <div style="background: rgba(42, 157, 143, 0.08); border-left: 4px solid #2a9d8f; padding: 1rem 1.25rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
        <h4 style="font-size: 0.95rem; color: #1b685f; margin-bottom: 0.25rem;"><i class="fa-solid fa-bell"></i> Housekeeping Workflow Status:</h4>
        <p style="font-size: 0.9rem; color: var(--text-primary); margin: 0;">
          ${req.status === 'PENDING' ? 'Request received. On-board housekeeping staff is being scheduled for Coach ' + req.coach_number + '.' :
            req.status === 'ASSIGNED' ? 'Attendant assigned. Expected arrival in coach shortly.' :
            req.status === 'CLEANING IN PROGRESS' ? 'Cleaning in progress by onboard sanitation crew.' :
            req.status === 'RESOLVED' ? 'Service marked as RESOLVED by onboard team. Thank you for your feedback.' :
            'Request ' + req.status + '.'}
        </p>
      </div>

      <p style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">
        * Note: Track this service anytime using Request ID <strong>${req.request_id}</strong> on this page.
      </p>
    </div>
  `;
  card.scrollIntoView({ behavior: 'smooth' });
}

async function trackIncidentStatus(incidentId) {
  const idUpper = (incidentId || '').trim().toUpperCase();
  if (idUpper.startsWith('CLR-')) {
    const res = await fetchApi(`/emergency/cleaning/${idUpper}`);
    if (!res.success) {
      showToast(`No cleaning request found matching '${incidentId}'`, 'warning');
      return;
    }
    renderCleaningReceipt(res.data);
  } else if (idUpper.startsWith('TTE-')) {
    const res = await fetchApi(`/emergency/tte/${idUpper}`);
    if (!res.success) {
      showToast(`No TTE assistance request found matching '${incidentId}'`, 'warning');
      return;
    }
    renderTteReceipt(res.data);
  } else if (idUpper.startsWith('LUG-')) {
    const res = await fetchApi(`/emergency/luggage/${idUpper}`);
    if (!res.success) {
      showToast(`No left luggage request found matching '${incidentId}'`, 'warning');
      return;
    }
    renderLuggageReceipt(res.data);
  } else {
    const res = await fetchApi(`/emergency/${idUpper}`);
    if (!res.success) {
      showToast(`No incident found matching '${incidentId}'`, 'warning');
      return;
    }
    renderIncidentReceipt(res.data);
  }
}

async function lookupTteTrain(trainNo) {
  const badgeEl = document.getElementById('tte-train-info-badge');
  if (!badgeEl) return;

  if (!trainNo || trainNo.length < 4) {
    badgeEl.style.display = 'none';
    badgeEl.textContent = '';
    return;
  }

  try {
    const res = await fetchApi(`/trains/number/${trainNo}`);
    if (res.success && res.data) {
      const t = res.data;
      const src = t.source_code || t.source || '';
      const dst = t.dest_code || t.destination || '';
      const routeText = src && dst ? ` (${src} ➔ ${dst})` : '';
      badgeEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${t.train_name}${routeText}`;
      badgeEl.style.color = 'var(--accent-green, #2a9d8f)';
      badgeEl.style.display = 'block';
    } else {
      badgeEl.innerHTML = `<i class="fa-solid fa-train"></i> Train ${trainNo}`;
      badgeEl.style.color = 'var(--text-muted)';
      badgeEl.style.display = 'block';
    }
  } catch (e) {
    badgeEl.style.display = 'none';
  }
}

async function executeTteDispatch() {
  const trainNo = document.getElementById('input-tte-train').value.trim();
  const dateVal = document.getElementById('input-tte-date').value.trim();
  const coach = document.getElementById('input-tte-coach').value.trim();
  const berth = document.getElementById('input-tte-berth').value.trim();
  const pnr = document.getElementById('input-tte-pnr').value.trim();
  const assistanceType = document.getElementById('input-tte-type').value.trim();
  const desc = document.getElementById('input-tte-desc').value.trim();

  if (!trainNo) {
    showToast('Please enter the Train Number.', 'warning');
    return;
  }
  if (!dateVal) {
    showToast('Please select your Journey Date.', 'warning');
    return;
  }
  if (!assistanceType) {
    showToast('Please select an Assistance Type.', 'warning');
    return;
  }
  if (!desc || desc.length < 5) {
    showToast('Please describe your issue (at least 5 characters).', 'warning');
    return;
  }
  if (pnr && !/^\d{10}$/.test(pnr)) {
    showToast('PNR must be a valid 10-digit number.', 'warning');
    return;
  }

  const btn = document.getElementById('btn-submit-tte');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Submitting Request...`;
  }

  const res = await fetchApi('/emergency/tte', {
    method: 'POST',
    body: JSON.stringify({
      train_number: trainNo,
      journey_date: dateVal,
      coach: coach || null,
      berth: berth || null,
      pnr: pnr || null,
      assistance_type: assistanceType,
      description: desc
    })
  });

  if (btn) {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-ticket"></i> Request TTE Assistance';
  }

  if (!res.success) {
    showToast(res.message, 'error', 'Submission Failed');
    return;
  }

  const req = res.data;
  showToast(`TTE Assistance Request Logged! Request ID: ${req.request_id}`, 'success', 'REQUEST REGISTERED');
  renderTteReceipt(req);
}

function renderTteReceipt(req) {
  const card = document.getElementById('sos-receipt-container');
  if (!card) return;

  const statusClass = req.status === 'Resolved' ? 'badge-confirmed' :
                      (req.status === 'Cancelled' ? 'badge-cancelled' :
                      (req.status === 'Submitted' ? 'badge-ai' : 'badge-available'));

  card.innerHTML = `
    <div class="card" style="border-left: 6px solid var(--accent-saffron, #f77f00); background: white; box-shadow: var(--shadow-xl); padding: 2rem; margin-top: 2rem;">
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.25rem;">
        <div>
          <span class="badge" style="background: rgba(247, 127, 0, 0.15); color: #c05621; font-size: 0.85rem;">
            <i class="fa-solid fa-ticket"></i> ONBOARD TTE & PASSENGER ASSISTANCE
          </span>
          <h2 style="font-size: 1.8rem; color: var(--primary-navy); margin-top: 0.5rem;">Request ID: ${req.request_id}</h2>
        </div>
        <span class="badge ${statusClass}" style="font-size: 0.9rem; padding: 0.4rem 1rem;">STATUS: ${req.status || 'Pending'}</span>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; background: var(--bg-slate); padding: 1.25rem; border-radius: var(--radius-md); margin-bottom: 1.5rem;">
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Assistance Type</span>
          <strong style="display: block; font-size: 1rem; color: var(--accent-saffron, #f77f00);">${req.assistance_type}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Train & Journey Date</span>
          <strong style="display: block; font-size: 1rem;">Train ${req.train_number} ${req.train_name ? '(' + req.train_name + ')' : ''} &bull; ${req.journey_date}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Coach & Berth</span>
          <strong style="display: block; font-size: 1rem;">Coach ${req.coach || 'N/A'}, Berth ${req.berth || 'N/A'}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">PNR Number</span>
          <strong style="display: block; font-size: 1rem;">${req.pnr || 'Not Provided'}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Submitted At</span>
          <strong style="display: block; font-size: 0.95rem;">${req.created_at || 'Just now'}</strong>
        </div>
      </div>

      ${req.description ? `
        <div style="background: #f8fafc; border: 1px solid var(--border-light); padding: 1rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
          <strong style="font-size: 0.85rem; color: var(--text-secondary); display: block; margin-bottom: 0.25rem;">Passenger Description:</strong>
          <p style="font-size: 0.9rem; margin: 0; color: var(--text-primary);">${req.description}</p>
        </div>
      ` : ''}

      <div style="background: rgba(247, 127, 0, 0.08); border-left: 4px solid var(--accent-saffron, #f77f00); padding: 1rem 1.25rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
        <h4 style="font-size: 0.95rem; color: #c05621; margin-bottom: 0.25rem;"><i class="fa-solid fa-circle-info"></i> Notice & Guidance:</h4>
        <p style="font-size: 0.9rem; color: var(--text-primary); margin: 0; line-height: 1.45;">
          Your assistance request has been recorded in SmartRail. For immediate onboard assistance, please contact the TTE/train staff directly or use Railway Helpline 139.
        </p>
      </div>

      <p style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">
        * Note: Track this service anytime using Request ID <strong>${req.request_id}</strong> on this page.
      </p>
    </div>
  `;
  card.scrollIntoView({ behavior: 'smooth' });
}

async function lookupLuggageTrain(trainNo) {
  const badgeEl = document.getElementById('luggage-train-info-badge');
  const nameInput = document.getElementById('input-luggage-train-name');
  const boardInput = document.getElementById('input-luggage-boarding');
  const deboardInput = document.getElementById('input-luggage-deboarding');

  if (!trainNo || trainNo.length < 4) {
    if (badgeEl) {
      badgeEl.style.display = 'none';
      badgeEl.textContent = '';
    }
    return;
  }

  try {
    const res = await fetchApi(`/trains/number/${trainNo}`);
    if (res.success && res.data) {
      const t = res.data;
      const src = t.source_code || t.source || '';
      const dst = t.dest_code || t.destination || '';
      const routeText = src && dst ? ` (${src} ➔ ${dst})` : '';
      if (badgeEl) {
        badgeEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${t.train_name}${routeText}`;
        badgeEl.style.color = '#2563eb';
        badgeEl.style.display = 'block';
      }
      if (nameInput && !nameInput.value) {
        nameInput.value = t.train_name || '';
      }
      if (boardInput && !boardInput.value && src) {
        boardInput.value = src;
      }
      if (deboardInput && !deboardInput.value && dst) {
        deboardInput.value = dst;
      }
    } else {
      if (badgeEl) {
        badgeEl.innerHTML = `<i class="fa-solid fa-train"></i> Train ${trainNo}`;
        badgeEl.style.color = 'var(--text-muted)';
        badgeEl.style.display = 'block';
      }
    }
  } catch (e) {
    if (badgeEl) badgeEl.style.display = 'none';
  }
}

async function lookupLuggagePnr(pnr) {
  const badgeEl = document.getElementById('luggage-pnr-info-badge');
  if (!pnr || pnr.length !== 10) {
    if (badgeEl) {
      badgeEl.style.display = 'none';
      badgeEl.textContent = '';
    }
    return;
  }

  try {
    const res = await fetchApi(`/pnr/${pnr}`);
    if (res.success && res.data) {
      const p = res.data;
      const trainInput = document.getElementById('input-luggage-train');
      const dateInput = document.getElementById('input-luggage-date');
      const coachInput = document.getElementById('input-luggage-coach');
      const seatInput = document.getElementById('input-luggage-seat');
      const boardInput = document.getElementById('input-luggage-boarding');
      const deboardInput = document.getElementById('input-luggage-deboarding');
      const nameInput = document.getElementById('input-luggage-train-name');

      if (trainInput && p.train_number) trainInput.value = p.train_number;
      if (dateInput && p.journey_date) dateInput.value = p.journey_date;
      if (nameInput && p.train_name) nameInput.value = p.train_name;
      if (boardInput && (p.source || p.source_code || p.boarding_station)) {
        boardInput.value = p.source_code || p.source || p.boarding_station;
      }
      if (deboardInput && (p.destination || p.dest_code || p.deboarding_station)) {
        deboardInput.value = p.dest_code || p.destination || p.deboarding_station;
      }

      if (p.passengers && p.passengers.length > 0) {
        const p1 = p.passengers[0];
        if (coachInput && !coachInput.value && p1.coach) coachInput.value = p1.coach;
        if (seatInput && !seatInput.value && (p1.berth_number || p1.seat_number)) {
          seatInput.value = p1.berth_number || p1.seat_number;
        }
      }

      if (badgeEl) {
        badgeEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> PNR Details Loaded: Train ${p.train_number || ''}`;
        badgeEl.style.color = 'var(--accent-green, #2a9d8f)';
        badgeEl.style.display = 'block';
      }

      if (trainInput && trainInput.value) {
        lookupLuggageTrain(trainInput.value);
      }
    } else {
      if (badgeEl) badgeEl.style.display = 'none';
    }
  } catch (e) {
    if (badgeEl) badgeEl.style.display = 'none';
  }
}

async function executeLuggageDispatch() {
  const trainNo = document.getElementById('input-luggage-train').value.trim();
  const dateVal = document.getElementById('input-luggage-date').value.trim();
  const coach = document.getElementById('input-luggage-coach').value.trim();
  const seat = document.getElementById('input-luggage-seat').value.trim();
  const deboarding = document.getElementById('input-luggage-deboarding').value.trim();
  const desc = document.getElementById('input-luggage-desc').value.trim();
  const mobile = document.getElementById('input-luggage-mobile').value.trim();

  const pnr = document.getElementById('input-luggage-pnr').value.trim();
  const boarding = document.getElementById('input-luggage-boarding').value.trim();
  const trainName = document.getElementById('input-luggage-train-name').value.trim();
  const contents = document.getElementById('input-luggage-contents').value.trim();
  const details = document.getElementById('input-luggage-details').value.trim();

  // Validations
  if (!trainNo) {
    showToast('Please enter the Train Number.', 'warning');
    return;
  }
  if (!dateVal) {
    showToast('Please select your Journey Date.', 'warning');
    return;
  }
  if (!coach) {
    showToast('Please enter your Coach Number (e.g. B2, S4).', 'warning');
    return;
  }
  if (!seat) {
    showToast('Please enter your Seat / Berth Number.', 'warning');
    return;
  }
  if (!deboarding) {
    showToast('Please enter the Deboarding Station where you got down.', 'warning');
    return;
  }
  if (!desc || desc.length < 5) {
    showToast('Please provide a description of the luggage (at least 5 characters).', 'warning');
    return;
  }
  if (!mobile || !/^\d{10,15}$/.test(mobile.replace(/[-\s]/g, ''))) {
    showToast('Please enter a valid passenger mobile number (at least 10 digits).', 'warning');
    return;
  }
  if (pnr && !/^\d{10}$/.test(pnr)) {
    showToast('PNR must be a valid 10-digit number.', 'warning');
    return;
  }

  const btn = document.getElementById('btn-submit-luggage');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Submitting Request...`;
  }

  const res = await fetchApi('/emergency/luggage', {
    method: 'POST',
    body: JSON.stringify({
      train_number: trainNo,
      journey_date: dateVal,
      coach: coach,
      seat: seat,
      deboarding_station: deboarding,
      luggage_description: desc,
      passenger_mobile: mobile,
      pnr: pnr || null,
      boarding_station: boarding || null,
      train_name: trainName || null,
      luggage_contents: contents || null,
      additional_details: details || null
    })
  });

  if (btn) {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-suitcase-rolling"></i> Register Left Luggage Assistance';
  }

  if (!res.success) {
    showToast(res.message, 'error', 'Submission Failed');
    return;
  }

  const req = res.data;
  showToast(`Left Luggage Request Registered! Request ID: ${req.request_id}`, 'success', 'REQUEST REGISTERED');
  renderLuggageReceipt(req);
}

function renderLuggageReceipt(req) {
  const card = document.getElementById('sos-receipt-container');
  if (!card) return;

  const statusClass = req.status === 'Found' || req.status === 'Returned' ? 'badge-confirmed' :
                      (req.status === 'Closed' || req.status === 'Cancelled' ? 'badge-cancelled' :
                      (req.status === 'Under Investigation' ? 'badge-available' : 'badge-ai'));

  card.innerHTML = `
    <div class="card" style="border-left: 6px solid #2563eb; background: white; box-shadow: var(--shadow-xl); padding: 2rem; margin-top: 2rem;">
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.25rem;">
        <div>
          <span class="badge" style="background: rgba(37, 99, 235, 0.15); color: #1d4ed8; font-size: 0.85rem;">
            <i class="fa-solid fa-suitcase-rolling"></i> LEFT / FORGOTTEN LUGGAGE ASSISTANCE
          </span>
          <h2 style="font-size: 1.8rem; color: var(--primary-navy); margin-top: 0.5rem;">Request ID: ${req.request_id}</h2>
        </div>
        <span class="badge ${statusClass}" style="font-size: 0.9rem; padding: 0.4rem 1rem;">STATUS: ${req.status || 'Submitted'}</span>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; background: var(--bg-slate); padding: 1.25rem; border-radius: var(--radius-md); margin-bottom: 1.5rem;">
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Train & Journey Date</span>
          <strong style="display: block; font-size: 1rem;">Train ${req.train_number} ${req.train_name ? '(' + req.train_name + ')' : ''} &bull; ${req.journey_date}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Coach & Seat</span>
          <strong style="display: block; font-size: 1rem; color: #2563eb;">Coach ${req.coach}, Seat / Berth ${req.seat}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Deboarding Station</span>
          <strong style="display: block; font-size: 1rem;">${req.deboarding_station} ${req.boarding_station ? '(Boarded: ' + req.boarding_station + ')' : ''}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Passenger Mobile</span>
          <strong style="display: block; font-size: 1rem;">${req.passenger_mobile}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">PNR Number</span>
          <strong style="display: block; font-size: 1rem;">${req.pnr || 'Not Provided'}</strong>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Submitted At</span>
          <strong style="display: block; font-size: 0.95rem;">${req.created_at || 'Just now'}</strong>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-bottom: 1.25rem;">
        <div style="background: #f8fafc; border: 1px solid var(--border-light); padding: 1rem; border-radius: var(--radius-sm);">
          <strong style="font-size: 0.85rem; color: var(--text-secondary); display: block; margin-bottom: 0.25rem;">Luggage Description:</strong>
          <p style="font-size: 0.95rem; font-weight: 600; margin: 0; color: var(--text-primary);">${req.luggage_description}</p>
          ${req.luggage_contents ? `<div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.4rem;"><strong>Contents:</strong> ${req.luggage_contents}</div>` : ''}
        </div>
        ${req.additional_details ? `
          <div style="background: #f8fafc; border: 1px solid var(--border-light); padding: 1rem; border-radius: var(--radius-sm);">
            <strong style="font-size: 0.85rem; color: var(--text-secondary); display: block; margin-bottom: 0.25rem;">Additional Details:</strong>
            <p style="font-size: 0.9rem; margin: 0; color: var(--text-primary);">${req.additional_details}</p>
          </div>
        ` : ''}
      </div>

      <div style="background: rgba(37, 99, 235, 0.08); border-left: 4px solid #2563eb; padding: 1rem 1.25rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
        <h4 style="font-size: 0.95rem; color: #1d4ed8; margin-bottom: 0.35rem;"><i class="fa-solid fa-phone-volume"></i> Immediate Recommended Action:</h4>
        <p style="font-size: 0.9rem; color: var(--text-primary); margin: 0; line-height: 1.5;">
          Your request has been logged in SmartRail under Request ID <strong>${req.request_id}</strong>. For the fastest response, immediately contact <strong>Railway Helpline 139</strong> or report in person to the <strong>RPF Assistance Post / Station Master</strong> at <strong>${req.deboarding_station}</strong> quoting this Request ID, your train number, and coach/seat.
        </p>
      </div>

      <p style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">
        * Notice: SmartRail records and manages your left luggage assistance details for tracing purposes. To track current status anytime, enter <strong>${req.request_id}</strong> in the Track Assistance section above.
      </p>
    </div>
  `;
  card.scrollIntoView({ behavior: 'smooth' });
}

