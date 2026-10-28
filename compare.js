/**
 * StockLens — Stock Comparison JavaScript
 * Compares multi-stock normalized returns, valuation ratios, and volatility.
 */

const PALETTE = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#06b6d4', '#8b5cf6'];

document.addEventListener('DOMContentLoaded', () => {
    runComparison();
});

function setPreset(tickers) {
    const input = document.getElementById('compareInput');
    if (input) {
        input.value = tickers;
        runComparison();
    }
}

async function runComparison() {
    const input = document.getElementById('compareInput');
    if (!input) return;

    let raw = input.value.trim();
    if (!raw) {
        showToast('Please enter at least 2 tickers to compare.', 'warning');
        return;
    }

    const tickers = raw.replace(/\s+/g, ',').split(',').map(t => t.trim().toUpperCase()).filter(Boolean);
    if (tickers.length < 2) {
        showToast('Please enter at least 2 tickers to compare.', 'warning');
        return;
    }
    if (tickers.length > 6) {
        showToast('Maximum 6 tickers can be compared at once.', 'warning');
        return;
    }

    const chartEl = document.getElementById('compareChart');
    const tableEl = document.getElementById('compareTableContainer');

    if (chartEl) chartEl.innerHTML = '<div class="skeleton skeleton-chart" style="height: 380px;"></div>';
    if (tableEl) tableEl.innerHTML = '<div class="skeleton skeleton-chart" style="height: 250px;"></div>';

    try {
        const res = await API.get(`/api/compare?tickers=${encodeURIComponent(tickers.join(','))}`);
        const items = res.comparison || [];

        renderCompareChart(items);
        renderCompareTable(items);
    } catch (err) {
        if (chartEl) chartEl.innerHTML = `<div class="error-message">${err.message}</div>`;
        if (tableEl) tableEl.innerHTML = '';
    }
}

function renderCompareChart(items) {
    const chartEl = document.getElementById('compareChart');
    if (!chartEl) return;

    const traces = [];

    items.forEach((stock, idx) => {
        if (stock.error || !stock.chartData || !stock.chartData.dates) return;

        traces.push({
            x: stock.chartData.dates,
            y: stock.chartData.normalized,
            type: 'scatter',
            mode: 'lines',
            name: `${stock.symbol} (${stock.return_1y != null ? (stock.return_1y >= 0 ? '+' : '') + stock.return_1y + '%' : ''})`,
            line: { color: PALETTE[idx % PALETTE.length], width: 2.2 },
            hovertemplate: `<b>${stock.symbol}</b>: %{y:.2f}%<extra></extra>`
        });
    });

    if (traces.length === 0) {
        chartEl.innerHTML = '<div class="empty-state p-4"><p>No chart performance history available for comparison.</p></div>';
        return;
    }

    const layout = getPlotlyLayout('', {
        height: 400,
        margin: { l: 50, r: 20, t: 20, b: 50 },
        yaxis: {
            title: 'Return (%)',
            ticksuffix: '%',
            zeroline: true,
            zerolinecolor: 'rgba(255,255,255,0.2)',
            gridcolor: getTheme() === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
        },
        xaxis: {
            type: 'date',
            gridcolor: getTheme() === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
        },
        legend: {
            orientation: 'h',
            y: -0.2
        }
    });

    chartEl.innerHTML = '';
    Plotly.newPlot(chartEl, traces, layout, getPlotlyConfig());
}

function renderCompareTable(items) {
    const tableEl = document.getElementById('compareTableContainer');
    if (!tableEl) return;

    // Header row with company names & symbols
    let headerCells = items.map(s => {
        if (s.error) {
            return `<th class="text-end" style="min-width: 150px;"><span class="text-danger">${s.symbol}</span><br><small class="text-muted">Error</small></th>`;
        }
        return `
            <th class="text-end" style="min-width: 150px;">
                <a href="/stock/${s.symbol}" class="fw-bold text-accent text-decoration-none">${s.symbol}</a>
                <div class="text-secondary fs-8 text-truncate" style="max-width: 140px; margin-left: auto;">${s.shortName || ''}</div>
            </th>
        `;
    }).join('');

    const metrics = [
        {
            label: 'Current Price',
            format: (s) => s.price != null ? `<span class="fw-bold font-monospace">${formatCurrency(s.price, s.currency)}</span>` : 'N/A'
        },
        {
            label: 'Day Change',
            format: (s) => {
                if (s.change == null) return 'N/A';
                const cls = changeClass(s.change);
                const icon = changeIcon(s.change);
                return `<span class="${cls} fw-semibold font-monospace">${icon} ${formatPercent(s.changePercent)}</span>`;
            }
        },
        {
            label: 'Market Cap',
            format: (s) => `<span class="font-monospace">${formatLargeNumber(s.marketCap)} ${s.currency || ''}</span>`
        },
        {
            label: 'Trailing P/E',
            format: (s) => `<span class="font-monospace">${formatNumber(s.trailingPE)}</span>`
        },
        {
            label: 'Trailing EPS',
            format: (s) => `<span class="font-monospace">${formatCurrency(s.trailingEps, s.currency)}</span>`
        },
        {
            label: '1-Month Return',
            format: (s) => {
                if (s.return_1m == null) return 'N/A';
                const cls = changeClass(s.return_1m);
                return `<span class="${cls} fw-semibold font-monospace">${formatPercent(s.return_1m)}</span>`;
            }
        },
        {
            label: '1-Year Return',
            format: (s) => {
                if (s.return_1y == null) return 'N/A';
                const cls = changeClass(s.return_1y);
                return `<span class="${cls} fw-semibold font-monospace">${formatPercent(s.return_1y)}</span>`;
            }
        },
        {
            label: 'Annualized Volatility',
            format: (s) => s.volatility != null ? `<span class="font-monospace">${s.volatility}%</span>` : 'N/A'
        },
        {
            label: 'Beta',
            format: (s) => `<span class="font-monospace">${formatNumber(s.beta, 2)}</span>`
        },
        {
            label: 'Profit Margin',
            format: (s) => `<span class="font-monospace">${formatPercentRaw(s.profitMargins)}</span>`
        },
        {
            label: 'Dividend Yield',
            format: (s) => `<span class="font-monospace">${formatPercentRaw(s.dividendYield)}</span>`
        },
        {
            label: 'Annual Revenue',
            format: (s) => `<span class="font-monospace">${formatLargeNumber(s.revenue)} ${s.currency || ''}</span>`
        }
    ];

    let bodyRows = metrics.map(m => {
        let cells = items.map(s => {
            if (s.error) return `<td class="text-end text-muted">N/A</td>`;
            return `<td class="text-end">${m.format(s)}</td>`;
        }).join('');

        return `
            <tr>
                <td class="fw-medium text-body">${m.label}</td>
                ${cells}
            </tr>
        `;
    }).join('');

    tableEl.innerHTML = `
        <table class="table table-hover table-custom align-middle mb-0">
            <thead>
                <tr>
                    <th style="min-width: 180px;">Metric</th>
                    ${headerCells}
                </tr>
            </thead>
            <tbody>${bodyRows}</tbody>
        </table>
    `;
}
