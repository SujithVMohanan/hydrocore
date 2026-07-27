'use strict';

let basinDropdownInstance = null;
let panelEl = null;
let triggerEl = null;

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
}

function positionPanel() {
    if (!panelEl || !triggerEl) return;
    const rect = triggerEl.getBoundingClientRect();
    panelEl.style.top = `${rect.bottom + window.scrollY + 6}px`;
    panelEl.style.left = `${rect.left + window.scrollX}px`;
    panelEl.style.width = `${rect.width}px`;
}

export function initBasinDropdown() {
    const dataEl = document.getElementById('basins-data');
    if (!dataEl) return;

    const basins = JSON.parse(dataEl.textContent);
    const wrap = document.getElementById('basinDropdown');
    const hiddenInput = document.getElementById('basin-select');
    triggerEl = document.getElementById('basinDropdownTrigger');
    panelEl = document.getElementById('basinDropdownPanel');
    const searchInput = document.getElementById('basinSearch');
    const listEl = document.getElementById('basinDropdownList');
    const labelEl = document.getElementById('basinDropdownLabel');
    const idEl = document.getElementById('basinDropdownId');

    if (!basins.length) {
        labelEl.textContent = 'No basins available';
        triggerEl.disabled = true;
        return;
    }

    function renderList(filter = '') {
        const q = filter.trim().toLowerCase();
        const filtered = basins.filter(b => {
            const name = (b.name || b.basin_id || '').toLowerCase();
            const id = (b.basin_id || '').toLowerCase();
            return !q || name.includes(q) || id.includes(q);
        });

        if (!filtered.length) {
            listEl.innerHTML = '<div class="basin-dropdown__empty">No basins found</div>';
            return;
        }

        listEl.innerHTML = filtered.map(b => {
            const selected = String(hiddenInput.value) === String(b.id);
            const title = b.name || b.basin_id;
            return `
                <button type="button" class="basin-dropdown__item${selected ? ' is-selected' : ''}"
                        data-id="${b.id}" data-label="${escapeHtml(title)}" data-basin-id="${escapeHtml(b.basin_id)}">
                    <span class="basin-dropdown__item-icon">
                        <span class="material-symbols-outlined">water</span>
                    </span>
                    <span class="basin-dropdown__item-text">
                        <span class="basin-dropdown__item-name">${escapeHtml(title)}</span>
                        <span class="basin-dropdown__item-id">${escapeHtml(b.basin_id)}</span>
                    </span>
                    ${selected ? '<span class="material-symbols-outlined basin-dropdown__check">check_circle</span>' : ''}
                </button>`;
        }).join('');

        listEl.querySelectorAll('.basin-dropdown__item').forEach(btn => {
            btn.addEventListener('mousedown', (e) => e.preventDefault());
            btn.addEventListener('click', () => {
                selectBasin(btn.dataset.id, btn.dataset.label, btn.dataset.basinId);
            });
        });
    }

    function selectBasin(id, label, basinId) {
        hiddenInput.value = id;
        labelEl.textContent = label;
        labelEl.classList.remove('is-placeholder');
        idEl.textContent = basinId || '';
        idEl.classList.remove('hidden');
        close();
        renderList(searchInput.value);
        hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function open() {
        positionPanel();
        wrap.classList.add('is-open');
        panelEl.hidden = false;
        panelEl.classList.add('is-visible');
        triggerEl.setAttribute('aria-expanded', 'true');
        searchInput.value = '';
        renderList();
        setTimeout(() => searchInput.focus(), 30);
    }

    function close() {
        wrap.classList.remove('is-open');
        panelEl.hidden = true;
        panelEl.classList.remove('is-visible');
        triggerEl.setAttribute('aria-expanded', 'false');
    }

    triggerEl.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        wrap.classList.contains('is-open') ? close() : open();
    });

    searchInput.addEventListener('input', () => renderList(searchInput.value));
    searchInput.addEventListener('click', (e) => e.stopPropagation());

    panelEl.addEventListener('mousedown', (e) => e.stopPropagation());
    panelEl.addEventListener('click', (e) => e.stopPropagation());

    document.addEventListener('click', () => close());
    window.addEventListener('resize', () => {
        if (wrap.classList.contains('is-open')) positionPanel();
    });
    window.addEventListener('scroll', () => {
        if (wrap.classList.contains('is-open')) positionPanel();
    }, true);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') close();
    });

    basinDropdownInstance = {
        clear() {
            hiddenInput.value = '';
            labelEl.textContent = 'Select a catchment basin';
            labelEl.classList.add('is-placeholder');
            idEl.textContent = '';
            idEl.classList.add('hidden');
            renderList();
        },
        getLabel() {
            return labelEl.classList.contains('is-placeholder') ? '' : labelEl.textContent;
        },
    };

    renderList();
}

export function clearBasinDropdown() {
    basinDropdownInstance?.clear();
}

export function getBasinDropdownLabel() {
    return basinDropdownInstance?.getLabel() || '';
}
