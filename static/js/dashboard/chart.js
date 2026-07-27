'use strict';

import { state } from './state.js';
import { isDarkMode } from './theme.js';
import { prepareChartData } from './chart-data.js';

/** Clear, consistent palette — blue = rain, orange = temperature */
export const COLORS = {
    rain: {
        bar: '#2563eb',
        barLight: '#60a5fa',
        barHover: '#1d4ed8',
        grid: 'rgba(37, 99, 235, 0.08)',
        axis: '#1e40af',
        label: 'Rainfall (mm)',
    },
    temp: {
        line: '#ea580c',
        lineLight: '#fb923c',
        fill: 'rgba(234, 88, 12, 0.12)',
        grid: 'rgba(234, 88, 12, 0.06)',
        axis: '#c2410c',
        label: 'Temperature (°C)',
    },
    event: { bg: 'rgba(250, 204, 21, 0.22)', border: '#eab308' },
    heavy: { bg: 'rgba(74, 222, 128, 0.22)', border: '#22c55e' },
};

function getTickColor() {
    return isDarkMode() ? '#94a3b8' : '#475569';
}

function baseOptions(gridColor) {
    const tick = getTickColor();
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: isDarkMode() ? '#0f172a' : '#1e293b',
                titleColor: '#f8fafc',
                bodyColor: '#e2e8f0',
                padding: 14,
                cornerRadius: 10,
                boxPadding: 6,
            },
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: {
                    font: { family: 'Inter', size: 10, weight: '500' },
                    color: tick,
                    maxRotation: 45,
                    autoSkip: true,
                    maxTicksLimit: 12,
                },
            },
        },
    };
}

export function renderChartFromState() {
    const data = prepareChartData(
        state.rawRainfallTimeseries,
        state.rawTemperatureTimeseries,
        state.rawEvents,
        state.chartViewMode,
    );

    updateLayoutVisibility();
    updateChartStats(data.rainfall, data.temperature, data.mode);

    if (state.chartLayoutMode === 'combined') {
        destroySplitCharts();
        renderCombinedChart(data.rainfall, data.temperature, data.events, data.mode);
    } else {
        destroyCombinedChart();
        renderRainfallChart(data.rainfall, data.events, data.mode);
        renderTemperatureChart(data.temperature, data.mode);
    }
}

export function setChartLayout(mode) {
    state.chartLayoutMode = mode;
    updateLayoutVisibility();
    renderChartFromState();
}

function updateLayoutVisibility() {
    const split = document.getElementById('chartSplitView');
    const combined = document.getElementById('chartCombinedView');
    const subtitle = document.getElementById('chartSectionSubtitle');

    if (state.chartLayoutMode === 'combined') {
        split?.classList.add('hidden');
        combined?.classList.remove('hidden');
        if (subtitle) subtitle.textContent = 'Combined view — rain (bars) and temperature (line) together';
    } else {
        split?.classList.remove('hidden');
        combined?.classList.add('hidden');
        if (subtitle) subtitle.textContent = 'Separate view — one chart for rain, one for temperature';
    }
}

function destroySplitCharts() {
    if (state.rainfallChart) { state.rainfallChart.destroy(); state.rainfallChart = null; }
    if (state.temperatureChart) { state.temperatureChart.destroy(); state.temperatureChart = null; }
}

function destroyCombinedChart() {
    if (state.combinedChart) { state.combinedChart.destroy(); state.combinedChart = null; }
}

function updateChartStats(rainData, tempData, mode) {
    const modeLabel = { daily: 'per day', monthly: 'per month', yearly: 'per year' }[mode] || '';
    const rainTotal = rainData.reduce((s, d) => s + (d.value || 0), 0);
    const tempAvg = tempData.length
        ? tempData.reduce((s, d) => s + (d.value || 0), 0) / tempData.length : 0;

    const rainSub = document.getElementById('rainChartSubtitle');
    const tempSub = document.getElementById('tempChartSubtitle');
    const combSub = document.getElementById('combinedChartSubtitle');
    if (rainSub) rainSub.textContent = `Total rainfall ${modeLabel} (mm)`;
    if (tempSub) tempSub.textContent = `Average temperature ${modeLabel} (°C)`;
    if (combSub) combSub.textContent = `Grouped ${modeLabel} · Blue = rain · Orange = temp · Yellow = event · Green = heavy rain`;

    const rainHtml = rainData.length
        ? `<span class="stat-label">Rain total</span><span class="stat-value">${rainTotal.toFixed(1)} mm</span>` : '—';
    const tempHtml = tempData.length
        ? `<span class="stat-label">Temp avg</span><span class="stat-value">${tempAvg.toFixed(1)} °C</span>` : '—';

    const rainStat = document.getElementById('rainChartStat');
    const tempStat = document.getElementById('tempChartStat');
    const combRain = document.getElementById('combinedRainStat');
    const combTemp = document.getElementById('combinedTempStat');
    if (rainStat) rainStat.innerHTML = rainHtml;
    if (tempStat) tempStat.innerHTML = tempHtml;
    if (combRain) combRain.innerHTML = rainHtml;
    if (combTemp) combTemp.innerHTML = tempHtml;
}

export function renderRainfallChart(rainfallData, events, mode = 'daily') {
    const canvas = document.getElementById('rainfallChart');
    const empty = document.getElementById('rainChartEmpty');
    if (!canvas) return;

    if (!rainfallData.length) {
        canvas.classList.add('hidden');
        empty?.classList.remove('hidden');
        if (state.rainfallChart) { state.rainfallChart.destroy(); state.rainfallChart = null; }
        return;
    }

    canvas.classList.remove('hidden');
    empty?.classList.add('hidden');

    const ctx = canvas.getContext('2d');
    const labels = rainfallData.map(d => d.timestamp);
    const values = rainfallData.map(d => d.value);
    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, isDarkMode() ? COLORS.rain.barLight : COLORS.rain.bar);
    gradient.addColorStop(1, 'rgba(37, 99, 235, 0.12)');

    if (state.rainfallChart) state.rainfallChart.destroy();

    const opts = baseOptions(COLORS.rain.grid);
    opts.plugins.annotation = { annotations: buildEventAnnotations(events, labels, mode) };
    opts.plugins.legend = buildLegend(true, false);
    opts.plugins.tooltip.callbacks = {
        label: (c) => ` 💧 Rainfall: ${c.parsed.y} mm`,
    };
    opts.scales.y = {
        beginAtZero: true,
        grid: { color: isDarkMode() ? 'rgba(255,255,255,0.06)' : COLORS.rain.grid },
        ticks: { color: COLORS.rain.axis, callback: v => v + ' mm', font: { size: 11 } },
        title: { display: true, text: 'Rainfall (mm)', color: COLORS.rain.axis, font: { size: 12, weight: '700' } },
    };

    state.rainfallChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: COLORS.rain.label,
                data: values,
                backgroundColor: gradient,
                borderColor: COLORS.rain.bar,
                borderWidth: 1.5,
                borderRadius: 6,
                barPercentage: 0.65,
            }],
        },
        options: opts,
    });
}

export function renderTemperatureChart(tempData, mode = 'daily') {
    const canvas = document.getElementById('temperatureChart');
    const empty = document.getElementById('tempChartEmpty');
    if (!canvas) return;

    if (!tempData.length) {
        canvas.classList.add('hidden');
        empty?.classList.remove('hidden');
        if (state.temperatureChart) { state.temperatureChart.destroy(); state.temperatureChart = null; }
        return;
    }

    canvas.classList.remove('hidden');
    empty?.classList.add('hidden');

    const ctx = canvas.getContext('2d');
    const labels = tempData.map(d => d.timestamp);
    const values = tempData.map(d => d.value);
    const fillGrad = ctx.createLinearGradient(0, 0, 0, 280);
    fillGrad.addColorStop(0, isDarkMode() ? 'rgba(251, 146, 60, 0.3)' : COLORS.temp.fill);
    fillGrad.addColorStop(1, 'transparent');

    if (state.temperatureChart) state.temperatureChart.destroy();

    const opts = baseOptions(COLORS.temp.grid);
    opts.plugins.legend = buildLegend(false, true);
    opts.plugins.tooltip.callbacks = {
        label: (c) => {
            const v = c.parsed.y;
            const tag = v < 0 ? ' ❄ Cold' : v > 25 ? ' ☀ Warm' : '';
            return ` 🌡 Temperature: ${v} °C${tag}`;
        },
    };
    opts.scales.y = {
        grid: { color: isDarkMode() ? 'rgba(255,255,255,0.06)' : COLORS.temp.grid },
        ticks: { color: COLORS.temp.axis, callback: v => v + ' °C', font: { size: 11 } },
        title: { display: true, text: 'Temperature (°C)', color: COLORS.temp.axis, font: { size: 12, weight: '700' } },
    };

    state.temperatureChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: COLORS.temp.label,
                data: values,
                borderColor: COLORS.temp.line,
                backgroundColor: fillGrad,
                fill: true,
                tension: 0.35,
                pointRadius: mode === 'daily' ? 3 : 5,
                pointBackgroundColor: COLORS.temp.line,
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                borderWidth: 3,
            }],
        },
        options: opts,
    });
}

export function renderCombinedChart(rainfallData, tempData, events, mode = 'daily') {
    const canvas = document.getElementById('combinedChart');
    const empty = document.getElementById('combinedChartEmpty');
    if (!canvas) return;

    if (!rainfallData.length && !tempData.length) {
        canvas.classList.add('hidden');
        empty?.classList.remove('hidden');
        if (state.combinedChart) { state.combinedChart.destroy(); state.combinedChart = null; }
        return;
    }

    canvas.classList.remove('hidden');
    empty?.classList.add('hidden');

    const ctx = canvas.getContext('2d');
    const allLabels = Array.from(new Set([
        ...rainfallData.map(d => d.timestamp),
        ...tempData.map(d => d.timestamp),
    ]));

    const rainMap = Object.fromEntries(rainfallData.map(d => [d.timestamp, d.value]));
    const tempMap = Object.fromEntries(tempData.map(d => [d.timestamp, d.value]));

    const rainGradient = ctx.createLinearGradient(0, 0, 0, 400);
    rainGradient.addColorStop(0, isDarkMode() ? COLORS.rain.barLight : COLORS.rain.bar);
    rainGradient.addColorStop(1, 'rgba(37, 99, 235, 0.1)');

    if (state.combinedChart) state.combinedChart.destroy();

    const datasets = [{
        label: COLORS.rain.label,
        data: allLabels.map(t => rainMap[t] ?? null),
        type: 'bar',
        backgroundColor: rainGradient,
        borderColor: COLORS.rain.bar,
        borderWidth: 1.5,
        borderRadius: 5,
        yAxisID: 'yRain',
        order: 2,
        barPercentage: 0.55,
    }];

    if (tempData.length) {
        datasets.push({
            label: COLORS.temp.label,
            data: allLabels.map(t => tempMap[t] ?? null),
            type: 'line',
            borderColor: COLORS.temp.line,
            backgroundColor: 'transparent',
            borderWidth: 3,
            pointRadius: 4,
            pointBackgroundColor: COLORS.temp.line,
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            tension: 0.35,
            yAxisID: 'yTemp',
            order: 1,
        });
    }

    const opts = baseOptions(null);
    opts.plugins.legend = buildLegend(true, tempData.length > 0);
    opts.plugins.annotation = { annotations: buildEventAnnotations(events, allLabels, mode) };
    opts.plugins.tooltip.callbacks = {
        label: (c) => {
            if (c.dataset.yAxisID === 'yRain' || c.dataset.type === 'bar') {
                return c.parsed.y != null ? ` 💧 Rainfall: ${c.parsed.y} mm` : '';
            }
            const v = c.parsed.y;
            return v != null ? ` 🌡 Temperature: ${v} °C` : '';
        },
    };
    opts.scales.yRain = {
        type: 'linear',
        position: 'left',
        beginAtZero: true,
        grid: { color: isDarkMode() ? 'rgba(255,255,255,0.06)' : COLORS.rain.grid },
        ticks: { color: COLORS.rain.axis, callback: v => v + ' mm', font: { size: 11, weight: '600' } },
        title: { display: true, text: '← Rainfall (mm)', color: COLORS.rain.axis, font: { size: 12, weight: '700' } },
    };
    opts.scales.yTemp = {
        type: 'linear',
        position: 'right',
        display: tempData.length > 0,
        grid: { display: false },
        ticks: { color: COLORS.temp.axis, callback: v => v + ' °C', font: { size: 11, weight: '600' } },
        title: { display: true, text: 'Temperature (°C) →', color: COLORS.temp.axis, font: { size: 12, weight: '700' } },
    };

    state.combinedChart = new Chart(ctx, {
        type: 'bar',
        data: { labels: allLabels, datasets },
        options: opts,
    });
}

function buildLegend(showRain, showTemp) {
    return {
        display: showRain || showTemp,
        position: 'top',
        align: 'center',
        labels: {
            usePointStyle: true,
            pointStyle: 'rectRounded',
            padding: 20,
            font: { family: 'Inter', size: 12, weight: '600' },
            color: getTickColor(),
            filter: (item) => {
                if (!showRain && item.text.includes('Rainfall')) return false;
                if (!showTemp && item.text.includes('Temperature')) return false;
                return true;
            },
            generateLabels: (chart) => {
                const items = [];
                if (showRain) {
                    items.push({
                        text: COLORS.rain.label,
                        fillStyle: COLORS.rain.bar,
                        strokeStyle: COLORS.rain.bar,
                        lineWidth: 0,
                        pointStyle: 'rectRounded',
                        hidden: false,
                        index: 0,
                    });
                }
                if (showTemp) {
                    items.push({
                        text: COLORS.temp.label,
                        fillStyle: COLORS.temp.line,
                        strokeStyle: COLORS.temp.line,
                        lineWidth: 2,
                        pointStyle: 'circle',
                        hidden: false,
                        index: 1,
                    });
                }
                return items;
            },
        },
    };
}

function buildEventAnnotations(events, labels, mode) {
    const annotations = {};
    events.forEach((ev, idx) => {
        const startDate = new Date(ev.start_timestamp);
        const endDate = new Date(ev.end_timestamp);
        const isHeavy = Number(ev.peak_value) >= 10;
        let startIdx = -1, endIdx = -1;

        labels.forEach((label, i) => {
            const labelDate = parseChartLabel(label, mode);
            if (!labelDate) return;
            const periodStart = startOfPeriod(labelDate, mode);
            const periodEnd = endOfPeriod(labelDate, mode);
            if (periodEnd >= startDate && periodStart <= endDate) {
                if (startIdx === -1) startIdx = i;
                endIdx = i;
            }
        });

        if (startIdx === -1) return;
        if (endIdx === -1) endIdx = startIdx;

        annotations[`ev${idx}`] = {
            type: 'box',
            xMin: startIdx - 0.4,
            xMax: endIdx + 0.4,
            yScaleID: state.chartLayoutMode === 'combined' ? 'yRain' : 'y',
            backgroundColor: isHeavy ? COLORS.heavy.bg : COLORS.event.bg,
            borderColor: isHeavy ? COLORS.heavy.border : COLORS.event.border,
            borderWidth: 1.5,
            borderDash: isHeavy ? [6, 3] : [4, 4],
            label: {
                display: events.length <= 8,
                content: isHeavy ? '⚡ Heavy rain' : '🌧 Rain event',
                position: 'start',
                font: { size: 9, weight: 'bold' },
                color: isHeavy ? COLORS.heavy.border : COLORS.event.border,
                backgroundColor: 'rgba(255,255,255,0.92)',
                padding: 4,
            },
        };
    });
    return annotations;
}

function parseChartLabel(label, mode) {
    if (mode === 'yearly') {
        const y = parseInt(label, 10);
        return isNaN(y) ? null : new Date(y, 0, 1);
    }
    const d = new Date(label);
    return isNaN(d.getTime()) ? null : d;
}

function startOfPeriod(date, mode) {
    if (mode === 'yearly') return new Date(date.getFullYear(), 0, 1);
    if (mode === 'monthly') return new Date(date.getFullYear(), date.getMonth(), 1);
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function endOfPeriod(date, mode) {
    if (mode === 'yearly') return new Date(date.getFullYear(), 11, 31, 23, 59, 59);
    if (mode === 'monthly') return new Date(date.getFullYear(), date.getMonth() + 1, 0, 23, 59, 59);
    return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59);
}

export function renderChart(rainfallData, tempData, events, mode) {
    renderChartFromState();
}
