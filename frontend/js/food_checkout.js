/**
 * SMART INDIAN RAILWAY - FOOD CHECKOUT CLIENT LOGIC
 * Validates delivery details, computes taxes/totals, handles simulated payments,
 * and submits orders to the backend.
 */

let foodCart = null;
let foodJourney = null;
let selectedPaymentMethod = 'UPI';

document.addEventListener('DOMContentLoaded', () => {
  // Load Cart & Journey from sessionStorage
  try {
    const cartStr = sessionStorage.getItem('railway_food_cart');
    const journeyStr = sessionStorage.getItem('railway_food_journey');
    
    if (cartStr) foodCart = JSON.parse(cartStr);
    if (journeyStr) foodJourney = JSON.parse(journeyStr);
  } catch (e) {
    console.error('Failed to parse checkout session data:', e);
  }

  // Validate cart
  if (!foodCart || !foodCart.items || foodCart.items.length === 0 || !foodCart.station || !foodCart.restaurant) {
    showToast('Your food tray is empty or incomplete. Redirecting...', 'warning');
    setTimeout(() => {
      window.location.href = 'food-order.html';
    }, 1200);
    return;
  }

  prefillCheckoutForm();
  renderOrderSummary();
});

// Pre-fill form from journey or authenticated user
function prefillCheckoutForm() {
  const trainInput = document.getElementById('chk-train-number');
  const stationInput = document.getElementById('chk-station');
  const nameInput = document.getElementById('chk-passenger-name');
  const phoneInput = document.getElementById('chk-passenger-phone');
  const coachInput = document.getElementById('chk-coach');
  const seatInput = document.getElementById('chk-seat');
  const pnrInput = document.getElementById('chk-pnr');

  if (foodJourney && foodJourney.train) {
    trainInput.value = `${foodJourney.train.number} (${foodJourney.train.name || ''})`;
  } else {
    trainInput.value = '12952'; // default fallback
  }

  stationInput.value = `${foodCart.station.name} (${foodCart.station.code})`;

  if (foodJourney && foodJourney.passenger_info) {
    const p = foodJourney.passenger_info;
    if (p.name) nameInput.value = p.name;
    if (p.phone) phoneInput.value = p.phone;
    if (p.coach) coachInput.value = p.coach;
    if (p.seat_number) seatInput.value = p.seat_number;
    if (p.pnr) pnrInput.value = p.pnr;
  }

  // If user is logged in and fields are still empty
  const user = getCurrentUser();
  if (user) {
    if (!nameInput.value && user.name) nameInput.value = user.name;
    if (!phoneInput.value && user.phone) phoneInput.value = user.phone;
  }
}

// Render Order Summary
function renderOrderSummary() {
  document.getElementById('sum-restaurant-name').textContent = foodCart.restaurant.name;
  document.getElementById('sum-station-name').textContent = `Delivery at ${foodCart.station.name} (${foodCart.station.code})`;

  const listEl = document.getElementById('sum-items-list');
  listEl.innerHTML = '';

  let subtotal = 0;
  foodCart.items.forEach(item => {
    const lineTotal = item.price * item.quantity;
    subtotal += lineTotal;

    const row = document.createElement('div');
    row.style.display = 'flex';
    row.style.justifyContent = 'space-between';
    row.style.marginBottom = '0.5rem';
    row.style.fontSize = '0.9rem';

    row.innerHTML = `
      <span>
        <span class="dish-icon ${item.is_veg ? 'veg' : 'non-veg'}" style="width: 10px; height: 10px; font-size: 6px;">●</span>
        ${item.name} &times; ${item.quantity}
      </span>
      <span style="font-weight: 600;">${formatINR(lineTotal)}</span>
    `;
    listEl.appendChild(row);
  });

  const deliveryFee = 20.00;
  const tax = Math.round(subtotal * 0.05 * 100) / 100; // 5% GST
  const grandTotal = subtotal + deliveryFee + tax;

  document.getElementById('sum-subtotal').textContent = formatINR(subtotal);
  document.getElementById('sum-delivery').textContent = formatINR(deliveryFee);
  document.getElementById('sum-tax').textContent = formatINR(tax);
  document.getElementById('sum-grand-total').textContent = formatINR(grandTotal);
}

// Payment Option Selection
function selectPaymentMethod(method) {
  selectedPaymentMethod = method;
  document.querySelectorAll('.payment-option').forEach(el => {
    el.classList.remove('selected');
    const radio = el.querySelector('input[type="radio"]');
    if (radio && radio.value === method) {
      radio.checked = true;
      el.classList.add('selected');
    }
  });
}

// Handle Order Submission
async function handlePlaceOrder(e) {
  if (e && e.preventDefault) e.preventDefault();

  const name = document.getElementById('chk-passenger-name').value.trim();
  const phone = document.getElementById('chk-passenger-phone').value.trim();
  const coach = document.getElementById('chk-coach').value.trim().toUpperCase();
  const seat = document.getElementById('chk-seat').value.trim();
  const pnr = document.getElementById('chk-pnr').value.trim();
  const notes = document.getElementById('chk-notes').value.trim();

  let trainNum = '';
  if (foodJourney && foodJourney.train && foodJourney.train.number) {
    trainNum = foodJourney.train.number;
  } else {
    trainNum = document.getElementById('chk-train-number').value.split(' ')[0];
  }

  // Validations
  if (!name) {
    showToast('Please provide the passenger full name.', 'warning');
    return;
  }
  if (!phone || phone.length !== 10) {
    showToast('Please provide a valid 10-digit mobile number.', 'warning');
    return;
  }
  if (!coach) {
    showToast('Please provide the coach number (e.g. B1, S4).', 'warning');
    return;
  }
  if (!seat) {
    showToast('Please provide the berth / seat number.', 'warning');
    return;
  }

  const btn = document.getElementById('btn-place-order');
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Payment & Order...';

  // Prepare order payload
  const orderPayload = {
    pnr_number: pnr || null,
    train_number: trainNum,
    delivery_station_id: foodCart.station.id,
    restaurant_id: foodCart.restaurant.id,
    coach: coach,
    seat_number: seat,
    passenger_name: name,
    passenger_phone: phone,
    items: foodCart.items.map(item => ({
      menu_item_id: item.id,
      quantity: item.quantity,
      item_price: item.price
    })),
    payment_method: selectedPaymentMethod,
    notes: notes || null
  };

  try {
    const res = await fetchApi('/food/orders', {
      method: 'POST',
      body: JSON.stringify(orderPayload)
    });

    if (!res.success) {
      showToast(res.message || 'Failed to place food order.', 'error', 'Order Error');
      btn.disabled = false;
      btn.innerHTML = originalHtml;
      return;
    }

    // Success! Clear cart
    sessionStorage.removeItem('railway_food_cart');

    showToast('Food order confirmed! Redirecting to live tracking...', 'success', 'Order Placed');

    const orderNumber = res.order ? res.order.order_number : (res.order_id || '');
    setTimeout(() => {
      window.location.href = `food-order-tracking.html?order_id=${encodeURIComponent(orderNumber)}`;
    }, 1000);

  } catch (err) {
    console.error('Order submission error:', err);
    showToast('An unexpected network error occurred while placing your order.', 'error', 'Error');
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}
