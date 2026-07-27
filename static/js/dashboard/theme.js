'use strict';

import { state } from './state.js';
import { renderChartFromState } from './chart.js';

export function initTheme() {
    const toggle = document.getElementById('themeToggle');
    const icon = document.getElementById('themeIcon');
    const html = document.documentElement;
    const saved = localStorage.getItem('theme');
    const sysDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (saved === 'dark' || (!saved && sysDark)) {
        html.classList.add('dark');
        icon.textContent = 'light_mode';
    }

    toggle.addEventListener('click', () => {
        html.classList.toggle('dark');
        const isDark = html.classList.contains('dark');
        icon.textContent = isDark ? 'light_mode' : 'dark_mode';
        localStorage.setItem('theme', isDark ? 'dark' : 'light');

        if (state.rainfallChart || state.rawRainfallTimeseries.length) {
            renderChartFromState();
        }
    });
}

export function isDarkMode() {
    return document.documentElement.classList.contains('dark');
}
