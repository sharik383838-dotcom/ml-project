/**
 * StockLens — Dashboard JavaScript
 * Manages Portfolio & Watchlist interactions, real-time PnL tracking,
 * ML Stock Price Predictions, and System Status health checks.
 */

document.addEventListener('DOMContentLoaded', async () => {
    await initDashboard();
});

let currentPredTicker = 'AAPL';

async function initDashboard() {
    // 1. Fetch system status (Database & Market Data)
    loadSystemStatus();

    try {
        document.getElementById('dashActionBtns')?.classList.remove('d-none');

        await Promise.allSettled([
            runPrediction(currentPredTicker),
            loadPredictionHistory()
        ]);

    } catch (err) {
        showError('predictionHistoryContainer', `Error initializing dashboard: ${err.message}`);
    }
}

// ─── System Health & Status ───
async function loadSystemStatus() {
    try {
        const res = await API.get('/api/status');
        const dbBadge = document.getElementById('dbStatusBadge');
        const marketBadge = document.getElementById('marketStatusBadge');
        const tsEl = document.getElementById('systemTimestamp');

        if (res && res.database) {
            const dbHealthy = res.database.isHealthy;
            if (dbBadge) {
                dbBadge.innerHTML = dbHealthy 
                    ? `<span class="badge rounded-pill bg-success-subtle text-success border border-success-subtle"><i class="bi bi-database-check me-1"></i>Database: Connected (${res.database.engine})</span>`
                    : `<span class="badge rounded-pill bg-danger-subtle text-danger border border-danger-subtle"><i class="bi bi-database-x me-1"></i>Database: Disconnected</span>`;
            }
        }

        if (res && res.marketData && marketBadge) {
            marketBadge.innerHTML = `<span class="badge rounded-pill bg-info-subtle text-info border border-info-subtle"><i class="bi bi-activity me-1"></i>Market Data: Real (${res.marketData.provider})</span>`;
        }

        if (tsEl) {
            tsEl.innerHTML = `<i class="bi bi-shield-check text-success me-1"></i>System Active • ${new Date().toLocaleTimeString()}`;
        }
    } catch (e) {
        console.warn('System status fetch failed:', e);
    }
}

// ─── ML Stock Price Prediction ───

function selectQuickTicker(ticker) {
    currentPredTicker = ticker.toUpperCase();
    const input = document.getElementById('predTickerInput');
    if (input) input.value = currentPredTicker;

    // Update active pill state
    document.querySelectorAll('#quickTickerPills button').forEach(btn => {
        if (btn.textContent.trim().toUpperCase() === currentPredTicker) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    runPrediction(currentPredTicker);
}

async function runPrediction(tickerParam) {
    const input = document.getElementById('predTickerInput');
    const ticker = (tickerParam || (input ? input.value : currentPredTicker) || 'AAPL').trim().toUpperCase();
    if (!ticker) {
        showToast('Please enter a stock ticker symbol.', 'warning');
        return;
    }
    currentPredTicker = ticker;

    const loadingEl = document.getElementById('predLoading');
    const contentEl = document.getElementById('predContent');
    const errorEl = document.getElementById('predError');
    const btn = document.getElementById('btnRunPrediction');

    if (loadingEl) loadingEl.classList.remove('d-none');
    if (contentEl) contentEl.classList.add('d-none');
    if (errorEl) errorEl.classList.add('d-none');
    if (btn) btn.disabled = true;

    try {
        const res = await API.get(`/api/stock/${encodeURIComponent(ticker)}/prediction`);
        renderPredictionData(res);
        if (contentEl) contentEl.classList.remove('d-none');
        loadPredictionHistory();
    } catch (err) {
        if (errorEl) {
            errorEl.className = 'error-message';
            errorEl.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>Prediction failed: ${err.message}`;
            errorEl.classList.remove('d-none');
        }
    } finally {
        if (loadingEl) loadingEl.classList.add('d-none');
        if (btn) btn.disabled = false;
    }
}

function renderPredictionData(pred) {
    if (!pred) return;

    // 1. Header Elements
    const targetPriceEl = document.getElementById('predTargetPrice');
    const targetDateEl = document.getElementById('predTargetDate');
    const currentPriceEl = document.getElementById('predCurrentPrice');
    const currentDateEl = document.getElementById('predCurrentDate');
    const changeEl = document.getElementById('predChange');
    const badgeEl = document.getElementById('predDirectionBadge');
    const intervalEl = document.getElementById('predConfidenceInterval');
    const modelBadge = document.getElementById('modelBadge');

    const currPrice = pred.currentPrice;
    const predPrice = pred.predictedPrice;
    const chg = pred.predictedChange;
    const chgPct = pred.predictedChangePercent;
    const isBullish = pred.direction === 'bullish';

    if (targetPriceEl) targetPriceEl.textContent = formatCurrency(predPrice);
    if (targetDateEl) targetDateEl.textContent = `Est. Target: ${pred.predictionDate}`;
    if (currentPriceEl) currentPriceEl.textContent = formatCurrency(currPrice);
    if (currentDateEl) currentDateEl.textContent = `As of: ${pred.lastTradingDate || 'Latest Close'}`;

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

    if (intervalEl && pred.uncertaintyInterval) {
        intervalEl.textContent = `${formatCurrency(pred.uncertaintyInterval.lower)} — ${formatCurrency(pred.uncertaintyInterval.upper)}`;
    }

    if (modelBadge) {
        modelBadge.textContent = `${pred.modelName || 'Random Forest'} (${pred.sampleCounts ? pred.sampleCounts.featuresUsed : 22} features)`;
    }

    // 2. Metrics
    const metrics = pred.metrics || {};
    const dirAccEl = document.getElementById('metricDirAcc');
    const maeEl = document.getElementById('metricMae');
    const rmseEl = document.getElementById('metricRmse');
    const r2El = document.getElementById('metricR2');

    if (dirAccEl) dirAccEl.textContent = `${metrics.directionalAccuracy != null ? metrics.directionalAccuracy : 'N/A'}%`;
    if (maeEl) maeEl.textContent = formatCurrency(metrics.mae);
    if (rmseEl) rmseEl.textContent = formatCurrency(metrics.rmse);
    if (r2El) r2El.textContent = metrics.r2 != null ? metrics.r2.toFixed(3) : 'N/A';

    // 3. Render Prediction Chart
    renderPredictionChart(pred);
}

function renderPredictionChart(pred) {
    const chartEl = document.getElementById('predictionChart');
    if (!chartEl) return;

    const comp = pred.chartComparison || {};
    const dates = comp.dates || [];
    const actualPrices = comp.actualPrices || [];
    const predPrices = comp.predictedPrices || [];
    const forecastDate = comp.forecastDate;
    const forecastPrice = comp.forecastPrice;

    if (dates.length === 0) {
        chartEl.innerHTML = '<div class="empty-state p-4"><p>Insufficient historical test series to plot.</p></div>';
        return;
    }

    // Trace 1: Actual Historical Test Prices
    const traceActual = {
        x: dates,
        y: actualPrices,
        name: 'Actual Price (Test Data)',
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#38bdf8', width: 2 },
        marker: { size: 4, color: '#38bdf8' }
    };

    // Trace 2: Model Predictions on Test Data
    const tracePred = {
        x: dates,
        y: predPrices,
        name: 'ML Predicted Price',
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#fbbf24', width: 2, dash: 'dot' },
        marker: { size: 4, color: '#fbbf24' }
    };

    const plotData = [traceActual, tracePred];

    // Trace 3: Out-of-sample Next Day Forecast Point
    if (forecastDate && forecastPrice != null && dates.length > 0) {
        const lastDate = dates[dates.length - 1];
        const lastActual = actualPrices[actualPrices.length - 1];

        // Connection line from last actual to forecast point
        plotData.push({
            x: [lastDate, forecastDate],
            y: [lastActual, forecastPrice],
            name: 'Forecast Projection',
            type: 'scatter',
            mode: 'lines',
            line: { color: pred.direction === 'bullish' ? '#10b981' : '#ef4444', width: 2, dash: 'dash' },
            showlegend: false,
            hoverinfo: 'skip'
        });

        // The forecast marker
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
                color: pred.direction === 'bullish' ? '#10b981' : '#ef4444',
                symbol: 'diamond',
                line: { color: '#ffffff', width: 2 }
            }
        });

        // Uncertainty interval visualization
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
        height: 340,
        margin: { l: 50, r: 20, t: 40, b: 50 }
    });

    Plotly.newPlot(chartEl, plotData, layout, getPlotlyConfig());
}

// ─── Prediction History ───
async function loadPredictionHistory() {
    const container = document.getElementById('predictionHistoryContainer');
    if (!container) return;

    try {
        const res = await API.get('/api/prediction/history');
        const records = res.predictions || [];

        if (records.length === 0) {
            container.innerHTML = `
                <div class="empty-state p-3 text-center">
                    <p class="text-secondary fs-7 mb-0">No past predictions recorded yet. Run a prediction above to store results.</p>
                </div>
            `;
            return;
        }

        let rows = records.map(r => {
            const chg = r.predicted_change;
            const chgPct = r.predicted_change_percent;
            const chgClass = changeClass(chg);
            const dateStr = (r.created_at || '').substring(0, 16).replace('T', ' ');

            return `
                <tr>
                    <td><a href="/stock/${r.ticker}" class="fw-bold text-accent">${r.ticker}</a></td>
                    <td>${formatCurrency(r.current_price)}</td>
                    <td class="fw-semibold">${formatCurrency(r.predicted_price)}</td>
                    <td class="${chgClass}">${chg >= 0 ? '+' : ''}${formatCurrency(chg)} (${chgPct >= 0 ? '+' : ''}${chgPct}%)</td>
                    <td>
                        <span class="badge ${chg >= 0 ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'}">
                            ${chg >= 0 ? 'Bullish' : 'Bearish'}
                        </span>
                    </td>
                    <td>${r.directional_accuracy != null ? `${r.directional_accuracy.toFixed(1)}%` : 'N/A'}</td>
                    <td class="text-muted fs-8">${r.model_name || 'Random Forest'}</td>
                    <td class="text-muted fs-8">${dateStr}</td>
                </tr>
            `;
        }).join('');

        container.innerHTML = `
            <table class="table custom-table align-middle mb-0">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Actual Price</th>
                        <th>Predicted Price</th>
                        <th>Expected Movement</th>
                        <th>Direction</th>
                        <th>Model Accuracy</th>
                        <th>Algorithm</th>
                        <th>Recorded At</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    } catch (e) {
        console.warn('Prediction history fetch failed:', e);
    }
}

function refreshDashboard() {
    showToast('Refreshing dashboard...', 'info');
    initDashboard();
}
