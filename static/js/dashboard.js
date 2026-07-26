/* ─────────────────────────────────────────────────────────────
   HydroCore Dashboard — Main JavaScript
   Handles: AJAX data fetch, Chart.js render, table pagination,
            quick-range pills, theme toggle, detect modal, CSV export.
───────────────────────────────────────────────────────────── */

'use strict';

// ── Module-level state ──────────────────────────────────────
let rainfallChart = null;
let allEvents     = [];
let rainfallTimeseriesData    = [];
let temperatureTimeseriesData = [];
let currentPage   = 1;
const PAGE_SIZE   = 10;

// Pending form values (read when modal confirms)
let pendingBasinId   = null;
let pendingStartDate = null;
let pendingEndDate   = null;
let pendingDryGap    = 6;

// ── DOM refs (resolved after DOMContentLoaded) ──────────────
let elTotalEvents, elMeanDuration, elHighestPeak;
let elEventBody, elPaginationInfo, elPageNumbers;
let elPrevPage, elNextPage;
let elSpinner, elBtnIcon, elBtnLabel, elExecuteBtn;

// ═══════════════════════════════════════════════════════════
// ENTRY POINT
// ═══════════════════════════════════════════════════════════
window.addEventListener('DOMContentLoaded', () => {
    // Resolve DOM refs
    elTotalEvents    = document.getElementById('summary-total-events');
    elMeanDuration   = document.getElementById('summary-mean-duration');
    elHighestPeak    = document.getElementById('summary-highest-peak');
    elEventBody      = document.getElementById('eventTableBody');
    elPaginationInfo = document.getElementById('paginationInfo');
    elPageNumbers    = document.getElementById('pageNumbers');
    elPrevPage       = document.getElementById('prev-page');
    elNextPage       = document.getElementById('next-page');
    elSpinner        = document.getElementById('globalSpinner');
    elBtnIcon        = document.getElementById('btnIcon');
    elBtnLabel       = document.getElementById('btnLabel');
    elExecuteBtn     = document.getElementById('executeBtn');

    initTheme();
    initForm();
    initFilterControls();
    initFilterChips();
    initExport();
    initDetectModal();

    // Pagination buttons
    elPrevPage.addEventListener('click', () => {
        if (currentPage > 1) { currentPage--; renderTable(); }
    });
    elNextPage.addEventListener('click', () => {
        if (currentPage < Math.ceil(allEvents.length / PAGE_SIZE)) { currentPage++; renderTable(); }
    });

    // Resize chart on window resize
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => { if (rainfallChart) rainfallChart.resize(); }, 100);
    });
});

// ═══════════════════════════════════════════════════════════
// FORM — opens detect modal first, then loads dashboard data
// ═══════════════════════════════════════════════════════════
function initForm() {
    document.getElementById('dashboard-form').addEventListener('submit', (e) => {
        e.preventDefault();

        const basinId   = document.getElementById('basin-select').value;
        const startDate = document.getElementById('start_date').value;
        const endDate   = document.getElementById('end_date').value;
        const dryGap    = document.getElementById('min_dry_gap_hours').value;

        if (!basinId) {
            showToast('Please select a catchment basin first.', 'warning');
            return;
        }

        // Store pending values
        pendingBasinId   = basinId;
        pendingStartDate = startDate;
        pendingEndDate   = endDate;
        pendingDryGap    = dryGap || 6;

        openDetectModal();
    });
}

// ═══════════════════════════════════════════════════════════
// DETECT MODAL
// ═══════════════════════════════════════════════════════════
function initDetectModal() {
    const backdrop  = document.getElementById('detectModalBackdrop');
    const cancelBtn = document.getElementById('detectCancelBtn');
    const runBtn    = document.getElementById('detectRunBtn');

    // Close on backdrop or cancel
    backdrop.addEventListener('click', closeDetectModal);
    cancelBtn.addEventListener('click', closeDetectModal);

    // Run detection (which internally detects + loads dashboard data)
    runBtn.addEventListener('click', async () => {
        await runDetection();
    });

    // Keyboard close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !document.getElementById('detectModal').classList.contains('hidden')) {
            closeDetectModal();
        }
    });
}

function openDetectModal() {
    const modal = document.getElementById('detectModal');

    // Populate modal params
    const basinSelect = document.getElementById('basin-select');
    const basinName   = basinSelect.options[basinSelect.selectedIndex]?.text || pendingBasinId;
    document.getElementById('modal-basin-name').textContent = basinName;
    document.getElementById('modal-dry-gap').textContent    = `${pendingDryGap} hrs`;
    document.getElementById('modal-start').textContent      = pendingStartDate
        ? new Date(pendingStartDate).toLocaleDateString() : 'All time';
    document.getElementById('modal-end').textContent        = pendingEndDate
        ? new Date(pendingEndDate).toLocaleDateString() : 'Now';

    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.body.style.overflow = 'hidden';
}

function closeDetectModal() {
    const modal = document.getElementById('detectModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.style.overflow = '';
    setLoading(false);
}

function setDetectBtnState(loading) {
    const runBtn = document.getElementById('detectRunBtn');
    if (!runBtn) return;
    runBtn.disabled = loading;
    runBtn.classList.toggle('opacity-60', loading);
    runBtn.classList.toggle('cursor-not-allowed', loading);
}

async function runDetection() {
    // The dashboard AJAX endpoint already calls detect_and_persist_events() internally,
    // so we just close the modal and load the dashboard data.
    closeDetectModal();
    await loadDashboardData();
}

// ═══════════════════════════════════════════════════════════
// LOAD DASHBOARD DATA (existing events + timeseries)
// ═══════════════════════════════════════════════════════════
async function loadDashboardData() {
    setLoading(true);

    const params = new URLSearchParams({
        ajax             : 'true',
        basin_id         : pendingBasinId,
        min_dry_gap_hours: pendingDryGap,
    });
    if (pendingStartDate) params.append('start_date', new Date(pendingStartDate).toISOString());
    if (pendingEndDate)   params.append('end_date',   new Date(pendingEndDate).toISOString());

    try {
        const res  = await fetch(`?${params.toString()}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const json = await res.json();

        if (json.status === 'success') {
            updateDashboard(json.data);
            showToast('Dashboard updated successfully.', 'success');
        } else {
            showError(json.message || 'Server returned an error.');
            showToast(json.message || 'Failed to load data.', 'error');
        }
    } catch (err) {
        console.error(err);
        showError('Network error. Check console for details.');
        showToast('Network error.', 'error');
    } finally {
        setLoading(false);
    }
}

// ═══════════════════════════════════════════════════════════
// DASHBOARD UPDATE
// ═══════════════════════════════════════════════════════════
function updateDashboard(data) {
    const s = data.summary || {};
    elTotalEvents.textContent  = s.total_events  ?? '0';
    elMeanDuration.textContent = s.mean_duration ?? '0.0';
    document.getElementById('dur-unit').textContent  = s.total_events ? 'hrs' : '';
    elHighestPeak.textContent  = s.highest_peak  ?? '0.0';
    document.getElementById('peak-unit').textContent = s.total_events ? 'mm/h' : '';

    rainfallTimeseriesData    = data.rainfall_timeseries    || [];
    temperatureTimeseriesData = data.temperature_timeseries || [];
    allEvents                 = data.events                 || [];
    currentPage               = 1;

    renderTable();
    renderChart(rainfallTimeseriesData, temperatureTimeseriesData, allEvents);
}

// ═══════════════════════════════════════════════════════════
// TABLE & PAGINATION
// ═══════════════════════════════════════════════════════════
function renderTable() {
    elEventBody.innerHTML = '';

    if (allEvents.length === 0) {
        elEventBody.innerHTML = `
            <tr>
              <td colspan="6" class="px-xl py-16 text-center text-outline font-body-md">
                <span class="material-symbols-outlined text-[48px] block mb-3 opacity-30">water_drop</span>
                No rainfall events detected in the selected window.
              </td>
            </tr>`;
        updatePagination(0);
        return;
    }

    const totalPages = Math.ceil(allEvents.length / PAGE_SIZE);
    const slice      = allEvents.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

    slice.forEach(ev => {
        const startStr  = ev.start_timestamp ? new Date(ev.start_timestamp).toLocaleString() : '—';
        const endStr    = ev.end_timestamp   ? new Date(ev.end_timestamp).toLocaleString()   : '—';
        const peak      = Number(ev.peak_value   || 0).toFixed(2);
        const vol       = Number(ev.total_volume || 0).toFixed(2);
        const dur       = ev.duration_hours ?? '—';
        const isIntense = Number(ev.peak_value) >= 10;
        const isCold    = ev.is_cold_event;

        // Determine badge
        let badge;
        if (isIntense) {
            badge = `<span class="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-black tracking-widest bg-error/10 text-error border border-error/20">Alert</span>`;
        } else if (isCold) {
            badge = `<span class="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-black tracking-widest bg-primary/10 text-primary border border-primary/20">Cold</span>`;
        } else {
            badge = `<span class="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-black tracking-widest bg-tertiary/10 text-tertiary border border-tertiary/20">Stable</span>`;
        }

        const tr = document.createElement('tr');
        tr.className = 'hover:bg-surface-container-low dark:hover:bg-on-surface/5 transition-all duration-150 cursor-default';
        tr.style.transition = 'transform 0.15s ease';
        tr.innerHTML = `
            <td class="px-lg py-md text-body-sm text-on-surface dark:text-inverse-on-surface/90">${startStr}</td>
            <td class="px-lg py-md text-body-sm text-on-surface dark:text-inverse-on-surface/90">${endStr}</td>
            <td class="px-lg py-md font-bold text-on-surface-variant dark:text-outline-variant">${dur} hrs</td>
            <td class="px-lg py-md font-black text-on-surface dark:text-inverse-on-surface">
                ${peak}<span class="text-[10px] ml-0.5 text-outline font-normal">mm/h</span>
            </td>
            <td class="px-lg py-md font-black text-primary dark:text-inverse-primary">
                ${vol}<span class="text-[10px] ml-0.5 opacity-60 font-normal">mm</span>
            </td>
            <td class="px-lg py-md text-right">${badge}</td>`;

        tr.addEventListener('mouseenter', () => { tr.style.transform = 'translateX(4px)'; });
        tr.addEventListener('mouseleave', () => { tr.style.transform = 'translateX(0)'; });
        elEventBody.appendChild(tr);
    });

    updatePagination(totalPages);
}

function updatePagination(totalPages) {
    const start = (currentPage - 1) * PAGE_SIZE + 1;
    const end   = Math.min(currentPage * PAGE_SIZE, allEvents.length);
    elPaginationInfo.textContent = allEvents.length > 0
        ? `Showing ${start}–${end} of ${allEvents.length} events`
        : 'Showing 0 events';

    // Page number buttons
    elPageNumbers.innerHTML = '';
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage   = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage + 1 < maxVisible) startPage = Math.max(1, endPage - maxVisible + 1);

    for (let p = startPage; p <= endPage; p++) {
        const btn = document.createElement('button');
        btn.textContent = p;
        btn.className = p === currentPage
            ? 'w-8 h-8 flex items-center justify-center rounded bg-primary text-white text-body-sm font-bold'
            : 'w-8 h-8 flex items-center justify-center rounded hover:bg-surface-variant text-body-sm text-on-surface-variant';
        btn.addEventListener('click', () => { currentPage = p; renderTable(); });
        elPageNumbers.appendChild(btn);
    }

    elPrevPage.disabled = currentPage <= 1;
    elNextPage.disabled = currentPage >= totalPages || totalPages === 0;
}

// ═══════════════════════════════════════════════════════════
// CHART
// ═══════════════════════════════════════════════════════════
function renderChart(rainfallData, tempData, events) {
    const canvas  = document.getElementById('rainfallChart');
    const empty   = document.getElementById('chartEmptyState');
    const ctx     = canvas.getContext('2d');
    const isDark  = document.documentElement.classList.contains('dark');
    const gridCol = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)';
    const tickCol = isDark ? '#8898b0' : '#737688';

    // Show canvas, hide empty state
    canvas.classList.remove('hidden');
    empty.classList.add('hidden');

    // Gradient fill
    const rainGradient = ctx.createLinearGradient(0, 0, 0, 420);
    rainGradient.addColorStop(0, isDark ? 'rgba(0,94,151,0.8)' : 'rgba(0,94,151,0.75)');
    rainGradient.addColorStop(1, 'rgba(0,94,151,0.04)');

    // Build merged label array
    const allTS = Array.from(new Set([
        ...rainfallData.map(d => d.timestamp),
        ...tempData.map(d => d.timestamp)
    ])).sort();

    const rainMap = Object.fromEntries(rainfallData.map(d => [d.timestamp, d.value]));
    const tempMap = Object.fromEntries(tempData.map(d => [d.timestamp, d.value]));

    const rainValues = allTS.map(t => rainMap[t] ?? null);
    const tempValues = allTS.map(t => tempMap[t] ?? null);

    const formattedLabels = allTS.map(t =>
        new Date(t).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    );

    // Annotation boxes for each detected event
    const annotations = {};
    events.forEach((ev, idx) => {
        const startISO = ev.start_timestamp;
        const endISO   = ev.end_timestamp;
        const startIdx = allTS.findIndex(t => t >= startISO);
        const endIdx   = allTS.findLastIndex ? allTS.findLastIndex(t => t <= endISO)
                                             : [...allTS].reverse().findIndex(t => t <= endISO);
        if (startIdx === -1 || endIdx === -1) return;

        const isIntense = Number(ev.peak_value) >= 10;
        annotations[`event${idx}`] = {
            type: 'box',
            xMin: startIdx,
            xMax: isIntense ? allTS.length - 1 - endIdx : endIdx,
            backgroundColor: isIntense ? 'rgba(186,26,26,0.07)' : 'rgba(0,94,151,0.06)',
            borderColor    : isIntense ? '#ba1a1a'              : '#005e97',
            borderWidth: 1,
            borderDash: [4, 4],
            label: {
                display : true,
                content : isIntense ? 'INTENSE' : 'EVENT',
                position: 'start',
                font    : { family: 'Inter', weight: 'bold', size: 9 },
                color   : isIntense ? '#ba1a1a' : '#005e97',
                padding : 6
            }
        };
    });

    if (rainfallChart) rainfallChart.destroy();

    const datasets = [
        {
            label             : 'Rainfall (mm)',
            data              : rainValues,
            backgroundColor   : rainGradient,
            borderRadius      : { topLeft: 4, topRight: 4 },
            type              : 'bar',
            yAxisID           : 'y',
            order             : 2,
            barPercentage     : 0.7,
            categoryPercentage: 0.8,
            hoverBackgroundColor: '#005e97'
        }
    ];

    if (tempData.length > 0) {
        datasets.push({
            label               : 'Temperature (°C)',
            data                : tempValues,
            borderColor         : '#27654a',
            backgroundColor     : 'transparent',
            type                : 'line',
            tension             : 0.45,
            pointRadius         : 0,
            pointHoverRadius    : 6,
            pointHoverBackgroundColor: '#27654a',
            pointHoverBorderColor    : '#fff',
            pointHoverBorderWidth    : 3,
            borderWidth         : 2.5,
            yAxisID             : 'y1',
            order               : 1
        });
    }

    rainfallChart = new Chart(ctx, {
        type: 'bar',
        data: { labels: formattedLabels, datasets },
        options: {
            responsive          : true,
            maintainAspectRatio : false,
            interaction         : { intersect: false, mode: 'index' },
            plugins: {
                legend    : { display: false },
                annotation: { annotations },
                tooltip   : {
                    backgroundColor: isDark ? '#2a303d' : '#0b1c30',
                    titleFont      : { family: 'Inter', weight: 'bold', size: 13 },
                    bodyFont       : { family: 'Inter', size: 12 },
                    padding        : 14,
                    cornerRadius   : 10,
                    displayColors  : true,
                    usePointStyle  : true,
                    boxPadding     : 6,
                    borderColor    : 'rgba(255,255,255,0.08)',
                    borderWidth    : 1
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        maxRotation  : 0,
                        autoSkip     : true,
                        maxTicksLimit: 12,
                        font         : { family: 'Inter', size: 10, weight: '500' },
                        color        : tickCol,
                        padding      : 12
                    }
                },
                y: {
                    position    : 'left',
                    beginAtZero : true,
                    grid        : { color: gridCol, drawBorder: false },
                    ticks       : {
                        font    : { family: 'Inter', size: 11 },
                        color   : tickCol,
                        callback: v => v + ' mm',
                        padding : 10
                    }
                },
                y1: {
                    display  : tempData.length > 0,
                    position : 'right',
                    grid     : { display: false },
                    ticks    : {
                        font    : { family: 'Inter', size: 11 },
                        color   : tickCol,
                        callback: v => v + ' °C',
                        padding : 10
                    }
                }
            }
        }
    });
}

// ═══════════════════════════════════════════════════════════
// FILTER CONTROLS & CHIPS
// ═══════════════════════════════════════════════════════════
function initFilterControls() {
    const resetBtn = document.getElementById('resetFiltersBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            document.getElementById('basin-select').value = '';
            document.getElementById('start_date').value = '';
            document.getElementById('end_date').value = '';
            document.getElementById('min_dry_gap_hours').value = '6';
            updateFilterChips();
        });
    }
}

function initFilterChips() {
    const fields = ['basin-select', 'start_date', 'end_date', 'min_dry_gap_hours'];
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', updateFilterChips);
            el.addEventListener('change', updateFilterChips);
        }
    });
}

function updateFilterChips() {
    const bar      = document.getElementById('activeFilters');
    const resetBtn = document.getElementById('resetFiltersBtn');
    const sel      = document.getElementById('basin-select');
    const start    = document.getElementById('start_date').value;
    const end      = document.getElementById('end_date').value;
    const gap      = document.getElementById('min_dry_gap_hours').value;
    const chips    = [];

    if (sel.value) {
        const label = sel.options[sel.selectedIndex]?.text || sel.value;
        chips.push(`
            <span class="filter-chip group">
                <span class="material-symbols-outlined text-[14px]">location_on</span>
                <span>${label}</span>
                <button type="button" onclick="clearFilterField('basin-select')" class="hover:text-error transition-colors p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 flex items-center justify-center">
                    <span class="material-symbols-outlined text-[13px]">close</span>
                </button>
            </span>`);
    }
    if (start) {
        chips.push(`
            <span class="filter-chip group">
                <span class="material-symbols-outlined text-[14px]">event_upcoming</span>
                <span>Start: ${new Date(start).toLocaleDateString()}</span>
                <button type="button" onclick="clearFilterField('start_date')" class="hover:text-error transition-colors p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 flex items-center justify-center">
                    <span class="material-symbols-outlined text-[13px]">close</span>
                </button>
            </span>`);
    }
    if (end) {
        chips.push(`
            <span class="filter-chip group">
                <span class="material-symbols-outlined text-[14px]">event_available</span>
                <span>End: ${new Date(end).toLocaleDateString()}</span>
                <button type="button" onclick="clearFilterField('end_date')" class="hover:text-error transition-colors p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 flex items-center justify-center">
                    <span class="material-symbols-outlined text-[13px]">close</span>
                </button>
            </span>`);
    }
    if (gap && gap !== '6') {
        chips.push(`
            <span class="filter-chip group">
                <span class="material-symbols-outlined text-[14px]">av_timer</span>
                <span>Gap: ${gap}h</span>
                <button type="button" onclick="clearFilterField('min_dry_gap_hours')" class="hover:text-error transition-colors p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 flex items-center justify-center">
                    <span class="material-symbols-outlined text-[13px]">close</span>
                </button>
            </span>`);
    }

    if (chips.length > 0) {
        bar.classList.remove('hidden');
        bar.innerHTML = `<span class="text-[11px] font-bold text-on-surface-variant dark:text-outline-variant uppercase tracking-widest self-center mr-1">Active Filters:</span>` + chips.join('');
        if (resetBtn) resetBtn.classList.remove('hidden');
    } else {
        bar.classList.add('hidden');
        if (resetBtn) resetBtn.classList.add('hidden');
    }
}

/** Global helper to clear an individual filter input */
window.clearFilterField = function(fieldId) {
    const el = document.getElementById(fieldId);
    if (!el) return;
    if (fieldId === 'min_dry_gap_hours') {
        el.value = '6';
    } else {
        el.value = '';
    }
    updateFilterChips();
};

// ═══════════════════════════════════════════════════════════
// THEME TOGGLE
// ═══════════════════════════════════════════════════════════
function initTheme() {
    const toggle  = document.getElementById('themeToggle');
    const icon    = document.getElementById('themeIcon');
    const html    = document.documentElement;
    const saved   = localStorage.getItem('theme');
    const sysDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (saved === 'dark' || (!saved && sysDark)) {
        html.classList.add('dark');
        icon.textContent = 'light_mode';
    } else {
        html.classList.remove('dark');
        icon.textContent = 'dark_mode';
    }

    toggle.addEventListener('click', () => {
        html.classList.toggle('dark');
        const dark = html.classList.contains('dark');
        icon.textContent = dark ? 'light_mode' : 'dark_mode';
        localStorage.setItem('theme', dark ? 'dark' : 'light');
        if (rainfallChart) {
            renderChart(rainfallTimeseriesData, temperatureTimeseriesData, allEvents);
        }
    });
}

// ═══════════════════════════════════════════════════════════
// CSV EXPORT
// ═══════════════════════════════════════════════════════════
function initExport() {
    document.getElementById('exportBtn').addEventListener('click', () => {
        if (allEvents.length === 0) {
            showToast('No events to export.', 'warning');
            return;
        }

        const rows = [
            ['Event Start', 'Event End', 'Duration (hrs)', 'Peak (mm/hr)', 'Total Volume (mm)', 'Status'],
            ...allEvents.map(ev => [
                ev.start_timestamp  ? new Date(ev.start_timestamp).toLocaleString()  : '',
                ev.end_timestamp    ? new Date(ev.end_timestamp).toLocaleString()    : '',
                ev.duration_hours   ?? '',
                ev.peak_value       ?? '',
                ev.total_volume     ?? '',
                Number(ev.peak_value) >= 10 ? 'Alert' : ev.is_cold_event ? 'Cold' : 'Stable'
            ])
        ];

        const csv  = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url;
        a.download = `hydrocore_events_${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('CSV export started.', 'success');
    });
}

// ═══════════════════════════════════════════════════════════
// TOAST NOTIFICATION
// ═══════════════════════════════════════════════════════════
let toastTimer = null;
function showToast(msg, type = 'info') {
    const toast   = document.getElementById('toast');
    const toastEl = toast.querySelector('div');
    const icon    = document.getElementById('toastIcon');
    const msgEl   = document.getElementById('toastMsg');

    const iconMap = { success: 'check_circle', error: 'error', warning: 'warning', info: 'info' };
    const bgMap   = {
        success: 'bg-tertiary text-white',
        error  : 'bg-error text-white',
        warning: 'bg-amber-600 text-white',
        info   : 'bg-inverse-surface dark:bg-surface text-inverse-on-surface dark:text-on-surface',
    };

    // Reset classes
    toastEl.className = `flex items-center gap-sm px-lg py-md rounded-xl shadow-xl border border-white/10 min-w-[260px] max-w-sm ${bgMap[type] || bgMap.info}`;
    icon.textContent = iconMap[type] || 'info';
    msgEl.textContent = msg;

    toast.classList.remove('hidden');
    toast.classList.add('flex');

    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
        toast.classList.add('hidden');
        toast.classList.remove('flex');
    }, 3500);
}

// ═══════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════
function setLoading(state) {
    if (elExecuteBtn) {
        elExecuteBtn.disabled = state;
        elExecuteBtn.classList.toggle('opacity-60', state);
        elExecuteBtn.classList.toggle('cursor-not-allowed', state);
    }
    if (elSpinner) {
        elSpinner.classList.toggle('hidden',  !state);
        elSpinner.classList.toggle('flex',     state);
    }
    if (elBtnIcon)  elBtnIcon.textContent  = state ? 'hourglass_empty' : 'analytics';
    if (elBtnLabel) elBtnLabel.textContent = state ? 'Analysing…'      : 'Analyse';
}

function showError(msg) {
    elEventBody.innerHTML = `
        <tr>
          <td colspan="6" class="px-xl py-12 text-center text-error font-body-md">
            <span class="material-symbols-outlined text-[40px] block mb-2 opacity-60">error</span>
            ${msg}
          </td>
        </tr>`;
}

function getCsrfToken() {
    // Try cookie first (Django standard)
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match) return match[1];
    // Fallback to meta tag
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}
