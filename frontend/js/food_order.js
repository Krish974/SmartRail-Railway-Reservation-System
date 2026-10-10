/**
 * SMART INDIAN RAILWAY - FOOD ORDER CLIENT LOGIC
 * Manages journey search, scheduled halt selection, restaurant listings,
 * categorized menus, pure-veg filtering, and persistent cart.
 */

// Application State
let activeTab = 'pnr';
let currentJourney = null;
let currentHalts = [];
let selectedHalt = null;
let currentRestaurants = [];
let selectedRestaurant = null;
let currentMenuItems = [];
let selectedCategory = 'All';
let vegOnlyFilter = false;

// Partner Showcase State
let allFoodPartners = [];
let selectedPartnerCategory = 'All';
let showingAllPartners = false;

// Cart State
let foodCart = {
  station: null,
  restaurant: null,
  items: []
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  // Load saved cart from sessionStorage if any
  try {
    const savedCart = sessionStorage.getItem('railway_food_cart');
    if (savedCart) {
      foodCart = JSON.parse(savedCart);
    }
  } catch (e) {
    console.warn('Error reading saved food cart:', e);
  }

  // Pre-fill date input with today's date
  const dateInput = document.getElementById('food-date-input');
  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
  }

  // Initial load of authorized IRCTC eCatering partners
  loadFoodPartners('All');

  // Handle URL query parameters (e.g. ?pnr=... or ?train=...&date=...)
  const pnrParam = getQueryParam('pnr');
  const trainParam = getQueryParam('train') || getQueryParam('train_number');
  const dateParam = getQueryParam('date');

  if (pnrParam) {
    const pnrInput = document.getElementById('food-pnr-input');
    if (pnrInput) {
      pnrInput.value = pnrParam;
      switchFoodTab('pnr');
      handlePnrSearch();
    }
  } else if (trainParam) {
    const trainInput = document.getElementById('food-train-input');
    if (trainInput) {
      trainInput.value = trainParam;
      if (dateParam && dateInput) {
        dateInput.value = dateParam;
      }
      switchFoodTab('train');
      handleTrainSearch();
    }
  }

  renderCart();
});

// Tab Switcher (PNR vs Train & Date)
function switchFoodTab(tab) {
  activeTab = tab;
  const tabPnr = document.getElementById('tab-pnr');
  const tabTrain = document.getElementById('tab-train');
  const formPnr = document.getElementById('food-pnr-form');
  const formTrain = document.getElementById('food-train-form');

  if (tab === 'pnr') {
    tabPnr.classList.add('active');
    tabTrain.classList.remove('active');
    formPnr.style.display = 'block';
    formTrain.style.display = 'none';
  } else {
    tabPnr.classList.remove('active');
    tabTrain.classList.add('active');
    formPnr.style.display = 'none';
    formTrain.style.display = 'block';
  }
}

// Quick demo fill helpers
function fillDemoPnr(pnr) {
  const input = document.getElementById('food-pnr-input');
  if (input) {
    input.value = pnr;
    switchFoodTab('pnr');
    handlePnrSearch();
  }
}

function fillDemoTrain(trainNum) {
  const input = document.getElementById('food-train-input');
  if (input) {
    input.value = trainNum;
    switchFoodTab('train');
    handleTrainSearch();
  }
}

// =============================================================
// IRCTC eCATERING PARTNERS & RESTAURANT BRANDS SHOWCASE
// =============================================================

async function loadFoodPartners(category = 'All') {
  selectedPartnerCategory = category;
  const featuredGrid = document.getElementById('partner-featured-grid');
  const moreGrid = document.getElementById('partner-more-grid');
  const toggleBtn = document.getElementById('btn-toggle-more-partners');

  if (!featuredGrid) return;

  try {
    const url = `/food/partners${category && category !== 'All' ? '?category=' + encodeURIComponent(category) : ''}`;
    const res = await fetchApi(url);
    if (!res || !res.success) {
      console.warn('Failed to load partners from API');
      return;
    }

    const partners = res.data && res.data.partners ? res.data.partners : [];
    allFoodPartners = partners;
    renderPartnerCards(partners, category);
  } catch (err) {
    console.error('Error loading food partners:', err);
  }
}

function renderPartnerCards(partners, category) {
  const featuredGrid = document.getElementById('partner-featured-grid');
  const moreGrid = document.getElementById('partner-more-grid');
  const toggleBtn = document.getElementById('btn-toggle-more-partners');
  if (!featuredGrid || !moreGrid) return;

  featuredGrid.innerHTML = '';
  moreGrid.innerHTML = '';

  if (partners.length === 0) {
    featuredGrid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 2.5rem 1rem; color: var(--text-muted); background: #f8fafc; border-radius: var(--radius-md); border: 1px dashed var(--border-light);">
        <i class="fa-solid fa-utensils" style="font-size: 2rem; color: #cbd5e1; margin-bottom: 0.5rem; display: block;"></i>
        No partner matches "${category}". Try another cuisine filter above.
      </div>
    `;
    if (toggleBtn) toggleBtn.style.display = 'none';
    moreGrid.style.display = 'none';
    return;
  }

  // If filtered by a specific category (not 'All'), display all matches in featuredGrid
  if (category && category !== 'All') {
    partners.forEach(p => {
      featuredGrid.appendChild(createPartnerCardEl(p, true));
    });
    if (toggleBtn) toggleBtn.style.display = 'none';
    moreGrid.style.display = 'none';
    return;
  }

  // Default 'All': 4 featured in featuredGrid, rest in moreGrid
  if (toggleBtn) toggleBtn.style.display = 'inline-flex';

  const featured = partners.filter(p => p.is_featured);
  const secondary = partners.filter(p => !p.is_featured);

  featured.forEach(p => {
    featuredGrid.appendChild(createPartnerCardEl(p, true));
  });

  secondary.forEach(p => {
    moreGrid.appendChild(createPartnerCardEl(p, false));
  });
}

function createPartnerCardEl(p, isFeatured) {
  const card = document.createElement('div');
  card.className = `partner-card ${isFeatured ? 'featured' : ''}`;
  card.innerHTML = `
    <div class="partner-card-header">
      <div class="partner-logo-icon">
        <i class="fa-solid ${p.logo_icon || 'fa-utensils'}"></i>
      </div>
      <div>
        <div class="partner-name">${p.name}</div>
        <div class="partner-tagline">${p.tagline || 'Authorised Catering'}</div>
      </div>
    </div>
    <span class="partner-badge-official">
      <i class="fa-solid fa-circle-check"></i> Authorised Partner
    </span>
    <div class="partner-desc">${p.description || ''}</div>
    <div class="partner-cuisines">
      <strong>Speciality:</strong> ${p.cuisines || 'Multi-Cuisine'}
    </div>
    <div class="partner-avail-note">
      <i class="fa-solid fa-circle-info"></i> Availability depends on station and journey.
    </div>
    <div class="partner-actions">
      <a href="${p.website_url}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline" title="Visit official partner website">
        <i class="fa-solid fa-arrow-up-right-from-square"></i> Visit Official Partner
      </a>
      <button class="btn btn-sm btn-accent" onclick="checkPartnerAvailability('${p.name.replace(/'/g, "\\'")}', '${p.slug}')">
        <i class="fa-solid fa-magnifying-glass"></i> Check Availability
      </button>
    </div>
  `;
  return card;
}

function filterPartnersByCategory(category) {
  selectedPartnerCategory = category;

  // Update pills UI
  document.querySelectorAll('.partner-filter-pill').forEach(pill => {
    if (pill.getAttribute('data-category') === category) {
      pill.classList.add('active');
    } else {
      pill.classList.remove('active');
    }
  });

  loadFoodPartners(category);
}

function toggleMorePartners() {
  const moreGrid = document.getElementById('partner-more-grid');
  const icon = document.getElementById('toggle-partners-icon');
  const text = document.getElementById('toggle-partners-text');
  if (!moreGrid) return;

  showingAllPartners = !showingAllPartners;
  if (showingAllPartners) {
    moreGrid.style.display = 'grid';
    if (text) text.textContent = 'Show Less Partners';
    if (icon) icon.className = 'fa-solid fa-chevron-up';
  } else {
    moreGrid.style.display = 'none';
    if (text) text.textContent = 'Show All Partners (Zoop, RailYatri, Haldiram\'s, Comesum, etc.)';
    if (icon) icon.className = 'fa-solid fa-chevron-down';
  }
}

function checkPartnerAvailability(partnerName, partnerSlug) {
  if (!currentJourney || !selectedHalt) {
    showToast('Enter your PNR or Train number above to check delivery at your journey halts.', 'info', 'Find Journey Halts');
    const input = document.getElementById('food-pnr-input');
    if (input) {
      input.scrollIntoView({ behavior: 'smooth', block: 'center' });
      input.focus();
    }
    return;
  }

  // We have a journey and a selected halt
  const stationName = selectedHalt.station_name;
  const stationCode = selectedHalt.station_code;

  // Check if currentRestaurants at this halt matches
  const hasMatch = currentRestaurants && currentRestaurants.some(r => 
    r.name.toLowerCase().includes(partnerName.toLowerCase()) ||
    (r.cuisine_type && r.cuisine_type.toLowerCase().includes(partnerName.toLowerCase())) ||
    (partnerSlug === 'dominos' && (r.cuisine_type || '').toLowerCase().includes('pizza')) ||
    (partnerSlug === 'irctc-ecatering' && (r.name || '').toLowerCase().includes('irctc'))
  );

  if (hasMatch) {
    showToast(`${partnerName} partner meals are available for delivery at ${stationName} (${stationCode})!`, 'success', 'Available at Halt');
    const vendorSec = document.getElementById('vendor-section');
    if (vendorSec) {
      vendorSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  } else {
    showToast(`${partnerName} is not currently delivering at ${stationName} (${stationCode}). Choose another halt or order via official partner website.`, 'warning', 'Halt Check');
  }
}

// 1. PNR Journey Search
async function handlePnrSearch(e) {
  if (e && e.preventDefault) e.preventDefault();
  const pnr = document.getElementById('food-pnr-input').value.trim();
  if (!pnr || pnr.length !== 10) {
    showToast('Please enter a valid 10-digit PNR number.', 'warning', 'Invalid PNR');
    return;
  }

  const btn = document.getElementById('btn-pnr-search');
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Checking PNR...';

  try {
    const res = await fetchApi(`/food/journey-info?pnr=${encodeURIComponent(pnr)}`);
    if (!res.success) {
      showToast(res.message || 'Journey details not found for this PNR.', 'error', 'Search Failed');
      return;
    }

    const payload = res.data || res;
    displayJourneyData(payload);
    const trainInfo = payload.train || { number: payload.train_number, name: payload.train_name };
    showToast(`Train ${trainInfo.number} ${trainInfo.name} halts retrieved!`, 'success', 'Journey Found');
  } catch (err) {
    console.error('PNR search error:', err);
    showToast('Failed to fetch PNR journey data. Please try again.', 'error', 'Network Error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

// 2. Train & Date Journey Search
async function handleTrainSearch(e) {
  if (e && e.preventDefault) e.preventDefault();
  const trainNum = document.getElementById('food-train-input').value.trim();
  const travelDate = document.getElementById('food-date-input').value;

  if (!trainNum) {
    showToast('Please enter a valid train number.', 'warning', 'Required Field');
    return;
  }

  const btn = document.getElementById('btn-train-search');
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Retrieving Route...';

  try {
    const url = `/food/journey-info?train_number=${encodeURIComponent(trainNum)}&date=${encodeURIComponent(travelDate || '')}`;
    const res = await fetchApi(url);
    if (!res.success) {
      showToast(res.message || 'Route information not found for this train.', 'error', 'Search Failed');
      return;
    }

    const payload = res.data || res;
    displayJourneyData(payload);
    const trainInfo = payload.train || { number: payload.train_number, name: payload.train_name };
    showToast(`Loaded ${payload.route_halts ? payload.route_halts.length : 0} scheduled halts for Train ${trainInfo.number}.`, 'success', 'Halts Loaded');
  } catch (err) {
    console.error('Train route search error:', err);
    showToast('Failed to retrieve train halts.', 'error', 'Network Error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

// Display retrieved Journey Info & Scheduled Halts
function displayJourneyData(data) {
  currentJourney = data;
  currentHalts = data.route_halts || [];

  // Persist journey info for checkout
  sessionStorage.setItem('railway_food_journey', JSON.stringify(currentJourney));

  const container = document.getElementById('food-container');
  container.style.display = 'block';

  // Populate Journey Banner
  const titleEl = document.getElementById('jb-train-title');
  const routeEl = document.getElementById('jb-route');
  const passEl = document.getElementById('jb-passenger');
  const liveEl = document.getElementById('jb-live');

  titleEl.innerHTML = `<i class="fa-solid fa-train"></i> Train ${data.train.number} - ${data.train.name}`;
  routeEl.innerHTML = `<span>${data.source_station}</span> <i class="fa-solid fa-arrow-right-long" style="color: var(--accent-saffron);"></i> <span>${data.destination_station}</span> &bull; Date: <strong>${data.journey_date || 'Today'}</strong>`;

  if (data.passenger_info && data.passenger_info.name) {
    passEl.innerHTML = `<i class="fa-solid fa-user-check"></i> Passenger: <strong>${data.passenger_info.name}</strong> (PNR: ${data.passenger_info.pnr}) &bull; Coach: <strong>${data.passenger_info.coach || 'B1'}</strong> Seat: <strong>${data.passenger_info.seat_number || '34'}</strong>`;
  } else {
    passEl.innerHTML = `<i class="fa-solid fa-info-circle"></i> Berth/seat details will be collected at checkout.`;
  }

  if (data.live_status && data.live_status.available && data.live_status.current_section) {
    liveEl.innerHTML = `<i class="fa-solid fa-satellite-dish" style="color: #2a9d8f;"></i> Live GPS: ${data.live_status.current_section}`;
  } else {
    liveEl.innerHTML = `<i class="fa-solid fa-satellite-dish" style="color: var(--text-muted);"></i> Live GPS unavailable`;
  }

  // Render Halts Carousel Track
  renderHaltsTrack();

  // Smooth scroll down to halts
  container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Render Halts Carousel Track
function renderHaltsTrack() {
  const track = document.getElementById('halt-track');
  track.innerHTML = '';

  if (!currentHalts || currentHalts.length === 0) {
    track.innerHTML = '<div style="padding: 1.5rem; color: var(--text-muted);">No scheduled halts found for this train route.</div>';
    return;
  }

  let defaultHalt = null;

  currentHalts.forEach((halt, idx) => {
    const card = document.createElement('div');
    card.className = 'halt-card';
    card.id = `halt-card-${halt.station_id}`;

    const partnerCount = halt.restaurant_count !== undefined ? halt.restaurant_count : (halt.restaurants_count || 0);
    const hasFood = partnerCount > 0;
    if (!defaultHalt && hasFood) {
      defaultHalt = halt;
    }

    card.innerHTML = `
      <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">
        Halt #${halt.stop_sequence || (idx + 1)}
      </div>
      <div class="halt-name">
        ${halt.station_name} (${halt.station_code})
      </div>
      <div class="halt-timing">
        Arr: <strong>${halt.arrival_time || '--:--'}</strong> | Dep: <strong>${halt.departure_time || '--:--'}</strong>
      </div>
      ${halt.halt_minutes ? `<div style="font-size: 0.75rem; color: var(--primary-blue); margin-top: 0.2rem;">Halt: ${halt.halt_minutes} min</div>` : ''}
      <div>
        ${hasFood 
          ? `<span class="halt-food-badge has-food"><i class="fa-solid fa-utensils"></i> ${partnerCount} partner${partnerCount === 1 ? '' : 's'}</span>` 
          : `<span class="halt-food-badge no-food"><i class="fa-solid fa-ban"></i> No food partners</span>`}
      </div>
    `;

    card.onclick = () => selectHalt(halt);
    track.appendChild(card);
  });

  // Automatically select the first halt with restaurants (or the first halt if none)
  if (defaultHalt) {
    selectHalt(defaultHalt);
  } else if (currentHalts.length > 0) {
    selectHalt(currentHalts[0]);
  }
}

// Smooth scroll back to halt track for choosing another station
function scrollToHaltTrack() {
  const haltSection = document.querySelector('.halt-selector-container');
  if (haltSection) {
    haltSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    haltSection.classList.remove('halt-track-highlight');
    void haltSection.offsetWidth;
    haltSection.classList.add('halt-track-highlight');
    setTimeout(() => {
      haltSection.classList.remove('halt-track-highlight');
    }, 4500);
  }
}

// Select a Halt
async function selectHalt(halt) {
  selectedHalt = halt;

  // Update UI active card
  document.querySelectorAll('.halt-card').forEach(el => el.classList.remove('selected'));
  const activeCard = document.getElementById(`halt-card-${halt.station_id}`);
  if (activeCard) activeCard.classList.add('selected');

  // Update badge and cart station label
  const badge = document.getElementById('selected-halt-badge');
  badge.style.display = 'block';
  document.getElementById('sh-name').textContent = `${halt.station_name} (${halt.station_code})`;
  document.getElementById('cart-station-label').textContent = `Delivery at ${halt.station_name} (${halt.station_code})`;

  // Reset to vendor view
  backToRestaurants();

  // Load Restaurants for this halt
  await loadRestaurants(halt.station_id, halt.station_name);
}

// Fetch Restaurants for selected Halt
async function loadRestaurants(stationId, stationName) {
  const grid = document.getElementById('restaurant-grid');
  const countBadge = document.getElementById('vendor-count-badge');
  const heading = document.getElementById('vendor-heading');

  grid.innerHTML = '<div style="padding: 2rem; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Finding approved food partners at ' + stationName + '...</div>';
  heading.textContent = `Restaurants at ${stationName}`;

  try {
    const res = await fetchApi(`/food/stations/${stationId}/restaurants`);
    if (!res.success) {
      grid.innerHTML = `<div style="padding: 1.5rem; color: var(--text-muted);">Could not retrieve restaurants for this station.</div>`;
      countBadge.textContent = '0 Vendors';
      return;
    }

    const payload = res.data || res;
    currentRestaurants = (payload && payload.restaurants) ? payload.restaurants : (res.restaurants || []);
    countBadge.textContent = `${currentRestaurants.length} Partner${currentRestaurants.length === 1 ? '' : 's'}`;

    if (currentRestaurants.length === 0) {
      grid.innerHTML = `
        <div class="empty-station-card">
          <div class="empty-station-icon">
            <i class="fa-solid fa-store-slash"></i>
          </div>
          <h3>No food partners available for this station.</h3>
          <p>Try another scheduled halt on your train route. Food partner availability varies by station and journey.</p>
          <button class="btn btn-accent btn-md" onclick="scrollToHaltTrack()">
            <i class="fa-solid fa-route"></i> Choose Another Station
          </button>
        </div>
      `;
      return;
    }

    renderRestaurantCards(currentRestaurants);
  } catch (err) {
    console.error('Error loading restaurants:', err);
    grid.innerHTML = `<div style="padding: 1.5rem; color: var(--accent-red);">Error loading restaurants.</div>`;
  }
}

// Render Restaurant Cards
function renderRestaurantCards(restaurants) {
  const grid = document.getElementById('restaurant-grid');
  grid.innerHTML = '';

  const fallbackImages = [
    'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1552566626-52f8b828add9?w=600&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1544025162-d76694265947?w=600&auto=format&fit=crop&q=80'
  ];

  restaurants.forEach((rest, idx) => {
    const card = document.createElement('div');
    card.className = 'restaurant-card';
    const imgSrc = rest.image_url || fallbackImages[idx % fallbackImages.length];

    card.innerHTML = `
      <img src="${imgSrc}" class="restaurant-img" alt="${rest.name}" onerror="this.src='${fallbackImages[0]}'">
      <div class="restaurant-body">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.25rem;">
          <h4 class="restaurant-title">${rest.name}</h4>
          <span style="background: #e8f5e9; color: #2e7d32; font-weight: 700; font-size: 0.8rem; padding: 0.15rem 0.45rem; border-radius: 4px; display: inline-flex; align-items: center; gap: 0.2rem;">
            ★ ${rest.rating || '4.2'}
          </span>
        </div>
        <div class="restaurant-meta">${rest.cuisine_type || 'North Indian, Thali, Snacks'}</div>
        <div class="restaurant-badges">
          ${rest.is_pure_veg 
            ? `<span class="veg-indicator veg-only"><i class="fa-solid fa-leaf"></i> Pure Veg</span>` 
            : `<span class="veg-indicator veg-nonveg"><i class="fa-solid fa-drumstick-bite"></i> Veg & Non-Veg</span>`}
          <span style="font-size: 0.75rem; color: var(--text-muted); display: inline-flex; align-items: center; gap: 0.3rem;">
            <i class="fa-regular fa-clock"></i> ${rest.delivery_time_mins || 30} mins
          </span>
          <span class="demo-data-badge">Demo partner data</span>
        </div>
        <div style="margin-top: auto;">
          <button class="btn btn-outline btn-block btn-sm" onclick='openRestaurantMenu(${JSON.stringify(rest).replace(/'/g, "&#39;")})'>
            <i class="fa-solid fa-utensils"></i> View Menu
          </button>
        </div>
      </div>
    `;

    grid.appendChild(card);
  });
}

// Open Restaurant Menu View
async function openRestaurantMenu(restaurant) {
  selectedRestaurant = restaurant;

  document.getElementById('vendor-section').style.display = 'none';
  const menuSec = document.getElementById('menu-section');
  menuSec.style.display = 'block';

  document.getElementById('menu-restaurant-name').textContent = restaurant.name;
  document.getElementById('menu-restaurant-cuisine').innerHTML = `
    <span>${restaurant.cuisine_type}</span> &bull; 
    <span>${restaurant.is_pure_veg ? '🌱 100% Pure Veg' : '🍗 Veg & Non-Veg'}</span> &bull; 
    <span>FSSAI Lic: ${restaurant.fssai_license || 'IRCTC-APPROVED'}</span>
  `;

  // Fetch Menu Items
  const dishesContainer = document.getElementById('dishes-container');
  dishesContainer.innerHTML = '<div style="padding: 2rem; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Loading appetizing dishes...</div>';

  try {
    const res = await fetchApi(`/food/restaurants/${restaurant.id}/menu`);
    if (!res.success) {
      dishesContainer.innerHTML = `<div style="padding: 1.5rem; color: var(--accent-red);">Failed to load menu items.</div>`;
      return;
    }

    const menuPayload = res.data || res;
    currentMenuItems = menuPayload.menu_items || menuPayload.all_items || [];
    renderMenuCategories(menuPayload.categories || []);
    renderDishes();
  } catch (err) {
    console.error('Error loading menu:', err);
    dishesContainer.innerHTML = `<div style="padding: 1.5rem; color: var(--accent-red);">Error loading menu.</div>`;
  }
}

// Back to Restaurants
function backToRestaurants() {
  selectedRestaurant = null;
  const menuSec = document.getElementById('menu-section');
  if (menuSec) menuSec.style.display = 'none';
  const vendorSec = document.getElementById('vendor-section');
  if (vendorSec) vendorSec.style.display = 'block';
}

// Render Menu Category Filter Pills
function renderMenuCategories(categories) {
  const container = document.getElementById('menu-categories');
  container.innerHTML = '';

  const allPill = document.createElement('button');
  allPill.className = `category-pill ${selectedCategory === 'All' ? 'active' : ''}`;
  allPill.textContent = 'All Items';
  allPill.onclick = () => selectCategory('All');
  container.appendChild(allPill);

  categories.forEach(cat => {
    const pill = document.createElement('button');
    pill.className = `category-pill ${selectedCategory === cat ? 'active' : ''}`;
    pill.textContent = cat;
    pill.onclick = () => selectCategory(cat);
    container.appendChild(pill);
  });
}

function selectCategory(category) {
  selectedCategory = category;
  document.querySelectorAll('.category-pill').forEach(pill => {
    pill.classList.toggle('active', pill.textContent === (category === 'All' ? 'All Items' : category));
  });
  renderDishes();
}

function toggleVegOnly() {
  const toggle = document.getElementById('veg-toggle');
  vegOnlyFilter = toggle ? toggle.checked : false;
  renderDishes();
}

// Render Dish Cards
function renderDishes() {
  const container = document.getElementById('dishes-container');
  container.innerHTML = '';

  let filtered = currentMenuItems;
  if (selectedCategory !== 'All') {
    filtered = filtered.filter(item => item.category === selectedCategory);
  }
  if (vegOnlyFilter) {
    filtered = filtered.filter(item => item.is_veg === true);
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="background: white; padding: 2rem; text-align: center; border-radius: var(--radius-md); color: var(--text-muted); border: 1px solid var(--border-light);">
        No dishes found for the selected filter. Try changing category or veg filter.
      </div>
    `;
    return;
  }

  const defaultDishImages = {
    'Meals': 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=300&auto=format&fit=crop&q=80',
    'Breakfast': 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=300&auto=format&fit=crop&q=80',
    'Snacks': 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=300&auto=format&fit=crop&q=80',
    'Beverages': 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=300&auto=format&fit=crop&q=80',
    'Desserts': 'https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=300&auto=format&fit=crop&q=80'
  };

  filtered.forEach(dish => {
    const card = document.createElement('div');
    card.className = 'dish-card';

    // Find quantity in cart
    const cartItem = foodCart.items.find(ci => ci.id === dish.id);
    const qtyInCart = cartItem ? cartItem.quantity : 0;
    const imgSrc = dish.image_url || defaultDishImages[dish.category] || 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=300&auto=format&fit=crop&q=80';

    card.innerHTML = `
      <span class="dish-icon ${dish.is_veg ? 'veg' : 'non-veg'}">●</span>
      <div class="dish-details">
        <div class="dish-name">${dish.name}</div>
        <div class="dish-desc">${dish.description || ''}</div>
        <div class="dish-price">${formatINR(dish.price)}</div>
      </div>
      ${imgSrc ? `<img src="${imgSrc}" class="dish-img" alt="${dish.name}" onerror="this.style.display='none'">` : ''}
      <div>
        ${qtyInCart > 0 ? `
          <div class="qty-controls">
            <button class="qty-btn" onclick="updateCartItemQty(${dish.id}, -1)">-</button>
            <span style="font-weight: 700; font-size: 0.9rem; min-width: 20px; text-align: center;">${qtyInCart}</span>
            <button class="qty-btn" onclick="updateCartItemQty(${dish.id}, 1)">+</button>
          </div>
        ` : `
          <button class="btn btn-sm btn-outline add-btn" onclick='addDishToCart(${JSON.stringify(dish).replace(/'/g, "&#39;")})'>
            ADD +
          </button>
        `}
      </div>
    `;

    container.appendChild(card);
  });
}

// -------------------------------------------------------------
// CART OPERATIONS
// -------------------------------------------------------------

function addDishToCart(dish) {
  if (!selectedHalt) {
    showToast('Please select a scheduled delivery halt first.', 'warning');
    return;
  }
  if (!selectedRestaurant) {
    showToast('Please select a restaurant first.', 'warning');
    return;
  }

  // Cross-restaurant or Cross-station check
  if (foodCart.restaurant && foodCart.restaurant.id !== selectedRestaurant.id) {
    const confirmSwitch = confirm(
      `Your cart contains items from "${foodCart.restaurant.name}". Adding items from "${selectedRestaurant.name}" will clear your previous selection. Continue?`
    );
    if (!confirmSwitch) return;
    foodCart.items = [];
  }

  foodCart.station = {
    id: selectedHalt.station_id,
    code: selectedHalt.station_code,
    name: selectedHalt.station_name
  };
  foodCart.restaurant = {
    id: selectedRestaurant.id,
    name: selectedRestaurant.name
  };

  const existing = foodCart.items.find(item => item.id === dish.id);
  if (existing) {
    existing.quantity += 1;
  } else {
    foodCart.items.push({
      id: dish.id,
      name: dish.name,
      price: parseFloat(dish.price),
      is_veg: dish.is_veg,
      quantity: 1
    });
  }

  renderCart();
  renderDishes();
  showToast(`Added ${dish.name} to tray`, 'success');
}

function updateCartItemQty(dishId, delta) {
  const itemIndex = foodCart.items.findIndex(item => item.id === dishId);
  if (itemIndex > -1) {
    foodCart.items[itemIndex].quantity += delta;
    if (foodCart.items[itemIndex].quantity <= 0) {
      foodCart.items.splice(itemIndex, 1);
    }
  }

  if (foodCart.items.length === 0) {
    foodCart.restaurant = null;
  }

  renderCart();
  renderDishes();
}

function clearCart() {
  foodCart.items = [];
  foodCart.restaurant = null;
  renderCart();
  renderDishes();
  showToast('Food tray cleared', 'info');
}

function renderCart() {
  const listEl = document.getElementById('cart-items-list');
  const subtotalEl = document.getElementById('cart-subtotal');
  const deliveryFeeEl = document.getElementById('cart-delivery-fee');
  const totalEl = document.getElementById('cart-total');
  const checkoutBtn = document.getElementById('btn-checkout');
  const stationLabel = document.getElementById('cart-station-label');

  if (foodCart.station) {
    stationLabel.textContent = `Delivery at ${foodCart.station.name} (${foodCart.station.code})`;
  } else if (selectedHalt) {
    stationLabel.textContent = `Delivery at ${selectedHalt.station_name} (${selectedHalt.station_code})`;
  } else {
    stationLabel.textContent = 'Select station & items';
  }

  if (!foodCart.items || foodCart.items.length === 0) {
    listEl.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); padding: 2rem 0;">
        <i class="fa-solid fa-utensils" style="font-size: 2rem; color: #cbd5e1; margin-bottom: 0.5rem; display: block;"></i>
        Your tray is currently empty.
      </div>
    `;
    subtotalEl.textContent = '₹0.00';
    deliveryFeeEl.textContent = '₹0.00';
    totalEl.textContent = '₹0.00';
    checkoutBtn.disabled = true;
    sessionStorage.removeItem('railway_food_cart');
    return;
  }

  let subtotal = 0;
  listEl.innerHTML = '';

  foodCart.items.forEach(item => {
    const itemTotal = item.price * item.quantity;
    subtotal += itemTotal;

    const row = document.createElement('div');
    row.className = 'cart-item';
    row.innerHTML = `
      <div style="flex: 1; padding-right: 0.5rem;">
        <div style="font-weight: 600; display: flex; align-items: center; gap: 0.35rem;">
          <span class="dish-icon ${item.is_veg ? 'veg' : 'non-veg'}" style="width: 10px; height: 10px; font-size: 6px;">●</span>
          ${item.name}
        </div>
        <div style="font-size: 0.8rem; color: var(--text-muted);">
          ${formatINR(item.price)} &times; ${item.quantity} = ${formatINR(itemTotal)}
        </div>
      </div>
      <div class="qty-controls">
        <button class="qty-btn" onclick="updateCartItemQty(${item.id}, -1)">-</button>
        <span style="font-weight: 700; font-size: 0.85rem; min-width: 16px; text-align: center;">${item.quantity}</span>
        <button class="qty-btn" onclick="updateCartItemQty(${item.id}, 1)">+</button>
      </div>
    `;
    listEl.appendChild(row);
  });

  const deliveryFee = 20.00;
  const total = subtotal + deliveryFee;

  subtotalEl.textContent = formatINR(subtotal);
  deliveryFeeEl.textContent = formatINR(deliveryFee);
  totalEl.textContent = formatINR(total);
  checkoutBtn.disabled = false;

  // Persist cart to sessionStorage
  sessionStorage.setItem('railway_food_cart', JSON.stringify(foodCart));
}

// Proceed to Checkout Page
function proceedToCheckout() {
  if (!foodCart.items || foodCart.items.length === 0) {
    showToast('Your tray is empty. Please add items to proceed.', 'warning');
    return;
  }

  if (!foodCart.station && !selectedHalt) {
    showToast('Please select a scheduled delivery halt.', 'warning');
    return;
  }

  // Ensure journey & cart are persisted
  sessionStorage.setItem('railway_food_cart', JSON.stringify(foodCart));
  if (currentJourney) {
    sessionStorage.setItem('railway_food_journey', JSON.stringify(currentJourney));
  }

  window.location.href = 'food-checkout.html';
}
