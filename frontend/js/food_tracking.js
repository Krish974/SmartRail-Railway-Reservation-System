/**
 * SMART INDIAN RAILWAY - FOOD ORDER TRACKING CLIENT LOGIC
 * Fetches real-time order status, renders 7-stage railway delivery timeline,
 * and handles order lookup.
 */

let currentOrderId = null;

const TIMELINE_STAGES = [
  { key: 'ORDER_PLACED', title: 'Order Placed & Payment Confirmed', desc: 'Order transmitted to railway catering partner and confirmed.' },
  { key: 'CONFIRMED', title: 'Accepted by Restaurant', desc: 'Kitchen acknowledged order details and scheduled preparation.' },
  { key: 'PREPARING', title: 'Meal Being Prepared Fresh', desc: 'Chefs are preparing your hot meal with fresh ingredients.' },
  { key: 'READY', title: 'Packed & Dispatched to Station', desc: 'Sealed with tamper-evident packaging and assigned to delivery agent.' },
  { key: 'OUT_FOR_DELIVERY', title: 'Executive on Station Platform', desc: 'Delivery partner has arrived at the platform awaiting train arrival.' },
  { key: 'DELIVERED_AT_STATION', title: 'Arrived at Coach & Berth', desc: 'Executive boarded coach and reached your designated seat.' },
  { key: 'DELIVERED_TO_PASSENGER', title: 'Delivered to Passenger', desc: 'Meal received at berth. Enjoy your fresh journey dining experience!' }
];

document.addEventListener('DOMContentLoaded', () => {
  // Check URL param or path
  let orderId = getQueryParam('order_id') || getQueryParam('order_number');
  if (!orderId) {
    const pathParts = window.location.pathname.split('/');
    const lastPart = pathParts[pathParts.length - 1];
    if (lastPart && lastPart.startsWith('FOOD-')) {
      orderId = lastPart;
    }
  }

  if (orderId) {
    const input = document.getElementById('order-id-input');
    if (input) input.value = orderId;
    fetchOrderDetails(orderId);
  }
});

function handleTrackSearch(e) {
  if (e && e.preventDefault) e.preventDefault();
  const input = document.getElementById('order-id-input');
  const orderId = input ? input.value.trim() : '';

  if (!orderId) {
    showToast('Please enter a Food Order ID (e.g. FOOD-20261001-XXXXX).', 'warning');
    return;
  }

  fetchOrderDetails(orderId);
}

function refreshCurrentOrder() {
  if (currentOrderId) {
    fetchOrderDetails(currentOrderId);
    showToast('Refreshed live order tracking.', 'info');
  }
}

async function fetchOrderDetails(orderId) {
  currentOrderId = orderId;
  const loading = document.getElementById('tracking-loading');
  const content = document.getElementById('tracking-content');
  const empty = document.getElementById('tracking-empty');

  loading.style.display = 'block';
  content.style.display = 'none';
  empty.style.display = 'none';

  try {
    const res = await fetchApi(`/food/orders/${encodeURIComponent(orderId)}`);
    loading.style.display = 'none';

    if (!res.success || !res.order) {
      empty.style.display = 'block';
      showToast(res.message || 'Order not found.', 'error');
      return;
    }

    renderOrderData(res.order);
    content.style.display = 'block';
  } catch (err) {
    console.error('Fetch order tracking error:', err);
    loading.style.display = 'none';
    empty.style.display = 'block';
    showToast('Failed to retrieve order tracking information.', 'error');
  }
}

function renderOrderData(order) {
  // Order Header
  document.getElementById('ord-number').textContent = order.order_number;
  document.getElementById('ord-created-at').textContent = `Placed on ${order.created_at || 'Today'}`;

  // Status Badge Styling
  const badge = document.getElementById('ord-status-badge');
  badge.textContent = (order.status || 'ORDER_PLACED').replace(/_/g, ' ');

  const statusColors = {
    'ORDER_PLACED': { bg: '#e0f2fe', text: '#0369a1' },
    'CONFIRMED': { bg: '#e0e7ff', text: '#4338ca' },
    'PREPARING': { bg: '#fef3c7', text: '#b45309' },
    'READY': { bg: '#ffedd5', text: '#c2410c' },
    'OUT_FOR_DELIVERY': { bg: '#f3e8ff', text: '#7e22ce' },
    'DELIVERED_AT_STATION': { bg: '#dcfce7', text: '#15803d' },
    'DELIVERED_TO_PASSENGER': { bg: '#dcfce7', text: '#15803d' },
    'CANCELLED': { bg: '#fee2e2', text: '#b91c1c' }
  };

  const style = statusColors[order.status] || { bg: '#f1f5f9', text: '#475569' };
  badge.style.background = style.bg;
  badge.style.color = style.text;

  // Passenger & Train Grid
  document.getElementById('ord-passenger').textContent = order.passenger_name || 'Passenger';
  document.getElementById('ord-phone').textContent = order.passenger_phone ? `+91 ${order.passenger_phone}` : '-';

  const trainText = order.train_name ? `${order.train_number} (${order.train_name})` : `Train #${order.train_number}`;
  document.getElementById('ord-train').textContent = trainText;
  document.getElementById('ord-berth').textContent = `Coach ${order.coach || '-'}, Seat ${order.seat_number || '-'}`;

  const stationText = order.station_code ? `${order.station_name} (${order.station_code})` : (order.station_name || 'Halt Station');
  document.getElementById('ord-station').textContent = stationText;
  document.getElementById('ord-pnr').textContent = order.pnr_number ? `PNR: ${order.pnr_number}` : 'PNR: Unlinked';

  document.getElementById('ord-restaurant').textContent = order.restaurant_name || 'Catering Partner';
  document.getElementById('ord-fssai').textContent = order.fssai_license ? `FSSAI: ${order.fssai_license}` : 'FSSAI Certified';

  // Render 7-Stage Timeline
  renderTimeline(order.status, order.status_history || []);

  // Render Items Table
  renderItemsTable(order.items || [], order);
}

function renderTimeline(currentStatus, history) {
  const container = document.getElementById('order-timeline');
  container.innerHTML = '';

  const currentIndex = TIMELINE_STAGES.findIndex(s => s.key === currentStatus);
  const isCancelled = currentStatus === 'CANCELLED';

  if (isCancelled) {
    container.innerHTML = `
      <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: var(--radius-md); padding: 1.25rem; color: #b91c1c;">
        <h4 style="margin-bottom: 0.25rem;"><i class="fa-solid fa-circle-xmark"></i> Order Cancelled</h4>
        <p style="font-size: 0.9rem; margin: 0;">This food order has been cancelled. Any pre-paid amount has been refunded to the original payment method.</p>
      </div>
    `;
    return;
  }

  // Create timestamp map from history
  const historyMap = {};
  if (Array.isArray(history)) {
    history.forEach(h => {
      historyMap[h.status] = h.timestamp || h.created_at;
    });
  }

  TIMELINE_STAGES.forEach((stage, idx) => {
    const stepEl = document.createElement('div');
    stepEl.className = 'timeline-step';

    let iconHtml = '<i class="fa-regular fa-circle"></i>';

    if (idx < currentIndex) {
      stepEl.classList.add('completed');
      iconHtml = '<i class="fa-solid fa-check"></i>';
    } else if (idx === currentIndex) {
      stepEl.classList.add('active');
      iconHtml = '<i class="fa-solid fa-utensils"></i>';
    } else {
      stepEl.classList.add('pending');
      iconHtml = `<span>${idx + 1}</span>`;
    }

    const timeStr = historyMap[stage.key] ? `<div class="timeline-time"><i class="fa-regular fa-clock"></i> ${historyMap[stage.key]}</div>` : '';

    stepEl.innerHTML = `
      <div class="timeline-icon">${iconHtml}</div>
      <div class="timeline-title">${stage.title}</div>
      <div class="timeline-desc">${stage.desc}</div>
      ${timeStr}
    `;

    container.appendChild(stepEl);
  });
}

function renderItemsTable(items, order) {
  const tbody = document.getElementById('ord-items-tbody');
  tbody.innerHTML = '';

  let calculatedSubtotal = 0;

  items.forEach(item => {
    const lineTotal = (item.item_price || 0) * (item.quantity || 1);
    calculatedSubtotal += lineTotal;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <span class="dish-icon ${item.is_veg ? 'veg' : 'non-veg'}" style="width: 10px; height: 10px; font-size: 6px;">●</span>
        <strong>${item.item_name || 'Dish'}</strong>
      </td>
      <td style="text-align: center;">${item.quantity || 1}</td>
      <td style="text-align: right;">${formatINR(item.item_price || 0)}</td>
      <td style="text-align: right; font-weight: 600;">${formatINR(lineTotal)}</td>
    `;
    tbody.appendChild(tr);
  });

  const deliveryFee = 20.00;
  const subtotal = calculatedSubtotal;
  const grandTotal = order.total_amount ? parseFloat(order.total_amount) : (subtotal + deliveryFee);

  document.getElementById('ord-subtotal').textContent = formatINR(subtotal);
  document.getElementById('ord-delivery').textContent = formatINR(deliveryFee);
  document.getElementById('ord-total').textContent = formatINR(grandTotal);
}
