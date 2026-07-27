'use strict';

import { state } from './state.js';
import { renderChartFromState, setChartLayout } from './chart.js';

export function initChartControls() {
    initLayoutToggle();
    initViewModePills();

    if (state.chartLayoutMode === 'combined') {
        setChartLayout('combined');
    }
}

function initLayoutToggle() {
    const saved = localStorage.getItem('hydrocore_chart_layout');
    if (saved === 'combined' || saved === 'split') {
        state.chartLayoutMode = saved;
        document.querySelectorAll('.layout-btn[data-chart-layout]').forEach(b => {
            b.classList.toggle('active', b.dataset.chartLayout === saved);
        });
    }

    document.querySelectorAll('.layout-btn[data-chart-layout]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.layout-btn[data-chart-layout]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            localStorage.setItem('hydrocore_chart_layout', btn.dataset.chartLayout);
            setChartLayout(btn.dataset.chartLayout);
        });
    });
}

function initViewModePills() {
    document.querySelectorAll('.chart-pill[data-chart-view]').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.chart-pill[data-chart-view]').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            state.chartViewMode = pill.dataset.chartView;
            renderChartFromState();
        });
    });
}

export function resetChartFilters() {
    state.chartViewMode = 'daily';
    document.querySelectorAll('.chart-pill[data-chart-view]').forEach(p => {
        p.classList.toggle('active', p.dataset.chartView === 'daily');
    });
}
