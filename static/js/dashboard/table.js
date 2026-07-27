'use strict';

import { state, PAGE_SIZE } from './state.js';
import { renderChartFromState } from './chart.js';
import { showToast } from './toast.js';
import { resetChartFilters } from './chart-controls.js';

export function updateDashboard(data) {
    const s = data.summary || {};

    document.getElementById('summary-total-events').textContent = s.total_events ?? '0';
    document.getElementById('summary-mean-duration').textContent = s.mean_duration ?? '0.0';
    document.getElementById('dur-unit').textContent = s.total_events ? 'hrs' : '';
    document.getElementById('summary-highest-peak').textContent = s.highest_peak ?? '0.0';
    document.getElementById('peak-unit').textContent = s.total_events ? 'mm/h' : '';

    state.rawRainfallTimeseries = data.rainfall_timeseries || [];
    state.rawTemperatureTimeseries = data.temperature_timeseries || [];
    state.rawEvents = data.events || [];
    state.rainfallTimeseries = state.rawRainfallTimeseries;
    state.temperatureTimeseries = state.rawTemperatureTimeseries;
    state.allEvents = state.rawEvents;
    state.currentPage = 1;

    resetChartFilters();
    renderTable();
    renderChartFromState();
}

export function renderTable() {
    const body = document.getElementById('eventTableBody');
    body.innerHTML = '';

    if (state.allEvents.length === 0) {
        body.innerHTML = `
            <tr>
                <td colspan="6" class="data-table__empty">
                    <span class="material-symbols-outlined" style="font-size:40px;display:block;margin-bottom:8px;opacity:0.25;">water_drop</span>
                    No rainfall events detected in the selected window.
                </td>
            </tr>`;
        updatePagination(0);
        return;
    }

    const totalPages = Math.ceil(state.allEvents.length / PAGE_SIZE);
    const slice = state.allEvents.slice(
        (state.currentPage - 1) * PAGE_SIZE,
        state.currentPage * PAGE_SIZE
    );

    slice.forEach(ev => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(ev.start_timestamp)}</td>
            <td>${formatDate(ev.end_timestamp)}</td>
            <td><strong>${ev.duration_hours ?? '—'}</strong> hrs</td>
            <td><strong>${Number(ev.peak_value || 0).toFixed(2)}</strong> <small style="color:var(--color-text-muted);">mm/h</small></td>
            <td style="color:var(--color-primary);"><strong>${Number(ev.total_volume || 0).toFixed(2)}</strong> <small style="opacity:0.6;">mm</small></td>
            <td style="text-align:right;">${buildBadge(ev)}</td>`;
        body.appendChild(tr);
    });

    updatePagination(totalPages);
}

function formatDate(iso) {
    return iso ? new Date(iso).toLocaleString() : '—';
}

function buildBadge(ev) {
    const peak = Number(ev.peak_value);
    if (peak >= 10) {
        return '<span class="badge badge--alert">Alert</span>';
    }
    if (ev.is_cold_event) {
        return '<span class="badge badge--cold">Cold</span>';
    }
    return '<span class="badge badge--stable">Stable</span>';
}

function updatePagination(totalPages) {
    const start = (state.currentPage - 1) * PAGE_SIZE + 1;
    const end = Math.min(state.currentPage * PAGE_SIZE, state.allEvents.length);

    document.getElementById('paginationInfo').textContent = state.allEvents.length > 0
        ? `Showing ${start}–${end} of ${state.allEvents.length} events`
        : 'Showing 0 events';

    const pageNumbers = document.getElementById('pageNumbers');
    pageNumbers.innerHTML = '';

    const maxVisible = 5;
    let startPage = Math.max(1, state.currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage + 1 < maxVisible) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    for (let p = startPage; p <= endPage; p++) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = p;
        btn.className = `page-btn${p === state.currentPage ? ' active' : ''}`;
        btn.addEventListener('click', () => {
            state.currentPage = p;
            renderTable();
        });
        pageNumbers.appendChild(btn);
    }

    document.getElementById('prev-page').disabled = state.currentPage <= 1;
    document.getElementById('next-page').disabled = state.currentPage >= totalPages || totalPages === 0;
}

export function initTableControls() {
    document.getElementById('prev-page').addEventListener('click', () => {
        if (state.currentPage > 1) {
            state.currentPage--;
            renderTable();
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        const totalPages = Math.ceil(state.allEvents.length / PAGE_SIZE);
        if (state.currentPage < totalPages) {
            state.currentPage++;
            renderTable();
        }
    });

    document.getElementById('exportBtn').addEventListener('click', exportCSV);
}

function exportCSV() {
    if (state.allEvents.length === 0) {
        showToast('No events to export.', 'warning');
        return;
    }

    const rows = [
        ['Event Start', 'Event End', 'Duration (hrs)', 'Peak (mm/hr)', 'Total Volume (mm)', 'Status'],
        ...state.allEvents.map(ev => [
            ev.start_timestamp ? new Date(ev.start_timestamp).toLocaleString() : '',
            ev.end_timestamp ? new Date(ev.end_timestamp).toLocaleString() : '',
            ev.duration_hours ?? '',
            ev.peak_value ?? '',
            ev.total_volume ?? '',
            Number(ev.peak_value) >= 10 ? 'Alert' : ev.is_cold_event ? 'Cold' : 'Stable',
        ]),
    ];

    const csv = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hydrocore_events_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('CSV export started.', 'success');
}
