'use strict';

import { state } from './state.js';
import { updateDashboard } from './table.js';
import { showToast } from './toast.js';

export async function loadDashboardData() {
    setLoading(true);
    showChartLoading(true);

    const params = new URLSearchParams({
        ajax: 'true',
        basin_id: state.pendingBasinId,
        min_dry_gap_hours: state.pendingDryGap,
    });

    if (state.pendingStartDate) {
        params.append('start_date', new Date(state.pendingStartDate).toISOString());
    }
    if (state.pendingEndDate) {
        params.append('end_date', new Date(state.pendingEndDate).toISOString());
    }

    try {
        const res = await fetch(`?${params.toString()}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        const json = await res.json();

        if (json.status === 'success') {
            updateDashboard(json.data);
            showToast('Dashboard updated successfully.', 'success');
        } else {
            showTableError(json.message || 'Server returned an error.');
            showToast(json.message || 'Failed to load data.', 'error');
        }
    } catch (err) {
        console.error(err);
        showTableError('Network error. Please try again.');
        showToast('Network error.', 'error');
    } finally {
        setLoading(false);
        showChartLoading(false);
    }
}

function setLoading(isLoading) {
    const btn = document.getElementById('executeBtn');
    const spinner = document.getElementById('globalSpinner');
    const icon = document.getElementById('btnIcon');
    const label = document.getElementById('btnLabel');

    if (btn) {
        btn.disabled = isLoading;
    }
    if (spinner) {
        spinner.classList.toggle('hidden', !isLoading);
    }
    if (icon) {
        icon.textContent = isLoading ? 'hourglass_empty' : 'analytics';
    }
    if (label) {
        label.textContent = isLoading ? 'Analysing…' : 'Analyse';
    }
}

function showChartLoading(show) {
    const el = document.getElementById('chartLoading');
    if (el) {
        el.classList.toggle('hidden', !show);
        el.classList.toggle('show', show);
    }
}

function showTableError(msg) {
    const body = document.getElementById('eventTableBody');
    if (!body) return;
    body.innerHTML = `
        <tr>
            <td colspan="6" class="data-table__empty" style="color:var(--color-error);">
                <span class="material-symbols-outlined" style="font-size:36px;display:block;margin-bottom:8px;opacity:0.6;">error</span>
                ${msg}
            </td>
        </tr>`;
}

export { setLoading, showChartLoading };
