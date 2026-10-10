/**
 * SMART RAILWAY - ADMIN ANALYTICS & CHART.JS CONTROLLER
 */

let dailyBookingsChart = null;
let classOccupancyChart = null;
let quotaUsageChart = null;
let delayDistChart = null;

document.addEventListener('DOMContentLoaded', async () => {
  // Check admin authorization
  const user = getCurrentUser();
  if (!user || user.role !== 'ADMIN') {
    // Show toast and notify, but still allow demo viewing
    showToast('Viewing Dashboard in Demo Mode. Log in as admin@railway.gov.in for full control.', 'info', 'Demo Mode');
  }

  setupDashboardTabs();
  setupTrainModal();
  await loadAdminStats();
  await loadAdminTables();
});

// Load KPI statistics & Chart data
async function loadAdminStats() {
  const res = await fetchApi('/admin/stats');
  if (!res.success || !res.data) return;

  const kpis = res.data.kpis;
  const charts = res.data.charts;

  // Render KPI values
  document.getElementById('kpi-users-val').textContent = (kpis.total_users || 0).toLocaleString();
  document.getElementById('kpi-trains-val').textContent = (kpis.active_trains || 0).toLocaleString();
  document.getElementById('kpi-bookings-val').textContent = (kpis.total_bookings || 0).toLocaleString();
  document.getElementById('kpi-revenue-val').textContent = formatINR(kpis.total_revenue || 0);
  document.getElementById('kpi-occupancy-val').textContent = `${kpis.average_occupancy_pct}%`;
  document.getElementById('kpi-emergency-val').textContent = (kpis.emergency_requests || 0).toLocaleString();

  // Render Charts using Chart.js
  renderDailyBookingsChart(charts.daily_bookings);
  renderClassOccupancyChart(charts.class_occupancy);
  renderQuotaUsageChart(charts.quota_usage);
  renderDelayDistributionChart(charts.delay_distribution);
}

// 1. Daily Bookings Trend (Line & Area)
function renderDailyBookingsChart(data) {
  const ctx = document.getElementById('chart-daily-bookings')?.getContext('2d');
  if (!ctx || !data) return;

  if (dailyBookingsChart) dailyBookingsChart.destroy();

  dailyBookingsChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.date),
      datasets: [
        {
          label: 'Bookings Volume',
          data: data.map(d => d.count),
          borderColor: '#134074',
          backgroundColor: 'rgba(19, 64, 116, 0.08)',
          fill: true,
          tension: 0.35,
          borderWidth: 3,
          pointRadius: 4,
          pointHoverRadius: 6
        },
        {
          label: 'Revenue (₹ Hundreds)',
          data: data.map(d => d.revenue / 100),
          borderColor: '#f77f00',
          backgroundColor: 'transparent',
          borderDash: [5, 5],
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: { mode: 'index', intersect: false }
      },
      scales: {
        y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false } }
      }
    }
  });
}

// 2. Class Occupancy (Bar)
function renderClassOccupancyChart(data) {
  const ctx = document.getElementById('chart-class-occupancy')?.getContext('2d');
  if (!ctx || !data) return;

  if (classOccupancyChart) classOccupancyChart.destroy();

  classOccupancyChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.class),
      datasets: [{
        label: 'Occupancy Rate (%)',
        data: data.map(d => d.percentage),
        backgroundColor: ['#0b2545', '#134074', '#1d5fa8', '#2a9d8f', '#ee6c4d'],
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { max: 100, beginAtZero: true, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false } }
      }
    }
  });
}

// 3. Quota Usage Distribution (Doughnut)
function renderQuotaUsageChart(data) {
  const ctx = document.getElementById('chart-quota-usage')?.getContext('2d');
  if (!ctx || !data) return;

  if (quotaUsageChart) quotaUsageChart.destroy();

  quotaUsageChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.quota),
      datasets: [{
        data: data.map(d => d.share),
        backgroundColor: ['#0b2545', '#ee6c4d', '#2a9d8f', '#fcbf49', '#8b5cf6'],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
      cutout: '68%'
    }
  });
}

// 4. Delay Distribution (Bar Histogram)
function renderDelayDistributionChart(data) {
  const ctx = document.getElementById('chart-delay-distribution')?.getContext('2d');
  if (!ctx || !data) return;

  if (delayDistChart) delayDistChart.destroy();

  delayDistChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.range),
      datasets: [{
        label: 'Trains Percentage (%)',
        data: data.map(d => d.count),
        backgroundColor: ['#2a9d8f', '#fcbf49', '#f77f00', '#ee6c4d', '#e63946'],
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false } }
      }
    }
  });
}

// Load Tables (Bookings, Trains, Users, Emergencies)
async function loadAdminTables() {
  loadBookingsTable();
  loadTrainsTable();
  loadUsersTable();
  loadEmergenciesTable();
  loadCleaningRequestsTable();
  loadFoodOrdersTable();
  loadTteRequestsTable();
  loadLuggageRequestsTable();
}

async function loadBookingsTable() {
  const tbody = document.getElementById('admin-bookings-tbody');
  if (!tbody) return;

  const res = await fetchApi('/admin/bookings?limit=15');
  if (res.success && res.data) {
    tbody.innerHTML = res.data.map(b => `
      <tr>
        <td><strong>${b.pnr}</strong></td>
        <td>${b.user_name || 'Passenger'}</td>
        <td>${b.train_number} - ${b.train_name}</td>
        <td>${b.journey_date}</td>
        <td>${b.coach_number} (${b.coach_class})</td>
        <td><strong>${formatINR(b.total_fare)}</strong></td>
        <td>
          <span class="badge ${b.status === 'CONFIRMED' ? 'badge-confirmed' : (b.status === 'CANCELLED' ? 'badge-cancelled' : 'badge-wl')}">
            ${b.status}
          </span>
        </td>
      </tr>
    `).join('');
  }
}

async function loadTrainsTable() {
  const tbody = document.getElementById('admin-trains-tbody');
  if (!tbody) return;

  const res = await fetchApi('/trains');
  if (res.success && res.data) {
    tbody.innerHTML = res.data.map(t => `
      <tr>
        <td><strong>${t.train_number}</strong></td>
        <td>${t.train_name}</td>
        <td>${t.source_code} ➔ ${t.dest_code}</td>
        <td>${t.departure_time} - ${t.arrival_time}</td>
        <td>${t.duration}</td>
        <td>${t.running_days}</td>
        <td>
          <button onclick="deactivateTrain(${t.id})" class="btn btn-sm btn-outline" style="color: var(--accent-red); border-color: var(--border-light);">
            <i class="fa-solid fa-trash"></i>
          </button>
        </td>
      </tr>
    `).join('');
  }
}

async function loadUsersTable() {
  const tbody = document.getElementById('admin-users-tbody');
  if (!tbody) return;

  const res = await fetchApi('/admin/users');
  if (res.success && res.data) {
    tbody.innerHTML = res.data.map(u => `
      <tr>
        <td>#${u.id}</td>
        <td><strong>${u.name}</strong></td>
        <td>${u.email}</td>
        <td>${u.phone}</td>
        <td><span class="badge ${u.role === 'ADMIN' ? 'badge-ai' : 'badge-available'}">${u.role}</span></td>
        <td>${u.created_at || 'Recent'}</td>
      </tr>
    `).join('');
  }
}

async function loadEmergenciesTable() {
  const tbody = document.getElementById('admin-emergencies-tbody');
  if (!tbody) return;

  const res = await fetchApi('/admin/emergencies');
  if (res.success && res.data) {
    tbody.innerHTML = res.data.map(e => `
      <tr>
        <td><strong>${e.incident_id}</strong></td>
        <td><span class="badge badge-cancelled">${e.emergency_type}</span></td>
        <td>Train ${e.train_number} (${e.coach}-${e.seat})</td>
        <td>${e.user_name} (${e.user_phone})</td>
        <td>${e.status}</td>
        <td>
          ${e.status !== 'RESOLVED' ? `
            <button onclick="resolveEmergency('${e.incident_id}')" class="btn btn-sm btn-primary">
              <i class="fa-solid fa-check"></i> Resolve
            </button>
          ` : '<span style="color: var(--accent-green); font-weight: 600;">Resolved</span>'}
        </td>
      </tr>
    `).join('');
  }
}

async function loadCleaningRequestsTable() {
  const tbody = document.getElementById('admin-cleaning-tbody');
  if (!tbody) return;

  const res = await fetchApi('/emergency/cleaning');
  if (res.success && res.data) {
    if (res.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No cleaning requests logged yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.data.map(c => {
      const statusBadge = c.status === 'RESOLVED' ? 'badge-confirmed' :
                          (c.status === 'CANCELLED' ? 'badge-cancelled' :
                          (c.status === 'CLEANING IN PROGRESS' ? 'badge-ai' :
                          (c.status === 'ASSIGNED' ? 'badge-available' : 'badge-wl')));

      return `
        <tr>
          <td><strong>${c.request_id}</strong></td>
          <td>Train ${c.train_number} (${c.coach_number})</td>
          <td>${c.seat_number ? c.seat_number : '<span style="color: var(--text-muted);">-</span>'}</td>
          <td><strong style="color: #2a9d8f;">${c.issue_type}</strong></td>
          <td>${c.passenger_name} (${c.contact_mobile})</td>
          <td>${c.created_at || 'Recent'}</td>
          <td><span class="badge ${statusBadge}">${c.status}</span></td>
          <td>
            <select onchange="updateCleaningStatus('${c.request_id}', this.value)" class="form-control" style="font-size: 0.85rem; padding: 0.35rem 0.6rem; width: auto; display: inline-block;">
              <option value="PENDING" ${c.status === 'PENDING' ? 'selected' : ''}>PENDING</option>
              <option value="ASSIGNED" ${c.status === 'ASSIGNED' ? 'selected' : ''}>ASSIGNED</option>
              <option value="CLEANING IN PROGRESS" ${c.status === 'CLEANING IN PROGRESS' ? 'selected' : ''}>CLEANING IN PROGRESS</option>
              <option value="RESOLVED" ${c.status === 'RESOLVED' ? 'selected' : ''}>RESOLVED</option>
              <option value="CANCELLED" ${c.status === 'CANCELLED' ? 'selected' : ''}>CANCELLED</option>
            </select>
          </td>
        </tr>
      `;
    }).join('');
  }
}

async function updateCleaningStatus(requestId, newStatus) {
  const res = await fetchApi(`/emergency/cleaning/${requestId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: newStatus })
  });
  if (res.success) {
    showToast(`Request ${requestId} status updated to ${newStatus}.`, 'success');
    loadCleaningRequestsTable();
  } else {
    showToast(res.message || 'Failed to update cleaning status', 'error');
    loadCleaningRequestsTable();
  }
}

async function loadFoodOrdersTable() {
  const tbody = document.getElementById('admin-food-orders-tbody');
  if (!tbody) return;

  const res = await fetchApi('/admin/food-orders');
  if (res.success && res.orders) {
    if (res.orders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No food orders placed yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.orders.map(o => {
      const statusBadge = o.status === 'DELIVERED_TO_PASSENGER' ? 'badge-confirmed' :
                          (o.status === 'CANCELLED' ? 'badge-cancelled' :
                          (o.status === 'OUT_FOR_DELIVERY' || o.status === 'DELIVERED_AT_STATION' ? 'badge-ai' :
                          (o.status === 'PREPARING' || o.status === 'READY' ? 'badge-available' : 'badge-wl')));

      const stages = [
        'ORDER_PLACED', 'CONFIRMED', 'PREPARING', 'READY',
        'OUT_FOR_DELIVERY', 'DELIVERED_AT_STATION', 'DELIVERED_TO_PASSENGER', 'CANCELLED'
      ];

      const optionsHtml = stages.map(st => `
        <option value="${st}" ${o.status === st ? 'selected' : ''}>${st.replace(/_/g, ' ')}</option>
      `).join('');

      return `
        <tr>
          <td><strong style="color: var(--primary-navy);">${o.order_number}</strong></td>
          <td>${o.passenger_name} <br><small style="color: var(--text-muted);">${o.passenger_phone || ''}</small></td>
          <td>Train ${o.train_number} <br><small style="color: var(--text-secondary);">Coach ${o.coach}, Berth ${o.seat_number}</small></td>
          <td>${o.station_name || o.station_code || 'Halt'}</td>
          <td><strong>${o.restaurant_name || '-'}</strong></td>
          <td><strong style="color: var(--accent-saffron);">${formatINR(o.total_amount)}</strong></td>
          <td><span class="badge ${statusBadge}">${(o.status || 'ORDER_PLACED').replace(/_/g, ' ')}</span></td>
          <td>
            <select onchange="updateFoodOrderStatus('${o.order_number}', this.value)" class="form-control" style="font-size: 0.85rem; padding: 0.35rem 0.5rem; width: auto; display: inline-block;">
              ${optionsHtml}
            </select>
          </td>
        </tr>
      `;
    }).join('');
  }
}

async function updateFoodOrderStatus(orderIdOrNumber, newStatus) {
  const res = await fetchApi(`/admin/food-orders/${orderIdOrNumber}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status: newStatus })
  });
  if (res.success) {
    showToast(`Order ${orderIdOrNumber} status updated to ${newStatus.replace(/_/g, ' ')}.`, 'success');
    loadFoodOrdersTable();
  } else {
    showToast(res.message || 'Failed to update order status.', 'error');
    loadFoodOrdersTable();
  }
}

async function loadTteRequestsTable() {
  const tbody = document.getElementById('admin-tte-tbody');
  if (!tbody) return;

  const res = await fetchApi('/emergency/tte?limit=50');
  if (res.success && res.data) {
    if (res.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;">No TTE assistance requests logged yet.</td></tr>`;
      return;
    }

    const statuses = ['Pending', 'Submitted', 'Resolved', 'Cancelled'];

    tbody.innerHTML = res.data.map(req => {
      const statusBadge = req.status === 'Resolved' ? 'badge-confirmed' :
                          (req.status === 'Cancelled' ? 'badge-cancelled' :
                          (req.status === 'Submitted' ? 'badge-ai' : 'badge-wl'));

      const optionsHtml = statuses.map(st => `
        <option value="${st}" ${req.status === st ? 'selected' : ''}>${st}</option>
      `).join('');

      return `
        <tr>
          <td><strong style="color: var(--primary-navy);">${req.request_id}</strong></td>
          <td>Train ${req.train_number} <br><small style="color: var(--text-muted);">${req.train_name || ''} &bull; ${req.journey_date}</small></td>
          <td>${req.coach || '-'}${req.berth ? ' / ' + req.berth : ''}</td>
          <td>${req.pnr || '<span style="color: var(--text-muted);">-</span>'}</td>
          <td><strong style="color: var(--accent-saffron, #f77f00);">${req.assistance_type}</strong></td>
          <td><span title="${req.description}" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; max-width: 260px;">${req.description}</span></td>
          <td>${req.created_at || 'Recent'}</td>
          <td><span class="badge ${statusBadge}">${req.status}</span></td>
          <td>
            <select onchange="updateTteRequestStatus('${req.request_id}', this.value)" class="form-control" style="font-size: 0.85rem; padding: 0.35rem 0.5rem; width: auto; display: inline-block;">
              ${optionsHtml}
            </select>
          </td>
        </tr>
      `;
    }).join('');
  }
}

async function updateTteRequestStatus(requestId, newStatus) {
  const res = await fetchApi(`/emergency/tte/${requestId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: newStatus })
  });
  if (res.success) {
    showToast(`Request ${requestId} status updated to ${newStatus}.`, 'success');
    loadTteRequestsTable();
  } else {
    showToast(res.message || 'Failed to update request status.', 'error');
    loadTteRequestsTable();
  }
}

async function loadLuggageRequestsTable() {
  const tbody = document.getElementById('admin-luggage-tbody');
  if (!tbody) return;

  const res = await fetchApi('/emergency/luggage?limit=50');
  if (res.success && res.data) {
    if (res.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;">No left luggage requests logged yet.</td></tr>`;
      return;
    }

    const statuses = ['Submitted', 'Under Investigation', 'Found', 'Returned', 'Closed', 'Cancelled'];

    tbody.innerHTML = res.data.map(req => {
      const statusBadge = req.status === 'Found' || req.status === 'Returned' ? 'badge-confirmed' :
                          (req.status === 'Closed' || req.status === 'Cancelled' ? 'badge-cancelled' :
                          (req.status === 'Under Investigation' ? 'badge-available' : 'badge-ai'));

      const optionsHtml = statuses.map(st => `
        <option value="${st}" ${req.status === st ? 'selected' : ''}>${st}</option>
      `).join('');

      return `
        <tr>
          <td><strong style="color: var(--primary-navy);">${req.request_id}</strong></td>
          <td>Train ${req.train_number} <br><small style="color: var(--text-muted);">${req.train_name || ''} &bull; ${req.journey_date}</small></td>
          <td>Coach ${req.coach} / Seat ${req.seat}</td>
          <td><strong>${req.deboarding_station}</strong> ${req.boarding_station ? `<br><small style="color: var(--text-muted);">From ${req.boarding_station}</small>` : ''}</td>
          <td>
            <strong style="color: #2563eb;">${req.luggage_description}</strong>
            ${req.luggage_contents ? `<br><small style="color: var(--text-muted);">${req.luggage_contents}</small>` : ''}
          </td>
          <td>${req.passenger_mobile} ${req.pnr ? `<br><small style="color: var(--text-muted);">PNR: ${req.pnr}</small>` : ''}</td>
          <td>${req.created_at || 'Recent'}</td>
          <td><span class="badge ${statusBadge}">${req.status}</span></td>
          <td>
            <select onchange="updateLuggageRequestStatus('${req.request_id}', this.value)" class="form-control" style="font-size: 0.85rem; padding: 0.35rem 0.5rem; width: auto; display: inline-block;">
              ${optionsHtml}
            </select>
          </td>
        </tr>
      `;
    }).join('');
  }
}

async function updateLuggageRequestStatus(requestId, newStatus) {
  const res = await fetchApi(`/emergency/luggage/${requestId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: newStatus })
  });
  if (res.success) {
    showToast(`Left luggage request ${requestId} status updated to ${newStatus}.`, 'success');
    loadLuggageRequestsTable();
  } else {
    showToast(res.message || 'Failed to update request status.', 'error');
    loadLuggageRequestsTable();
  }
}

async function resolveEmergency(incidentId) {
  const res = await fetchApi(`/admin/emergencies/${incidentId}`, {
    method: 'PUT',
    body: JSON.stringify({ status: 'RESOLVED', response_note: 'Resolved by RPF Station Master.' })
  });
  if (res.success) {
    showToast(`Incident ${incidentId} marked as RESOLVED.`, 'success');
    loadEmergenciesTable();
  }
}

async function deactivateTrain(trainId) {
  if (!confirm(`Are you sure you want to deactivate Train ID ${trainId}?`)) return;
  const res = await fetchApi(`/admin/trains/${trainId}`, { method: 'DELETE' });
  if (res.success) {
    showToast(`Train ${trainId} removed.`, 'info');
    loadTrainsTable();
  }
}

function setupDashboardTabs() {
  document.querySelectorAll('.admin-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.admin-tab-pane').forEach(p => p.style.display = 'none');
      tab.classList.add('active');
      const targetId = tab.getAttribute('data-target');
      const pane = document.getElementById(targetId);
      if (pane) pane.style.display = 'block';
    });
  });
}

function setupTrainModal() {
  const addBtn = document.getElementById('btn-open-add-train-modal');
  const modal = document.getElementById('add-train-modal');
  const form = document.getElementById('add-train-form');

  if (addBtn && modal) {
    addBtn.addEventListener('click', () => modal.classList.add('active'));
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        train_number: document.getElementById('new-train-number').value.trim(),
        train_name: document.getElementById('new-train-name').value.trim(),
        source_station_id: document.getElementById('new-train-src').value,
        dest_station_id: document.getElementById('new-train-dst').value,
        departure_time: document.getElementById('new-train-dep').value,
        arrival_time: document.getElementById('new-train-arr').value,
        duration: document.getElementById('new-train-duration').value,
        running_days: document.getElementById('new-train-days').value,
        train_type: document.getElementById('new-train-type').value
      };

      const res = await fetchApi('/admin/trains', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (res.success) {
        showToast(`Train ${payload.train_number} added successfully!`, 'success');
        modal.classList.remove('active');
        form.reset();
        loadTrainsTable();
      } else {
        showToast(res.message, 'error');
      }
    });
  }
}

function closeTrainModal() {
  const modal = document.getElementById('add-train-modal');
  if (modal) modal.classList.remove('active');
}
