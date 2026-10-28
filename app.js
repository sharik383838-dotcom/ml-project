/**
 * StockLens — Global Application JavaScript
 * Theme toggle, search, API helpers, formatters, toast notifications
 */

// ─── API Helper ───
function _unwrapApiResponse(payload, status = 200) {
    if (!payload || typeof payload !== 'object') {
        return payload;
    }
    // Check explicit error response
    if (payload.success === false) {
        throw new Error(payload.error || `Request failed (${status})`);
    }
    // If standardized success response: { success: true, data: ..., error: null }
    if (payload.success === true && payload.data !== undefined) {
        const inner = payload.data;
        if (inner && typeof inner === 'object') {
            if (Array.isArray(inner)) {
                const arr = inner.slice();
                arr.data = inner;
                arr.success = true;
                arr.error = null;
                return arr;
            }
            // For objects: preserve both inner properties AND inner.data if present
            const merged = { ...inner };
            if (!('data' in merged)) {
                merged.data = inner;
            }
            merged.success = true;
            merged.error = null;
            return merged;
        }
        return inner;
    }
    return payload;
}

const API = {
    async get(url) {
        let res;
        try {
            res = await fetch(url, {
                headers: { 'Accept': 'application/json' }
            });
        } catch (err) {
            throw new Error('Network connection error. Please verify your internet connection.');
        }

        let data;
        try {
            data = await res.json();
        } catch (jsonErr) {
            throw new Error(`Server returned invalid response (${res.status}). Please try again.`);
        }

        if (!res.ok) {
            const errMsg = (data && data.error) ? data.error : `Request failed with status ${res.status}`;
            throw new Error(errMsg);
        }
        return _unwrapApiResponse(data, res.status);
    },

    async post(url, body) {
        let res;
        try {
            res = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(body)
            });
        } catch (err) {
            throw new Error('Network connection error. Please verify your internet connection.');
        }

        let data;
        try {
            data = await res.json();
        } catch (jsonErr) {
            throw new Error(`Server returned invalid response (${res.status}). Please try again.`);
        }

        if (!res.ok) {
            const errMsg = (data && data.error) ? data.error : `Request failed with status ${res.status}`;
            throw new Error(errMsg);
        }
        return _unwrapApiResponse(data, res.status);
    },

    async delete(url, body) {
        let res;
        try {
            res = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: body ? JSON.stringify(body) : undefined
            });
        } catch (err) {
            throw new Error('Network connection error. Please verify your internet connection.');
        }

        let data;
        try {
            data = await res.json();
        } catch (jsonErr) {
            throw new Error(`Server returned invalid response (${res.status}). Please try again.`);
        }

        if (!res.ok) {
            const errMsg = (data && data.error) ? data.error : `Request failed with status ${res.status}`;
            throw new Error(errMsg);
        }
        return _unwrapApiResponse(data, res.status);
    }
};

// ─── Theme ───
function getTheme() {
    return localStorage.getItem('stocklens-theme') || 'dark';
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('stocklens-theme', theme);
    const icon = document.getElementById('themeIcon');
    if (icon) {
        icon.className = theme === 'dark' ? 'bi bi-moon-stars' : 'bi bi-sun';
    }
}

function toggleTheme() {
    const current = getTheme();
    setTheme(current === 'dark' ? 'light' : 'dark');
}

// ─── Formatters ───
function formatCurrency(value, currency = 'USD') {
    if (value == null || isNaN(value)) return 'N/A';
    try {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    } catch {
        return '$' + Number(value).toFixed(2);
    }
}

function formatNumber(value, decimals = 2) {
    if (value == null || isNaN(value)) return 'N/A';
    return Number(value).toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

function formatLargeNumber(value) {
    if (value == null || isNaN(value)) return 'N/A';
    const num = Number(value);
    if (Math.abs(num) >= 1e12) return (num / 1e12).toFixed(2) + 'T';
    if (Math.abs(num) >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (Math.abs(num) >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (Math.abs(num) >= 1e3) return (num / 1e3).toFixed(2) + 'K';
    return num.toFixed(2);
}

function formatPercent(value) {
    if (value == null || isNaN(value)) return 'N/A';
    const sign = value >= 0 ? '+' : '';
    return sign + Number(value).toFixed(2) + '%';
}

function formatPercentRaw(value) {
    if (value == null || isNaN(value)) return 'N/A';
    return (Number(value) * 100).toFixed(2) + '%';
}

function changeClass(value) {
    if (value == null) return '';
    return value >= 0 ? 'text-success-custom' : 'text-danger-custom';
}

function changeIcon(value) {
    if (value == null) return '';
    return value >= 0 ? '<i class="bi bi-caret-up-fill"></i>' : '<i class="bi bi-caret-down-fill"></i>';
}

// ─── Search ───
function handleNavSearch(e) {
    e.preventDefault();
    const input = document.getElementById('navSearchInput');
    const query = input.value.trim().toUpperCase();
    if (!query) {
        showToast('Please enter a ticker symbol.', 'warning');
        return false;
    }
    window.location.href = '/stock/' + encodeURIComponent(query);
    return false;
}

// ─── Toast ───
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        info: 'bi-info-circle',
        success: 'bi-check-circle',
        warning: 'bi-exclamation-triangle',
        error: 'bi-x-circle'
    };

    const colors = {
        info: 'var(--accent-info)',
        success: 'var(--accent-success)',
        warning: 'var(--accent-warning)',
        error: 'var(--accent-danger)'
    };

    const id = 'toast-' + Date.now();
    const html = `
        <div id="${id}" class="toast align-items-center show" role="alert" style="border-left: 3px solid ${colors[type]}">
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center gap-2">
                    <i class="bi ${icons[type]}" style="color: ${colors[type]}; font-size: 1.1rem;"></i>
                    <span>${message}</span>
                </div>
                <button type="button" class="btn-close me-2 m-auto" onclick="this.closest('.toast').remove()" aria-label="Close" style="font-size: 0.7rem;"></button>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', html);

    setTimeout(() => {
        const el = document.getElementById(id);
        if (el) el.remove();
    }, 4000);
}

// ─── Skeleton Loaders ───
function showSkeleton(containerId, count = 3, type = 'card') {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '';
    for (let i = 0; i < count; i++) {
        if (type === 'card') {
            html += `<div class="skeleton skeleton-card"></div>`;
        } else if (type === 'text') {
            html += `<div class="skeleton skeleton-text" style="width: ${60 + Math.random() * 30}%"></div>`;
        } else if (type === 'chart') {
            html += `<div class="skeleton skeleton-chart"></div>`;
        }
    }
    container.innerHTML = html;
}

function showLoadingSpinner(containerId, text = 'Fetching market data...') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-custom mx-auto"></div>
            <p class="loading-text mt-3">${text}</p>
        </div>
    `;
}

function showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `
        <div class="error-message">
            <i class="bi bi-exclamation-triangle me-2"></i>${message}
        </div>
    `;
}

function showEmpty(containerId, icon, title, subtitle) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `
        <div class="empty-state">
            <i class="bi ${icon}"></i>
            <h5>${title}</h5>
            <p>${subtitle || ''}</p>
        </div>
    `;
}

// ─── Plotly Theme Config ───
function getPlotlyLayout(title = '', extraLayout = {}) {
    const theme = getTheme();
    const isDark = theme === 'dark';

    return Object.assign({
        title: {
            text: title,
            font: { family: 'Inter', size: 14, color: isDark ? '#e2e8f0' : '#0f172a' }
        },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {
            family: 'Inter',
            color: isDark ? '#94a3b8' : '#475569',
            size: 12
        },
        xaxis: {
            gridcolor: isDark ? 'rgba(30,41,59,0.5)' : 'rgba(226,232,240,0.8)',
            linecolor: isDark ? '#1e293b' : '#e2e8f0',
            zerolinecolor: isDark ? '#1e293b' : '#e2e8f0',
        },
        yaxis: {
            gridcolor: isDark ? 'rgba(30,41,59,0.5)' : 'rgba(226,232,240,0.8)',
            linecolor: isDark ? '#1e293b' : '#e2e8f0',
            zerolinecolor: isDark ? '#1e293b' : '#e2e8f0',
        },
        margin: { l: 50, r: 20, t: title ? 40 : 20, b: 40 },
        hovermode: 'x unified',
        showlegend: true,
        legend: {
            bgcolor: 'transparent',
            font: { size: 11, color: isDark ? '#94a3b8' : '#475569' },
            orientation: 'h',
            y: -0.15,
        },
        dragmode: 'zoom',
    }, extraLayout);
}

function getPlotlyConfig() {
    return {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        displaylogo: false,
    };
}

// ─── Init ───
document.addEventListener('DOMContentLoaded', () => {
    setTheme(getTheme());

    // Highlight active nav link
    const path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (href === path || (href !== '/' && path.startsWith(href))) {
            link.classList.add('active');
        }
    });
});
