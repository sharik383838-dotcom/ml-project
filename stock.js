/**
 * StockLens — Stock Detail Page JavaScript
 * Handles candlestick charts, technical indicators, fundamentals,
 * financial statements, news feed, quantitative metrics, and user actions.
 */

let currentTicker = '';
let currentPeriod = '1y';
let currentInterval = '1d';
let currentStmtType = 'income';
let currentFreq = 'annual';
let stockData = null;

async function initStockPage(ticker) {
    currentTicker = ticker.toUpperCase();

    // Load data in parallel
    await Promise.allSettled([
        loadStockHeaderAndInfo(),
        loadPriceHistory(currentPeriod, currentInterval),
        loadTechnicalAnalysis(),
        loadNews(),
        loadFinancials(currentStmtType)
    ]);
}

// ─── Header & Basic Info ───
async function loadStockHeaderAndInfo() {
    try {
        stockData = await API.get(`/api/stock/${currentTicker}`);
        
        // Update document title
        document.title = `${stockData.shortName || currentTicker} (${currentTicker}) — StockLens`;

        // Update header details
        const companyNameEl = document.getElementById('companyName');
        const tickerBadgeEl = document.getElementById('tickerBadge');
        const stockMetaEl = document.getElementById('stockMeta');
        const priceDisplayEl = document.getElementById('priceDisplay');
        const priceChangeEl = document.getElementById('priceChange');
        const actionButtonsEl = document.getElementById('actionButtons');

        if (companyNameEl) {
            companyNameEl.textContent = stockData.shortName || stockData.longName || currentTicker;
        }
        if (tickerBadgeEl) {
            tickerBadgeEl.textContent = currentTicker;
        }

        const currency = stockData.currency || 'USD';
        const price = stockData.regularMarketPrice;
        const change = stockData.change;
        const changePercent = stockData.changePercent;

        if (priceDisplayEl) {
            priceDisplayEl.innerHTML = formatCurrency(price, currency);
        }

        if (priceChangeEl) {
            const chgClass = changeClass(change);
            const icon = changeIcon(change);
            priceChangeEl.className = `price-change ${chgClass} fs-6 fw-semibold`;
            priceChangeEl.innerHTML = `${icon} ${change != null ? formatNumber(Math.abs(change), 2) : ''} (${formatPercent(changePercent)}) <span class="text-muted fw-normal fs-7 ms-1">Today</span>`;
        }

        if (stockMetaEl) {
            const metaParts = [];
            if (stockData.exchange) metaParts.push(`<span class="badge bg-secondary-subtle text-body-secondary me-1">${stockData.exchange}</span>`);
            if (stockData.sector) metaParts.push(`<span><i class="bi bi-tag me-1"></i>${stockData.sector}</span>`);
            if (stockData.industry) metaParts.push(`<span><i class="bi bi-building me-1"></i>${stockData.industry}</span>`);
            if (stockData.country) metaParts.push(`<span><i class="bi bi-geo-alt me-1"></i>${stockData.country}</span>`);
            stockMetaEl.innerHTML = metaParts.join(' <span class="mx-2 text-muted">•</span> ');
        }

        if (actionButtonsEl) {
            actionButtonsEl.style.display = 'block';
        }

        // Populate Fundamentals Tab
        renderFundamentals(stockData);

    } catch (err) {
        showError('stockHeader', `Failed to load data for ${currentTicker}: ${err.message}`);
    }
}

// ─── Price Chart & History ───
async function loadPriceHistory(period = '1y', interval = '1d') {
    currentPeriod = period;
    currentInterval = interval;
    const chartEl = document.getElementById('priceChart');
    if (!chartEl) return;

    chartEl.innerHTML = '<div class="skeleton skeleton-chart"></div>';

    try {
        const res = await API.get(`/api/stock/${currentTicker}/history?period=${period}&interval=${interval}`);
        const data = res.data;

        if (!data || data.length === 0) {
            chartEl.innerHTML = '<div class="empty-state p-4"><p>No price history data available for this timeframe.</p></div>';
            return;
        }

        const dates = data.map(d => d.date);
        const opens = data.map(d => d.open);
        const highs = data.map(d => d.high);
        const lows = data.map(d => d.low);
        const closes = data.map(d => d.close);
        const volumes = data.map(d => d.volume);

        const isIntraday = period === '1d' || period === '5d';

        // Trace 1: Candlestick or Line Chart
        let priceTrace;
        if (isIntraday && data.length > 50) {
            priceTrace = {
                x: dates,
                y: closes,
                type: 'scatter',
                mode: 'lines',
                name: currentTicker,
                line: { color: '#6366f1', width: 2 },
                yaxis: 'y'
            };
        } else {
            priceTrace = {
                x: dates,
                open: opens,
                high: highs,
                low: lows,
                close: closes,
                type: 'candlestick',
                name: currentTicker,
                increasing: { line: { color: '#10b981' } },
                decreasing: { line: { color: '#ef4444' } },
                yaxis: 'y'
            };
        }

        // Trace 2: Volume bar chart
        const volumeColors = closes.map((c, i) => {
            if (i === 0) return 'rgba(99, 102, 241, 0.3)';
            return c >= closes[i - 1] ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)';
        });

        const volumeTrace = {
            x: dates,
            y: volumes,
            type: 'bar',
            name: 'Volume',
            marker: { color: volumeColors },
            yaxis: 'y2',
            hoverinfo: 'x+y'
        };

        const layout = getPlotlyLayout('', {
            xaxis: {
                rangeslider: { visible: false },
                type: 'date',
                gridcolor: getTheme() === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
            },
            yaxis: {
                title: 'Price',
                domain: [0.25, 1],
                gridcolor: getTheme() === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
            },
            yaxis2: {
                title: 'Volume',
                domain: [0, 0.2],
                showgrid: false
            },
            showlegend: false,
            height: 480,
            margin: { l: 50, r: 20, t: 15, b: 35 }
        });

        chartEl.innerHTML = '';
        Plotly.newPlot(chartEl, [priceTrace, volumeTrace], layout, getPlotlyConfig());

    } catch (err) {
        chartEl.innerHTML = `<div class="error-message"><i class="bi bi-exclamation-triangle me-2"></i>Error loading chart: ${err.message}</div>`;
    }
}

function changePeriod(period, interval) {
    // Update active button
    const controls = document.getElementById('periodControls');
    if (controls) {
        controls.querySelectorAll('button').forEach(btn => btn.classList.remove('active'));
        if (event && event.target) {
            event.target.classList.add('active');
        }
    }
    loadPriceHistory(period, interval);
}

// ─── Technical Analysis ───
async function loadTechnicalAnalysis() {
    const statsEl = document.getElementById('technicalStats');
    const rsiEl = document.getElementById('rsiChart');
    const macdEl = document.getElementById('macdChart');
    const summaryEl = document.getElementById('summaryContainer');

    try {
        const analysis = await API.get(`/api/stock/${currentTicker}/analysis`);

        // 1. Technical Stats Cards
        if (statsEl) {
            const summary = analysis.summary || {};
            const indicators = analysis.indicators || {};
            const latest = analysis.latest || {};

            let badgeClass = 'badge-neutral';
            if (summary.signal === 'BULLISH') badgeClass = 'badge-bullish';
            else if (summary.signal === 'BEARISH') badgeClass = 'badge-bearish';

            statsEl.innerHTML = `
                <div class="col-md-4 col-sm-6">
                    <div class="glass-card-static p-3 h-100">
                        <span class="text-muted fs-7 text-uppercase fw-semibold">Technical Outlook</span>
                        <div class="d-flex align-items-center gap-2 mt-2">
                            <span class="analysis-badge ${badgeClass} fs-6">${summary.signal || 'NEUTRAL'}</span>
                            <span class="text-muted fs-7">(${summary.bullishCount || 0} Bull / ${summary.bearishCount || 0} Bear)</span>
                        </div>
                        <div class="mt-2 fs-7 text-secondary">${summary.description || 'Quantitative indicators evaluated.'}</div>
                    </div>
                </div>
                <div class="col-md-4 col-sm-6">
                    <div class="glass-card-static p-3 h-100">
                        <span class="text-muted fs-7 text-uppercase fw-semibold">Moving Averages</span>
                        <div class="mt-2 d-flex flex-column gap-1 fs-7">
                            <div class="d-flex justify-content-between"><span>SMA (20):</span> <strong>${formatNumber(latest.sma20)}</strong></div>
                            <div class="d-flex justify-content-between"><span>SMA (50):</span> <strong>${formatNumber(latest.sma50)}</strong></div>
                            <div class="d-flex justify-content-between"><span>SMA (200):</span> <strong>${formatNumber(latest.sma200)}</strong></div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 col-sm-6">
                    <div class="glass-card-static p-3 h-100">
                        <span class="text-muted fs-7 text-uppercase fw-semibold">Momentum & Range</span>
                        <div class="mt-2 d-flex flex-column gap-1 fs-7">
                            <div class="d-flex justify-content-between"><span>RSI (14):</span> <strong>${formatNumber(latest.rsi, 2)} (${indicators.rsiStatus || 'Normal'})</strong></div>
                            <div class="d-flex justify-content-between"><span>MACD:</span> <strong>${formatNumber(latest.macd, 2)}</strong></div>
                            <div class="d-flex justify-content-between"><span>Bollinger Upper/Lower:</span> <strong>${formatNumber(latest.bbUpper, 1)} / ${formatNumber(latest.bbLower, 1)}</strong></div>
                        </div>
                    </div>
                </div>
            `;
        }

        // 2. RSI Chart
        if (rsiEl && analysis.charts && analysis.charts.rsi) {
            const rsiData = analysis.charts.rsi;
            const dates = rsiData.dates;
            const values = rsiData.values;

            const rsiTrace = {
                x: dates,
                y: values,
                type: 'scatter',
                mode: 'lines',
                name: 'RSI 14',
                line: { color: '#8b5cf6', width: 2 }
            };

            const rsiLayout = getPlotlyLayout('', {
                height: 240,
                margin: { l: 40, r: 15, t: 10, b: 30 },
                yaxis: {
                    range: [0, 100],
                    tickvals: [30, 50, 70],
                    gridcolor: getTheme() === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
                },
                shapes: [
                    { type: 'line', x0: dates[0], x1: dates[dates.length - 1], y0: 70, y1: 70, line: { color: '#ef4444', width: 1, dash: 'dash' } },
                    { type: 'line', x0: dates[0], x1: dates[dates.length - 1], y0: 30, y1: 30, line: { color: '#10b981', width: 1, dash: 'dash' } }
                ],
                showlegend: false
            });

            rsiEl.innerHTML = '';
            Plotly.newPlot(rsiEl, [rsiTrace], rsiLayout, getPlotlyConfig());
        }

        // 3. MACD Chart
        if (macdEl && analysis.charts && analysis.charts.macd) {
            const macdData = analysis.charts.macd;
            const dates = macdData.dates;

            const macdLine = {
                x: dates,
                y: macdData.macd,
                type: 'scatter',
                mode: 'lines',
                name: 'MACD',
                line: { color: '#3b82f6', width: 1.8 }
            };

            const signalLine = {
                x: dates,
                y: macdData.signal,
                type: 'scatter',
                mode: 'lines',
                name: 'Signal',
                line: { color: '#f59e0b', width: 1.8 }
            };

            const histColors = macdData.histogram.map(v => v >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)');
            const histBar = {
                x: dates,
                y: macdData.histogram,
                type: 'bar',
                name: 'Histogram',
                marker: { color: histColors }
            };

            const macdLayout = getPlotlyLayout('', {
                height: 240,
                margin: { l: 40, r: 15, t: 10, b: 30 },
                legend: { orientation: 'h', y: 1.15 }
            });

            macdEl.innerHTML = '';
            Plotly.newPlot(macdEl, [macdLine, signalLine, histBar], macdLayout, getPlotlyConfig());
        }

        // 4. Quantitative Summary Tab
        if (summaryEl) {
            const q = analysis.quantitative || {};
            const sum = analysis.summary || {};

            summaryEl.innerHTML = `
                <div class="row g-3">
                    <div class="col-lg-6">
                        <div class="glass-card-static p-4 h-100">
                            <h6 class="fw-bold mb-3"><i class="bi bi-cpu me-2 text-primary"></i>Quantitative Signals</h6>
                            <ul class="list-unstyled d-flex flex-column gap-3 mb-0">
                                <li class="d-flex justify-content-between align-items-center pb-2 border-bottom border-secondary-subtle">
                                    <span>Signal Direction</span>
                                    <span class="badge ${sum.signal === 'BULLISH' ? 'bg-success' : sum.signal === 'BEARISH' ? 'bg-danger' : 'bg-secondary'}">${sum.signal || 'NEUTRAL'}</span>
                                </li>
                                <li class="d-flex justify-content-between align-items-center pb-2 border-bottom border-secondary-subtle">
                                    <span>Trend Momentum (RSI)</span>
                                    <span class="fw-semibold">${formatNumber(analysis.latest?.rsi, 2)} (${analysis.indicators?.rsiStatus || 'Normal'})</span>
                                </li>
                                <li class="d-flex justify-content-between align-items-center pb-2 border-bottom border-secondary-subtle">
                                    <span>Golden/Death Cross Status</span>
                                    <span class="fw-semibold">${analysis.indicators?.crossStatus || 'None'}</span>
                                </li>
                                <li class="d-flex justify-content-between align-items-center">
                                    <span>Bollinger Position</span>
                                    <span class="fw-semibold">${analysis.indicators?.bbPosition || 'Within Bands'}</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                    <div class="col-lg-6">
                        <div class="glass-card-static p-4 h-100">
                            <h6 class="fw-bold mb-3"><i class="bi bi-shield-check me-2 text-info"></i>Risk & Volatility Profile</h6>
                            <ul class="list-unstyled d-flex flex-column gap-3 mb-0">
                                <li class="d-flex justify-content-between align-items-center pb-2 border-bottom border-secondary-subtle">
                                    <span>Annualized Volatility</span>
                                    <span class="fw-semibold">${q.volatility != null ? q.volatility + '%' : 'N/A'}</span>
                                </li>
                                <li class="d-flex justify-content-between align-items-center pb-2 border-bottom border-secondary-subtle">
                                    <span>Beta (vs S&P 500)</span>
                                    <span class="fw-semibold">${formatNumber(stockData?.beta, 2)}</span>
                                </li>
                                <li class="d-flex justify-content-between align-items-center pb-2 border-bottom border-secondary-subtle">
                                    <span>52-Week Range Position</span>
                                    <span class="fw-semibold">${calculateRangePosition(stockData)}</span>
                                </li>
                                <li class="d-flex justify-content-between align-items-center">
                                    <span>Average Daily Volume</span>
                                    <span class="fw-semibold">${formatLargeNumber(stockData?.averageVolume)}</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            `;
        }

    } catch (err) {
        if (statsEl) statsEl.innerHTML = `<div class="col-12"><div class="error-message">${err.message}</div></div>`;
    }
}

function calculateRangePosition(data) {
    if (!data || !data.fiftyTwoWeekLow || !data.fiftyTwoWeekHigh || !data.regularMarketPrice) return 'N/A';
    const low = data.fiftyTwoWeekLow;
    const high = data.fiftyTwoWeekHigh;
    const current = data.regularMarketPrice;
    if (high === low) return '50%';
    const pct = Math.round(((current - low) / (high - low)) * 100);
    return `${pct}% of 52W High`;
}

// ─── Fundamentals ───
function renderFundamentals(data) {
    const metricsEl = document.getElementById('fundamentalMetrics');
    const profileEl = document.getElementById('companyProfile');
    const currency = data.currency || 'USD';

    if (metricsEl) {
        metricsEl.innerHTML = `
            <div class="metric-card">
                <span class="metric-label">Market Cap</span>
                <span class="metric-value">${formatLargeNumber(data.marketCap)} ${currency}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Trailing P/E</span>
                <span class="metric-value">${formatNumber(data.trailingPE)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Forward P/E</span>
                <span class="metric-value">${formatNumber(data.forwardPE)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">EPS (TTM)</span>
                <span class="metric-value">${formatCurrency(data.trailingEps, currency)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Dividend Yield</span>
                <span class="metric-value">${formatPercentRaw(data.dividendYield)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Beta</span>
                <span class="metric-value">${formatNumber(data.beta, 2)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">52-Week High</span>
                <span class="metric-value">${formatCurrency(data.fiftyTwoWeekHigh, currency)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">52-Week Low</span>
                <span class="metric-value">${formatCurrency(data.fiftyTwoWeekLow, currency)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Volume</span>
                <span class="metric-value">${formatLargeNumber(data.regularMarketVolume)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Avg Volume</span>
                <span class="metric-value">${formatLargeNumber(data.averageVolume)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Profit Margin</span>
                <span class="metric-value">${formatPercentRaw(data.profitMargins)}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Revenue (TTM)</span>
                <span class="metric-value">${formatLargeNumber(data.revenue)} ${currency}</span>
            </div>
        `;
    }

    if (profileEl) {
        profileEl.innerHTML = `
            <div class="d-flex flex-column gap-3">
                <p class="mb-0 text-secondary" style="line-height: 1.7;">
                    ${data.longBusinessSummary || 'No detailed business summary available for this company.'}
                </p>
                <hr class="my-2 border-secondary-subtle">
                <div class="row g-3 fs-7">
                    <div class="col-sm-4"><strong>Full Time Employees:</strong> ${data.fullTimeEmployees ? formatNumber(data.fullTimeEmployees, 0) : 'N/A'}</div>
                    <div class="col-sm-4"><strong>Website:</strong> ${data.website ? `<a href="${data.website}" target="_blank" rel="noopener" class="text-accent text-decoration-none">${data.website} <i class="bi bi-box-arrow-up-right fs-8"></i></a>` : 'N/A'}</div>
                    <div class="col-sm-4"><strong>City & State:</strong> ${[data.city, data.state, data.country].filter(Boolean).join(', ') || 'N/A'}</div>
                </div>
            </div>
        `;
    }
}

// ─── Financial Statements ───
async function loadFinancials(stmtType = 'income', btnEl = null) {
    currentStmtType = stmtType;
    if (btnEl) {
        btnEl.parentElement.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        btnEl.classList.add('active');
    }

    const tableEl = document.getElementById('financialsTable');
    if (!tableEl) return;

    tableEl.innerHTML = '<div class="skeleton skeleton-chart" style="height:250px"></div>';

    try {
        const res = await API.get(`/api/stock/${currentTicker}/financials?type=${stmtType}&freq=${currentFreq}`);
        const data = res.data;

        if (!data || !data.dates || data.dates.length === 0 || !data.rows || Object.keys(data.rows).length === 0) {
            tableEl.innerHTML = '<div class="empty-state p-4"><p>No financial statement data available for this selection.</p></div>';
            return;
        }

        const dates = data.dates;
        const rows = data.rows;

        let thead = `<tr><th style="min-width: 200px;">Metric</th>${dates.map(d => `<th class="text-end" style="min-width: 120px;">${d}</th>`).join('')}</tr>`;

        let tbody = Object.entries(rows).map(([metric, values]) => {
            return `<tr>
                <td class="fw-medium">${metric}</td>
                ${values.map(v => `<td class="text-end font-monospace">${formatLargeNumber(v)}</td>`).join('')}
            </tr>`;
        }).join('');

        tableEl.innerHTML = `
            <table class="table table-hover table-custom align-middle">
                <thead>${thead}</thead>
                <tbody>${tbody}</tbody>
            </table>
        `;
    } catch (err) {
        tableEl.innerHTML = `<div class="error-message"><i class="bi bi-exclamation-triangle me-2"></i>Error loading financials: ${err.message}</div>`;
    }
}

function changeFreq(freq) {
    currentFreq = freq;
    const annBtn = document.getElementById('freqAnnual');
    const qtrBtn = document.getElementById('freqQuarterly');
    if (annBtn) annBtn.classList.toggle('active', freq === 'annual');
    if (qtrBtn) qtrBtn.classList.toggle('active', freq === 'quarterly');
    loadFinancials(currentStmtType);
}

// ─── News ───
async function loadNews() {
    const container = document.getElementById('newsContainer');
    if (!container) return;

    try {
        const res = await API.get(`/api/stock/${currentTicker}/news`);
        const articles = res.articles;

        if (!articles || articles.length === 0) {
            container.innerHTML = '<div class="col-12"><div class="empty-state p-4"><p>No recent news articles found for this ticker.</p></div></div>';
            return;
        }

        container.innerHTML = articles.map(item => {
            const dateStr = item.publishedAt ? new Date(item.publishedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
            return `
                <div class="col-md-6">
                    <div class="glass-card-static p-3 h-100 d-flex flex-column justify-content-between">
                        <div>
                            <div class="d-flex justify-content-between text-muted fs-8 mb-2">
                                <span class="fw-semibold text-accent"><i class="bi bi-newspaper me-1"></i>${item.publisher || 'News'}</span>
                                <span>${dateStr}</span>
                            </div>
                            <h6 class="fw-bold mb-2">
                                <a href="${item.link}" target="_blank" rel="noopener noreferrer" class="text-body text-decoration-none hover-accent">
                                    ${item.title}
                                </a>
                            </h6>
                            ${item.summary ? `<p class="fs-7 text-secondary mb-3">${item.summary.substring(0, 160)}...</p>` : ''}
                        </div>
                        <a href="${item.link}" target="_blank" rel="noopener noreferrer" class="btn btn-glass btn-sm w-auto align-self-start mt-2">
                            Read Story <i class="bi bi-box-arrow-up-right ms-1 fs-8"></i>
                        </a>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        container.innerHTML = `<div class="col-12"><div class="error-message">Failed to load news: ${err.message}</div></div>`;
    }
}

function refreshData() {
    showToast('Refreshing stock data...', 'info');
    predictionLoaded = false;
    initStockPage(currentTicker);
}

// ─── Machine Learning Stock Price Prediction ───
let predictionLoaded = false;

async function loadStockPrediction(force = false) {
    if (predictionLoaded && !force) return;

    const loadingEl = document.getElementById('stockPredLoading');
    const contentEl = document.getElementById('stockPredContent');
    const errorEl = document.getElementById('stockPredError');

    if (loadingEl) loadingEl.classList.remove('d-none');
    if (contentEl) contentEl.classList.add('d-none');
    if (errorEl) errorEl.classList.add('d-none');

    try {
        const res = await API.get(`/api/stock/${encodeURIComponent(currentTicker)}/prediction${force ? '?refresh=true' : ''}`);
        renderStockPredictionData(res);
        predictionLoaded = true;
        if (contentEl) contentEl.classList.remove('d-none');
    } catch (err) {
        if (errorEl) {
            errorEl.className = 'error-message';
            errorEl.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>Prediction failed: ${err.message}`;
            errorEl.classList.remove('d-none');
        }
    } finally {
        if (loadingEl) loadingEl.classList.add('d-none');
    }
}

function renderStockPredictionData(pred) {
    if (!pred) return;

    const targetPriceEl = document.getElementById('stockPredTargetPrice');
    const targetDateEl = document.getElementById('stockPredTargetDate');
    const currentPriceEl = document.getElementById('stockPredCurrentPrice');
    const currentDateEl = document.getElementById('stockPredCurrentDate');
    const changeEl = document.getElementById('stockPredChange');
    const badgeEl = document.getElementById('stockPredDirectionBadge');
    const confEl = document.getElementById('stockPredConfidence');
    const modelBadge = document.getElementById('stockModelBadge');

    const currPrice = pred.currentPrice;
    const predPrice = pred.predictedPrice;
    const chg = pred.predictedChange;
    const chgPct = pred.predictedChangePercent;
    const isBullish = pred.direction === 'bullish';

    if (targetPriceEl) targetPriceEl.textContent = formatCurrency(predPrice);
    if (targetDateEl) targetDateEl.textContent = `Target: ${pred.predictionDate}`;
    if (currentPriceEl) currentPriceEl.textContent = formatCurrency(currPrice);
    if (currentDateEl) currentDateEl.textContent = `As of: ${pred.lastTradingDate || 'Last Close'}`;

    if (changeEl) {
        const sign = chg >= 0 ? '+' : '';
        const chgClass = changeClass(chg);
        changeEl.className = `fs-3 fw-bold mt-1 ${chgClass}`;
        changeEl.textContent = `${sign}${formatCurrency(chg)} (${sign}${chgPct}%)`;
    }

    if (badgeEl) {
        badgeEl.innerHTML = isBullish
            ? `<span class="badge bg-success-subtle text-success fs-7 border border-success-subtle"><i class="bi bi-arrow-up-right me-1"></i>Bullish Estimate</span>`
            : `<span class="badge bg-danger-subtle text-danger fs-7 border border-danger-subtle"><i class="bi bi-arrow-down-right me-1"></i>Bearish Estimate</span>`;
    }

    if (confEl && pred.uncertaintyInterval) {
        confEl.textContent = `${formatCurrency(pred.uncertaintyInterval.lower)} — ${formatCurrency(pred.uncertaintyInterval.upper)}`;
    }

    if (modelBadge) {
        modelBadge.textContent = `${pred.modelName || 'Random Forest Regressor'} (${pred.sampleCounts ? pred.sampleCounts.featuresUsed : 22} features)`;
    }

    // Metrics
    const metrics = pred.metrics || {};
    const dirAccEl = document.getElementById('stockMetricDirAcc');
    const maeEl = document.getElementById('stockMetricMae');
    const rmseEl = document.getElementById('stockMetricRmse');
    const r2El = document.getElementById('stockMetricR2');

    if (dirAccEl) dirAccEl.textContent = `${metrics.directionalAccuracy != null ? metrics.directionalAccuracy : 'N/A'}%`;
    if (maeEl) maeEl.textContent = formatCurrency(metrics.mae);
    if (rmseEl) rmseEl.textContent = formatCurrency(metrics.rmse);
    if (r2El) r2El.textContent = metrics.r2 != null ? metrics.r2.toFixed(3) : 'N/A';

    // Plotly Chart
    const chartEl = document.getElementById('stockPredictionChart');
    if (!chartEl) return;

    const comp = pred.chartComparison || {};
    const dates = comp.dates || [];
    const actualPrices = comp.actualPrices || [];
    const predPrices = comp.predictedPrices || [];
    const forecastDate = comp.forecastDate;
    const forecastPrice = comp.forecastPrice;

    if (dates.length === 0) {
        chartEl.innerHTML = '<div class="empty-state p-4"><p>No test data available for chart.</p></div>';
        return;
    }

    const plotData = [
        {
            x: dates,
            y: actualPrices,
            name: 'Actual Price (Test Data)',
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#38bdf8', width: 2 },
            marker: { size: 4, color: '#38bdf8' }
        },
        {
            x: dates,
            y: predPrices,
            name: 'ML Predicted Price',
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#fbbf24', width: 2, dash: 'dot' },
            marker: { size: 4, color: '#fbbf24' }
        }
    ];

    if (forecastDate && forecastPrice != null && dates.length > 0) {
        const lastDate = dates[dates.length - 1];
        const lastActual = actualPrices[actualPrices.length - 1];

        plotData.push({
            x: [lastDate, forecastDate],
            y: [lastActual, forecastPrice],
            name: 'Forecast Projection',
            type: 'scatter',
            mode: 'lines',
            line: { color: isBullish ? '#10b981' : '#ef4444', width: 2, dash: 'dash' },
            showlegend: false,
            hoverinfo: 'skip'
        });

        plotData.push({
            x: [forecastDate],
            y: [forecastPrice],
            name: 'Next-Period Estimate',
            type: 'scatter',
            mode: 'markers+text',
            text: [formatCurrency(forecastPrice)],
            textposition: 'top center',
            marker: {
                size: 11,
                color: isBullish ? '#10b981' : '#ef4444',
                symbol: 'diamond',
                line: { color: '#ffffff', width: 2 }
            }
        });

        if (pred.uncertaintyInterval) {
            plotData.push({
                x: [forecastDate, forecastDate],
                y: [pred.uncertaintyInterval.lower, pred.uncertaintyInterval.upper],
                name: 'Uncertainty Interval (±1.96× RMSE)',
                type: 'scatter',
                mode: 'lines',
                line: { color: 'rgba(234, 179, 8, 0.7)', width: 4 },
                hoverinfo: 'text',
                hovertext: `Range: ${formatCurrency(pred.uncertaintyInterval.lower)} — ${formatCurrency(pred.uncertaintyInterval.upper)}`
            });
        }
    }

    const layout = getPlotlyLayout(`Price Prediction Model vs Historical Test Data (${pred.symbol})`, {
        xaxis: {
            title: 'Trading Date',
            gridcolor: 'rgba(255,255,255,0.05)',
            type: 'category'
        },
        yaxis: {
            title: 'Price ($)',
            gridcolor: 'rgba(255,255,255,0.05)',
            tickformat: '$.2f'
        },
        height: 350,
        margin: { l: 50, r: 20, t: 40, b: 50 }
    });

    Plotly.newPlot(chartEl, plotData, layout, getPlotlyConfig());
}
