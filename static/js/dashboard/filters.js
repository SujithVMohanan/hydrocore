'use strict';

import { state } from './state.js';
import { loadDashboardData } from './api.js';
import { showToast } from './toast.js';
import { clearBasinDropdown, getBasinDropdownLabel } from './basin-dropdown.js';

const FP_CONFIG = {
    enableTime: true,
    dateFormat: 'Y-m-d H:i',
    altInput: true,
    altFormat: 'M j, Y — H:i',
    time_24hr: true,
    allowInput: false,
};

export function initFilters() {
    initDatePickers();
    initForm();
    initQuickRangePills();
    initFilterChips();
    initResetButton();
    initDetectModal();
}

function initDatePickers() {
    state.startPicker = flatpickr('#start_date', {
        ...FP_CONFIG,
        onChange: updateFilterChips,
    });
    state.endPicker = flatpickr('#end_date', {
        ...FP_CONFIG,
        onChange: updateFilterChips,
    });
}

function initForm() {
    document.getElementById('dashboard-form').addEventListener('submit', (e) => {
        e.preventDefault();

        const basinId = document.getElementById('basin-select').value;
        if (!basinId) {
            showToast('Please select a catchment basin first.', 'warning');
            return;
        }

        state.pendingBasinId = basinId;
        state.pendingStartDate = state.startPicker.selectedDates[0] || null;
        state.pendingEndDate = state.endPicker.selectedDates[0] || null;
        state.pendingDryGap = document.getElementById('min_dry_gap_hours').value || 6;

        openDetectModal();
    });

    ['basin-select', 'min_dry_gap_hours'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', updateFilterChips);
            el.addEventListener('input', updateFilterChips);
        }
    });
}

function initQuickRangePills() {
    document.querySelectorAll('.pill[data-range]').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.pill[data-range]').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const range = pill.dataset.range;
            const now = new Date();

            if (range === 'all') {
                state.startPicker.clear();
                state.endPicker.clear();
            } else {
                const days = parseInt(range, 10);
                const start = new Date(now);
                start.setDate(start.getDate() - days);
                state.startPicker.setDate(start);
                state.endPicker.setDate(now);
            }

            updateFilterChips();
        });
    });
}

function initFilterChips() {
    window.clearFilterField = function (fieldId) {
        if (fieldId === 'start_date') {
            state.startPicker.clear();
        } else if (fieldId === 'end_date') {
            state.endPicker.clear();
        } else if (fieldId === 'min_dry_gap_hours') {
            document.getElementById('min_dry_gap_hours').value = '6';
        } else {
            clearBasinDropdown();
        }
        updateFilterChips();
    };
}

function initResetButton() {
    document.getElementById('resetFiltersBtn').addEventListener('click', () => {
        clearBasinDropdown();
        state.startPicker.clear();
        state.endPicker.clear();
        document.getElementById('min_dry_gap_hours').value = '6';
        document.querySelectorAll('.pill[data-range]').forEach(p => p.classList.remove('active'));
        updateFilterChips();
    });
}

export function updateFilterChips() {
    const bar = document.getElementById('activeFilters');
    const resetBtn = document.getElementById('resetFiltersBtn');
    const sel = document.getElementById('basin-select');
    const start = state.startPicker?.selectedDates[0];
    const end = state.endPicker?.selectedDates[0];
    const gap = document.getElementById('min_dry_gap_hours').value;
    const chips = [];

    if (sel.value) {
        const label = getBasinDropdownLabel() || sel.value;
        chips.push(chipHTML('location_on', label, 'basin-select'));
    }
    if (start) {
        chips.push(chipHTML('event_upcoming', `Start: ${start.toLocaleDateString()}`, 'start_date'));
    }
    if (end) {
        chips.push(chipHTML('event_available', `End: ${end.toLocaleDateString()}`, 'end_date'));
    }
    if (gap && gap !== '6') {
        chips.push(chipHTML('av_timer', `Gap: ${gap}h`, 'min_dry_gap_hours'));
    }

    if (chips.length > 0) {
        bar.classList.remove('hidden');
        bar.innerHTML = `<span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--color-text-muted);">Active:</span>${chips.join('')}`;
        resetBtn.classList.remove('hidden');
    } else {
        bar.classList.add('hidden');
        resetBtn.classList.add('hidden');
    }
}

function chipHTML(icon, text, fieldId) {
    return `
        <span class="filter-chip">
            <span class="material-symbols-outlined" style="font-size:14px;">${icon}</span>
            <span>${text}</span>
            <button type="button" onclick="clearFilterField('${fieldId}')">
                <span class="material-symbols-outlined" style="font-size:13px;">close</span>
            </button>
        </span>`;
}

function initDetectModal() {
    const modal = document.getElementById('detectModal');
    const backdrop = document.getElementById('detectModalBackdrop');

    backdrop.addEventListener('click', closeDetectModal);
    document.getElementById('detectCancelBtn').addEventListener('click', closeDetectModal);
    document.getElementById('detectRunBtn').addEventListener('click', async () => {
        closeDetectModal();
        await loadDashboardData();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('open')) {
            closeDetectModal();
        }
    });
}

function openDetectModal() {
    const basinName = getBasinDropdownLabel() || state.pendingBasinId;

    document.getElementById('modal-basin-name').textContent = basinName;
    document.getElementById('modal-dry-gap').textContent = `${state.pendingDryGap} hrs`;
    document.getElementById('modal-start').textContent = state.pendingStartDate
        ? state.pendingStartDate.toLocaleDateString() : 'All time';
    document.getElementById('modal-end').textContent = state.pendingEndDate
        ? state.pendingEndDate.toLocaleDateString() : 'Now';

    document.getElementById('detectModal').classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeDetectModal() {
    document.getElementById('detectModal').classList.remove('open');
    document.body.style.overflow = '';
}
