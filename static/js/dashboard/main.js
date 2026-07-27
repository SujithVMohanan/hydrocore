'use strict';

import { state } from './state.js';
import { initTheme } from './theme.js';
import { initFilters } from './filters.js';
import { initTableControls } from './table.js';
import { initChartControls } from './chart-controls.js';
import { initBasinDropdown } from './basin-dropdown.js';

window.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initBasinDropdown();
    initFilters();
    initChartControls();
    initTableControls();

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (state.rainfallChart) state.rainfallChart.resize();
            if (state.temperatureChart) state.temperatureChart.resize();
            if (state.combinedChart) state.combinedChart.resize();
        }, 150);
    });
});
