/**
 * SMART RAILWAY - INTERACTIVE COACH SEAT MAP, COMPOSITION & AI RECOMMENDER
 */

let currentCoach = null;
let currentSeats = [];
let selectedSeats = []; // array of seat objects
let lockTimerInterval = null;
let lockExpiresAt = null;

const trainId = getQueryParam('train_id') || '1';
let coachId = getQueryParam('coach_id');
const initialClass = getQueryParam('class');
const journeyDate = getQueryParam('date') || new Date().toISOString().split('T')[0];
const quotaCode = getQueryParam('quota') || 'GN';
const fromStation = getQueryParam('from') || '';
const toStation = getQueryParam('to') || '';
const passedFare = getQueryParam('fare') || '';

let currentClassCode = null;
let allTrainClasses = [];
let allTrainCoaches = [];
let allAiRecommendations = [];

document.addEventListener('DOMContentLoaded', async () => {
  setupAIRecommenderControls();
  await loadTrainCompositionAndCoaches();
});

// 1. Load Train Composition & Available Coaches
async function loadTrainCompositionAndCoaches() {
  const container = document.getElementById('seat-map-render-target');
  if (container) {
    container.innerHTML = `
      <div class="state-box">
        <div class="spinner"></div>
        <h3>Loading Train Coach Composition...</h3>
        <p>Fetching train rake configuration, class availability and seat inventory.</p>
      </div>
    `;
  }

  try {
    let compUrl = `/trains/${trainId}/coaches?date=${encodeURIComponent(journeyDate)}&quota=${encodeURIComponent(quotaCode)}`;
    if (fromStation && toStation) {
      compUrl += `&from=${encodeURIComponent(fromStation)}&to=${encodeURIComponent(toStation)}`;
    }
    const res = await fetchApi(compUrl);
    if (res.success && res.data) {
      allTrainClasses = res.data.classes || [];
      allTrainCoaches = res.data.coaches || res.data.all_coaches || [];

      // Update train header info
      const titleEl = document.getElementById('train-header-title');
      if (titleEl && res.data.train_number) {
        titleEl.textContent = `${res.data.train_number} - ${res.data.train_name}`;
      }

      // Determine initial active class
      if (initialClass && allTrainClasses.some(c => c.class_code.toUpperCase() === initialClass.toUpperCase())) {
        currentClassCode = initialClass.toUpperCase();
      } else if (coachId) {
        const matchingCoach = allTrainCoaches.find(c => String(c.id) === String(coachId));
        if (matchingCoach) {
          currentClassCode = matchingCoach.coach_class;
        }
      }
      
      if (!currentClassCode && allTrainClasses.length > 0) {
        currentClassCode = allTrainClasses[0].class_code;
      } else if (!currentClassCode) {
        currentClassCode = '3A';
      }

      // Render Class Tabs & Coach Tabs
      renderClassTabs();
      renderCoachTabs();

      // Determine initial coachId
      const coachesForClass = allTrainCoaches.filter(c => c.coach_class === currentClassCode);
      if (coachId && coachesForClass.some(c => String(c.id) === String(coachId))) {
        // coachId is valid in active class
      } else if (coachesForClass.length > 0) {
        coachId = coachesForClass[0].id;
      }

      // Render active coach selection
      updateCoachTabsActiveState();
      await loadCoachAndSeats();
    } else {
      // Fallback: If composition endpoint returns error, load directly with coachId
      if (!coachId) coachId = '1';
      await loadCoachAndSeats();
    }
  } catch (err) {
    console.error('Error loading train composition:', err);
    if (!coachId) coachId = '1';
    await loadCoachAndSeats();
  }
}

// Render Class Filter Selector Tabs
function renderClassTabs() {
  const container = document.getElementById('class-tabs-container');
  if (!container) return;

  if (allTrainClasses.length === 0) {
    container.innerHTML = `<span style="font-size:0.85rem; color:var(--text-muted);">Standard</span>`;
    return;
  }

  container.innerHTML = allTrainClasses.map(cls => {
    const isActive = cls.class_code === currentClassCode;
    return `
      <button class="coach-tab-btn ${isActive ? 'active' : ''}" 
              onclick="switchClass('${cls.class_code}')"
              title="${cls.class_code} (${cls.coach_count} coaches, ${cls.status})">
        <span>${cls.class_code}</span>
        <span style="font-size: 0.72rem; opacity: 0.85; font-weight: 500;">(${cls.coach_count})</span>
      </button>
    `;
  }).join('');
}

// Render Coach Selector Tabs for the currently active class
function renderCoachTabs() {
  const container = document.getElementById('coach-tabs-container');
  if (!container) return;

  const coachesForClass = allTrainCoaches.filter(c => c.coach_class === currentClassCode);
  if (coachesForClass.length === 0) {
    container.innerHTML = `<span style="font-size:0.85rem; color:var(--text-muted);">No coaches available</span>`;
    return;
  }

  container.innerHTML = coachesForClass.map(c => {
    const isActive = String(c.id) === String(coachId);
    return `
      <button class="coach-tab-btn ${isActive ? 'active' : ''}" 
              data-coach-id="${c.id}"
              onclick="switchCoach(${c.id})"
              title="Coach ${c.coach_number} (${c.status})">
        ${c.coach_number}
      </button>
    `;
  }).join('');
}

function updateCoachTabsActiveState() {
  document.querySelectorAll('#coach-tabs-container .coach-tab-btn').forEach(btn => {
    const bId = btn.getAttribute('data-coach-id');
    btn.classList.toggle('active', String(bId) === String(coachId));
  });
}

// Switch Active Class Filter
async function switchClass(newClassCode) {
  if (newClassCode === currentClassCode) return;
  currentClassCode = newClassCode;
  
  // Clear any existing selected seats if changing class
  if (selectedSeats.length > 0) {
    selectedSeats = [];
    clearLockTimer();
  }

  renderClassTabs();
  
  const coachesForClass = allTrainCoaches.filter(c => c.coach_class === currentClassCode);
  if (coachesForClass.length > 0) {
    coachId = coachesForClass[0].id;
  }
  
  renderCoachTabs();
  await loadCoachAndSeats();
}

// Switch Active Coach
async function switchCoach(newCoachId) {
  if (String(newCoachId) === String(coachId)) return;
  coachId = newCoachId;
  
  // Clear any existing selected seats if switching coaches
  if (selectedSeats.length > 0) {
    selectedSeats = [];
    clearLockTimer();
  }

  updateCoachTabsActiveState();
  await loadCoachAndSeats();
}

// Load coach data and seat layout
async function loadCoachAndSeats() {
  const container = document.getElementById('seat-map-render-target');
  if (container) {
    container.innerHTML = `
      <div class="state-box">
        <div class="spinner"></div>
        <h3>Loading Coach Layout...</h3>
        <p>Fetching real-time berth allocation and active seat locks.</p>
      </div>
    `;
  }

  const sid = getSessionId();
  const res = await fetchApi(`/coaches/${coachId}/seats?date=${encodeURIComponent(journeyDate)}&session_id=${encodeURIComponent(sid)}`);

  if (!res.success) {
    if (container) {
      container.innerHTML = `
        <div class="state-box">
          <i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-red);"></i>
          <h3>Failed to Load Seat Map</h3>
          <p>${res.message}</p>
          <button class="btn btn-outline" onclick="loadCoachAndSeats()">Retry</button>
        </div>
      `;
    }
    return;
  }

  currentCoach = res.data.coach;
  currentSeats = res.data.seats;
  selectedSeats = [];

  updateHeaderDetails();
  renderSeatMap();
  updateSummaryBar();
  triggerAIRecommendations(); // Automatically score seats across the rake
}

function updateHeaderDetails() {
  const titleEl = document.getElementById('train-header-title');
  const metaEl = document.getElementById('train-header-meta');
  if (titleEl && currentCoach) {
    titleEl.textContent = `${currentCoach.train_number} - ${currentCoach.train_name}`;
  }
  if (metaEl && currentCoach) {
    metaEl.textContent = `Coach: ${currentCoach.coach_number} (${currentCoach.coach_class}) | Journey Date: ${journeyDate} | Quota: ${quotaCode}`;
  }
}

// Render Indian Railway Coach Compartment Bays
function renderSeatMap() {
  const container = document.getElementById('seat-map-render-target');
  if (!container || !currentCoach) return;

  const coachClass = currentCoach.coach_class;
  let baysHtml = '';

  if (['3A', 'SL'].includes(coachClass)) {
    // 72 seats in 9 compartments of 8 berths (1-6 in main bay, 7-8 in side bay)
    const numCompartments = Math.ceil(currentSeats.length / 8);
    for (let comp = 0; comp < numCompartments; comp++) {
      const startIdx = comp * 8;
      const compSeats = currentSeats.slice(startIdx, startIdx + 8);
      const mainBaySeats = compSeats.slice(0, 6);
      const sideBaySeats = compSeats.slice(6, 8);

      baysHtml += `
        <div class="compartment-bay">
          <div class="compartment-label">Bay ${comp + 1} (Seats ${startIdx + 1}-${Math.min(startIdx + 8, currentSeats.length)})</div>
          
          <div class="main-bay">
            ${mainBaySeats.map(s => renderSeatElement(s)).join('')}
          </div>

          <div class="aisle-gap">GANGWAY / AISLE</div>

          <div class="side-bay">
            ${sideBaySeats.map(s => renderSeatElement(s)).join('')}
          </div>
        </div>
      `;
    }
  } else if (coachClass === '2A') {
    // 48 seats in compartments of 6 berths (4 main bay, 2 side bay)
    const numCompartments = Math.ceil(currentSeats.length / 6);
    for (let comp = 0; comp < numCompartments; comp++) {
      const startIdx = comp * 6;
      const compSeats = currentSeats.slice(startIdx, startIdx + 6);
      const mainBaySeats = compSeats.slice(0, 4);
      const sideBaySeats = compSeats.slice(4, 6);

      baysHtml += `
        <div class="compartment-bay">
          <div class="compartment-label">Bay ${comp + 1} (Seats ${startIdx + 1}-${Math.min(startIdx + 6, currentSeats.length)})</div>
          
          <div class="main-bay" style="grid-template-columns: repeat(2, 1fr);">
            ${mainBaySeats.map(s => renderSeatElement(s)).join('')}
          </div>

          <div class="aisle-gap">AISLE</div>

          <div class="side-bay">
            ${sideBaySeats.map(s => renderSeatElement(s)).join('')}
          </div>
        </div>
      `;
    }
  } else if (coachClass === '1A') {
    // 1A Coupe & Cabin Layout: 4 berths per compartment (2 Lower, 2 Upper)
    const numCompartments = Math.ceil(currentSeats.length / 4);
    for (let comp = 0; comp < numCompartments; comp++) {
      const startIdx = comp * 4;
      const compSeats = currentSeats.slice(startIdx, startIdx + 4);

      baysHtml += `
        <div class="compartment-bay" style="grid-template-columns: 1fr 60px;">
          <div class="compartment-label">Cabin ${comp + 1} (Seats ${startIdx + 1}-${Math.min(startIdx + 4, currentSeats.length)})</div>
          
          <div class="main-bay" style="grid-template-columns: repeat(2, 1fr);">
            ${compSeats.map(s => renderSeatElement(s)).join('')}
          </div>

          <div class="aisle-gap">CORRIDOR</div>
        </div>
      `;
    }
  } else if (coachClass === 'EC') {
    // Executive Chair Car: 2+2 Seating
    const numRows = Math.ceil(currentSeats.length / 4);
    for (let r = 0; r < numRows; r++) {
      const startIdx = r * 4;
      const rowSeats = currentSeats.slice(startIdx, startIdx + 4);
      const leftBay = rowSeats.slice(0, 2);
      const rightBay = rowSeats.slice(2, 4);

      baysHtml += `
        <div class="compartment-bay" style="grid-template-columns: 1fr 60px 1fr;">
          <div class="compartment-label">Row ${r + 1}</div>
          <div class="main-bay" style="grid-template-columns: repeat(2, 1fr);">
            ${leftBay.map(s => renderSeatElement(s)).join('')}
          </div>
          <div class="aisle-gap">AISLE</div>
          <div class="side-bay" style="grid-template-columns: repeat(2, 1fr);">
            ${rightBay.map(s => renderSeatElement(s)).join('')}
          </div>
        </div>
      `;
    }
  } else {
    // Chair Car (CC): 3+2 Seating
    const numRows = Math.ceil(currentSeats.length / 5);
    for (let r = 0; r < numRows; r++) {
      const startIdx = r * 5;
      const rowSeats = currentSeats.slice(startIdx, startIdx + 5);
      const leftBay = rowSeats.slice(0, 3);
      const rightBay = rowSeats.slice(3, 5);

      baysHtml += `
        <div class="compartment-bay">
          <div class="compartment-label">Row ${r + 1}</div>
          <div class="main-bay" style="grid-template-columns: repeat(3, 1fr);">
            ${leftBay.map(s => renderSeatElement(s)).join('')}
          </div>
          <div class="aisle-gap">AISLE</div>
          <div class="side-bay" style="grid-template-columns: repeat(2, 1fr);">
            ${rightBay.map(s => renderSeatElement(s)).join('')}
          </div>
        </div>
      `;
    }
  }

  container.innerHTML = `
    <div class="coach-hull">
      <div class="coach-hull-header">
        <span><i class="fa-solid fa-door-open"></i> Coach Entrance / Vestibule</span>
        <span>Coach ${currentCoach.coach_number} (${currentCoach.coach_class})</span>
        <span>Lavatory / Exit <i class="fa-solid fa-restroom"></i></span>
      </div>
      <div class="coach-grid">
        ${baysHtml}
      </div>
    </div>
  `;
}

function renderSeatElement(seat) {
  const isSelected = selectedSeats.some(s => s.id === seat.id);
  let statusClass = `seat-${seat.status}`;
  if (isSelected) statusClass = 'seat-selected';

  let sparkleIcon = '';
  if (seat.is_recommended) {
    statusClass += ' seat-recommended';
    sparkleIcon = `<span class="seat-sparkle" title="${seat.recommendation_reason || 'AI Recommended'}"><i class="fa-solid fa-wand-magic-sparkles"></i></span>`;
  }

  const berthLabel = seat.seat_type.replace('_', ' ');

  return `
    <div class="seat ${statusClass}" 
         id="seat-node-${seat.id}"
         onclick="handleSeatClick(${seat.id})"
         title="Seat ${seat.seat_number} - ${berthLabel} (${seat.status})">
      ${sparkleIcon}
      <span class="seat-number">${seat.seat_number}</span>
      <span class="seat-berth">${berthLabel}</span>
    </div>
  `;
}

// Seat Click Handler
async function handleSeatClick(seatId) {
  const seat = currentSeats.find(s => s.id === seatId);
  if (!seat) return;

  if (seat.status === 'occupied') {
    showToast(`Seat ${seat.seat_number} is already booked.`, 'warning');
    return;
  }
  if (seat.status === 'temporarily_locked') {
    showToast(`Seat ${seat.seat_number} is currently locked by another passenger.`, 'warning');
    return;
  }

  const existingIdx = selectedSeats.findIndex(s => s.id === seatId);
  if (existingIdx > -1) {
    // Deselect
    selectedSeats.splice(existingIdx, 1);
  } else {
    // Max 6 passengers per booking
    if (selectedSeats.length >= 6) {
      showToast('Maximum 6 seats can be reserved in a single booking.', 'warning');
      return;
    }
    selectedSeats.push(seat);
  }

  // Refresh visual state
  currentSeats.forEach(s => {
    const el = document.getElementById(`seat-node-${s.id}`);
    if (el) {
      const isSel = selectedSeats.some(sel => sel.id === s.id);
      el.classList.toggle('seat-selected', isSel);
    }
  });

  updateSummaryBar();

  // Trigger seat locking when seats are selected
  if (selectedSeats.length > 0) {
    await acquireSeatLocks();
  } else {
    clearLockTimer();
  }
}

// Lock Seats on Backend
async function acquireSeatLocks() {
  const sid = getSessionId();
  const seatIds = selectedSeats.map(s => s.id);

  const res = await fetchApi('/seats/lock', {
    method: 'POST',
    body: JSON.stringify({
      seat_ids: seatIds,
      journey_date: journeyDate,
      session_id: sid
    })
  });

  if (!res.success) {
    showToast(res.message, 'error', 'Seat Lock Failed');
    // Deselect conflicting seat
    selectedSeats = [];
    renderSeatMap();
    updateSummaryBar();
    return;
  }

  startLockTimer(res.data.duration_seconds || 300);
}

// Countdown Timer for Seat Lock
function startLockTimer(seconds) {
  clearLockTimer();
  const banner = document.getElementById('seat-lock-banner');
  const timerText = document.getElementById('lock-countdown-display');
  if (banner) banner.style.display = 'flex';

  let remaining = seconds;
  updateTimerDisplay(remaining, timerText);

  lockTimerInterval = setInterval(() => {
    remaining--;
    if (remaining <= 0) {
      clearLockTimer();
      showToast('Your seat lock has expired. Seats released.', 'warning', 'Lock Expired');
      selectedSeats = [];
      loadCoachAndSeats();
    } else {
      updateTimerDisplay(remaining, timerText);
    }
  }, 1000);
}

function updateTimerDisplay(remaining, element) {
  if (!element) return;
  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;
  element.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function clearLockTimer() {
  if (lockTimerInterval) {
    clearInterval(lockTimerInterval);
    lockTimerInterval = null;
  }
  const banner = document.getElementById('seat-lock-banner');
  if (banner && selectedSeats.length === 0) {
    banner.style.display = 'none';
  }
}

// Update Sticky Summary Bar
function updateSummaryBar() {
  const countEl = document.getElementById('selected-count-val');
  const seatsListEl = document.getElementById('selected-seats-list');
  const fareEl = document.getElementById('selected-total-fare');
  const proceedBtn = document.getElementById('btn-proceed-booking');

  const count = selectedSeats.length;
  if (countEl) countEl.textContent = count;

  if (seatsListEl) {
    seatsListEl.textContent = count > 0 
      ? selectedSeats.map(s => `${currentCoach.coach_number}-${s.seat_number}`).join(', ')
      : 'None Selected';
  }

  if (fareEl && currentCoach) {
    const total = currentCoach.base_fare * count;
    fareEl.textContent = formatINR(total);
  }

  if (proceedBtn) {
    proceedBtn.disabled = count === 0;
  }
}

// AI Seat Recommendation Logic
function setupAIRecommenderControls() {
  const btn = document.getElementById('btn-run-ai-rec');
  if (btn) {
    btn.addEventListener('click', triggerAIRecommendations);
  }
}

async function triggerAIRecommendations() {
  const passengerType = document.getElementById('ai-passenger-type')?.value || 'general';
  const preference = document.getElementById('ai-berth-preference')?.value || 'WINDOW';
  const recBanner = document.getElementById('ai-rec-banner');
  const recText = document.getElementById('ai-rec-text');
  const countBadge = document.getElementById('ai-rec-eval-count');
  const allRecsBtnCount = document.getElementById('all-recs-count');

  const res = await fetchApi('/seats/recommend', {
    method: 'POST',
    body: JSON.stringify({
      train_id: trainId,
      coach_class: currentClassCode,
      coach_id: coachId,
      journey_date: journeyDate,
      passenger_type: passengerType,
      preference: preference,
      count: null // Retrieve full evaluated set
    })
  });

  if (res.success && res.data.recommendations) {
    allAiRecommendations = res.data.recommendations;
    
    // Highlight top recommendations for the CURRENT coach
    const curCoachRecs = allAiRecommendations.filter(r => String(r.coach_id) === String(coachId));
    const topCurCoachSeatIds = new Set(curCoachRecs.slice(0, 8).map(r => r.seat_id));

    currentSeats.forEach(s => {
      if (topCurCoachSeatIds.has(s.id)) {
        s.is_recommended = true;
        const matchingRec = curCoachRecs.find(r => r.seat_id === s.id);
        s.recommendation_reason = matchingRec?.explanation;
      } else {
        s.is_recommended = false;
      }
    });

    renderSeatMap();

    if (recBanner) {
      recBanner.style.display = 'flex';
      const best = res.data.top_match || allAiRecommendations[0];
      if (best && recText) {
        recText.innerHTML = `<strong>Top AI Match:</strong> Coach ${best.coach_number} - Seat ${best.seat_number} (${best.recommendation_score}% match) — ${best.explanation}`;
      }
      if (countBadge) {
        countBadge.textContent = `• Evaluated ${res.data.total_evaluated || allAiRecommendations.length} available berths in ${res.data.total_coaches || 1} coach(es)`;
      }
      if (allRecsBtnCount) {
        allRecsBtnCount.textContent = allAiRecommendations.length;
      }
    }
    showToast(`AI evaluated ${res.data.total_evaluated || allAiRecommendations.length} available berths across ${res.data.total_coaches || 1} coach(es).`, 'info', 'AI Recommender');
  }
}

// Open "View All AI Recommendations" Modal
function openAllRecommendationsModal() {
  const modal = document.getElementById('ai-recs-modal');
  const modalBody = document.getElementById('ai-recs-modal-body');
  const subtitle = document.getElementById('ai-modal-subtitle');
  if (!modal || !modalBody) return;

  const passengerType = document.getElementById('ai-passenger-type')?.value || 'general';
  const preference = document.getElementById('ai-berth-preference')?.value || 'WINDOW';

  if (subtitle) {
    const coachCount = allTrainCoaches.filter(c => c.coach_class === currentClassCode).length;
    subtitle.textContent = `Ranked recommendations across ${coachCount} coaches in ${currentClassCode} class • Profile: ${passengerType.toUpperCase()} • Preference: ${preference}`;
  }

  if (allAiRecommendations.length === 0) {
    modalBody.innerHTML = `
      <div class="state-box" style="padding: 2rem;">
        <i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-orange);"></i>
        <h3>No Available Seats Evaluated</h3>
        <p>No seats matching current filters are available. Try switching class or quota.</p>
      </div>
    `;
  } else {
    modalBody.innerHTML = allAiRecommendations.map((r, idx) => {
      const isCurrentCoach = String(r.coach_id) === String(coachId);
      const isSelected = selectedSeats.some(s => s.id === r.seat_id);

      let scoreBg = 'rgba(16, 185, 129, 0.12)';
      let scoreColor = '#059669';
      if (r.recommendation_score < 70) {
        scoreBg = 'rgba(59, 130, 246, 0.12)';
        scoreColor = '#2563eb';
      } else if (r.recommendation_score < 85) {
        scoreBg = 'rgba(121, 40, 202, 0.12)';
        scoreColor = '#7928ca';
      }

      const tagsHtml = (r.match_factors || []).map(tag => 
        `<span class="badge" style="background: #f1f5f9; color: #475569; font-size: 0.72rem; padding: 2px 8px;">${tag}</span>`
      ).join('');

      return `
        <div class="ai-rec-card" style="display: flex; align-items: center; justify-content: space-between; padding: 0.9rem 1.1rem; border: 1.5px solid ${isSelected ? 'var(--primary-navy)' : 'var(--border-light)'}; border-left: 5px solid ${scoreColor}; border-radius: var(--radius-md); margin-bottom: 0.75rem; background: ${isSelected ? '#f0fdf4' : (isCurrentCoach ? '#f8faff' : '#ffffff')}; gap: 1rem; transition: all 0.2s ease;">
          <div style="flex: 1;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 5px; flex-wrap: wrap;">
              <span class="badge" style="background: var(--primary-navy); color: white; font-weight: 700; font-size: 0.75rem;">#${idx + 1}</span>
              <strong style="font-size: 0.98rem; color: var(--primary-navy);">Coach ${r.coach_number} • Seat ${r.seat_number} (${r.seat_type.replace('_', ' ')})</strong>
              <span class="badge" style="background: ${scoreBg}; color: ${scoreColor}; font-weight: 700; font-size: 0.75rem;">${r.recommendation_score}% Match</span>
              ${isCurrentCoach ? '<span class="badge" style="background: rgba(19, 64, 116, 0.1); color: var(--primary-navy); font-size: 0.7rem;">Current Coach</span>' : ''}
              ${isSelected ? '<span class="badge" style="background: #dcfce7; color: #15803d; font-size: 0.7rem; font-weight: 700;">Locked by You</span>' : ''}
            </div>
            <p style="margin: 0 0 6px 0; font-size: 0.84rem; color: var(--text-secondary); line-height: 1.45;">
              ${r.explanation}
            </p>
            <div style="display: flex; gap: 0.35rem; flex-wrap: wrap;">
              ${tagsHtml}
            </div>
          </div>
          <div style="flex-shrink: 0;">
            <button class="btn btn-sm ${isSelected ? 'btn-outline' : 'btn-primary'}" 
                    style="font-size: 0.82rem; padding: 0.45rem 0.9rem; font-weight: 600;"
                    onclick="selectRecommendedSeat(${r.coach_id}, ${r.seat_id}, '${r.coach_number}', ${r.seat_number})">
              ${isSelected ? '<i class="fa-solid fa-check"></i> Selected' : '<i class="fa-solid fa-plus"></i> Select Seat'}
            </button>
          </div>
        </div>
      `;
    }).join('');
  }

  modal.style.display = 'flex';
  modal.classList.add('active');
}

function closeAllRecommendationsModal() {
  const modal = document.getElementById('ai-recs-modal');
  if (modal) {
    modal.classList.remove('active');
    modal.style.display = 'none';
  }
}

// Select a recommended seat from the modal (handles cross-coach switching seamlessly)
async function selectRecommendedSeat(targetCoachId, targetSeatId, targetCoachNum, targetSeatNum) {
  closeAllRecommendationsModal();

  // If the recommended seat is in another coach of this class, switch to that coach first
  if (String(targetCoachId) !== String(coachId)) {
    coachId = targetCoachId;
    updateCoachTabsActiveState();
    await loadCoachAndSeats();
  }

  // Find the seat in the active coach layout
  const seatNode = document.getElementById(`seat-node-${targetSeatId}`);
  await handleSeatClick(targetSeatId);

  if (seatNode) {
    seatNode.scrollIntoView({ behavior: 'smooth', block: 'center' });
    seatNode.classList.add('seat-selected');
    showToast(`Selected Seat ${targetSeatNum} in Coach ${targetCoachNum}.`, 'success', 'Berth Reserved');
  }
}

// Proceed to Booking Page
function proceedToBooking() {
  if (selectedSeats.length === 0) {
    showToast('Please select at least one seat to proceed.', 'warning');
    return;
  }

  const effFare = currentCoach.adjusted_fare || currentCoach.base_fare || (passedFare ? parseFloat(passedFare) : 0);
  // Save selected booking session in sessionStorage
  const bookingPayload = {
    train_id: currentCoach.train_id,
    train_number: currentCoach.train_number,
    train_name: currentCoach.train_name,
    coach_id: currentCoach.id,
    coach_number: currentCoach.coach_number,
    coach_class: currentCoach.coach_class,
    base_fare: effFare,
    from_station: fromStation,
    to_station: toStation,
    journey_date: journeyDate,
    quota_code: quotaCode,
    selected_seats: selectedSeats.map(s => ({
      seat_id: s.id,
      seat_number: s.seat_number,
      seat_type: s.seat_type
    }))
  };

  sessionStorage.setItem('current_booking_intent', JSON.stringify(bookingPayload));
  window.location.href = 'booking.html';
}
