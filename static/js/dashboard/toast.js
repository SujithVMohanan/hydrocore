'use strict';

let toastTimer = null;

const ICON_MAP = {
    success: 'check_circle',
    error: 'error',
    warning: 'warning',
    info: 'info',
};

const CLASS_MAP = {
    success: 'toast__inner--success',
    error: 'toast__inner--error',
    warning: 'toast__inner--warning',
    info: 'toast__inner--info',
};

export function showToast(msg, type = 'info') {
    const toast = document.getElementById('toast');
    const inner = document.getElementById('toastInner');
    const icon = document.getElementById('toastIcon');
    const msgEl = document.getElementById('toastMsg');

    inner.className = `toast__inner ${CLASS_MAP[type] || CLASS_MAP.info}`;
    icon.textContent = ICON_MAP[type] || 'info';
    msgEl.textContent = msg;

    toast.classList.add('show');

    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 3500);
}
