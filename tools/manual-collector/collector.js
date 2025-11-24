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
            fund_name: '',           // Berkshire Hathaway
            portfolio_manager: '',   // Warren Buffett
            performance_3y: 0,       // 7.17% (peut être 25Q3, 26Q1, etc.)
            aum_billions: 0,         // 267.34
            total_holdings: 0,       // 41
            holdings: []
        };
        
        // Initialize holdings - Structure complète HedgeFollow
        for (let j = 0; j < NUM_HOLDINGS; j++) {
            fundsData[i].holdings[j] = {
                position: j + 1,
                ticker: '',                     // AAPL
                company_name: '',               // Apple Inc
                portfolio_pct: 0,               // 22.69%
                delta_portfolio_pct: 0,         // 0.38% (Δ % of Portf)
                shares_owned_millions: 0,       // 238.21M
                value_millions: 0,              // $ 60.66B → 60660M
                trade_value_millions: 0,        // $ 9.61B → 9610M
                latest_activity_pct: 0,         // -14.92%
                latest_activity_shares: '',     // (-41.79M)
                avg_buy_price: 0,               // $39.59
                price_change_pct: 0,            // (+585.8%)
                sector: '',                     // Technology
                date: ''                        // 2025-09-30
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
            
            <!-- Smart Parser HedgeFollow Exact Format -->
            <div class="quick-paste-container">
                <div class="quick-paste-header">
                    <h3>⚡ Copier-Coller HedgeFollow Direct</h3>
                    <span style="background: #ff5722; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">FORMAT EXACT</span>
                </div>
                
                <div class="paste-zone">
                    <textarea 
                        class="paste-textarea"
                        id="smart-paste-${i}" 
                        placeholder="📋 COLLER ICI tout le contenu depuis HedgeFollow&#10;&#10;1️⃣ Sélectionnez TOUT depuis le titre (ex: Warren Buffett 13F Portfolio)&#10;2️⃣ Jusqu'au dernier holding&#10;3️⃣ Ctrl+C puis collez ici&#10;&#10;Format attendu:&#10;Warren Buffett 13F Portfolio&#10;Berkshire Hathaway | Warren Buffett | 7.17% | $267.34B | 41&#10;AAPL&#10;Apple Inc&#10;22.69%&#10;0.38%&#10;238.21M&#10;$ 60.66B&#10;..."
                        rows="12"
                    ></textarea>
                    
                    <div class="parse-buttons">
                        <button class="btn btn-primary" onclick="smartParse(${i})">
                            <span>🚀</span> Parser Direct
                        </button>
                        <button class="btn btn-warning" onclick="clearPaste(${i})">
                            <span>🗑️</span> Clear
                        </button>
                    </div>
                </div>
                
                <div class="format-hint">
                    <strong>📌 Format HedgeFollow Standard:</strong><br>
                    <div style="background: #f5f5f5; padding: 8px; border-radius: 4px; margin-top: 5px; font-size: 11px;">
                        🔹 <b>Header:</b> [Manager] 13F Portfolio<br>
                        🔹 <b>Info:</b> [Fund] | [Manager] | [Perf%] | [$AUM] | [Holdings#]<br>
                        🔹 <b>Holdings (Format Tableau):</b><br>
                        &nbsp;&nbsp;&nbsp;&nbsp;Stock → Company → % Portfolio → Δ% → Shares → Value → ...<br>
                        🔹 <b>OU Format Vertical:</b> Chaque champ sur une ligne séparée
                    </div>
                </div>
                
                <div id="parse-status-${i}" class="parse-status"></div>
            </div>
            
            <div class="fund-info">
                <div class="form-group">
                    <label>Hedge Fund</label>
                    <input type="text" id="fund-name-${i}" placeholder="Ex: Berkshire Hathaway" 
                           onchange="updateFundData(${i}, 'fund_name', this.value)">
                </div>
                <div class="form-group">
                    <label>Portfolio Manager</label>
                    <input type="text" id="fund-manager-${i}" placeholder="Ex: Warren Buffett"
                           onchange="updateFundData(${i}, 'portfolio_manager', this.value)">
                </div>
                <div class="form-group">
                    <label>Performance (25Q3, 26Q1...)</label>
                    <input type="number" step="0.01" id="fund-perf-${i}" placeholder="Ex: 7.17"
                           onchange="updateFundData(${i}, 'performance_3y', parseFloat(this.value) || 0)">
                </div>
                <div class="form-group">
                    <label>AUM (13F) en Milliards</label>
                    <input type="number" step="0.01" id="fund-aum-${i}" placeholder="Ex: 267.34"
                           onchange="updateFundData(${i}, 'aum_billions', parseFloat(this.value) || 0)">
                </div>
                <div class="form-group">
                    <label># of Holdings</label>
                    <input type="number" id="fund-holdings-${i}" placeholder="Ex: 41"
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
                                <th>Stock</th>
                                <th>Company</th>
                                <th>% Portfolio</th>
                                <th>Δ%</th>
                                <th>Shares (M)</th>
                                <th>Value ($M)</th>
<th>Activity %</th>
<th>Δ Shares (M)</th>
<th>Avg Price</th>
<th>Sector</th>
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

// Parse le header du fond (titre + ligne info)
function parseFundHeader(lines, fundIndex) {
    let lineIdx = 0;
    let fundParsed = false;
    
    while (lineIdx < lines.length && lineIdx < 10) {
        const line = lines[lineIdx].trim();
        
        // 1. Titre du portfolio "Warren Buffett 13F Portfolio"
        if (line.includes('13F Portfolio')) {
            const managerMatch = line.match(/^(.+?)\s+13F\s+Portfolio$/i);
            if (managerMatch) {
                const manager = managerMatch[1].trim();
                document.getElementById(`fund-manager-${fundIndex}`).value = manager;
                updateFundData(fundIndex, 'portfolio_manager', manager);
            }
            lineIdx++;
            continue;
        }
        
        // 2. Ligne info avec pipes ou tabs
        // Format: Berkshire Hathaway | Warren Buffett | 7.17% | $267.34B | 41
        if ((line.includes('|') || line.includes('\t')) && line.includes('%')) {
            const separator = line.includes('|') ? '|' : '\t';
            const parts = line.split(separator).map(p => p.trim());
            
            parts.forEach((part, idx) => {
                // Fund Name (généralement premier)
                if (idx === 0 && part.length > 2 && !part.includes('%') && !part.includes('$')) {
                    document.getElementById(`fund-name-${fundIndex}`).value = part;
                    updateFundData(fundIndex, 'fund_name', part);
                    fundParsed = true;
                }
                
                // Manager (si pas déjà trouvé)
                if (idx === 1 && !fundsData[fundIndex].portfolio_manager) {
                    document.getElementById(`fund-manager-${fundIndex}`).value = part;
                    updateFundData(fundIndex, 'portfolio_manager', part);
                }
                
                // Performance % (peut être 25Q3, 26Q1, etc. - on prend juste le nombre)
                const perfMatch = part.match(/(\d+\.?\d*)%/);
                if (perfMatch && idx <= 3) {
                    const perf = parseFloat(perfMatch[1]);
                    if (perf > 0 && perf < 100) {
                        document.getElementById(`fund-perf-${fundIndex}`).value = perf;
                        updateFundData(fundIndex, 'performance_3y', perf);
                    }
                }
                
                // AUM ($XXX.XXB ou $XXX.XXT)
                const aumMatch = part.match(/\$(\d+\.?\d*)([BT])/i);
                if (aumMatch) {
                    let aum = parseFloat(aumMatch[1]);
                    if (aumMatch[2].toUpperCase() === 'T') {
                        aum = aum * 1000; // Trillion to Billion
                    }
                    document.getElementById(`fund-aum-${fundIndex}`).value = aum;
                    updateFundData(fundIndex, 'aum_billions', aum);
                }
                
                // Number of holdings (nombre seul, généralement < 10000)
                if (part.match(/^\d+$/) && parseInt(part) < 10000) {
                    const holdings = parseInt(part);
                    document.getElementById(`fund-holdings-${fundIndex}`).value = holdings;
                    updateFundData(fundIndex, 'total_holdings', holdings);
                }
            });
            
            return lineIdx + 1; // On a trouvé le header, on retourne l'index suivant
        }
        
        lineIdx++;
    }
    
    return fundParsed ? lineIdx : 0;
}

/* ========= HELPERS & PARSERS POUR LES HOLDINGS ========= */

// Helpers nombres / montants
function parseSharesValue(str) {
    if (!str) return 0;
    const s = str.replace(/,/g, '').trim();
    const match = s.match(/([\d.]+)\s*([MBK])?/i);
    if (!match) return 0;

    let value = parseFloat(match[1]) || 0;
    const suffix = (match[2] || '').toUpperCase();

    // HedgeFollow: M = millions, B = billions, K = milliers
    if (suffix === 'B') value *= 1000;      // milliards → millions
    else if (suffix === 'K') value /= 1000; // milliers → millions
    else if (!suffix && value > 1_000_000) value /= 1_000_000; // brut → millions

    return value;
}

function parseMoneyValue(str) {
    if (!str) return 0;
    const s = str.replace(/\$/g, '').replace(/,/g, '').trim();
    const match = s.match(/([\d.]+)\s*([MBK])?/i);
    if (!match) return 0;

    let value = parseFloat(match[1]) || 0;
    const suffix = (match[2] || '').toUpperCase();

    if (suffix === 'B') value *= 1000;      // milliards → millions
    else if (suffix === 'K') value /= 1000; // milliers → millions

    return value;
}

function parseActivityValue(str) {
    if (!str) return 0;
    const match = str.match(/([+-]?\d+\.?\d*)%/);
    return match ? parseFloat(match[1]) : 0;
}

// "-34.3% (-645.5k)" -> -0.65  (millions)
function parseActivityShares(str) {
    if (!str) return 0;
    const match = str.match(/\(([+-]?[\d.]+)\s*([MBK])?\)/i);
    if (!match) return 0;

    let value = parseFloat(match[1]) || 0;
    const suffix = (match[2] || '').toUpperCase();

    // on convertit TOUT en millions d'actions
    if (suffix === 'B') value *= 1000;      // milliards -> millions
    else if (suffix === 'K') value /= 1000; // milliers -> millions
    // M ou rien = déjà millions

    return value;
}

// ex: "$14.62 (+959.2%)" → 959.2
function parsePriceChange(str) {
    if (!str) return 0;
    const matches = str.match(/\(([+-]?\d+\.?\d*)%\)/g);
    if (!matches || matches.length === 0) return 0;
    const last = matches[matches.length - 1];
    return parseFloat(last.replace(/[()%]/g, '')) || 0;
}

// ===== PARSER FORMAT TABLEAU (copie d'une ligne complète avec \t) =====
// AAPL\tApple Inc\t22.69%\t0.38%\t238.21M\t$ 60.66B\t$ 9.61B\t-14.92% (-41.79M)\t$39.59 (+585.8%)\tTechnology\t2025-09-30

function parseTableFormat(lines, startIdx, fundIndex) {
    let holdingsParsed = 0;
    let currentHoldingIndex = 0;

    for (let i = startIdx; i < lines.length && currentHoldingIndex < NUM_HOLDINGS; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        const cols = line.split('\t');
        // On veut au moins toutes les colonnes du tableau HF
        if (cols.length < 11) continue;

        const firstColLower = cols[0].toLowerCase();
        const secondColLower = (cols[1] || '').toLowerCase();

        // Skip ligne d'en-tête
        if (firstColLower === 'stock' || secondColLower.startsWith('company')) {
            continue;
        }

        const ticker        = cols[0].trim();
        const company       = cols[1].trim();
        const portfolioPct  = parseFloat(cols[2].replace('%', '')) || 0;
        const deltaPct      = parseFloat(cols[3].replace('%', '')) || 0;
        const shares        = parseSharesValue(cols[4]);
        const value         = parseMoneyValue(cols[5]);
        const tradeValue    = parseMoneyValue(cols[6]);
        const activityStr   = cols[7];
        const activity      = parseActivityValue(activityStr);
        const activityShares= parseActivityShares(activityStr);
        const avgPriceLine  = cols[8];
        const avgPrice      = parseMoneyValue(avgPriceLine);
        const priceChange   = parsePriceChange(avgPriceLine);
        const sector        = cols[9] ? cols[9].trim() : '';
        const date          = cols[10] ? cols[10].trim() : '';

        fillHoldingData(fundIndex, currentHoldingIndex, {
            ticker,
            company,
            portfolioPct,
            deltaPct,
            shares,
            value,
            tradeValue,
            activity,
            activityShares,
            avgPrice,
            priceChange,
            sector,
            date
        });

        currentHoldingIndex++;
        holdingsParsed++;
    }

    return holdingsParsed;
}

// ===== PARSER FORMAT VERTICAL =====
// PLTR
// Palantir Technologies Inc
// 2.06%
// -0.39%
// 8.57M
// $ 1.56B
// $ 786.68M
// -36.56% (-4.94M)
// $14.62 (+959.2%)
// Technology\t2025-09-30

function parseVerticalFormat(lines, startIdx, fundIndex) {
    let holdingsParsed = 0;
    let currentHoldingIndex = 0;

    const tickerPattern = /^[A-Z]{1,5}(\.[A-Z])?$/;

    for (let i = startIdx; i < lines.length && currentHoldingIndex < NUM_HOLDINGS;) {
        const line = lines[i].trim();

        // Cherche un ticker
        if (!tickerPattern.test(line)) {
            i++;
            continue;
        }

        // On doit avoir au moins 10 lignes pour un holding complet
        if (i + 9 >= lines.length) break;

        const ticker          = lines[i].trim();
        const company         = lines[i + 1].trim();
        const portfolioPct    = parseFloat(lines[i + 2].replace('%', '')) || 0;
        const deltaPct        = parseFloat(lines[i + 3].replace('%', '')) || 0;
        const shares          = parseSharesValue(lines[i + 4]);
        const value           = parseMoneyValue(lines[i + 5]);
        const tradeValue      = parseMoneyValue(lines[i + 6]);
        const activityStr     = lines[i + 7];
        const activity        = parseActivityValue(activityStr);
        const activityShares  = parseActivityShares(activityStr);
        const avgPriceLine    = lines[i + 8];
        const avgPrice        = parseMoneyValue(avgPriceLine);
        const priceChange     = parsePriceChange(avgPriceLine);
        const sectorDateLine  = lines[i + 9];

        let sector = '';
        let date   = '';

        if (sectorDateLine) {
            const parts = sectorDateLine.split('\t');
            if (parts.length >= 2) {
                sector = parts[0].trim();
                date   = parts[1].trim();
            } else {
                // Chercher une date YYYY-MM-DD à la fin
                const m = sectorDateLine.match(/(.*?)(\d{4}-\d{2}-\d{2})$/);
                if (m) {
                    sector = m[1].trim();
                    date   = m[2];
                } else {
                    sector = sectorDateLine.trim();
                }
            }
        }

        fillHoldingData(fundIndex, currentHoldingIndex, {
            ticker,
            company,
            portfolioPct,
            deltaPct,
            shares,
            value,
            tradeValue,
            activity,
            activityShares,
            avgPrice,
            priceChange,
            sector,
            date
        });

        currentHoldingIndex++;
        holdingsParsed++;

        // On avance d'un bloc complet de 10 lignes
        i += 10;
    }

    return holdingsParsed;
}

// Remplir les données d'un holding (inputs + structure JS)
function fillHoldingData(fundIndex, holdingIndex, data) {
    // Inputs visibles
    document.getElementById(`ticker-${fundIndex}-${holdingIndex}`).value   = data.ticker;
    document.getElementById(`company-${fundIndex}-${holdingIndex}`).value  = data.company;
    document.getElementById(`pct-${fundIndex}-${holdingIndex}`).value      = data.portfolioPct;
    document.getElementById(`delta-${fundIndex}-${holdingIndex}`).value    = data.deltaPct;
    document.getElementById(`shares-${fundIndex}-${holdingIndex}`).value   = data.shares.toFixed(2);
    document.getElementById(`value-${fundIndex}-${holdingIndex}`).value    = data.value.toFixed(2);
    document.getElementById(`activity-${fundIndex}-${holdingIndex}`).value = data.activity;
    document.getElementById(`actshares-${fundIndex}-${holdingIndex}`).value =
        (data.activityShares ?? 0).toFixed ? data.activityShares.toFixed(2) : data.activityShares;
    document.getElementById(`avgprice-${fundIndex}-${holdingIndex}`).value = data.avgPrice;
    document.getElementById(`sector-${fundIndex}-${holdingIndex}`).value   = data.sector;
    
    // Structure JS (JSON)
    updateHoldingData(fundIndex, holdingIndex, 'ticker',                data.ticker);
    updateHoldingData(fundIndex, holdingIndex, 'company_name',          data.company);
    updateHoldingData(fundIndex, holdingIndex, 'portfolio_pct',         data.portfolioPct);
    updateHoldingData(fundIndex, holdingIndex, 'delta_portfolio_pct',   data.deltaPct);
    updateHoldingData(fundIndex, holdingIndex, 'shares_owned_millions', data.shares);
    updateHoldingData(fundIndex, holdingIndex, 'value_millions',        data.value);
    updateHoldingData(fundIndex, holdingIndex, 'trade_value_millions',  data.tradeValue);
    updateHoldingData(fundIndex, holdingIndex, 'latest_activity_pct',   data.activity);
    updateHoldingData(fundIndex, holdingIndex, 'latest_activity_shares',data.activityShares || 0);
    updateHoldingData(fundIndex, holdingIndex, 'avg_buy_price',         data.avgPrice);
    updateHoldingData(fundIndex, holdingIndex, 'price_change_pct',      data.priceChange);
    updateHoldingData(fundIndex, holdingIndex, 'sector',                data.sector);
    updateHoldingData(fundIndex, holdingIndex, 'date',                  data.date);
}

// Smart Parser Principal
function smartParse(fundIndex) {
    const textarea = document.getElementById(`smart-paste-${fundIndex}`);
    const text = textarea.value.trim();
    const statusDiv = document.getElementById(`parse-status-${fundIndex}`);
    
    if (!text) {
        showStatus(statusDiv, 'error', '❌ Aucune donnée à parser');
        return;
    }
    
    // Split en lignes et nettoyer
    const lines = text.split('\n').map(line => line.trim()).filter(line => line.length > 0);
    
    // Reset status
    statusDiv.className = 'parse-status';
    statusDiv.textContent = '⏳ Parsing en cours...';
    
    // 1. Parser le header du fond
    const headerEndIdx = parseFundHeader(lines, fundIndex);
    
    // 2. Déterminer le format (tableau avec tabs ou vertical)
    let holdingsParsed = 0;
    
    // Chercher si on a un format tableau (présence de tabs dans les holdings)
    let hasTableFormat = false;
    for (let i = headerEndIdx; i < Math.min(lines.length, headerEndIdx + 20); i++) {
        if (lines[i].split('\t').length >= 10) {
            hasTableFormat = true;
            break;
        }
    }
    
    // 3. Parser les holdings selon le format détecté
    if (hasTableFormat) {
        holdingsParsed = parseTableFormat(lines, headerEndIdx, fundIndex);
    } else {
        holdingsParsed = parseVerticalFormat(lines, headerEndIdx, fundIndex);
    }
    
    // Update UI
    updateProgress();
    updateTabBadge(fundIndex);
    
    // Show status
    const format = hasTableFormat ? 'TABLEAU' : 'VERTICAL';
    let statusMessage = `✅ Parsing terminé (Format ${format}): `;
    if (fundsData[fundIndex].fund_name) {
        statusMessage += `${fundsData[fundIndex].fund_name} - `;
    }
    statusMessage += `${holdingsParsed} holdings parsés`;
    showStatus(statusDiv, 'success', statusMessage);
    
    // Clear textarea après succès
    textarea.value = '';
}

// Show status message
function showStatus(div, type, message) {
    div.className = `parse-status ${type}`;
    div.textContent = message;
    if (type !== 'error') {
        setTimeout(() => {
            div.className = 'parse-status';
        }, 5000);
    }
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
        
        // Update tab name with fund name if available
        const tab = document.getElementById(`tab-${fundIndex}`);
        if (fundsData[fundIndex].fund_name) {
            tab.innerHTML = fundsData[fundIndex].fund_name.substring(0, 15);
            tab.appendChild(badge);
        }
    } else {
        badge.style.display = 'none';
    }
}

// Create holdings rows HTML (avec colonne Δ% et Sector)
function createHoldingsRows(fundIndex) {
    let html = '';
    for (let j = 0; j < NUM_HOLDINGS; j++) {
        html += `
            <tr>
                <td>${j + 1}</td>
                <td><input type="text" id="ticker-${fundIndex}-${j}" style="width: 60px;"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'ticker', this.value.toUpperCase())"></td>
                <td><input type="text" id="company-${fundIndex}-${j}" style="width: 150px;"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'company_name', this.value)"></td>
                <td><input type="number" step="0.01" id="pct-${fundIndex}-${j}" style="width: 70px;"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'portfolio_pct', parseFloat(this.value) || 0)"></td>
                <td><input type="number" step="0.01" id="delta-${fundIndex}-${j}" style="width: 60px;"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'delta_portfolio_pct', parseFloat(this.value) || 0)"></td>
                <td><input type="number" step="0.01" id="shares-${fundIndex}-${j}" style="width: 80px;"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'shares_owned_millions', parseFloat(this.value) || 0)"></td>
                <td><input type="number" step="0.01" id="value-${fundIndex}-${j}" style="width: 90px;"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'value_millions', parseFloat(this.value) || 0)"></td>

                <!-- Activity en % -->
                <td><input type="number" step="any" id="activity-${fundIndex}-${j}" style="width: 70px;"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'latest_activity_pct', parseFloat(this.value) || 0)"></td>

                <!-- Δ Shares en millions -->
                <td><input type="number" step="0.01" id="actshares-${fundIndex}-${j}" style="width: 80px;"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'latest_activity_shares', parseFloat(this.value) || 0)"></td>

                <!-- Average buy price -->
                <td><input type="number" step="0.01" id="avgprice-${fundIndex}-${j}" style="width: 70px;"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'avg_buy_price', parseFloat(this.value) || 0)"></td>

                <!-- Sector -->
                <td><input type="text" id="sector-${fundIndex}-${j}" style="width: 100px;"
                        onchange="updateHoldingData(${fundIndex}, ${j}, 'sector', this.value)"></td>
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
                    date: h.date || today
                }))
        }));
    
    // Calculate universe stats
    const allTickers = new Set();
    const tickerCounts = {};
    const sectorCounts = {};
    
    cleanedFunds.forEach(fund => {
        fund.top_holdings.forEach(holding => {
            if (holding.ticker) {
                allTickers.add(holding.ticker);
                tickerCounts[holding.ticker] = (tickerCounts[holding.ticker] || 0) + 1;
                
                if (holding.sector) {
                    sectorCounts[holding.sector] = (sectorCounts[holding.sector] || 0) + 1;
                }
            }
        });
    });
    
    // Sort tickers by count
    const sortedTickers = Object.entries(tickerCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 30);
    
    // Sort sectors
    const sortedSectors = Object.entries(sectorCounts)
        .sort((a, b) => b[1] - a[1]);
    
    const jsonData = {
        metadata: {
            last_updated: today,
            source: "HedgeFollow Manual Collection V5.1 Fixed",
            format: "hedgefollow_exact",
            description: "Top hedge funds 13F portfolios with complete holdings data"
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
            sector_distribution: sortedSectors.map(([sector, count]) => ({
                sector,
                count,
                percentage: ((count / (cleanedFunds.length * 30)) * 100).toFixed(1) + '%'
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
    a.download = `hedgefollow_manual_${today}.json`;
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
    if (progressBar) {
        progressBar.style.width = progress + '%';
        progressBar.textContent = `${progress}% (${filledFunds}/10 fonds, ${totalHoldings} holdings)`;
    }
}

// Update stats
function updateStats(funds, tickers) {
    const statsSection = document.getElementById('statsSection');
    if (statsSection) {
        statsSection.style.display = 'grid';
        
        document.getElementById('statFunds').textContent = funds.length;
        
        let totalHoldings = 0;
        let totalPerf = 0;
        let totalAUM = 0;
        
        funds.forEach(fund => {
            totalHoldings += fund.top_holdings.length;
            totalPerf += fund.performance_3y;
            totalAUM += fund.aum_billions;
        });
        
        document.getElementById('statHoldings').textContent = totalHoldings;
        document.getElementById('statTickers').textContent = tickers.size;
        document.getElementById('statAvgPerf').textContent = 
            funds.length > 0 ? (totalPerf / funds.length).toFixed(2) + '%' : '0%';
        
        // Ajouter AUM total si élément existe
        if (document.getElementById('statTotalAUM')) {
            document.getElementById('statTotalAUM').textContent = `$${totalAUM.toFixed(1)}B`;
        }
    }
}

// Save to localStorage
function saveToLocalStorage() {
    localStorage.setItem('hedgeFollowDataV5', JSON.stringify(fundsData));
}

// Load from localStorage
function loadFromLocalStorage() {
    const saved = localStorage.getItem('hedgeFollowDataV5');
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
                document.getElementById(`ticker-${i}-${j}`).value   = holding.ticker;
                document.getElementById(`company-${i}-${j}`).value  = holding.company_name;
                document.getElementById(`pct-${i}-${j}`).value      = holding.portfolio_pct;
                document.getElementById(`delta-${i}-${j}`).value    = holding.delta_portfolio_pct;
                document.getElementById(`shares-${i}-${j}`).value   = holding.shares_owned_millions;
                document.getElementById(`value-${i}-${j}`).value    = holding.value_millions;
                document.getElementById(`activity-${i}-${j}`).value = holding.latest_activity_pct;

                // Δ Shares (M) - compatible ancienne sauvegarde (string type "-4.94M")
                let actShares = holding.latest_activity_shares;
                if (typeof actShares === 'string') {
                    actShares = parseActivityShares(`(${actShares})`);
                }
                if (typeof actShares === 'number' && !isNaN(actShares)) {
                    document.getElementById(`actshares-${i}-${j}`).value = actShares.toFixed(2);
                }

                document.getElementById(`avgprice-${i}-${j}`).value = holding.avg_buy_price;
                document.getElementById(`sector-${i}-${j}`).value   = holding.sector || '';
            }
        });
        updateTabStatus(i);
        updateTabBadge(i);
    });
    
    updateProgress();
    alert('✅ Données chargées depuis la sauvegarde locale!');
} else {
    alert('❌ Aucune sauvegarde trouvée');
}

// Clear all data
function clearAllData() {
    if (confirm('⚠️ Êtes-vous sûr de vouloir effacer TOUTES les données?')) {
        initializeFunds();
        document.querySelectorAll('input').forEach(input => input.value = '');
        document.querySelectorAll('textarea').forEach(textarea => textarea.value = '');
        updateProgress();
        localStorage.removeItem('hedgeFollowDataV5');
        
        // Reset tabs
        document.querySelectorAll('.tab').forEach((tab, i) => {
            tab.classList.remove('completed');
            tab.innerHTML = `Fund ${i + 1}`;
        });
        
        // Reset badges
        for (let i = 0; i < NUM_FUNDS; i++) {
            const badge = document.getElementById(`badge-${i}`);
            if (badge) badge.style.display = 'none';
        }
        
        alert('🗑️ Toutes les données ont été effacées');
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
    let analysis = '📊 ANALYSE HEDGEFOLLOW - TOP HEDGE FUNDS\n';
    analysis += '='.repeat(60) + '\n\n';
    
    // Top funds by performance
    analysis += '🏆 TOP FONDS PAR PERFORMANCE:\n';
    jsonData.top_funds
        .sort((a, b) => b.performance_3y - a.performance_3y)
        .slice(0, 5)
        .forEach((fund, i) => {
            analysis += `${i+1}. ${fund.fund_name} (${fund.portfolio_manager})\n`;
            analysis += `   Performance: ${fund.performance_3y}% | AUM: $${fund.aum_billions}B | Holdings: ${fund.total_holdings}\n\n`;
        });
    
    // Most held tickers
    analysis += '\n🎯 TICKERS LES PLUS DÉTENUS:\n';
    jsonData.smart_universe_summary.most_held_tickers
        .slice(0, 15)
        .forEach((ticker, i) => {
            analysis += `${i+1}. ${ticker.ticker}: ${ticker.count} fonds (${ticker.percentage})\n`;
        });
    
    // Sector distribution
    if (jsonData.smart_universe_summary.sector_distribution.length > 0) {
        analysis += '\n📈 RÉPARTITION SECTORIELLE:\n';
        jsonData.smart_universe_summary.sector_distribution
            .slice(0, 10)
            .forEach((sector, i) => {
                analysis += `${i+1}. ${sector.sector}: ${sector.count} positions (${sector.percentage})\n`;
            });
    }
    
    // Show in preview
    const preview = document.getElementById('jsonPreview');
    preview.style.display = 'block';
    preview.innerHTML = `<pre style="color: #00bcd4; font-size: 13px; font-family: 'Courier New', monospace;">${analysis}</pre>`;
}

// Initialize on load
window.onload = function() {
    initializeFunds();
    createTabs();
    createFundSections();
    
    // Messages console
    console.log('💼 HedgeFollow Manual Collector V5.1 Fixed - Ready!');
    console.log('📋 Format: Exact HedgeFollow (Table ou Vertical)');
    console.log('💾 Auto-save: Enabled (localStorage)');
    console.log('🎯 Parser adaptatif pour Performance 25Q3, 26Q1, etc.');
    console.log('🔧 Colonnes corrigées: Sector, Avg Price, Latest Activity Shares');
};

