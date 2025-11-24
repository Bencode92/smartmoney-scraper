// Configuration
const NUM_FUNDS = 10;
const NUM_HOLDINGS = 30;
let currentTab = 0;
let fundsData = [];

// Initialize funds data structure
function initializeFunds() {
    for (let i = 0; i < NUM_FUNDS; i++) {
        fundsData[i] = {
            rank: i + 1,
            fund_id: `fund-${i + 1}`,
            fund_name: '',
            portfolio_manager: '',
            performance_3y: 0,
            aum_billions: 0,
            total_holdings: 0,
            holdings: []
        };
        
        // Initialize holdings
        for (let j = 0; j < NUM_HOLDINGS; j++) {
            fundsData[i].holdings[j] = {
                position: j + 1,
                ticker: '',
                company_name: '',
                portfolio_pct: 0,
                shares_owned_millions: 0,
                value_millions: 0,
                latest_activity_pct: 0,
                avg_buy_price: 0,
                price_change_pct: 0
            };
        }
    }
}

// Create tabs
function createTabs() {
    const container = document.getElementById('tabsContainer');
    container.innerHTML = '';
    
    for (let i = 0; i < NUM_FUNDS; i++) {
        const tab = document.createElement('button');
        tab.className = `tab ${i === 0 ? 'active' : ''}`;
        tab.id = `tab-${i}`;
        tab.onclick = () => switchTab(i);
        
        const badge = document.createElement('span');
        badge.className = 'tab-badge';
        badge.id = `badge-${i}`;
        badge.textContent = '0';
        badge.style.display = 'none';
        
        tab.innerHTML = `Fund ${i + 1}`;
        tab.appendChild(badge);
        container.appendChild(tab);
    }
}

// Create fund sections HTML
function createFundSections() {
    const container = document.getElementById('fundSections');
    
    for (let i = 0; i < NUM_FUNDS; i++) {
        const section = document.createElement('div');
        section.className = `fund-section ${i === 0 ? 'active' : ''}`;
        section.id = `fund-${i}`;
        
        section.innerHTML = `
            <h2>📈 Fund #${i + 1}</h2>
            
            <!-- Smart Parser for Full HedgeFollow Copy -->
            <div class="quick-paste-container">
                <div class="quick-paste-header">
                    <h3>⚡ Collage Rapide HedgeFollow</h3>
                    <span style="background: #4caf50; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">AUTO-DETECT</span>
                </div>
                
                <div class="paste-zone">
                    <textarea 
                        class="paste-textarea"
                        id="smart-paste-${i}" 
                        placeholder="Collez ICI tout le contenu copié depuis HedgeFollow:&#10;&#10;1. Le titre (ex: Jim Simons 13F Portfolio)&#10;2. La ligne d'info du fond&#10;3. Les holdings&#10;&#10;Le parser détectera automatiquement le format!"
                    ></textarea>
                    
                    <div class="parse-buttons">
                        <button class="btn btn-primary" onclick="smartParse(${i})">
                            <span>🤖</span> Parser Auto
                        </button>
                        <button class="btn btn-info" onclick="clearPaste(${i})">
                            <span>🧹</span> Nettoyer
                        </button>
                    </div>
                </div>
                
                <div class="format-hint">
                    <strong>Formats reconnus:</strong><br>
                    ✅ Titre portfolio: <code>Jim Simons 13F Portfolio</code><br>
                    ✅ Info fond: <code>Renaissance Technologies | Jim Simons | 19.55% | $75.79B | 3457</code><br>
                    ✅ Holdings: <code>1.26% | 6.88M | $953.51M | 12.81% | $60.8 | +46.8%</code><br>
                    ✅ Ou format ticker: <code>RBLX | Roblox Corp | 1.26% ...</code>
                </div>
                
                <div id="parse-status-${i}" class="parse-status"></div>
            </div>
            
            <div class="fund-info">
                <div class="form-group">
                    <label>Nom du Fond</label>
                    <input type="text" id="fund-name-${i}" placeholder="Ex: Renaissance Technologies" 
                           onchange="updateFundData(${i}, 'fund_name', this.value)">
                </div>
                <div class="form-group">
                    <label>Portfolio Manager</label>
                    <input type="text" id="fund-manager-${i}" placeholder="Ex: Jim Simons"
                           onchange="updateFundData(${i}, 'portfolio_manager', this.value)">
                </div>
                <div class="form-group">
                    <label>Performance 3Y (%)</label>
                    <input type="number" step="0.01" id="fund-perf-${i}" placeholder="Ex: 19.55"
                           onchange="updateFundData(${i}, 'performance_3y', parseFloat(this.value) || 0)">
                </div>
                <div class="form-group">
                    <label>AUM (Milliards $)</label>
                    <input type="number" step="0.01" id="fund-aum-${i}" placeholder="Ex: 75.79"
                           onchange="updateFundData(${i}, 'aum_billions', parseFloat(this.value) || 0)">
                </div>
                <div class="form-group">
                    <label>Nombre Total Holdings</label>
                    <input type="number" id="fund-holdings-${i}" placeholder="Ex: 3457"
                           onchange="updateFundData(${i}, 'total_holdings', parseInt(this.value) || 0)">
                </div>
            </div>
            
            <div class="holdings-section">
                <h3>📊 Top 30 Holdings</h3>
                
                <div class="holdings-table">
                    <table id="holdings-table-${i}">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Ticker</th>
                                <th>Company</th>
                                <th>% Portfolio</th>
                                <th>Shares (M)</th>
                                <th>Value ($M)</th>
                                <th>Activity (%)</th>
                                <th>Avg Price</th>
                                <th>Change (%)</th>
                            </tr>
                        </thead>
                        <tbody id="holdings-tbody-${i}">
                            ${createHoldingsRows(i)}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        
        container.appendChild(section);
    }
}

// Smart Parser - Détecte automatiquement le format HedgeFollow
function smartParse(fundIndex) {
    const textarea = document.getElementById(`smart-paste-${fundIndex}`);
    const text = textarea.value.trim();
    const statusDiv = document.getElementById(`parse-status-${fundIndex}`);
    
    if (!text) {
        showStatus(statusDiv, 'error', '❌ Aucune donnée à parser');
        return;
    }
    
    const lines = text.split('\n').filter(line => line.trim());
    let fundParsed = false;
    let holdingsParsed = 0;
    let currentHoldingIndex = 0;
    
    // Reset status
    statusDiv.className = 'parse-status';
    statusDiv.textContent = '';
    
    lines.forEach(line => {
        const trimmed = line.trim();
        
        // 1. Détection du titre du portfolio (ex: "Jim Simons 13F Portfolio")
        if (trimmed.includes('13F Portfolio') || trimmed.includes('Portfolio')) {
            const managerMatch = trimmed.match(/^(.+?)\s+13F\s+Portfolio/i) || 
                                trimmed.match(/^(.+?)\s+Portfolio/i);
            if (managerMatch) {
                const managerName = managerMatch[1].trim();
                document.getElementById(`fund-manager-${fundIndex}`).value = managerName;
                updateFundData(fundIndex, 'portfolio_manager', managerName);
            }
        }
        
        // 2. Détection de la ligne info fond (avec tabs ou pipes)
        if (!fundParsed && (trimmed.includes('\t') || trimmed.includes('|'))) {
            let parts = trimmed.includes('\t') ? trimmed.split('\t') : trimmed.split('|').map(p => p.trim());
            
            // Chercher le nom du fond (généralement premier élément non-numérique)
            parts.forEach((part, idx) => {
                part = part.trim();
                
                // Nom du fond (ex: "Renaissance Technologies")
                if (idx < 2 && part.length > 3 && !part.match(/^\d/) && !part.includes('%') && !part.includes('$')) {
                    if (part.includes('Technologies') || part.includes('Capital') || part.includes('Management') || 
                        part.includes('Partners') || part.includes('Fund')) {
                        document.getElementById(`fund-name-${fundIndex}`).value = part;
                        updateFundData(fundIndex, 'fund_name', part);
                        fundParsed = true;
                    }
                }
                
                // Manager (si pas déjà trouvé)
                if ((part.includes('Jim') || part.includes('Ken') || part.includes('Ray') || 
                     part.includes('Steve') || part.includes('David')) && 
                    !fundsData[fundIndex].portfolio_manager) {
                    document.getElementById(`fund-manager-${fundIndex}`).value = part;
                    updateFundData(fundIndex, 'portfolio_manager', part);
                }
                
                // Performance (XX.XX% ou juste XX%)
                const perfMatch = part.match(/^(\d+\.?\d*)%$/);
                if (perfMatch) {
                    const perf = parseFloat(perfMatch[1]);
                    if (perf > 0 && perf < 100) { // Performance raisonnable
                        document.getElementById(`fund-perf-${fundIndex}`).value = perf;
                        updateFundData(fundIndex, 'performance_3y', perf);
                    }
                }
                
                // AUM ($XX.XXB)
                const aumMatch = part.match(/^\$?(\d+\.?\d*)([BT])$/i);
                if (aumMatch) {
                    let aum = parseFloat(aumMatch[1]);
                    if (aumMatch[2].toUpperCase() === 'T') {
                        aum = aum * 1000;
                    }
                    document.getElementById(`fund-aum-${fundIndex}`).value = aum;
                    updateFundData(fundIndex, 'aum_billions', aum);
                }
                
                // Holdings count (nombre seul, généralement > 100)
                if (part.match(/^\d{3,4}$/) && parseInt(part) > 100) {
                    const holdings = parseInt(part);
                    document.getElementById(`fund-holdings-${fundIndex}`).value = holdings;
                    updateFundData(fundIndex, 'total_holdings', holdings);
                }
            });
        }
        
        // 3. Détection des holdings
        // Format 1: "1.26% 6.88M $953.51M 12.81% (+781.89k) $60.8 (+46.8%)"
        // Format 2: "RBLX Roblox Corp 1.26% ..."
        
        // Détection par % de portfolio au début
        if (trimmed.match(/^\d+\.?\d*%/) && currentHoldingIndex < NUM_HOLDINGS) {
            parseHoldingLine(trimmed, fundIndex, currentHoldingIndex);
            currentHoldingIndex++;
            holdingsParsed++;
        }
        
        // Détection par ticker (lettres majuscules au début)
        else if (trimmed.match(/^[A-Z]{1,5}(\.[A-Z])?\s/) && currentHoldingIndex < NUM_HOLDINGS) {
            parseHoldingLine(trimmed, fundIndex, currentHoldingIndex);
            currentHoldingIndex++;
            holdingsParsed++;
        }
    });
    
    // Update progress and status
    updateProgress();
    updateTabBadge(fundIndex);
    
    // Show status
    let statusMessage = '✅ Parsing terminé: ';
    if (fundParsed) statusMessage += 'Info fond OK, ';
    statusMessage += `${holdingsParsed} holdings parsés`;
    showStatus(statusDiv, 'success', statusMessage);
    
    // Clear textarea
    textarea.value = '';
}

// Parse une ligne de holding
function parseHoldingLine(line, fundIndex, holdingIndex) {
    // Nettoyer la ligne
    line = line.replace(/[()]/g, ' ').replace(/\s+/g, ' ').trim();
    
    // Essayer différents patterns
    let parts = [];
    
    // Si contient des tabs
    if (line.includes('\t')) {
        parts = line.split('\t').map(p => p.trim());
    }
    // Si contient des pipes
    else if (line.includes('|')) {
        parts = line.split('|').map(p => p.trim());
    }
    // Sinon, split par espaces multiples ou patterns reconnaissables
    else {
        // Essayer de trouver les patterns
        const patterns = {
            ticker: line.match(/^([A-Z]{1,5}(?:\.[A-Z])?)\s/),
            pct: line.match(/(\d+\.?\d*)%/),
            shares: line.match(/(\d+\.?\d*)[MBK]/i),
            value: line.match(/\$(\d+\.?\d*)[MBK]?/i),
            activity: line.match(/([+-]?\d+\.?\d*)%.*(?:k|M|B)/),
            price: line.match(/\$(\d+\.?\d*)\s/),
            change: line.match(/[+-](\d+\.?\d*)%(?!.*[kMB])/g)
        };
        
        // Ticker
        if (patterns.ticker) {
            document.getElementById(`ticker-${fundIndex}-${holdingIndex}`).value = patterns.ticker[1];
            updateHoldingData(fundIndex, holdingIndex, 'ticker', patterns.ticker[1]);
            
            // Company name (après le ticker, avant le premier %)
            const afterTicker = line.substring(patterns.ticker[0].length).trim();
            const beforePct = afterTicker.indexOf('%');
            if (beforePct > 0) {
                const companyName = afterTicker.substring(0, beforePct).replace(/\d+\.?\d*/g, '').trim();
                if (companyName.length > 2) {
                    document.getElementById(`company-${fundIndex}-${holdingIndex}`).value = companyName;
                    updateHoldingData(fundIndex, holdingIndex, 'company_name', companyName);
                }
            }
        }
        
        // Portfolio %
        if (patterns.pct && patterns.pct[1]) {
            const pct = parseFloat(patterns.pct[1]);
            if (pct > 0 && pct < 100) {
                document.getElementById(`pct-${fundIndex}-${holdingIndex}`).value = pct;
                updateHoldingData(fundIndex, holdingIndex, 'portfolio_pct', pct);
            }
        }
        
        // Shares
        if (patterns.shares && patterns.shares[1]) {
            let shares = parseFloat(patterns.shares[1]);
            const suffix = patterns.shares[0].slice(-1).toUpperCase();
            if (suffix === 'B') shares *= 1000;
            else if (suffix === 'K') shares /= 1000;
            
            document.getElementById(`shares-${fundIndex}-${holdingIndex}`).value = shares.toFixed(2);
            updateHoldingData(fundIndex, holdingIndex, 'shares_owned_millions', shares);
        }
        
        // Value
        if (patterns.value && patterns.value[1]) {
            let value = parseFloat(patterns.value[1]);
            if (patterns.value[0].includes('B')) value *= 1000;
            else if (patterns.value[0].includes('K')) value /= 1000;
            
            document.getElementById(`value-${fundIndex}-${holdingIndex}`).value = value.toFixed(2);
            updateHoldingData(fundIndex, holdingIndex, 'value_millions', value);
        }
        
        // Activity
        if (patterns.activity && patterns.activity[1]) {
            const activity = parseFloat(patterns.activity[1]);
            document.getElementById(`activity-${fundIndex}-${holdingIndex}`).value = activity;
            updateHoldingData(fundIndex, holdingIndex, 'latest_activity_pct', activity);
        }
        
        // Price
        if (patterns.price && patterns.price[1]) {
            const price = parseFloat(patterns.price[1]);
            document.getElementById(`avgprice-${fundIndex}-${holdingIndex}`).value = price;
            updateHoldingData(fundIndex, holdingIndex, 'avg_buy_price', price);
        }
        
        // Price change (dernier % trouvé généralement)
        if (patterns.change && patterns.change.length > 0) {
            const lastChange = patterns.change[patterns.change.length - 1];
            const change = parseFloat(lastChange);
            document.getElementById(`change-${fundIndex}-${holdingIndex}`).value = change;
            updateHoldingData(fundIndex, holdingIndex, 'price_change_pct', change);
        }
    }
}

// Show status message
function showStatus(div, type, message) {
    div.className = `parse-status ${type}`;
    div.textContent = message;
    setTimeout(() => {
        div.className = 'parse-status';
    }, 5000);
}

// Clear paste area
function clearPaste(fundIndex) {
    document.getElementById(`smart-paste-${fundIndex}`).value = '';
    document.getElementById(`parse-status-${fundIndex}`).className = 'parse-status';
}

// Update tab badge
function updateTabBadge(fundIndex) {
    const badge = document.getElementById(`badge-${fundIndex}`);
    let count = 0;
    
    fundsData[fundIndex].holdings.forEach(h => {
        if (h.ticker && h.ticker.trim() !== '') count++;
    });
    
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline-block';
        badge.className = count >= 10 ? 'tab-badge complete' : 'tab-badge';
    } else {
        badge.style.display = 'none';
    }
}

// Create holdings rows HTML
function createHoldingsRows(fundIndex) {
    let html = '';
    for (let j = 0; j < NUM_HOLDINGS; j++) {
        html += `
            <tr>
                <td>${j + 1}</td>
                <td><input type="text" id="ticker-${fundIndex}-${j}" 
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'ticker', this.value.toUpperCase())"></td>
                <td><input type="text" id="company-${fundIndex}-${j}"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'company_name', this.value)"></td>
                <td><input type="number" step="0.01" id="pct-${fundIndex}-${j}"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'portfolio_pct', parseFloat(this.value) || 0)"></td>
                <td><input type="number" step="0.01" id="shares-${fundIndex}-${j}"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'shares_owned_millions', parseFloat(this.value) || 0)"></td>
                <td><input type="number" step="0.01" id="value-${fundIndex}-${j}"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'value_millions', parseFloat(this.value) || 0)"></td>
                <td><input type="number" step="any" id="activity-${fundIndex}-${j}"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'latest_activity_pct', parseFloat(this.value) || 0)"></td>
                <td><input type="number" step="0.01" id="avgprice-${fundIndex}-${j}"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'avg_buy_price', parseFloat(this.value) || 0)"></td>
                <td><input type="number" step="any" id="change-${fundIndex}-${j}"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'price_change_pct', parseFloat(this.value) || 0)"></td>
            </tr>
        `;
    }
    return html;
}

// Update fund data
function updateFundData(fundIndex, field, value) {
    fundsData[fundIndex][field] = value;
    updateProgress();
    updateTabStatus(fundIndex);
    updateTabBadge(fundIndex);
    saveToLocalStorage();
}

// Update holding data
function updateHoldingData(fundIndex, holdingIndex, field, value) {
    fundsData[fundIndex].holdings[holdingIndex][field] = value;
    updateProgress();
    updateTabBadge(fundIndex);
    saveToLocalStorage();
}

// Update tab status
function updateTabStatus(fundIndex) {
    const fund = fundsData[fundIndex];
    const tab = document.getElementById(`tab-${fundIndex}`);
    
    if (fund.fund_name && fund.performance_3y && fund.aum_billions) {
        tab.classList.add('completed');
    } else {
        tab.classList.remove('completed');
    }
}

// Switch tab
function switchTab(index) {
    currentTab = index;
    
    // Update tabs
    document.querySelectorAll('.tab').forEach((tab, i) => {
        tab.classList.toggle('active', i === index);
    });
    
    // Update sections
    document.querySelectorAll('.fund-section').forEach((section, i) => {
        section.classList.toggle('active', i === index);
    });
}

// Generate JSON
function generateJSON() {
    const today = new Date().toISOString().split('T')[0];
    
    // Clean up data
    const cleanedFunds = fundsData
        .filter(fund => fund.fund_name && fund.fund_name.trim() !== '')
        .map(fund => ({
            ...fund,
            fund_id: fund.fund_name.toLowerCase().replace(/\s+/g, '-'),
            scraped_date: today,
            top_holdings: fund.holdings
                .filter(h => h.ticker && h.ticker.trim() !== '')
                .map(h => ({
                    ...h,
                    date: today
                }))
        }));
    
    // Calculate universe
    const allTickers = new Set();
    const tickerCounts = {};
    
    cleanedFunds.forEach(fund => {
        fund.top_holdings.forEach(holding => {
            if (holding.ticker) {
                allTickers.add(holding.ticker);
                tickerCounts[holding.ticker] = (tickerCounts[holding.ticker] || 0) + 1;
            }
        });
    });
    
    // Sort tickers by count
    const sortedTickers = Object.entries(tickerCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 20);
    
    const jsonData = {
        metadata: {
            last_updated: today,
            source: "HedgeFollow Manual Collection V3",
            description: "Top hedge funds by performance with top 30 holdings each"
        },
        top_funds: cleanedFunds,
        smart_universe_summary: {
            total_unique_tickers: allTickers.size,
            tickers_list: Array.from(allTickers).sort(),
            most_held_tickers: sortedTickers.map(([ticker, count]) => ({
                ticker,
                count,
                percentage: ((count / cleanedFunds.length) * 100).toFixed(1) + '%'
            })),
            generation_date: today
        }
    };
    
    // Display preview
    const preview = document.getElementById('jsonPreview');
    preview.style.display = 'block';
    preview.textContent = JSON.stringify(jsonData, null, 2);
    
    // Update stats
    updateStats(cleanedFunds, allTickers);
    
    return jsonData;
}

// Download JSON
function downloadJSON() {
    const jsonData = generateJSON();
    const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const today = new Date().toISOString().split('T')[0];
    a.href = url;
    a.download = `smart_money_data_${today}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Update progress
function updateProgress() {
    let filledFunds = 0;
    let totalHoldings = 0;
    
    fundsData.forEach((fund, i) => {
        if (fund.fund_name && fund.fund_name.trim() !== '') {
            filledFunds++;
        }
        fund.holdings.forEach(holding => {
            if (holding.ticker && holding.ticker.trim() !== '') {
                totalHoldings++;
            }
        });
        updateTabStatus(i);
    });
    
    const maxHoldings = NUM_FUNDS * NUM_HOLDINGS;
    const progress = Math.round((totalHoldings / maxHoldings) * 100);
    
    const progressBar = document.getElementById('progressBar');
    progressBar.style.width = progress + '%';
    progressBar.textContent = progress + '% Complete';
}

// Update stats
function updateStats(funds, tickers) {
    document.getElementById('statsSection').style.display = 'grid';
    document.getElementById('statFunds').textContent = funds.length;
    
    let totalHoldings = 0;
    let totalPerf = 0;
    
    funds.forEach(fund => {
        totalHoldings += fund.top_holdings.length;
        totalPerf += fund.performance_3y;
    });
    
    document.getElementById('statHoldings').textContent = totalHoldings;
    document.getElementById('statTickers').textContent = tickers.size;
    document.getElementById('statAvgPerf').textContent = 
        funds.length > 0 ? (totalPerf / funds.length).toFixed(2) + '%' : '0%';
}

// Save to localStorage
function saveToLocalStorage() {
    localStorage.setItem('smartMoneyDataV3', JSON.stringify(fundsData));
}

// Load from localStorage
function loadFromLocalStorage() {
    const saved = localStorage.getItem('smartMoneyDataV3');
    if (saved) {
        fundsData = JSON.parse(saved);
        
        // Populate form fields
        fundsData.forEach((fund, i) => {
            if (fund.fund_name) {
                document.getElementById(`fund-name-${i}`).value = fund.fund_name;
                document.getElementById(`fund-manager-${i}`).value = fund.portfolio_manager;
                document.getElementById(`fund-perf-${i}`).value = fund.performance_3y;
                document.getElementById(`fund-aum-${i}`).value = fund.aum_billions;
                document.getElementById(`fund-holdings-${i}`).value = fund.total_holdings;
            }
            
            fund.holdings.forEach((holding, j) => {
                if (holding.ticker) {
                    document.getElementById(`ticker-${i}-${j}`).value = holding.ticker;
                    document.getElementById(`company-${i}-${j}`).value = holding.company_name;
                    document.getElementById(`pct-${i}-${j}`).value = holding.portfolio_pct;
                    document.getElementById(`shares-${i}-${j}`).value = holding.shares_owned_millions;
                    document.getElementById(`value-${i}-${j}`).value = holding.value_millions;
                    document.getElementById(`activity-${i}-${j}`).value = holding.latest_activity_pct;
                    document.getElementById(`avgprice-${i}-${j}`).value = holding.avg_buy_price;
                    document.getElementById(`change-${i}-${j}`).value = holding.price_change_pct;
                }
            });
            updateTabStatus(i);
            updateTabBadge(i);
        });
        
        updateProgress();
        alert('✅ Données chargées avec succès!');
    } else {
        alert('❌ Aucune sauvegarde trouvée');
    }
}

// Clear all data
function clearAllData() {
    if (confirm('⚠️ Êtes-vous sûr de vouloir effacer toutes les données?')) {
        initializeFunds();
        document.querySelectorAll('input').forEach(input => input.value = '');
        document.querySelectorAll('textarea').forEach(textarea => textarea.value = '');
        updateProgress();
        localStorage.removeItem('smartMoneyDataV3');
        
        // Reset tabs
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.remove('completed');
        });
        
        // Reset badges
        for (let i = 0; i < NUM_FUNDS; i++) {
            const badge = document.getElementById(`badge-${i}`);
            badge.style.display = 'none';
        }
    }
}

// Analyze data
function analyzeData() {
    const jsonData = generateJSON();
    
    if (jsonData.top_funds.length === 0) {
        alert('⚠️ Veuillez entrer au moins un fond avant d\'analyser');
        return;
    }
    
    // Create analysis summary
    let analysis = '📊 ANALYSE SMART MONEY\n';
    analysis += '=' .repeat(50) + '\n\n';
    
    // Top funds
    analysis += '🏦 TOP FONDS PAR PERFORMANCE:\n';
    jsonData.top_funds
        .sort((a, b) => b.performance_3y - a.performance_3y)
        .slice(0, 5)
        .forEach((fund, i) => {
            analysis += `${i+1}. ${fund.fund_name}: ${fund.performance_3y}% (${fund.aum_billions}B AUM)\n`;
        });
    
    analysis += '\n🎯 TICKERS LES PLUS DÉTENUS:\n';
    jsonData.smart_universe_summary.most_held_tickers
        .slice(0, 10)
        .forEach((ticker, i) => {
            analysis += `${i+1}. ${ticker.ticker}: ${ticker.count} fonds (${ticker.percentage})\n`;
        });
    
    // Show in a better format
    const preview = document.getElementById('jsonPreview');
    preview.style.display = 'block';
    preview.innerHTML = `<pre style="color: #4fc3f7; font-size: 14px;">${analysis}</pre>`;
}

// Initialize on load
window.onload = function() {
    initializeFunds();
    createTabs();
    createFundSections();
    
    // Auto-save enabled
    console.log('💾 Auto-save enabled - Data saved to localStorage automatically');
};