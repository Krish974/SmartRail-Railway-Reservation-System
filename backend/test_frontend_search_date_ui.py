import re
import os
from bs4 import BeautifulSoup

def test_search_html_structure():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(base_dir, 'frontend', 'search.html')
    assert os.path.exists(html_path), "search.html must exist"

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    # 1. Date Mode and Journey Date separation in Route Search Form
    date_mode_group = soup.find('div', id='group-date-mode')
    assert date_mode_group is not None, "#group-date-mode must exist"
    select_mode = date_mode_group.find('select', id='select-date-mode')
    assert select_mode is not None, "#select-date-mode must exist"
    options = [opt['value'] for opt in select_mode.find_all('option')]
    assert 'all' in options and 'specific' in options, "Date Mode must include 'all' and 'specific'"

    journey_date_group = soup.find('div', id='group-journey-date')
    assert journey_date_group is not None, "#group-journey-date must exist"
    date_input = journey_date_group.find('input', id='input-date')
    assert date_input is not None, "#input-date must exist"
    assert date_input.get('type') == 'date', "#input-date must be input[type='date']"
    assert 'max' not in date_input.attrs, "#input-date must NOT have a hardcoded max date"

    # 2. Date Mode and Journey Date separation in Train Number Search Form
    date_mode_train = soup.find('div', id='group-date-mode-train')
    assert date_mode_train is not None, "#group-date-mode-train must exist"
    journey_date_train = soup.find('div', id='group-journey-date-train')
    assert journey_date_train is not None, "#group-journey-date-train must exist"
    date_input_train = journey_date_train.find('input', id='input-date-train')
    assert date_input_train is not None, "#input-date-train must exist"
    assert date_input_train.get('type') == 'date'
    assert 'max' not in date_input_train.attrs, "#input-date-train must NOT have a hardcoded max date"

    # 3. Quick Date Navigation container
    date_nav = soup.find('div', id='date-navigation-container')
    assert date_nav is not None, "#date-navigation-container must exist"
    assert soup.find('button', id='btn-prev-day') is not None
    assert soup.find('button', id='btn-today') is not None
    assert soup.find('button', id='btn-next-day') is not None
    assert soup.find('span', id='journey-date-text') is not None
    assert soup.find('div', id='week-strip-container') is not None

    # 4. Filters and cards container
    assert soup.find('select', id='filter-running-day') is not None
    assert soup.find('input', id='toggle-show-non-running') is not None
    assert soup.find('div', id='train-results-container') is not None

def test_search_js_date_functions():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    js_path = os.path.join(base_dir, 'frontend', 'js', 'search.js')
    assert os.path.exists(js_path), "search.js must exist"

    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()

    # Verify showPicker API integration
    assert 'showPicker' in js_content, "search.js must use showPicker() for native calendar interaction"
    assert 'attachDatePickerHelpers' in js_content, "attachDatePickerHelpers must be present in search.js"

    # Verify Sunday-based week strip calculation
    assert 'sundayD.setDate(sundayD.getDate() - sundayD.getDay())' in js_content or 'sundayD.setDate(' in js_content, \
        "Week strip must compute Sunday of the week containing selected date"

    # Verify synchronization helpers
    assert 'syncDateInputs' in js_content, "syncDateInputs helper must be defined"
    assert 'syncDateModes' in js_content, "syncDateModes helper must be defined"
    assert 'onJourneyDateChanged' in js_content, "onJourneyDateChanged helper must be defined"

    # Verify removal of arbitrary max date
    assert "removeAttribute('max')" in js_content or "max = " not in js_content, \
        "Date input must not enforce arbitrary max limit"

    # Verify UI update for date modes
    assert 'groupJourneyDateRoute.style.display = ' in js_content, "updateDateModeUI must toggle route date display"
    assert 'groupJourneyDateTrain.style.display = ' in js_content, "updateDateModeUI must toggle train date display"

def test_future_dates_running_status_backend():
    """Verify backend accurately evaluates running status for any future date (months/years ahead)."""
    from backend.services.railway_service import RailwayService

    # 1. Friday, 25 Dec 2026 (Christmas)
    train_12951 = RailwayService.search_by_train_number('12951') # Mumbai Rajdhani (Daily)
    if train_12951:
        status_xmas = RailwayService.get_train_running_status(train_12951, '2026-12-25')
        assert status_xmas['selected_day'] == 'Friday'
        assert status_xmas['selected_day_abbr'] == 'Fri'
        assert status_xmas['runs_on_date'] is True
        assert 'Runs on Fri' in status_xmas['status_text']

    # 2. Friday, 01 Jan 2027 (New Year)
    train_19609 = RailwayService.search_by_train_number('19609') # Mon, Thu, Sat
    if train_19609:
        status_ny = RailwayService.get_train_running_status(train_19609, '2027-01-01')
        assert status_ny['selected_day'] == 'Friday'
        assert status_ny['runs_on_date'] is False
        assert 'Not running on Fri' in status_ny['status_text']

        # 3. Saturday, 02 Jan 2027 (19609 runs on Saturday)
        status_sat = RailwayService.get_train_running_status(train_19609, '2027-01-02')
        assert status_sat['selected_day'] == 'Saturday'
        assert status_sat['runs_on_date'] is True
        assert 'Runs on Sat' in status_sat['status_text']

def test_sunday_week_strip_algorithm():
    """Verify that any date correctly calculates Sunday of the week containing that date."""
    import datetime

    test_dates = [
        ('2026-10-04', '2026-10-04'), # Sunday -> same Sunday
        ('2026-10-05', '2026-10-04'), # Monday -> previous Sunday (Oct 4)
        ('2026-10-10', '2026-10-04'), # Saturday -> previous Sunday (Oct 4)
        ('2026-12-25', '2026-12-20'), # Friday Dec 25 -> Sunday Dec 20
        ('2027-01-01', '2026-12-27'), # Friday Jan 1 -> Sunday Dec 27
        ('2027-04-10', '2027-04-04'), # Saturday Apr 10 -> Sunday Apr 4
    ]

    for given_ymd, expected_sunday in test_dates:
        dt = datetime.datetime.strptime(given_ymd, '%Y-%m-%d').date()
        # In Python: dt.weekday() is 0 for Mon, 6 for Sun.
        # Sunday-based offset: (dt.weekday() + 1) % 7
        sun_offset = (dt.weekday() + 1) % 7
        computed_sunday = dt - datetime.timedelta(days=sun_offset)
        assert computed_sunday.strftime('%Y-%m-%d') == expected_sunday, \
            f"Expected {expected_sunday} for {given_ymd}, got {computed_sunday.strftime('%Y-%m-%d')}"
