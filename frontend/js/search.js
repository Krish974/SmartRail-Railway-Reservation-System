/**
 * SMART RAILWAY - TRAIN SEARCH & FILTER CONTROLLER
 * Single Source of Truth consumer supporting:
 * 1. Station & city autocomplete with relevance scoring
 * 2. Exact train number and train name search
 * 3. Route search respecting stop sequence
 * 4. Railway-style date search (All Dates vs Specific Date)
 * 5. Operating days indicator (S M T W T F S) and selected-date highlight
 * 6. Running Day filter and Non-running trains grouping
 * 7. Quota adjusted pricing & dynamic seat status
 */

let allTrainResults = [];
let currentSearchMode = 'route'; // 'route' or 'train'
let debounceTimers = {};
let currentServerDateMode = 'all'; // 'all' or 'specific'

document.addEventListener('DOMContentLoaded', async () => {
  setupAutocomplete('input-from', 'dropdown-from');
  setupAutocomplete('input-to', 'dropdown-to');
  populateFormFromUrl();
  setupEventListeners();
  attachDatePickerHelpers('input-date');
  attachDatePickerHelpers('input-date-train');
  updateDateModeUI();
  performSearch();
});

// Calendar date parsing to prevent UTC midnight timezone shifts
function parseDateParts(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return null;
  const parts = dateStr.trim().split('-');
  if (parts.length !== 3) return null;
  const y = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10) - 1;
  const d = parseInt(parts[2], 10);
  if (isNaN(y) || isNaN(m) || isNaN(d)) return null;
  return new Date(y, m, d);
}

// Format Date object to "YYYY-MM-DD"
function formatDateToYMD(d) {
  if (!d) return '';
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

// Indian railway date format e.g. "Sun, 04 Oct 2026"
function formatIndianDisplayDate(dateStr) {
  const d = parseDateParts(dateStr);
  if (!d) return dateStr || '';
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const dayName = days[d.getDay()];
  const monthName = months[d.getMonth()];
  const dayNum = String(d.getDate()).padStart(2, '0');
  return `${dayName}, ${dayNum} ${monthName} ${d.getFullYear()}`;
}

// Indian railway full date format e.g. "Sunday, 04 Oct 2026"
function formatIndianFullDisplayDate(dateStr) {
  const d = parseDateParts(dateStr);
  if (!d) return dateStr || '';
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const dayName = days[d.getDay()];
  const monthName = months[d.getMonth()];
  const dayNum = String(d.getDate()).padStart(2, '0');
  return `${dayName}, ${dayNum} ${monthName} ${d.getFullYear()}`;
}

// Attach calendar picker click handlers (showPicker API)
function attachDatePickerHelpers(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;

  // Clicking on the input directly invokes browser date picker
  input.addEventListener('click', () => {
    try {
      if (typeof input.showPicker === 'function') {
        input.showPicker();
      }
    } catch (e) {}
  });

  // Clicking anywhere on the wrapper container
  const wrapper = input.closest('.date-input-wrapper');
  if (wrapper) {
    wrapper.addEventListener('click', (e) => {
      if (e.target !== input) {
        input.focus();
        try {
          if (typeof input.showPicker === 'function') {
            input.showPicker();
          }
        } catch (e) {}
      }
    });
  }
}

// Synchronize date input values between Route and Train forms
function syncDateInputs(dateStr) {
  if (!dateStr) return;
  const dateInputRoute = document.getElementById('input-date');
  const dateInputTrain = document.getElementById('input-date-train');
  if (dateInputRoute && dateInputRoute.value !== dateStr) dateInputRoute.value = dateStr;
  if (dateInputTrain && dateInputTrain.value !== dateStr) dateInputTrain.value = dateStr;
}

// Synchronize date mode selects between Route and Train forms
function syncDateModes(mode) {
  if (!mode) return;
  const modeRoute = document.getElementById('select-date-mode');
  const modeTrain = document.getElementById('select-date-mode-train');
  if (modeRoute && modeRoute.value !== mode) modeRoute.value = mode;
  if (modeTrain && modeTrain.value !== mode) modeTrain.value = mode;
}

// Handles user picking a date from calendar picker
function onJourneyDateChanged(newDateStr) {
  if (!newDateStr) return;
  const todayStr = formatDateToYMD(new Date());
  if (newDateStr < todayStr) {
    if (typeof showToast === 'function') {
      showToast('Journey date cannot be in the past.', 'warning', 'Invalid Date');
    }
    newDateStr = todayStr;
  }
  syncDateInputs(newDateStr);
  syncDateModes('specific');
  updateDateModeUI();
  updateDateDisplayAndWeekStrip();
  performSearch();
}

// Switch between Route Search and Train Number/Name Search
function setSearchMode(mode) {
  currentSearchMode = mode;
  const routeForm = document.getElementById('search-filter-form');
  const trainForm = document.getElementById('train-number-search-form');
  const tabBtnRoute = document.getElementById('tab-btn-route');
  const tabBtnTrain = document.getElementById('tab-btn-train');

  if (mode === 'route') {
    if (routeForm) routeForm.style.display = 'grid';
    if (trainForm) trainForm.style.display = 'none';
    if (tabBtnRoute) tabBtnRoute.classList.add('active');
    if (tabBtnTrain) tabBtnTrain.classList.remove('active');
  } else {
    if (routeForm) routeForm.style.display = 'none';
    if (trainForm) trainForm.style.display = 'grid';
    if (tabBtnRoute) tabBtnRoute.classList.remove('active');
    if (tabBtnTrain) tabBtnTrain.classList.add('active');
  }
  updateDateModeUI();
}

// Sync Date Mode UI (All Dates vs Specific Date)
function updateDateModeUI() {
  const isTrain = currentSearchMode === 'train';
  const modeSelect = isTrain 
    ? document.getElementById('select-date-mode-train')
    : document.getElementById('select-date-mode');
  const selectedMode = modeSelect ? modeSelect.value : 'specific';

  // Keep both mode selectors synchronized
  syncDateModes(selectedMode);

  const routeForm = document.getElementById('search-filter-form');
  const trainForm = document.getElementById('train-number-search-form');

  const groupJourneyDateRoute = document.getElementById('group-journey-date');
  const groupJourneyDateTrain = document.getElementById('group-journey-date-train');

  const dateInputRoute = document.getElementById('input-date');
  const dateInputTrain = document.getElementById('input-date-train');

  const dateNavContainer = document.getElementById('date-navigation-container');
  const nonRunningFilterGroup = document.getElementById('filter-group-non-running');

  if (selectedMode === 'all') {
    if (groupJourneyDateRoute) groupJourneyDateRoute.style.display = 'none';
    if (groupJourneyDateTrain) groupJourneyDateTrain.style.display = 'none';
    if (dateInputRoute) dateInputRoute.required = false;
    if (dateInputTrain) dateInputTrain.required = false;

    if (routeForm) routeForm.style.gridTemplateColumns = '1.2fr auto 1.2fr 1fr 1fr 1fr auto';
    if (trainForm) trainForm.style.gridTemplateColumns = '2fr 1fr 1fr 1fr auto';

    if (dateNavContainer) dateNavContainer.style.display = 'none';
    if (nonRunningFilterGroup) nonRunningFilterGroup.style.display = 'none';
  } else {
    // Specific Date mode
    if (groupJourneyDateRoute) groupJourneyDateRoute.style.display = 'block';
    if (groupJourneyDateTrain) groupJourneyDateTrain.style.display = 'block';
    if (dateInputRoute) dateInputRoute.required = true;
    if (dateInputTrain) dateInputTrain.required = true;

    if (routeForm) routeForm.style.gridTemplateColumns = '1.2fr auto 1.2fr 0.95fr 1.15fr 1fr 1fr auto';
    if (trainForm) trainForm.style.gridTemplateColumns = '1.8fr 1fr 1.15fr 1fr 1fr auto';

    const todayStr = formatDateToYMD(new Date());
    if (dateInputRoute && !dateInputRoute.value) dateInputRoute.value = todayStr;
    if (dateInputTrain && !dateInputTrain.value) dateInputTrain.value = todayStr;

    if (dateNavContainer) dateNavContainer.style.display = 'block';
    if (nonRunningFilterGroup) nonRunningFilterGroup.style.display = 'block';

    updateDateDisplayAndWeekStrip();
  }
}

// Current journey date value
function getSelectedDateStr() {
  const isTrain = currentSearchMode === 'train';
  const dateInput = isTrain
    ? document.getElementById('input-date-train')
    : document.getElementById('input-date');
  return dateInput?.value || formatDateToYMD(new Date());
}

// Programmatically set journey date and trigger search
function setSelectedDateStr(dateStr, triggerSearch = true) {
  syncDateInputs(dateStr);
  syncDateModes('specific');

  updateDateModeUI();
  updateDateDisplayAndWeekStrip();

  if (triggerSearch) {
    performSearch();
  }
}

// Renders the 7-day compact week selector strip for the week containing selected date
function updateDateDisplayAndWeekStrip() {
  const currentYMD = getSelectedDateStr();
  const journeyDateText = document.getElementById('journey-date-text');
  if (journeyDateText) {
    journeyDateText.textContent = formatIndianFullDisplayDate(currentYMD);
  }

  const weekStrip = document.getElementById('week-strip-container');
  if (!weekStrip) return;

  const currentD = parseDateParts(currentYMD) || new Date();
  const todayD = new Date();
  todayD.setHours(0, 0, 0, 0);

  // Find the Sunday of the week containing currentD
  const sundayD = new Date(currentD.getFullYear(), currentD.getMonth(), currentD.getDate());
  sundayD.setDate(sundayD.getDate() - sundayD.getDay());

  const daysArr = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  let chipsHtml = '';
  for (let i = 0; i < 7; i++) {
    const d = new Date(sundayD.getFullYear(), sundayD.getMonth(), sundayD.getDate() + i);
    d.setHours(0, 0, 0, 0);
    const ymd = formatDateToYMD(d);
    const dayName = daysArr[d.getDay()];
    const dayNum = String(d.getDate()).padStart(2, '0');
    const isSelected = (ymd === currentYMD);
    const isPast = (d < todayD);

    if (isPast) {
      chipsHtml += `
        <div class="week-strip-chip past-day" title="Past dates cannot be selected">
          <span class="week-day-name">${dayName}</span>
          <span class="week-day-num">${dayNum}</span>
        </div>
      `;
    } else {
      chipsHtml += `
        <div class="week-strip-chip ${isSelected ? 'active' : ''}" onclick="setSelectedDateStr('${ymd}', true)" title="${dayName}, ${dayNum} (${ymd})">
          <span class="week-day-name">${dayName}</span>
          <span class="week-day-num">${dayNum}</span>
        </div>
      `;
    }
  }
  weekStrip.innerHTML = chipsHtml;
}

// Step previous day, today, or next day (Section 13)
function navigateDate(offset) {
  if (offset === 0) {
    const todayStr = formatDateToYMD(new Date());
    setSelectedDateStr(todayStr, true);
    return;
  }

  const currentYMD = getSelectedDateStr();
  const d = parseDateParts(currentYMD) || new Date();
  d.setDate(d.getDate() + offset);

  const todayD = new Date();
  todayD.setHours(0, 0, 0, 0);
  if (d < todayD) {
    if (typeof showToast === 'function') {
      showToast('Cannot select a date in the past.', 'warning', 'Past Date');
    }
    return;
  }

  setSelectedDateStr(formatDateToYMD(d), true);
}

// Prefill form inputs from URL parameters
function populateFormFromUrl() {
  const source = getQueryParam('source');
  const destination = getQueryParam('destination');
  const trainNumber = getQueryParam('train_number');
  const trainName = getQueryParam('train_name');
  const query = getQueryParam('query') || getQueryParam('q');
  const date = getQueryParam('date');
  const dateModeParam = getQueryParam('date_mode');
  const classType = getQueryParam('class');
  const quota = getQueryParam('quota');
  const runningDayParam = getQueryParam('running_day');
  const showNonRunningParam = getQueryParam('show_non_running');

  const todayStr = formatDateToYMD(new Date());

  // Determine initial date mode:
  // Default is 'specific' if not explicitly set to 'all'
  let initialMode = 'specific';
  if (dateModeParam) {
    initialMode = dateModeParam.toLowerCase() === 'all' ? 'all' : 'specific';
  }

  const modeRoute = document.getElementById('select-date-mode');
  const modeTrain = document.getElementById('select-date-mode-train');
  if (modeRoute) modeRoute.value = initialMode;
  if (modeTrain) modeTrain.value = initialMode;

  // Set date fields: set min to today, do NOT set max so user can select any future date
  const chosenDate = (date && date >= todayStr) ? date : todayStr;
  const dateInputRoute = document.getElementById('input-date');
  const dateInputTrain = document.getElementById('input-date-train');
  if (dateInputRoute) {
    dateInputRoute.min = todayStr;
    dateInputRoute.removeAttribute('max');
    dateInputRoute.value = chosenDate;
  }
  if (dateInputTrain) {
    dateInputTrain.min = todayStr;
    dateInputTrain.removeAttribute('max');
    dateInputTrain.value = chosenDate;
  }

  // Quota & Class
  if (classType) {
    if (document.getElementById('select-class')) document.getElementById('select-class').value = classType;
    if (document.getElementById('select-class-train')) document.getElementById('select-class-train').value = classType;
  }
  if (quota) {
    if (document.getElementById('select-quota')) document.getElementById('select-quota').value = quota;
    if (document.getElementById('select-quota-train')) document.getElementById('select-quota-train').value = quota;
  }

  // Running day filter
  if (runningDayParam && document.getElementById('filter-running-day')) {
    document.getElementById('filter-running-day').value = runningDayParam;
  }

  // Non-running toggle
  if (showNonRunningParam && document.getElementById('toggle-show-non-running')) {
    document.getElementById('toggle-show-non-running').checked = (showNonRunningParam === '1' || showNonRunningParam === 'true');
  }

  // If train number or query provided in URL, switch to train mode
  if (trainNumber || trainName || (query && /^\d{5}$/.test(query.trim()))) {
    setSearchMode('train');
    const inputTrain = document.getElementById('input-train-query');
    if (inputTrain) {
      inputTrain.value = trainNumber || trainName || query;
    }
  } else {
    if (source) document.getElementById('input-from').value = source;
    if (destination) document.getElementById('input-to').value = destination;
  }
}

// Setup floating debounced autocomplete dropdown for station inputs
function setupAutocomplete(inputId, dropdownId) {
  const input = document.getElementById(inputId);
  const dropdown = document.getElementById(dropdownId);
  if (!input || !dropdown) return;

  let activeIndex = -1;

  input.addEventListener('input', () => {
    clearTimeout(debounceTimers[inputId]);
    const q = input.value.trim();

    if (q.length === 0) {
      dropdown.style.display = 'none';
      dropdown.innerHTML = '';
      return;
    }

    debounceTimers[inputId] = setTimeout(async () => {
      try {
        const res = await fetchApi(`/stations/search?q=${encodeURIComponent(q)}&limit=8`);
        if (res.success && res.data && res.data.length > 0) {
          renderDropdownItems(res.data, input, dropdown);
          dropdown.style.display = 'block';
          activeIndex = -1;
        } else {
          dropdown.innerHTML = `<div style="padding: 10px 14px; color: #94a3b8; font-size: 0.85rem;">No matching stations found</div>`;
          dropdown.style.display = 'block';
        }
      } catch (err) {
        console.error('Autocomplete fetch error:', err);
      }
    }, 180);
  });

  input.addEventListener('focus', () => {
    if (input.value.trim().length > 0 && dropdown.children.length > 0) {
      dropdown.style.display = 'block';
    }
  });

  // Keyboard navigation
  input.addEventListener('keydown', (e) => {
    const items = dropdown.querySelectorAll('.autocomplete-item');
    if (!items.length || dropdown.style.display === 'none') return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      updateActiveItem(items, activeIndex);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
      updateActiveItem(items, activeIndex);
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0 && activeIndex < items.length) {
        e.preventDefault();
        items[activeIndex].click();
      }
    } else if (e.key === 'Escape') {
      dropdown.style.display = 'none';
    }
  });

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });
}

function updateActiveItem(items, index) {
  items.forEach((it, i) => {
    if (i === index) {
      it.classList.add('active');
      it.scrollIntoView({ block: 'nearest' });
    } else {
      it.classList.remove('active');
    }
  });
}

function renderDropdownItems(stations, input, dropdown) {
  dropdown.innerHTML = stations.map(s => `
    <div class="autocomplete-item" data-code="${s.code}" data-name="${s.name}" data-city="${s.city}">
      <div>
        <span style="font-weight: 600;">${s.name}</span>
        <span class="station-city-badge">${s.city}, ${s.state}</span>
      </div>
      <span class="station-code-badge">${s.code}</span>
    </div>
  `).join('');

  dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
    item.addEventListener('click', () => {
      const code = item.getAttribute('data-code');
      const name = item.getAttribute('data-name');
      input.value = `${name} (${code})`;
      input.dataset.stationCode = code;
      dropdown.style.display = 'none';
    });
  });
}

function setupEventListeners() {
  // Route Search Form
  const searchForm = document.getElementById('search-filter-form');
  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      performSearch();
    });
  }

  // Train Number Search Form
  const trainForm = document.getElementById('train-number-search-form');
  if (trainForm) {
    trainForm.addEventListener('submit', (e) => {
      e.preventDefault();
      performSearch();
    });
  }

  // Date Mode Selectors
  const modeRoute = document.getElementById('select-date-mode');
  if (modeRoute) {
    modeRoute.addEventListener('change', (e) => {
      syncDateModes(e.target.value);
      updateDateModeUI();
      performSearch();
    });
  }

  const modeTrain = document.getElementById('select-date-mode-train');
  if (modeTrain) {
    modeTrain.addEventListener('change', (e) => {
      syncDateModes(e.target.value);
      updateDateModeUI();
      performSearch();
    });
  }

  // Date Inputs
  const dateInputRoute = document.getElementById('input-date');
  if (dateInputRoute) {
    dateInputRoute.addEventListener('change', (e) => {
      onJourneyDateChanged(e.target.value);
    });
  }

  const dateInputTrain = document.getElementById('input-date-train');
  if (dateInputTrain) {
    dateInputTrain.addEventListener('change', (e) => {
      onJourneyDateChanged(e.target.value);
    });
  }

  // Date Navigation buttons
  const prevBtn = document.getElementById('btn-prev-day');
  if (prevBtn) prevBtn.addEventListener('click', () => navigateDate(-1));

  const todayBtn = document.getElementById('btn-today');
  if (todayBtn) todayBtn.addEventListener('click', () => navigateDate(0));

  const nextBtn = document.getElementById('btn-next-day');
  if (nextBtn) nextBtn.addEventListener('click', () => navigateDate(1));

  // Swap button
  const swapBtn = document.getElementById('btn-swap-stations');
  if (swapBtn) {
    swapBtn.addEventListener('click', () => {
      const from = document.getElementById('input-from');
      const to = document.getElementById('input-to');
      const tempVal = from.value;
      const tempCode = from.dataset.stationCode;

      from.value = to.value;
      from.dataset.stationCode = to.dataset.stationCode || '';

      to.value = tempVal;
      to.dataset.stationCode = tempCode || '';
    });
  }

  // Running Day Filter
  const runningDaySelect = document.getElementById('filter-running-day');
  if (runningDaySelect) {
    runningDaySelect.addEventListener('change', () => {
      applyFiltersAndSort();
    });
  }

  // Show Non-running toggle
  const nonRunningToggle = document.getElementById('toggle-show-non-running');
  if (nonRunningToggle) {
    nonRunningToggle.addEventListener('change', () => {
      // Re-trigger search to ensure backend returns non-running trains if specific date mode
      performSearch();
    });
  }

  // Sorting
  const sortSelect = document.getElementById('sort-by');
  if (sortSelect) {
    sortSelect.addEventListener('change', applyFiltersAndSort);
  }

  // Filter checkboxes & radio controls
  document.querySelectorAll('.filter-control').forEach(el => {
    el.addEventListener('change', applyFiltersAndSort);
  });
}

// Extract raw station code or city query from input
function parseStationInput(val) {
  if (!val) return '';
  const match = val.match(/\(([^)]+)\)/);
  if (match) return match[1].trim();
  return val.trim();
}

// Main Search Trigger
async function performSearch() {
  const container = document.getElementById('train-results-container');
  const countBadge = document.getElementById('results-count-badge');

  if (container) {
    container.innerHTML = `
      <div class="state-box">
        <div class="spinner"></div>
        <h3>Searching Railway Network...</h3>
        <p>Querying verified train database, operating schedules, route halts, and live seat inventories.</p>
      </div>
    `;
  }

  const isTrain = currentSearchMode === 'train';
  const dateModeSelect = isTrain ? document.getElementById('select-date-mode-train') : document.getElementById('select-date-mode');
  const dateMode = dateModeSelect ? dateModeSelect.value : 'all';
  currentServerDateMode = dateMode;

  const runningDay = document.getElementById('filter-running-day')?.value || 'all';
  const showNonRunning = document.getElementById('toggle-show-non-running')?.checked ? '1' : '0';

  let queryUrl = '/trains/search?';

  if (isTrain) {
    const trainQuery = document.getElementById('input-train-query')?.value.trim() || '';
    const date = document.getElementById('input-date-train')?.value || '';
    const classType = document.getElementById('select-class-train')?.value || '';
    const quota = document.getElementById('select-quota-train')?.value || 'GN';

    if (!trainQuery) {
      if (container) {
        container.innerHTML = `
          <div class="state-box">
            <i class="fa-solid fa-train"></i>
            <h3>Enter Train Number or Name</h3>
            <p>Please enter a 5-digit train number (e.g. 12951, 12015, 20977) or name (e.g. Rajdhani, Shatabdi) to search.</p>
          </div>
        `;
      }
      return;
    }

    if (/^\d{5}$/.test(trainQuery)) {
      queryUrl += `train_number=${encodeURIComponent(trainQuery)}&`;
    } else {
      queryUrl += `train_name=${encodeURIComponent(trainQuery)}&`;
    }
    queryUrl += `date_mode=${encodeURIComponent(dateMode)}&class=${encodeURIComponent(classType)}&quota=${encodeURIComponent(quota)}`;
    if (dateMode === 'specific') {
      queryUrl += `&date=${encodeURIComponent(date)}`;
    }
    if (runningDay && runningDay !== 'all') {
      queryUrl += `&running_day=${encodeURIComponent(runningDay)}`;
    }
    if (showNonRunning === '1') {
      queryUrl += `&show_non_running=1`;
    }

  } else {
    // Route Search
    const sourceRaw = document.getElementById('input-from')?.value || '';
    const destRaw = document.getElementById('input-to')?.value || '';
    const source = parseStationInput(sourceRaw);
    const destination = parseStationInput(destRaw);
    const date = document.getElementById('input-date')?.value || '';
    const classType = document.getElementById('select-class')?.value || '';
    const quota = document.getElementById('select-quota')?.value || 'GN';

    if (!source || !destination) {
      if (container) {
        container.innerHTML = `
          <div class="state-box">
            <i class="fa-solid fa-route"></i>
            <h3>Enter Source and Destination</h3>
            <p>Please enter departure and arrival stations to search available routes.</p>
          </div>
        `;
      }
      return;
    }

    queryUrl += `source=${encodeURIComponent(source)}&destination=${encodeURIComponent(destination)}&date_mode=${encodeURIComponent(dateMode)}&class=${encodeURIComponent(classType)}&quota=${encodeURIComponent(quota)}`;
    if (dateMode === 'specific') {
      queryUrl += `&date=${encodeURIComponent(date)}`;
    }
    if (runningDay && runningDay !== 'all') {
      queryUrl += `&running_day=${encodeURIComponent(runningDay)}`;
    }
    if (showNonRunning === '1') {
      queryUrl += `&show_non_running=1`;
    }
  }

  try {
    const res = await fetchApi(queryUrl);

    if (!res.success) {
      if (container) {
        container.innerHTML = `
          <div class="state-box">
            <i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-red);"></i>
            <h3>Search Error</h3>
            <p>${res.message || 'Unable to retrieve train search results.'}</p>
            <button class="btn btn-outline" onclick="performSearch()"><i class="fa-solid fa-rotate-right"></i> Try Again</button>
          </div>
        `;
      }
      return;
    }

    allTrainResults = res.trains || res.data || [];
    currentServerDateMode = res.date_mode || dateMode;
    applyFiltersAndSort();
  } catch (err) {
    console.error('performSearch exception:', err);
    if (container) {
      container.innerHTML = `
        <div class="state-box">
          <i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-red);"></i>
          <h3>Search Failed</h3>
          <p>An unexpected error occurred while processing train results. Please try again.</p>
          <button class="btn btn-outline" onclick="performSearch()"><i class="fa-solid fa-rotate-right"></i> Try Again</button>
        </div>
      `;
    }
  }
}

// Apply client-side filters and sorting to search results
function applyFiltersAndSort() {
  try {
    let filtered = [...allTrainResults];

    // AC / Non-AC filter
    const acOnly = document.getElementById('filter-ac')?.checked;
    const sleeperOnly = document.getElementById('filter-sleeper')?.checked;
    if (acOnly) {
      filtered = filtered.filter(t => (t.classes || []).some(c => ['1A', '2A', '3A', 'CC', 'EC'].includes(c.class_code)));
    }
    if (sleeperOnly) {
      filtered = filtered.filter(t => (t.classes || []).some(c => c.class_code === 'SL'));
    }

    // Departure time filter (Morning 06:00-12:00, etc.)
    const timeFilter = document.querySelector('input[name="departure-time"]:checked')?.value;
    if (timeFilter && timeFilter !== 'all') {
      filtered = filtered.filter(t => {
        const dep = t.leg_departure_time || t.departure_time;
        if (!dep || dep === 'START' || dep === '--:--') return true;
        const parts = dep.split(':');
        const hour = parseInt(parts[0], 10);
        if (isNaN(hour)) return true;
        if (timeFilter === 'morning') return hour >= 6 && hour < 12;
        if (timeFilter === 'afternoon') return hour >= 12 && hour < 18;
        if (timeFilter === 'evening') return hour >= 18 && hour < 24;
        if (timeFilter === 'night') return hour >= 0 && hour < 6;
        return true;
      });
    }

    // Running Day filter (Section 12: works for both All Dates & Specific Date)
    const runningDayFilter = document.getElementById('filter-running-day')?.value || 'all';
    if (runningDayFilter && runningDayFilter !== 'all') {
      filtered = filtered.filter(t => {
        const runInfo = t.running_status;
        if (runInfo && Array.isArray(runInfo.running_days)) {
          return runInfo.running_days.includes(runningDayFilter);
        }
        if (t.running_days_list && Array.isArray(t.running_days_list)) {
          return t.running_days_list.includes(runningDayFilter);
        }
        if (t.running_days && typeof t.running_days === 'string') {
          return t.running_days.includes(runningDayFilter);
        }
        return false;
      });
    }

    // If Specific Date mode and toggle not checked, filter out non-running trains
    const isSpecificDate = (currentServerDateMode === 'specific');
    const showNonRunning = document.getElementById('toggle-show-non-running')?.checked;
    if (isSpecificDate && !showNonRunning) {
      filtered = filtered.filter(t => t.runs_on_date !== false);
    }

    // Sorting (Section 21)
    const sortBy = document.getElementById('sort-by')?.value || 'cheapest';
    filtered.sort((a, b) => {
      if (sortBy === 'runs_selected') {
        const runScoreA = (a.runs_on_date === true) ? 2 : (a.runs_on_date === null ? 1 : 0);
        const runScoreB = (b.runs_on_date === true) ? 2 : (b.runs_on_date === null ? 1 : 0);
        if (runScoreB !== runScoreA) return runScoreB - runScoreA;
        const depA = a.leg_departure_time || a.departure_time || '--:--';
        const depB = b.leg_departure_time || b.departure_time || '--:--';
        return depA.localeCompare(depB);
      }

      const classesA = a.classes || [];
      const classesB = b.classes || [];
      const faresA = classesA.map(c => c.adjusted_fare || c.base_fare).filter(f => f > 0);
      const faresB = classesB.map(c => c.adjusted_fare || c.base_fare).filter(f => f > 0);
      const minFareA = faresA.length ? Math.min(...faresA) : 99999;
      const minFareB = faresB.length ? Math.min(...faresB) : 99999;
      
      if (sortBy === 'cheapest') return minFareA - minFareB;
      if (sortBy === 'earliest') {
        const depA = a.leg_departure_time || a.departure_time || '--:--';
        const depB = b.leg_departure_time || b.departure_time || '--:--';
        return depA.localeCompare(depB);
      }
      if (sortBy === 'duration') {
        const durMinsA = a.duration_minutes || 9999;
        const durMinsB = b.duration_minutes || 9999;
        return durMinsA - durMinsB;
      }
      if (sortBy === 'availability') {
        const availA = classesA.reduce((sum, c) => sum + (c.available_seats || 0), 0);
        const availB = classesB.reduce((sum, c) => sum + (c.available_seats || 0), 0);
        return availB - availA;
      }
      return 0;
    });

    renderTrainCards(filtered);
  } catch (err) {
    console.error('applyFiltersAndSort error:', err);
    renderTrainCards(allTrainResults);
  }
}

// Builds the railway S M T W T F S operating indicator widget
function buildRunningDaysWidget(t, isSpecificDate, dateVal) {
  const runInfo = t.running_status || {};
  const displayList = runInfo.running_days_display || t.running_days_display;

  // No data fabrication: if running days are missing
  if (!displayList || t.running_days === null || t.running_days === undefined || t.running_days === '') {
    return `
      <div class="running-days-widget">
        <div class="running-days-row">
          <span class="run-status-badge run-status-unavail">
            <i class="fa-solid fa-circle-question"></i> Running days unavailable
          </span>
        </div>
      </div>
    `;
  }

  // Render 7 standard day pills (S M T W T F S)
  const pillsHtml = displayList.map(d => {
    const isRuns = d.runs;
    const isSelected = isSpecificDate && d.is_selected;
    let stateClass = 'unavail';
    if (isRuns === true) stateClass = 'runs';
    else if (isRuns === false) stateClass = 'no-run';

    const selectedClass = isSelected ? (isRuns === false ? 'selected no-run' : 'selected') : '';
    const titleText = `${d.full}: ${isRuns ? 'Runs' : (isRuns === false ? 'Does not run' : 'Unavailable')}${isSelected ? ' (Selected Journey Date)' : ''}`;

    return `<div class="day-pill ${stateClass} ${selectedClass}" title="${titleText}">${d.day}</div>`;
  }).join('');

  // Status badge
  let statusBadge = '';
  if (isSpecificDate) {
    if (t.runs_on_date === true) {
      statusBadge = `<span class="run-status-badge run-status-runs"><i class="fa-solid fa-circle-check"></i> ${t.status_text || 'Runs on selected date'}</span>`;
    } else if (t.runs_on_date === false) {
      statusBadge = `<span class="run-status-badge run-status-not-runs"><i class="fa-solid fa-circle-xmark"></i> ${t.status_text || 'Not running on selected date'}</span>`;
    } else {
      statusBadge = `<span class="run-status-badge run-status-unavail"><i class="fa-solid fa-circle-question"></i> Running days unavailable</span>`;
    }
  } else {
    if (t.status_text && t.status_text !== 'Running days unavailable') {
      statusBadge = `<span class="run-status-badge run-status-info"><i class="fa-solid fa-calendar-days"></i> ${t.status_text}</span>`;
    } else {
      statusBadge = `<span class="run-status-badge run-status-unavail"><i class="fa-solid fa-circle-question"></i> Running days unavailable</span>`;
    }
  }

  return `
    <div class="running-days-widget">
      <div class="running-days-row">
        <div class="days-pills-row">${pillsHtml}</div>
        <div>${statusBadge}</div>
      </div>
    </div>
  `;
}

// Renders an individual train card HTML
function renderTrainCardHtml(t, isNonRunning, dateVal, quotaVal, isSpecificDate) {
  const boardCode = t.boarding_code || t.source_code || 'START';
  const boardName = t.boarding_name || t.source_name || boardCode;
  const depTime = (t.leg_departure_time && t.leg_departure_time !== 'START') ? t.leg_departure_time : (t.departure_time || '--:--');

  const deboardCode = t.deboarding_code || t.dest_code || 'END';
  const deboardName = t.deboarding_name || t.dest_name || deboardCode;
  const arrTime = (t.leg_arrival_time && t.leg_arrival_time !== 'END') ? t.leg_arrival_time : (t.arrival_time || '--:--');

  const isIntermediate = (t.boarding_code && t.source_code && t.boarding_code !== t.source_code) || (t.deboarding_code && t.dest_code && t.deboarding_code !== t.dest_code);
  const routeSubtitle = isIntermediate
    ? `Full Route: ${t.source_name || ''} (${t.source_code || ''}) ➔ ${t.dest_name || ''} (${t.dest_code || ''})`
    : `Direct Route`;

  const distanceInfo = (t.leg_distance_km && t.leg_distance_km > 0) ? `${Math.round(t.leg_distance_km)} km` : '';
  const hasRouteData = t.has_route_data !== false;

  const runningDaysWidgetHtml = buildRunningDaysWidget(t, isSpecificDate, dateVal);

  const classList = t.classes || [];
  const classBoxes = classList.map(c => {
    const isUnavailable = !c.coach_id || c.status === 'Seat availability unavailable' || c.status === 'Availability unavailable' || c.status === 'Not Applicable';
    const isAvail = !isUnavailable && (c.available_seats != null && c.available_seats > 0);
    const badgeClass = (c.status && c.status.startsWith('AVAILABLE')) ? 'badge-available' : 'badge-wl';
    const fareToShow = (c.adjusted_fare != null) ? c.adjusted_fare : (c.base_fare != null ? c.base_fare : 0);
    const fareText = (c.fare_unavailable || fareToShow <= 0 || fareToShow == null) ? 'Fare unavailable' : formatINR(fareToShow);

    let statusText = c.status || 'Availability unavailable';
    if (isNonRunning) {
      statusText = 'Not Running';
    } else if (!isSpecificDate) {
      statusText = c.status || 'Select date for live availability';
    }

    let clickHandler;
    if (isNonRunning) {
      clickHandler = `showToast('This train does not operate on ${formatIndianDisplayDate(dateVal)}. Please select another running day.', 'warning', 'Train Not Running')`;
    } else if (c.status === 'Not Applicable') {
      clickHandler = `showToast('Quota ${quotaVal} is not applicable for class ${c.class_code}.', 'info', 'Not Applicable')`;
    } else if (!isSpecificDate) {
      clickHandler = `showToast('Please select a specific journey date above to check seat availability and book.', 'info', 'Select Date')`;
    } else {
      clickHandler = `selectCoachAndProceed(${t.id}, ${c.coach_id || 'null'}, '${c.class_code}', '${dateVal}', '${quotaVal}', '${boardCode}', '${deboardCode}', ${fareToShow})`;
    }

    return `
      <div class="class-card-box ${isAvail && !isNonRunning ? '' : 'class-wl'}" onclick="${clickHandler}">
        <div class="class-top">
          <span class="class-title">${c.class_code}</span>
          <span class="class-fare">${fareText}</span>
        </div>
        <div class="class-bottom">
          <span class="badge ${badgeClass}">${statusText}</span>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="card train-result-card ${isNonRunning ? 'non-running-train-card' : ''}" style="margin-bottom: 1.5rem;">
      <div class="train-card-header">
        <div>
          <div class="train-title-row">
            <span class="train-number">#${t.train_number}</span>
            <h3 class="train-name">${t.train_name}</h3>
            <span class="badge" style="background: rgba(19, 64, 116, 0.08); color: var(--primary-navy);">${t.train_type || 'Express'}</span>
            ${isNonRunning ? `<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #dc2626; font-weight: 700;"><i class="fa-solid fa-calendar-xmark"></i> NOT RUNNING ON SELECTED DATE</span>` : ''}
            ${!hasRouteData ? `<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #b45309;"><i class="fa-solid fa-clock-rotate-left"></i> Timetable Route Pending</span>` : ''}
            ${quotaVal !== 'GN' ? `<span class="badge" style="background: rgba(243, 114, 44, 0.15); color: #c2410c;">Quota: ${quotaVal}</span>` : ''}
          </div>
          ${runningDaysWidgetHtml}
        </div>
        <div class="train-card-actions">
          <a href="live-tracking.html?train_id=${t.id}" class="btn btn-sm btn-outline" title="Track Live Location">
            <i class="fa-solid fa-satellite-dish" style="color: var(--accent-orange);"></i> Live Track
          </a>
        </div>
      </div>

      <div class="train-schedule-bar">
        <div class="station-stop">
          <span class="time">${depTime}</span>
          <span class="code">${boardCode}</span>
          <span class="name">${boardName}</span>
        </div>

        <div class="duration-indicator">
          <span class="duration-text">${t.duration || 'N/A'}</span>
          <div class="duration-line">
            <i class="fa-solid fa-train"></i>
          </div>
          <span class="route-sub">${routeSubtitle}${distanceInfo ? ' • ' + distanceInfo : ''}</span>
        </div>

        <div class="station-stop text-right">
          <span class="time">${arrTime}</span>
          <span class="code">${deboardCode}</span>
          <span class="name">${deboardName}</span>
        </div>
      </div>

      <div class="classes-row-label">
        <span>Available Classes & Fares:</span>
      </div>

      <div class="classes-grid">
        ${classBoxes}
      </div>
    </div>
  `;
}

// Render Train Cards with Running Days & Non-running grouping
function renderTrainCards(trains) {
  const container = document.getElementById('train-results-container');
  const countBadge = document.getElementById('results-count-badge');
  const heading = document.getElementById('search-results-heading');
  
  const isTrain = currentSearchMode === 'train';
  const isSpecificDate = (currentServerDateMode === 'specific');
  const dateVal = getSelectedDateStr();
  
  const quotaVal = (isTrain
    ? document.getElementById('select-quota-train')?.value
    : document.getElementById('select-quota')?.value) || 'GN';

  if (!container) return;

  if (trains.length === 0) {
    if (countBadge) countBadge.textContent = '0 Trains Found';
    if (heading) heading.textContent = isSpecificDate ? `Trains on ${formatIndianDisplayDate(dateVal)}` : 'Available Trains';
    container.innerHTML = `
      <div class="state-box">
        <i class="fa-solid fa-train"></i>
        <h3>No Trains Found</h3>
        <p>No direct trains match your selected criteria. Try selecting "All Dates", choosing another running day, or enabling "Show trains not running on selected date".</p>
        <button class="btn btn-outline" onclick="resetFilters()"><i class="fa-solid fa-arrows-rotate"></i> Reset Filters</button>
      </div>
    `;
    return;
  }

  // Update header text based on date mode
  if (isSpecificDate) {
    const formattedDate = formatIndianDisplayDate(dateVal);
    if (heading) heading.textContent = `Available Trains on ${formattedDate}`;
  } else {
    if (heading) heading.textContent = 'All Available Trains on Route';
  }

  // Group into operating vs non-operating if in specific date mode
  let operatingTrains = trains;
  let nonOperatingTrains = [];

  if (isSpecificDate) {
    operatingTrains = trains.filter(t => t.runs_on_date !== false);
    nonOperatingTrains = trains.filter(t => t.runs_on_date === false);
  }

  if (countBadge) {
    if (isSpecificDate && nonOperatingTrains.length > 0) {
      countBadge.textContent = `${operatingTrains.length} Operating (${trains.length} Total)`;
    } else {
      countBadge.textContent = `${trains.length} Train${trains.length !== 1 ? 's' : ''} Found`;
    }
  }

  let html = '';

  // 1. Operating trains
  if (operatingTrains.length > 0) {
    operatingTrains.forEach(t => {
      html += renderTrainCardHtml(t, false, dateVal, quotaVal, isSpecificDate);
    });
  } else if (isSpecificDate && nonOperatingTrains.length > 0) {
    html += `
      <div class="state-box" style="margin-bottom: 1.5rem; padding: 1.5rem;">
        <i class="fa-solid fa-calendar-xmark" style="color: var(--accent-orange);"></i>
        <h3>No Trains Operating on ${formatIndianDisplayDate(dateVal)}</h3>
        <p>There are ${nonOperatingTrains.length} train(s) running on this route on other days of the week, shown below.</p>
      </div>
    `;
  }

  // 2. Section 10: Non-running trains on this route
  if (isSpecificDate && nonOperatingTrains.length > 0) {
    html += `
      <div class="non-running-section-header" style="margin-top: 2.25rem; margin-bottom: 1.25rem; padding-top: 1.5rem; border-top: 2px dashed #cbd5e1;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
          <h3 style="font-size: 1.15rem; color: #475569; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-triangle-exclamation" style="color: #ef4444;"></i>
            OTHER TRAINS ON THIS ROUTE <span style="font-size: 0.85rem; font-weight: 500; color: #64748b;">(Not running on ${formatIndianDisplayDate(dateVal)})</span>
          </h3>
          <span class="badge" style="background: #f1f5f9; color: #64748b; font-size: 0.8rem;">${nonOperatingTrains.length} Train(s)</span>
        </div>
        <p style="font-size: 0.82rem; color: #64748b; margin-top: 4px;">These trains operate between these stations on other days of the week.</p>
      </div>
    `;

    nonOperatingTrains.forEach(t => {
      html += renderTrainCardHtml(t, true, dateVal, quotaVal, isSpecificDate);
    });
  }

  container.innerHTML = html;
}

// Navigate to seat selection
function selectCoachAndProceed(trainId, coachId, classCode, date, quota, boardCode, deboardCode, fare) {
  if (!coachId || coachId === 'null' || coachId === 'undefined') {
    if (typeof showToast === 'function') {
      showToast('Seat booking is currently unavailable for this train.', 'warning', 'Unavailable');
    }
    return;
  }
  let url = `seat-selection.html?train_id=${trainId}&coach_id=${coachId}&class=${encodeURIComponent(classCode)}&date=${encodeURIComponent(date)}&quota=${encodeURIComponent(quota)}`;
  if (boardCode && deboardCode) {
    url += `&from=${encodeURIComponent(boardCode)}&to=${encodeURIComponent(deboardCode)}`;
  }
  if (fare && fare > 0) {
    url += `&fare=${encodeURIComponent(fare)}`;
  }
  window.location.href = url;
}

// Reset all sidebar filters
function resetFilters() {
  document.querySelectorAll('.filter-control').forEach(el => {
    if (el.type === 'checkbox') el.checked = false;
    if (el.type === 'radio' && el.value === 'all') el.checked = true;
  });
  const sort = document.getElementById('sort-by');
  if (sort) sort.value = 'cheapest';
  const runningDaySelect = document.getElementById('filter-running-day');
  if (runningDaySelect) runningDaySelect.value = 'all';

  applyFiltersAndSort();
}
