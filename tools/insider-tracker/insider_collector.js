// ============================================================
// INSIDER TRACKER - SmartMoney Scraper
// Collecte et analyse des transactions insiders (Form 4 SEC)
// ============================================================

let insiderTrades = [];
let filteredTrades = [];

// ============== GITHUB CONFIG ==============

const GITHUB_CONFIG = {
    owner: 'Bencode92',
    repo: 'smartmoney-scraper',
    branch: 'main',
    basePath: 'data/raw/insider'
};

// ============== HELPERS PARSING ==============

function parseNumberWithSuffix(str) {
    if (!str) return 0;
    // Nettoie: $, virgules, espaces, flèches, parenthèses
    const s = String(str).replace(/[$,\s↓↑()]/g, '').trim();
    const match = s.match(/^([+-]?[\d.]+)\s*([KMB])?$/i);
    if (!match) return 0;

    let value = parseFloat(match[1]) || 0;
    const suffix = (match[2] || '').toUpperCase();

    if (suffix === 'B') value *= 1000;      // milliards → millions
    else if (suffix === 'K') value /= 1000; // milliers → millions
    // M ou rien: déjà millions

    return value;
}

function parsePrice(str) {
    if (!str) return 0;
    const s = String(str).replace(/[$,]/g, '').trim();
    const m = s.match(/([+-]?[\d.]+)/);
    return m ? parseFloat(m[1]) : 0;
}

function detectDirection(changeStr, tradeType) {
    const lower = (tradeType || '').toLowerCase();
    
    // Types explicites de vente
    if (lower.includes('sale') || lower.includes('sell')) return 'Sell';
    if (lower.includes('buy') || lower.includes('purchase')) return 'Buy';
    if (lower.includes('tax') || lower.includes('liability')) return 'Sell'; // Tax liability = vente forcée
    if (lower.includes('gift')) return 'Gift';
    if (lower.includes('exercise')) return 'Exercise';
    
    // Sinon, basé sur le signe du changement
    if (changeStr) {
        if (changeStr.includes('↓') || changeStr.includes('-')) return 'Sell';
        if (changeStr.includes('↑') || changeStr.includes('+')) return 'Buy';
    }
    
    return 'Unknown';
}

function parseRole(insiderCell) {
    let name = insiderCell;
    let role = '';
    
    // Patterns courants pour les rôles
    const rolePatterns = [
        /\b(CEO|CFO|COO|CTO|CMO|President|Chairman|Director|Officer|VP|SVP|EVP|General Counsel|Secretary|Treasurer)\b/i,
        /\b(10%\s*Owner|Major Shareholder|Beneficial Owner)\b/i
    ];
    
    for (const pattern of rolePatterns) {
        const match = insiderCell.match(pattern);
        if (match) {
            role = match[0];
            name = insiderCell.replace(match[0], '').trim();
            break;
        }
    }
    
    // Nettoyage
    name = name.replace(/[|\-–,]/g, ' ').replace(/\s+/g, ' ').trim();
    
    return { name, role };
}

function isInformativeTrade(trade) {
    const type = (trade.trade_type || '').toLowerCase();
    const role = (trade.role || '').toLowerCase();
    
    // Ventes planifiées (10b5-1) = moins informatif
    if (type.includes('plan') || type.includes('10b5')) return false;
    
    // Tax liability = pas informatif
    if (type.includes('tax') || type.includes('liability')) return false;
    
    // Achats open market par C-suite = très informatif
    if (trade.direction === 'Buy' && 
        (role.includes('ceo') || role.includes('cfo') || role.includes('director'))) {
        return true;
    }
    
    // Grosses transactions (>$1M) = informatif
    if (Math.abs(trade.transaction_value_millions) > 1) return true;
    
    return false;
}

// ============== PARSING PRINCIPAL ==============

function parseInsiderText() {
    const textarea = document.getElementById('insider-paste');
    const preview = document.getElementById('json-preview');
    const raw = textarea.value.trim();

    if (!raw) {
        alert('❌ Rien à parser');
        return;
    }

    // Lignes nettoyées
    const lines = raw
        .split('\n')
        .map(l => l.replace(/\r/g, '').trim())
        .filter(l => l.length > 0);

    const hasTab = raw.includes('\t');
    const sep = hasTab ? '\t' : /\s{2,}/; // tab ou ≥2 espaces

    // --- trouver la ligne d'en-tête ---
    let startIdx = 0;
    for (let i = 0; i < Math.min(lines.length, 5); i++) {
        const lower = lines[i].toLowerCase();
        if (lower.includes('stock') && (lower.includes('insider') || lower.includes('trade'))) {
            startIdx = i + 1;
            break;
        }
    }

    insiderTrades = [];
    filteredTrades = [];

    // --- détection du format (row vs vertical) ---
    let hasRowFormat = false;
    for (let i = startIdx; i < Math.min(lines.length, startIdx + 30); i++) {
        const parts = hasTab
            ? lines[i].split('\t').map(c => c.trim()).filter(Boolean)
            : lines[i].split(sep).map(c => c.trim()).filter(Boolean);

        // Si on trouve une ligne avec beaucoup de colonnes, on considère que
        // c'est un format "1 ligne = 1 trade"
        if (parts.length >= 7) {
            hasRowFormat = true;
            break;
        }
    }

    let parseErrors = 0;

    if (!hasRowFormat) {
        // ---------- FORMAT VERTICAL (OpenInsider copier-coller) ----------
        parseErrors = parseInsiderVerticalBlocks(lines, startIdx, hasTab, sep);
    } else {
        // ---------- FORMAT LIGNE PAR LIGNE (TSV/CSV) ----------
        for (let i = startIdx; i < lines.length; i++) {
            const line = lines[i];
            if (!line || line.startsWith('---')) continue;

            let cols = hasTab
                ? line.split('\t').map(c => c.trim())
                : line.split(sep).map(c => c.trim()).filter(c => c);

            if (cols.length < 6) {
                parseErrors++;
                continue;
            }

            // Ticker
            const tickerIdx = cols.findIndex(c => /^[A-Z]{1,6}$/.test(c));
            let ticker = '';
            let insiderCell = '';
            let tradeType = '';
            let changeSharesStr = '';
            let avgPriceStr = '';
            let transValueStr = '';
            let sharesOwnedStr = '';
            let title = '';
            let tradeDate = '';
            let filedDate = '';

            if (tickerIdx >= 0) {
                ticker           = cols[tickerIdx];
                insiderCell      = cols[tickerIdx + 1] || '';
                tradeType        = cols[tickerIdx + 2] || '';
                changeSharesStr  = cols[tickerIdx + 3] || '';
                avgPriceStr      = cols[tickerIdx + 4] || '';
                transValueStr    = cols[tickerIdx + 5] || '';
                sharesOwnedStr   = cols[tickerIdx + 6] || '';
                title            = cols[tickerIdx + 7] || '';
                tradeDate        = cols[tickerIdx + 8] || '';
                filedDate        = cols[tickerIdx + 9] || '';
            } else {
                ticker           = cols[0];
                insiderCell      = cols[1] || '';
                tradeType        = cols[2] || '';
                changeSharesStr  = cols[3] || '';
                avgPriceStr      = cols[4] || '';
                transValueStr    = cols[5] || '';
                sharesOwnedStr   = cols[6] || '';
                title            = cols[7] || '';
                tradeDate        = cols[8] || '';
                filedDate        = cols[9] || '';
            }

            if (!ticker || ticker.length > 6) continue;

            const { name, role } = parseRole(insiderCell);
            const direction = detectDirection(changeSharesStr, tradeType);

            let changeShares = parseNumberWithSuffix(changeSharesStr);
            if (direction === 'Sell' && changeShares > 0) changeShares = -changeShares;

            const avgPrice        = parsePrice(avgPriceStr);
            const transactionValue = parseNumberWithSuffix(transValueStr);
            const sharesOwned     = parseNumberWithSuffix(sharesOwnedStr);

            tradeDate = tradeDate.replace(/[^0-9-]/g, '');
            filedDate = filedDate.replace(/[^0-9-]/g, '');

            const trade = {
                ticker: ticker.toUpperCase(),
                insider_name: name,
                role: role,
                trade_type: tradeType,
                direction: direction,
                change_shares_millions: changeShares,
                avg_price: avgPrice,
                transaction_value_millions:
                    direction === 'Sell' ? -Math.abs(transactionValue) : transactionValue,
                shares_owned_millions: sharesOwned || null,
                title: title,
                trade_date: tradeDate,
                filed_date: filedDate,
                is_informative: false
            };

            trade.is_informative = isInformativeTrade(trade);
            insiderTrades.push(trade);
        }
    }

    // ---------- Post-traitement / affichage ----------
    filteredTrades = [...insiderTrades];

    const jsonData = generateInsiderJSON();
    preview.textContent = JSON.stringify(jsonData, null, 2);

    updateStats();
    renderTradesTable();

    document.getElementById('statsSection').style.display = 'grid';
    document.getElementById('tradesPanel').hidden = false;
    document.getElementById('progressBar').style.width = '100%';

    const msg = `✅ ${insiderTrades.length} transactions parsées`;
    if (parseErrors > 0) {
        alert(`${msg}\n⚠️ ${parseErrors} lignes / blocs ignorés (format invalide)`);
    } else {
        console.log(msg);
    }
}

// -------- PARSER FORMAT VERTICAL (OpenInsider copier-coller) --------
// Bloc typique :
// L0: TICKER + Nom         ex: "CNTB\tPanacea Innovation Ltd"
// L1: Rôle                 ex: "10% Owner"
// L2: Type de trade        ex: "Proposed Sale"
// L3: Δ Shares             ex: "2M"
// L4: Avg Price            ex: "$ 3"
// L5: Transaction Value    ex: "$ 6M"
// L6: Shares Owned         ex: "N/A" ou "296.79k"
// L7: Title + Dates        ex: "Ordinary Shares\t2025-11-24\t2025-11-24"

function parseInsiderVerticalBlocks(lines, startIdx, hasTab, sep) {
    let parseErrors = 0;

    for (let i = startIdx; i < lines.length; ) {
        const line = lines[i];
        if (!line) { i++; continue; }

        const firstParts = hasTab
            ? line.split('\t').map(c => c.trim()).filter(Boolean)
            : line.split(sep).map(c => c.trim()).filter(Boolean);

        const maybeTicker = firstParts[0];
        if (!maybeTicker || !/^[A-Z]{1,6}$/.test(maybeTicker)) {
            // pas un début de bloc, on avance
            i++;
            continue;
        }

        // On a besoin d'au moins 7 lignes supplémentaires pour un bloc complet
        if (i + 7 >= lines.length) {
            parseErrors++;
            break;
        }

        const ticker = maybeTicker.toUpperCase();
        const insiderNameLine = firstParts[1] || '';

        const roleLine        = (lines[i + 1] || '').trim();
        const tradeTypeLine   = (lines[i + 2] || '').trim();
        const changeLine      = (lines[i + 3] || '').trim();
        const priceLine       = (lines[i + 4] || '').trim();
        const valueLine       = (lines[i + 5] || '').trim();
        const ownedLine       = (lines[i + 6] || '').trim();
        const lastLine        = (lines[i + 7] || '').trim();

        const lastParts = hasTab
            ? lastLine.split('\t').map(c => c.trim()).filter(Boolean)
            : lastLine.split(sep).map(c => c.trim()).filter(Boolean);

        const title     = lastParts[0] || '';
        let tradeDate   = lastParts[1] || '';
        let filedDate   = lastParts[2] || '';

        // Recompose "nom + rôle" puis applique ton parseur de rôle
        const insiderCell = `${insiderNameLine} ${roleLine}`.trim();
        const { name, role } = parseRole(insiderCell);
        const direction = detectDirection(changeLine, tradeTypeLine);

        // Nombres
        let changeShares = parseNumberWithSuffix(changeLine);
        if (direction === 'Sell' && changeShares > 0) changeShares = -changeShares;

        const avgPrice         = parsePrice(priceLine);
        const transactionValue = parseNumberWithSuffix(valueLine);
        const sharesOwned      = parseNumberWithSuffix(ownedLine);

        // Nettoie les dates
        tradeDate = tradeDate.replace(/[^0-9-]/g, '');
        filedDate = filedDate.replace(/[^0-9-]/g, '');

        const trade = {
            ticker: ticker,
            insider_name: name,
            role: role,
            trade_type: tradeTypeLine,
            direction: direction,
            change_shares_millions: changeShares,
            avg_price: avgPrice,
            transaction_value_millions:
                direction === 'Sell' ? -Math.abs(transactionValue) : transactionValue,
            shares_owned_millions: sharesOwned || null,
            title: title,
            trade_date: tradeDate,
            filed_date: filedDate,
            is_informative: false
        };

        trade.is_informative = isInformativeTrade(trade);
        insiderTrades.push(trade);

        // on saute au bloc suivant
        i += 8;
    }

    return parseErrors;
}

// ============== GÉNÉRATION JSON ==============

function generateInsiderJSON() {
    const today = new Date().toISOString().split('T')[0];
    
    // Calculs agrégés
    const tickers = [...new Set(insiderTrades.map(t => t.ticker))];
    const sells = insiderTrades.filter(t => t.direction === 'Sell');
    const buys = insiderTrades.filter(t => t.direction === 'Buy');
    
    const totalSellValue = sells.reduce((sum, t) => sum + Math.abs(t.transaction_value_millions), 0);
    const totalBuyValue = buys.reduce((sum, t) => sum + Math.abs(t.transaction_value_millions), 0);
    
    // Agrégation par ticker
    const tickerSummary = {};
    insiderTrades.forEach(t => {
        if (!tickerSummary[t.ticker]) {
            tickerSummary[t.ticker] = {
                ticker: t.ticker,
                total_sells: 0,
                total_buys: 0,
                sell_value_millions: 0,
                buy_value_millions: 0,
                net_value_millions: 0,
                insider_count: new Set(),
                has_ceo_cfo_activity: false
            };
        }
        
        const s = tickerSummary[t.ticker];
        s.insider_count.add(t.insider_name);
        
        if (t.direction === 'Sell') {
            s.total_sells++;
            s.sell_value_millions += Math.abs(t.transaction_value_millions);
        } else if (t.direction === 'Buy') {
            s.total_buys++;
            s.buy_value_millions += Math.abs(t.transaction_value_millions);
        }
        
        s.net_value_millions = s.buy_value_millions - s.sell_value_millions;
        
        if (t.role && /ceo|cfo|president|chairman/i.test(t.role)) {
            s.has_ceo_cfo_activity = true;
        }
    });
    
    // Convertir Set en count
    Object.values(tickerSummary).forEach(s => {
        s.insider_count = s.insider_count.size;
    });
    
    // Top ventes et achats
    const topSellers = Object.values(tickerSummary)
        .filter(s => s.sell_value_millions > 0)
        .sort((a, b) => b.sell_value_millions - a.sell_value_millions)
        .slice(0, 10);
        
    const topBuyers = Object.values(tickerSummary)
        .filter(s => s.buy_value_millions > 0)
        .sort((a, b) => b.buy_value_millions - a.buy_value_millions)
        .slice(0, 10);
    
    return {
        metadata: {
            last_updated: today,
            source: "Insider Tracker - SmartMoney Scraper",
            description: "Transactions insiders (Form 4 SEC)",
            total_trades: insiderTrades.length,
            date_range: getDateRange()
        },
        summary: {
            total_transactions: insiderTrades.length,
            total_sells: sells.length,
            total_buys: buys.length,
            unique_tickers: tickers.length,
            unique_insiders: [...new Set(insiderTrades.map(t => t.insider_name))].length,
            total_sell_value_millions: Math.round(totalSellValue * 100) / 100,
            total_buy_value_millions: Math.round(totalBuyValue * 100) / 100,
            net_flow_millions: Math.round((totalBuyValue - totalSellValue) * 100) / 100,
            sell_buy_ratio: buys.length > 0 ? Math.round((sells.length / buys.length) * 100) / 100 : null
        },
        ticker_summary: Object.values(tickerSummary).sort((a, b) => 
            Math.abs(b.net_value_millions) - Math.abs(a.net_value_millions)
        ),
        signals: {
            top_net_sellers: topSellers,
            top_net_buyers: topBuyers,
            cluster_sells: Object.values(tickerSummary)
                .filter(s => s.insider_count >= 3 && s.total_sells >= 3)
                .map(s => s.ticker),
            ceo_cfo_activity: Object.values(tickerSummary)
                .filter(s => s.has_ceo_cfo_activity)
                .map(s => s.ticker)
        },
        insider_trades: insiderTrades
    };
}

function getDateRange() {
    const dates = insiderTrades
        .map(t => t.trade_date)
        .filter(d => d && d.match(/\d{4}-\d{2}-\d{2}/))
        .sort();
    
    if (dates.length === 0) return null;
    return {
        start: dates[0],
        end: dates[dates.length - 1]
    };
}

// ============== STATISTIQUES ==============

function updateStats() {
    const sells = insiderTrades.filter(t => t.direction === 'Sell');
    const buys = insiderTrades.filter(t => t.direction === 'Buy');
    const tickers = [...new Set(insiderTrades.map(t => t.ticker))];
    
    const sellVolume = sells.reduce((sum, t) => sum + Math.abs(t.transaction_value_millions), 0);
    const buyVolume = buys.reduce((sum, t) => sum + Math.abs(t.transaction_value_millions), 0);
    
    document.getElementById('statTotal').textContent = insiderTrades.length;
    document.getElementById('statSells').textContent = sells.length;
    document.getElementById('statBuys').textContent = buys.length;
    document.getElementById('statTickers').textContent = tickers.length;
    document.getElementById('statSellVolume').textContent = `$${sellVolume.toFixed(1)}M`;
    document.getElementById('statBuyVolume').textContent = `$${buyVolume.toFixed(1)}M`;
}

// ============== ANALYSE DES SIGNAUX ==============

function analyzeSignals() {
    if (insiderTrades.length === 0) {
        alert('⚠️ Aucune transaction à analyser');
        return;
    }
    
    const jsonData = generateInsiderJSON();
    const alerts = [];
    
    // 1. Clusters de ventes (bearish)
    jsonData.signals.cluster_sells.forEach(ticker => {
        const summary = jsonData.ticker_summary.find(s => s.ticker === ticker);
        alerts.push({
            type: 'danger',
            icon: '🔴',
            message: `<strong>${ticker}</strong>: Cluster de ventes - ${summary.insider_count} insiders ont vendu ($${summary.sell_value_millions.toFixed(1)}M)`
        });
    });
    
    // 2. Activité CEO/CFO
    jsonData.signals.ceo_cfo_activity.forEach(ticker => {
        const trades = insiderTrades.filter(t => t.ticker === ticker && /ceo|cfo|president/i.test(t.role));
        const hasBuy = trades.some(t => t.direction === 'Buy');
        const hasSell = trades.some(t => t.direction === 'Sell');
        
        if (hasBuy) {
            alerts.push({
                type: 'success',
                icon: '🟢',
                message: `<strong>${ticker}</strong>: Achat C-suite détecté - signal bullish fort`
            });
        }
        if (hasSell) {
            alerts.push({
                type: 'warning',
                icon: '🟡',
                message: `<strong>${ticker}</strong>: Vente C-suite - à surveiller (vérifier si planifiée)`
            });
        }
    });
    
    // 3. Grosses transactions (>$10M)
    insiderTrades
        .filter(t => Math.abs(t.transaction_value_millions) >= 10)
        .forEach(t => {
            const type = t.direction === 'Buy' ? 'success' : 'warning';
            const icon = t.direction === 'Buy' ? '💚' : '💰';
            alerts.push({
                type: type,
                icon: icon,
                message: `<strong>${t.ticker}</strong>: Transaction majeure $${Math.abs(t.transaction_value_millions).toFixed(1)}M (${t.direction}) par ${t.insider_name}`
            });
        });
    
    // 4. Ratio sell/buy global
    if (jsonData.summary.sell_buy_ratio > 5) {
        alerts.push({
            type: 'danger',
            icon: '⚠️',
            message: `Ratio ventes/achats élevé: ${jsonData.summary.sell_buy_ratio}x - sentiment bearish général`
        });
    } else if (jsonData.summary.sell_buy_ratio < 0.5 && jsonData.summary.total_buys > 5) {
        alerts.push({
            type: 'success',
            icon: '📈',
            message: `Ratio ventes/achats faible: ${jsonData.summary.sell_buy_ratio}x - sentiment bullish`
        });
    }
    
    // Affichage
    const alertsSection = document.getElementById('alertsSection');
    if (alerts.length > 0) {
        alertsSection.innerHTML = alerts.map(a => `
            <div class="alert alert-${a.type}">
                <span>${a.icon}</span>
                <span>${a.message}</span>
            </div>
        `).join('');
        alertsSection.style.display = 'block';
    } else {
        alertsSection.innerHTML = '<div class="alert alert-info">ℹ️ Aucun signal particulier détecté</div>';
        alertsSection.style.display = 'block';
    }
}

// ============== TABLE DES TRADES ==============

function renderTradesTable() {
    const tbody = document.getElementById('tradesBody');
    tbody.innerHTML = '';
    
    filteredTrades.forEach(t => {
        const directionClass = t.direction === 'Sell' ? 'badge-sell' : 'badge-buy';
        const valueColor = t.direction === 'Sell' ? 'color: #ef4444' : 'color: #10b981';
        
        tbody.innerHTML += `
            <tr>
                <td><a class="ticker-link" href="https://finance.yahoo.com/quote/${t.ticker}" target="_blank">${t.ticker}</a></td>
                <td>${t.insider_name}</td>
                <td>${t.role || '-'}</td>
                <td>${t.trade_type}</td>
                <td><span class="badge ${directionClass}">${t.direction}</span></td>
                <td>${formatNumber(t.change_shares_millions)}M</td>
                <td>$${t.avg_price.toFixed(2)}</td>
                <td style="${valueColor}; font-weight: 600;">$${Math.abs(t.transaction_value_millions).toFixed(2)}M</td>
                <td>${t.trade_date}</td>
            </tr>
        `;
    });
}

function formatNumber(num) {
    if (num === null || num === undefined) return 'N/A';
    const sign = num >= 0 ? '+' : '';
    return sign + num.toFixed(2);
}

function filterTrades(type) {
    // Update button states
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    switch (type) {
        case 'sell':
            filteredTrades = insiderTrades.filter(t => t.direction === 'Sell');
            break;
        case 'buy':
            filteredTrades = insiderTrades.filter(t => t.direction === 'Buy');
            break;
        case 'ceo':
            filteredTrades = insiderTrades.filter(t => 
                t.role && /ceo|cfo|president|chairman|director/i.test(t.role)
            );
            break;
        case 'large':
            filteredTrades = insiderTrades.filter(t => 
                Math.abs(t.transaction_value_millions) >= 5
            );
            break;
        default:
            filteredTrades = [...insiderTrades];
    }
    
    renderTradesTable();
}

// ============== DOWNLOAD ==============

function downloadInsiderJSON() {
    const data = generateInsiderJSON();
    if (!data.insider_trades || data.insider_trades.length === 0) {
        alert('⚠️ Aucune transaction à sauvegarder');
        return;
    }
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const today = new Date().toISOString().split('T')[0];
    a.href = url;
    a.download = `insider_trades_${today}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// ============== GITHUB INTEGRATION ==============

function getGitHubToken() {
    let token = localStorage.getItem('github_token');
    if (!token) {
        token = prompt('🔑 Entre ton GitHub Personal Access Token (stocké localement):');
        if (token) {
            localStorage.setItem('github_token', token);
        }
    }
    return token;
}

function clearGitHubToken() {
    localStorage.removeItem('github_token');
    alert('🗑️ Token GitHub supprimé');
}

async function pushToGitHub() {
    const token = getGitHubToken();
    if (!token) {
        alert('❌ Token GitHub requis');
        return;
    }

    const jsonData = generateInsiderJSON();
    if (jsonData.insider_trades.length === 0) {
        alert('⚠️ Aucune transaction à sauvegarder');
        return;
    }

    const today = new Date().toISOString().split('T')[0];
    const filename = `insider_trades_${today}.json`;
    const filePath = `${GITHUB_CONFIG.basePath}/${filename}`;
    
    const content = btoa(unescape(encodeURIComponent(JSON.stringify(jsonData, null, 2))));

    const statusDiv = document.getElementById('github-status');
    statusDiv.textContent = '⏳ Push en cours vers GitHub...';
    statusDiv.className = 'github-status pending';
    statusDiv.style.display = 'block';

    try {
        // 1. Vérifier si le fichier existe
        let sha = null;
        const checkUrl = `https://api.github.com/repos/${GITHUB_CONFIG.owner}/${GITHUB_CONFIG.repo}/contents/${filePath}?ref=${GITHUB_CONFIG.branch}`;
        
        const checkResp = await fetch(checkUrl, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        });
        
        if (checkResp.ok) {
            const existingFile = await checkResp.json();
            sha = existingFile.sha;
        }

        // 2. Créer ou mettre à jour
        const putUrl = `https://api.github.com/repos/${GITHUB_CONFIG.owner}/${GITHUB_CONFIG.repo}/contents/${filePath}`;
        
        const body = {
            message: `🕵️ Update insider trades ${today} - ${jsonData.insider_trades.length} transactions`,
            content: content,
            branch: GITHUB_CONFIG.branch
        };
        
        if (sha) body.sha = sha;

        const putResp = await fetch(putUrl, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });

        const result = await putResp.json();

        if (!putResp.ok) {
            throw new Error(result.message || 'Erreur GitHub API');
        }

        statusDiv.innerHTML = `✅ Push réussi! <a href="${result.content.html_url}" target="_blank">Voir sur GitHub</a>`;
        statusDiv.className = 'github-status success';
        
        alert(`✅ Fichier pushé: ${filePath}`);

    } catch (err) {
        console.error('GitHub push error:', err);
        statusDiv.textContent = `❌ Erreur: ${err.message}`;
        statusDiv.className = 'github-status error';
        
        if (err.message.includes('Bad credentials')) {
            localStorage.removeItem('github_token');
            alert('❌ Token invalide. Réessaie.');
        } else {
            alert(`❌ Erreur push GitHub: ${err.message}`);
        }
    }
}

// ============== UTILITIES ==============

function clearAll() {
    document.getElementById('insider-paste').value = '';
    document.getElementById('json-preview').textContent = '// Le JSON apparaîtra ici après parsing...';
    document.getElementById('alertsSection').style.display = 'none';
    document.getElementById('statsSection').style.display = 'none';
    document.getElementById('tradesPanel').hidden = true;
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('github-status').style.display = 'none';
    insiderTrades = [];
    filteredTrades = [];
}

// ============== INIT ==============

console.log('🕵️ Insider Tracker - SmartMoney Scraper');
console.log('📋 Colle le tableau d\'insider trades et clique Parser');

