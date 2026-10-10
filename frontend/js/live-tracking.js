/**
 * SMART RAILWAY - VERTICAL ROUTE TIMELINE & TELEMETRY CONTROLLER
 * Supports Scheduled Commercial Halts AND Operational Passing Stations
 * with real-time in-transit tracking and view filtering.
 */

let trackingInterval = null;
let currentTrainId = getQueryParam('train_id') || '1';
let currentFilter = 'all'; // 'all' (Two-Level: Halts + Clickable Sections) or 'halts' (Halts Only)
let expandedSectionId = null; // Stores currently expanded section ID (Accordion: only 1 open)
let lastTelemetryData = null;

// Global toggle for accordion sections between consecutive commercial halts
window.toggleSection = function(sectionId) {
  if (expandedSectionId === sectionId) {
    expandedSectionId = null; // Collapse if already open
  } else {
    expandedSectionId = sectionId; // Open this section, automatically collapsing any other
  }
  if (lastTelemetryData) {
    renderRouteTimeline(lastTelemetryData);
  }
};

document.addEventListener('DOMContentLoaded', async () => {
  setupFilterButtons();
  await loadTrainSelector();
  startLiveTracking(currentTrainId);
});

// Setup filter toggle buttons (Two-Level vs. Scheduled Halts Only)
function setupFilterButtons() {
  const allBtn = document.getElementById('filter-all-btn');
  const haltsBtn = document.getElementById('filter-halts-btn');

  if (allBtn && haltsBtn) {
    allBtn.textContent = 'All Sections (Two-Level)';
    haltsBtn.textContent = 'Scheduled Halts Only';

    allBtn.addEventListener('click', () => {
      currentFilter = 'all';
      allBtn.classList.add('active');
      haltsBtn.classList.remove('active');
      if (lastTelemetryData) renderRouteTimeline(lastTelemetryData);
    });

    haltsBtn.addEventListener('click', () => {
      currentFilter = 'halts';
      haltsBtn.classList.add('active');
      allBtn.classList.remove('active');
      if (lastTelemetryData) renderRouteTimeline(lastTelemetryData);
    });
  }
}

// Reset Telemetry Dashboard & Route Timeline upon switching trains
function resetTelemetryUI() {
  lastTelemetryData = null;
  expandedSectionId = null;

  const titleEl = document.getElementById('telemetry-train-title');
  if (titleEl) titleEl.textContent = 'Loading...';

  const routeEl = document.getElementById('telemetry-route');
  if (routeEl) routeEl.textContent = '--';

  const speedEl = document.getElementById('telemetry-speed');
  if (speedEl) speedEl.textContent = '-- km/h';

  const speedDescEl = document.getElementById('telemetry-speed-desc');
  if (speedDescEl) speedDescEl.textContent = 'Fetching telemetry...';

  const delayBadge = document.getElementById('telemetry-delay-badge');
  if (delayBadge) {
    delayBadge.textContent = 'Checking...';
    delayBadge.className = 'badge';
    delayBadge.style.background = '#e2e8f0';
    delayBadge.style.color = '#475569';
  }

  const delayDescEl = document.getElementById('telemetry-delay-desc');
  if (delayDescEl) delayDescEl.textContent = 'Contacting railway telemetry...';

  const nextStEl = document.getElementById('telemetry-next-station');
  if (nextStEl) nextStEl.textContent = '--';

  const etaEl = document.getElementById('telemetry-eta');
  if (etaEl) etaEl.textContent = 'ETA: --';

  const distEl = document.getElementById('telemetry-distance');
  if (distEl) distEl.textContent = '-- km';

  const progTextEl = document.getElementById('telemetry-progress-text');
  if (progTextEl) progTextEl.textContent = '0% • Updating route progress';

  const progFill = document.getElementById('route-progress-bar');
  if (progFill) progFill.style.width = '0%';

  const progPill = document.getElementById('timeline-progress-pill');
  if (progPill) progPill.textContent = 'Loading Route...';

  const subtitleEl = document.getElementById('timeline-subtitle');
  if (subtitleEl) subtitleEl.textContent = 'Retrieving station route and telemetry...';

  const container = document.getElementById('route-timeline-container');
  if (container) {
    container.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
        <i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary-blue); margin-bottom: 0.75rem; display: block;"></i>
        <h4 style="margin-bottom: 0.25rem;">Fetching Route & Telemetry</h4>
        <p style="font-size: 0.85rem;">Retrieving real-time positioning for selected train...</p>
      </div>
    `;
  }
}

// Load train options into dropdown
async function loadTrainSelector() {
  const res = await fetchApi('/trains');
  const selector = document.getElementById('select-tracking-train');
  if (res.success && res.data && selector) {
    selector.innerHTML = res.data.map(t => `
      <option value="${t.id}" ${t.id == currentTrainId ? 'selected' : ''}>
        ${t.train_number} - ${t.train_name} (${t.source_code} ➔ ${t.dest_code})
      </option>
    `).join('');

    selector.addEventListener('change', (e) => {
      currentTrainId = e.target.value;
      const newUrl = `${window.location.pathname}?train_id=${currentTrainId}`;
      window.history.replaceState({ path: newUrl }, '', newUrl);
      resetTelemetryUI();
      startLiveTracking(currentTrainId);
    });
  }
}

// Start Live Tracking Polling (every 3 seconds)
function startLiveTracking(trainId) {
  if (trackingInterval) clearInterval(trackingInterval);

  fetchTelemetry(trainId);
  trackingInterval = setInterval(() => {
    fetchTelemetry(trainId);
  }, 3000);
}

// Fetch Telemetry from Backend API
async function fetchTelemetry(trainId) {
  const res = await fetchApi(`/tracking/${trainId}`);
  if (!res.success || !res.data) {
    const container = document.getElementById('route-timeline-container');
    if (container) {
      container.innerHTML = `
        <div style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
          <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; color: var(--accent-red); margin-bottom: 0.5rem; display: block;"></i>
          <h3>Telemetry Unavailable</h3>
          <p>${res.message || 'Could not retrieve live tracking data for this train.'}</p>
        </div>
      `;
    }
    return;
  }

  lastTelemetryData = res.data;
  updateTelemetryCards(res.data);
  renderRouteTimeline(res.data);
}

// Update Top Dashboard Telemetry Cards
function updateTelemetryCards(data) {
  // Train & Route Card
  const titleEl = document.getElementById('telemetry-train-title');
  if (titleEl) titleEl.textContent = `${data.train_number} - ${data.train_name}`;

  const routeEl = document.getElementById('telemetry-route');
  if (routeEl) routeEl.textContent = `${data.source} ➔ ${data.destination}`;

  // Live Speedometer Card
  const speedEl = document.getElementById('telemetry-speed');
  if (speedEl) {
    if (data.status_code === 'NOT_RUNNING_TODAY') {
      speedEl.textContent = 'Not Running Today';
    } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
      speedEl.textContent = 'Not Started';
    } else if (data.status_code === 'COMPLETED') {
      speedEl.textContent = 'Journey Completed';
    } else if (data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      speedEl.textContent = 'Live data unavailable';
    } else if (data.status_code === 'RUNNING') {
      if (data.current_speed !== null && data.current_speed !== undefined) {
        speedEl.textContent = `${data.current_speed} km/h`;
      } else {
        speedEl.textContent = 'Speed unavailable';
      }
    } else if (data.current_speed !== null && data.current_speed !== undefined) {
      speedEl.textContent = `${data.current_speed} km/h`;
    } else {
      speedEl.textContent = data.speed_display || 'Speed unavailable';
    }
  }

  const speedDescEl = document.getElementById('telemetry-speed-desc');
  if (speedDescEl) {
    if (data.status_code === 'NOT_RUNNING_TODAY') {
      speedDescEl.textContent = 'Train not scheduled today';
    } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
      speedDescEl.textContent = data.status_message || 'Departure time has not arrived';
    } else if (data.status_code === 'COMPLETED') {
      speedDescEl.textContent = 'Journey finished at destination';
    } else if (data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      speedDescEl.textContent = 'Live telemetry signal unavailable';
    } else if (data.status_code === 'RUNNING') {
      if (data.current_speed !== null && data.current_speed !== undefined && data.current_speed > 0) {
        if (data.current_position && data.current_position.mode === 'BETWEEN_STATIONS') {
          speedDescEl.textContent = `Running between ${data.current_position.from_station} and ${data.current_position.to_station}`;
        } else if (data.current_position && data.current_position.mode === 'PASSING_POINT') {
          speedDescEl.textContent = data.current_position.status_text;
        } else {
          speedDescEl.textContent = 'Section Running Speed';
        }
      } else if (data.current_speed === 0.0) {
        speedDescEl.textContent = 'Station Stop / Signal Halt';
      } else {
        speedDescEl.textContent = 'Live speed not reported';
      }
    } else {
      speedDescEl.textContent = (data.current_speed > 0) ? 'Cruising Speed' : 'Station Stop / Terminus Reached';
    }
  }

  // Punctuality Card
  const delayBadge = document.getElementById('telemetry-delay-badge');
  if (delayBadge) {
    delayBadge.textContent = data.delay_status;
    if (data.status_code === 'NOT_RUNNING_TODAY') {
      delayBadge.className = 'badge';
      delayBadge.style.background = '#e2e8f0';
      delayBadge.style.color = '#475569';
    } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
      delayBadge.className = 'badge badge-available';
      delayBadge.style.background = '';
      delayBadge.style.color = '';
    } else if (data.status_code === 'COMPLETED') {
      delayBadge.className = 'badge badge-available';
      delayBadge.style.background = '';
      delayBadge.style.color = '';
    } else if (data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      delayBadge.className = 'badge';
      delayBadge.style.background = '#fffbeb';
      delayBadge.style.color = '#92400e';
    } else {
      delayBadge.className = data.delay_minutes > 0 ? 'badge badge-wl' : 'badge badge-available';
      delayBadge.style.background = '';
      delayBadge.style.color = '';
    }
  }

  const delayDescEl = document.getElementById('telemetry-delay-desc');
  if (delayDescEl) {
    if (data.status_code === 'NOT_RUNNING_TODAY') {
      delayDescEl.textContent = 'Not operating on current date';
    } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
      delayDescEl.textContent = 'Timetable schedule for today';
    } else if (data.status_code === 'COMPLETED') {
      delayDescEl.textContent = 'Final arrival completed';
    } else if (data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      delayDescEl.textContent = 'Live signal unavailable';
    } else {
      delayDescEl.textContent = 'Calculated vs. Section Timetable';
    }
  }

  // Next Station & ETA Card
  const nextStEl = document.getElementById('telemetry-next-station');
  if (nextStEl) {
    if (data.status_code === 'NOT_RUNNING_TODAY' || data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      nextStEl.textContent = data.next_station || 'Not Available';
    } else {
      nextStEl.textContent = data.next_station || '--';
    }
  }

  const etaEl = document.getElementById('telemetry-eta');
  if (etaEl) {
    if (data.status_code === 'NOT_RUNNING_TODAY' || data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      etaEl.textContent = 'ETA: Not Available';
    } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
      etaEl.textContent = data.eta || 'Scheduled';
    } else if (data.status_code === 'COMPLETED') {
      etaEl.textContent = 'Arrived';
    } else {
      etaEl.textContent = data.eta ? (data.eta.startsWith('ETA:') ? data.eta : `ETA: ${data.eta}`) : 'ETA: --';
    }
  }

  // Distance Covered Card
  const distEl = document.getElementById('telemetry-distance');
  if (distEl) {
    if (data.status_code === 'NOT_RUNNING_TODAY' || data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      distEl.textContent = 'Not Available';
    } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
      distEl.textContent = '0 km';
    } else if (data.status_code === 'COMPLETED') {
      distEl.textContent = `${data.total_distance_km} km`;
    } else {
      distEl.textContent = `${data.distance_travelled_km} km`;
    }
  }

  const progTextEl = document.getElementById('telemetry-progress-text');
  if (progTextEl) {
    if (data.status_code === 'NOT_RUNNING_TODAY') {
      progTextEl.textContent = '0% • Not running today';
    } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
      progTextEl.textContent = '0% • Journey not started';
    } else if (data.status_code === 'COMPLETED') {
      progTextEl.textContent = `100% of ${data.total_distance_km} km`;
    } else if (data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      progTextEl.textContent = 'Live telemetry unavailable';
    } else {
      progTextEl.textContent = `${data.percentage_completed}% of ${data.total_distance_km} km`;
    }
  }

  // Progress Bar
  const progFill = document.getElementById('route-progress-bar');
  if (progFill) {
    if (data.status_code === 'COMPLETED') {
      progFill.style.width = '100%';
    } else if (data.is_running && data.percentage_completed > 0) {
      progFill.style.width = `${data.percentage_completed}%`;
    } else {
      progFill.style.width = '0%';
    }
  }

  const progPill = document.getElementById('timeline-progress-pill');
  if (progPill) {
    if (data.status_code === 'NOT_RUNNING_TODAY') {
      progPill.textContent = 'Not Running Today';
    } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
      progPill.textContent = `0% Completed • Scheduled (${data.departure_time || '--'})`;
    } else if (data.status_code === 'COMPLETED') {
      progPill.textContent = '100% Completed (Journey Ended)';
    } else if (data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      progPill.textContent = 'Live Telemetry Unavailable';
    } else {
      progPill.textContent = `${data.percentage_completed}% Completed (${data.distance_travelled_km}/${data.total_distance_km} km)`;
    }
  }

  // Timeline Subtitle
  const subtitleEl = document.getElementById('timeline-subtitle');
  if (subtitleEl) {
    if (data.status_code === 'NOT_RUNNING_TODAY') {
      subtitleEl.textContent = `${data.total_halts || data.total_stops} Scheduled Halts • Route Timetable for ${data.train_name} [Not Running Today]`;
    } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
      subtitleEl.textContent = `${data.total_halts || data.total_stops} Scheduled Halts • Departs today at ${data.departure_time || '--'} IST`;
    } else if (data.status_code === 'COMPLETED') {
      subtitleEl.textContent = `${data.total_halts || data.total_stops} Scheduled Halts • Journey completed from ${data.source} to ${data.destination}`;
    } else if (data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      subtitleEl.textContent = `${data.total_halts || data.total_stops} Scheduled Halts • Complete Timetable (Live Telemetry Unavailable)`;
    } else {
      subtitleEl.textContent = `${data.total_halts || data.total_stops} Scheduled Halts • ${data.total_passing_points || 0} Passing Points • Section: ${data.previous_station} ➔ ${data.next_station}`;
    }
  }

  // Filter summary chip
  const filterChip = document.getElementById('filter-summary-chip');
  if (filterChip) {
    if (currentFilter === 'halts') {
      filterChip.innerHTML = `Showing <strong>${data.total_halts}</strong> Scheduled Commercial Halts Only`;
    } else {
      filterChip.innerHTML = `Level 1: <strong>${data.total_halts}</strong> Halts • Level 2: Click sections to expand <strong>${data.total_passing_points || 0}</strong> intermediate points`;
    }
  }
}

// Render Complete Ordered Vertical Railway Timeline with Two-Level Architecture
function renderRouteTimeline(data) {
  const container = document.getElementById('route-timeline-container');
  if (!container) return;

  const halts = data.halts || (data.stops ? data.stops.filter(s => s.is_scheduled_halt) : []);
  if (!halts || halts.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 2.5rem; color: var(--text-muted);">No halting station records available.</div>`;
    return;
  }

  // Informative Status Alert Banner at top of timeline
  let statusBannerHtml = '';
  if (data.status_code === 'NOT_RUNNING_TODAY') {
    statusBannerHtml = `
      <div class="route-status-alert not-running">
        <i class="fa-solid fa-calendar-xmark"></i>
        <div>
          <strong style="display: block; font-size: 1rem; color: #1e293b; margin-bottom: 2px;">Not Running Today</strong>
          <span>${data.status_message || 'This train is not scheduled to operate on the current date.'}</span>
          <div style="font-size: 0.8rem; margin-top: 3px; color: var(--text-muted);">
            Scheduled route timetable and commercial halts are displayed below for journey planning.
          </div>
        </div>
      </div>
    `;
  } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
    statusBannerHtml = `
      <div class="route-status-alert scheduled">
        <i class="fa-solid fa-clock"></i>
        <div>
          <strong style="display: block; font-size: 1rem; color: #1e40af; margin-bottom: 2px;">Journey Scheduled Today</strong>
          <span>${data.status_message || 'Train scheduled to depart today.'}</span>
          <div style="font-size: 0.8rem; margin-top: 3px; color: #2563eb;">
            Live telemetry and real-time station progression will activate once the train departs from its origin station.
          </div>
        </div>
      </div>
    `;
  } else if (data.status_code === 'COMPLETED') {
    statusBannerHtml = `
      <div class="route-status-alert completed">
        <i class="fa-solid fa-circle-check"></i>
        <div>
          <strong style="display: block; font-size: 1rem; color: #166534; margin-bottom: 2px;">Journey Completed</strong>
          <span>${data.status_message || 'Train has arrived at its final destination.'}</span>
          <div style="font-size: 0.8rem; margin-top: 3px; color: #15803d;">
            All commercial halts and intermediate waypoints have been completed for this journey.
          </div>
        </div>
      </div>
    `;
  } else if (data.status_code === 'LIVE_DATA_UNAVAILABLE') {
    statusBannerHtml = `
      <div class="route-status-alert unavailable">
        <i class="fa-solid fa-satellite-dish"></i>
        <div>
          <strong style="display: block; font-size: 1rem; color: #92400e; margin-bottom: 2px;">Live Telemetry Signal Unavailable</strong>
          <span>${data.status_message || 'Real-time GPS and speed telemetry could not be retrieved at this moment.'}</span>
          <div style="font-size: 0.8rem; margin-top: 3px; color: #b45309;">
            Displaying official scheduled route timetable without fabricated telemetry.
          </div>
        </div>
      </div>
    `;
  }

  // Retrieve or compute Level 2 Inter-Halt Sections
  let sections = data.sections;
  if (!sections || sections.length === 0) {
    sections = [];
    const allStops = data.stops || [];
    for (let k = 0; k < halts.length - 1; k++) {
      const hFrom = halts[k];
      const hTo = halts[k + 1];
      const secPts = allStops.filter(s => !s.is_scheduled_halt && (s.sequence ? (s.sequence > hFrom.sequence && s.sequence < hTo.sequence) : (s.distance_km > hFrom.distance_km && s.distance_km < hTo.distance_km)));
      const isCurSec = data.is_running && ((hFrom.sequence && data.current_stop_sequence)
        ? (data.current_stop_sequence >= hFrom.sequence && data.current_stop_sequence < hTo.sequence)
        : (data.distance_travelled_km >= hFrom.distance_km && data.distance_travelled_km < hTo.distance_km));
      sections.push({
        section_id: `sec-${k}-${k+1}`,
        section_index: k,
        from_station_code: hFrom.station_code,
        from_station_name: hFrom.station_name,
        to_station_code: hTo.station_code,
        to_station_name: hTo.station_name,
        section_title: `${hFrom.station_name} ➔ ${hTo.station_name}`,
        distance_km: Math.round((hTo.distance_km - hFrom.distance_km) * 10) / 10,
        intermediate_count: secPts.length,
        intermediate_points: secPts,
        is_current_section: isCurSec
      });
    }
  }

  let html = statusBannerHtml;

  halts.forEach((st, idx) => {
    const isCompleted = st.status === 'COMPLETED';
    const isCurrent = Boolean(st.is_current && data.is_running);
    const isUpcoming = st.status === 'UPCOMING';

    // Step classes
    let stepClass = 'timeline-step halt-step';
    if (isCompleted) stepClass += ' completed';
    if (isCurrent) stepClass += ' current';
    if (isUpcoming) stepClass += ' upcoming';

    // Node icon
    let nodeIcon = '';
    if (isCurrent) {
      nodeIcon = `<i class="fa-solid fa-train"></i>`;
    } else if (isCompleted) {
      nodeIcon = `<i class="fa-solid fa-check"></i>`;
    } else if (st.point_type === 'ORIGIN') {
      nodeIcon = `<i class="fa-solid fa-play"></i>`;
    } else if (st.point_type === 'DESTINATION') {
      nodeIcon = `<i class="fa-solid fa-flag-checkered"></i>`;
    } else {
      nodeIcon = `<span>${st.halt_sequence || (idx + 1)}</span>`;
    }

    // Type Badge
    let typeBadge = '';
    if (st.point_type === 'ORIGIN') {
      typeBadge = `<span class="badge" style="background: rgba(42, 157, 143, 0.15); color: #1b685f; font-weight: 700;"><i class="fa-solid fa-play"></i> 🟢 ORIGIN</span>`;
    } else if (st.point_type === 'DESTINATION') {
      typeBadge = `<span class="badge" style="background: #fef3c7; color: #92400e; font-weight: 700;"><i class="fa-solid fa-flag-checkered"></i> 🏁 DESTINATION</span>`;
    } else {
      typeBadge = `<span class="badge" style="background: rgba(42, 157, 143, 0.15); color: #1b685f; font-weight: 700;"><i class="fa-solid fa-circle-dot"></i> 🟢 HALT (${st.halt_minutes} min)</span>`;
    }

    // Status Badge
    let statusBadge = '';
    if (isCompleted) {
      statusBadge = `<span class="badge" style="background: rgba(42, 157, 143, 0.12); color: #1b685f;"><i class="fa-solid fa-check"></i> ${st.point_type === 'DESTINATION' ? 'Arrived' : 'Departed'}</span>`;
    } else if (isCurrent) {
      statusBadge = `<span class="badge" style="background: rgba(247, 127, 0, 0.15); color: #c2410c; font-weight: 800;"><i class="fa-solid fa-circle-dot fa-fade"></i> AT STATION</span>`;
    } else if (data.status_code === 'NOT_RUNNING_TODAY') {
      statusBadge = `<span class="badge" style="background: rgba(100, 116, 139, 0.1); color: #64748b;"><i class="fa-regular fa-calendar-xmark"></i> Not Running Today</span>`;
    } else if (data.status_code === 'SCHEDULED_NOT_STARTED') {
      statusBadge = `<span class="badge" style="background: rgba(100, 116, 139, 0.1); color: #64748b;"><i class="fa-regular fa-clock"></i> Scheduled Stop</span>`;
    } else if (data.status_code === 'LIVE_DATA_UNAVAILABLE') {
      statusBadge = `<span class="badge" style="background: rgba(100, 116, 139, 0.1); color: #64748b;"><i class="fa-regular fa-clock"></i> Timetable Stop</span>`;
    } else {
      statusBadge = `<span class="badge" style="background: rgba(100, 116, 139, 0.1); color: #64748b;">Upcoming Halt</span>`;
    }

    // Special banner if train is actively confirmed stopped at this halt
    let haltCurrentBanner = '';
    if (isCurrent) {
      haltCurrentBanner = `
        <div class="current-train-special-banner">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 0.95rem; margin-bottom: 2px; text-transform: uppercase;">
              <span>🟠</span> CURRENT TRAIN
            </div>
            <div style="font-size: 1.25rem; font-weight: 800;">
              ${data.train_number} — ${data.train_name}
            </div>
            <div style="font-size: 0.9rem; margin-top: 3px; font-weight: 600;">
              <i class="fa-solid fa-location-dot"></i> At Station Stop: <strong>${st.station_name} (${st.station_code})</strong>
            </div>
          </div>
          <div style="display: flex; gap: 1rem; align-items: center; background: rgba(0,0,0,0.18); padding: 8px 14px; border-radius: 8px;">
            <div>
              <div style="font-size: 0.7rem; text-transform: uppercase; opacity: 0.85; font-weight: 600;">Status</div>
              <strong style="font-size: 1.05rem;">Station Halt</strong>
            </div>
            <div style="border-left: 1px solid rgba(255,255,255,0.25); padding-left: 0.75rem;">
              <div style="font-size: 0.7rem; text-transform: uppercase; opacity: 0.85; font-weight: 600;">Next Station</div>
              <strong style="font-size: 0.95rem;">${data.next_station}</strong>
            </div>
          </div>
        </div>
      `;
    }

    const arrDisplay = st.arrival_time === 'START' ? 'Origin (Starts)' : (st.arrival_time || '--:--');
    const depDisplay = st.departure_time === 'END' ? 'Terminus (Ends)' : (st.departure_time || '--:--');

    // LEVEL 1: Render Scheduled Commercial Halt Card
    html += `
      <div class="${stepClass}">
        <div class="timeline-node-icon">
          ${nodeIcon}
        </div>
        <div class="timeline-card-content">
          ${haltCurrentBanner}
          <div class="timeline-station-header">
            <div>
              <div class="timeline-station-title">
                <span class="timeline-seq-chip">#${st.halt_sequence || (idx + 1)}</span>
                <span>${st.station_name}</span>
                <span class="station-code-badge" style="font-size: 0.8rem;">${st.station_code}</span>
              </div>
              <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">
                ${st.city ? st.city : ''}${st.state ? `, ${st.state}` : ''} • Distance from origin: <strong>${st.distance_km} km</strong>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
              ${typeBadge}
              ${statusBadge}
            </div>
          </div>

          <div class="timeline-times-grid">
            <div class="time-slot">
              <label><i class="fa-regular fa-clock" style="color: var(--primary-blue);"></i> Scheduled Arrival</label>
              <strong>${arrDisplay}</strong>
            </div>
            <div class="time-slot">
              <label><i class="fa-solid fa-clock" style="color: var(--accent-saffron);"></i> Scheduled Departure</label>
              <strong>${depDisplay}</strong>
            </div>
            <div class="time-slot">
              <label><i class="fa-solid fa-hourglass-half" style="color: var(--accent-green);"></i> Stop Type / Halt</label>
              <strong style="font-size: 0.95rem; color: var(--accent-green);">${st.halt_desc}</strong>
            </div>
            <div class="time-slot">
              <label><i class="fa-solid fa-road" style="color: var(--text-muted);"></i> Cumulative Distance</label>
              <strong>${st.distance_km} km</strong>
            </div>
          </div>
        </div>
      </div>
    `;

    // LEVEL 2: Between Halt k and Halt k+1, render the Route Section Accordion
    if (idx < halts.length - 1 && currentFilter !== 'halts') {
      const sec = sections[idx];
      if (sec) {
        const isExpanded = (expandedSectionId === sec.section_id);
        const isCurrentSec = Boolean(sec.is_current_section && data.is_running);

        let curSectionBadge = '';
        if (isCurrentSec) {
          curSectionBadge = `
            <span class="badge" style="background: #f77f00; color: white; font-weight: 700; font-size: 0.78rem; padding: 4px 8px;">
              <i class="fa-solid fa-train fa-fade"></i> Train is currently running in this section
            </span>
          `;
        }

        let actionPillHtml = '';
        if (sec.intermediate_count > 0) {
          actionPillHtml = isExpanded
            ? `<span class="section-action-pill"><i class="fa-solid fa-chevron-up"></i> Hide intermediate points</span>`
            : `<span class="section-action-pill"><i class="fa-solid fa-chevron-down"></i> Click to view ${sec.intermediate_count} intermediate points</span>`;
        } else {
          actionPillHtml = `<span class="section-action-pill" style="opacity: 0.7; cursor: default;"><i class="fa-solid fa-arrows-left-right"></i> Direct section</span>`;
        }

        // Render intermediate points inside the accordion drawer
        let drawerHtml = '';
        if (sec.intermediate_count > 0) {
          const itemsHtml = sec.intermediate_points.map(pt => {
            const isPtCompleted = pt.status === 'COMPLETED' && (data.is_running || data.status_code === 'COMPLETED');
            const isPtCurrent = Boolean(pt.is_current && data.is_running);

            let ptClass = 'intermediate-item';
            let ptProximityBadge = '';
            if (isPtCompleted) {
              ptClass += ' completed';
              ptProximityBadge = `<span class="badge" style="background: rgba(42, 157, 143, 0.12); color: #1b685f; font-size: 0.75rem;"><i class="fa-solid fa-check"></i> Passed</span>`;
            } else if (isPtCurrent) {
              ptClass += ' current';
              ptProximityBadge = `<span class="badge" style="background: rgba(247, 127, 0, 0.18); color: #c2410c; font-weight: 800; font-size: 0.75rem;"><i class="fa-solid fa-train fa-fade"></i> PASSING NOW</span>`;
            } else {
              ptClass += ' upcoming';
              ptProximityBadge = `<span class="badge" style="background: rgba(100, 116, 139, 0.1); color: #64748b; font-size: 0.75rem;"><i class="fa-regular fa-clock"></i> Timetable Waypoint</span>`;
            }

            return `
              <div class="${ptClass}">
                <div style="display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;">
                  <div>
                    <span style="font-weight: 700; color: var(--primary-navy); font-size: 0.95rem;">${pt.station_name}</span>
                    <span class="station-code-badge" style="font-size: 0.75rem; background: #f1f5f9; color: #475569; margin-left: 4px;">${pt.station_code}</span>
                  </div>
                  <span class="badge" style="background: #f1f5f9; color: #475569; font-size: 0.72rem; border: 1px solid #cbd5e1;">
                    <i class="fa-solid fa-ban"></i> No Halt / Pass-through
                  </span>
                  ${ptProximityBadge}
                </div>

                <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;">
                  <div class="passing-time-badge ${pt.is_estimated ? 'estimated' : ''}">
                    <i class="fa-regular fa-clock"></i>
                    <strong>${pt.passing_label}</strong>
                  </div>
                  <span style="font-size: 0.8rem; color: var(--text-muted);">
                    Distance from origin: <strong style="color: var(--primary-navy);">${pt.distance_km} km</strong>
                  </span>
                </div>
              </div>
            `;
          }).join('');

          drawerHtml = `
            <div class="section-drawer">
              <div class="drawer-header">
                <span class="drawer-title">
                  <i class="fa-solid fa-train-subway" style="color: var(--accent-saffron);"></i> Intermediate Non-Stopping Points (${sec.intermediate_count})
                </span>
                <span style="font-size: 0.78rem; color: var(--text-muted);">
                  Points train passes without scheduled commercial halt
                </span>
              </div>
              <div class="intermediate-list">
                ${itemsHtml}
              </div>
            </div>
          `;
        }

        let secSpeedChip = '';
        if (isCurrentSec) {
          if (data.current_speed !== null && data.current_speed !== undefined) {
            if (data.current_speed > 0) {
              secSpeedChip = `<span>•</span><span style="color: #c2410c; font-weight: 700;"><i class="fa-solid fa-gauge-high"></i> Speed: ${data.current_speed} km/h</span>`;
            } else if (data.current_speed === 0) {
              secSpeedChip = `<span>•</span><span style="color: #c2410c; font-weight: 700;"><i class="fa-solid fa-pause"></i> Halted at Station (0 km/h)</span>`;
            }
          } else {
            secSpeedChip = `<span>•</span><span style="color: #b45309; font-weight: 600;"><i class="fa-solid fa-gauge-high"></i> Speed unavailable</span>`;
          }
        }

        html += `
          <div class="timeline-section-connector ${isCurrentSec ? 'current' : ''}">
            <div class="section-node-dot" title="Intermediate Route Section">
              <i class="fa-solid ${isCurrentSec ? 'fa-train' : 'fa-arrows-up-down'}"></i>
            </div>
            <div class="section-accordion-card ${isCurrentSec ? 'current-section' : ''} ${isExpanded ? 'expanded' : ''}" id="card-${sec.section_id}">
              <button type="button" class="section-trigger-btn" onclick="toggleSection('${sec.section_id}')" aria-expanded="${isExpanded}">
                <div class="section-title-group">
                  <div class="section-leg-title">
                    <i class="fa-solid fa-route" style="color: ${isCurrentSec ? '#f77f00' : 'var(--primary-blue)'};"></i>
                    <span>[ ${sec.from_station_name} → ${sec.to_station_name} ]</span>
                    ${curSectionBadge}
                  </div>
                  <div class="section-meta-chips">
                    <span><i class="fa-solid fa-road"></i> ${sec.distance_km} km section</span>
                    <span>•</span>
                    <span><i class="fa-solid fa-map-pin"></i> ${sec.intermediate_count} intermediate railway points</span>
                    ${secSpeedChip}
                  </div>
                </div>
                <div>
                  ${actionPillHtml}
                </div>
              </button>
              ${drawerHtml}
            </div>
          </div>
        `;
      }
    }
  });

  container.innerHTML = html;
}


window.addEventListener('beforeunload', () => {
  if (trackingInterval) clearInterval(trackingInterval);
});
