// ============================================================
// INSTITUTIONAL TRACKER - SmartMoney Scraper
// Collecte: "Top 100 stocks owned by hedge funds"
// ============================================================

let institutionalStocks = [];

// ============== GITHUB CONFIG ==============

const GITHUB_CONFIG = {
    owner: 'Bencode92',
    repo: 'smartmoney-scraper',
    branch: 'main',
    basePath: 'data/raw/institutional'
};

// ============== HELPERS ==============

/**
 * Parse un entier depuis une string ("1,374" → 1374)
 */
function parseIntSafe(str) {
    if (!str) return 0;
    const s = String(str).replace(/[,\s]/g, '').trim();
    const n = parseInt(s, 10);
    return isNaN(n) ? 0 : n;
}

/**
 * Parse une valeur monétaire avec suffixe ("$ 2.73T" → 2730 billions)
 * Tout est normalisé en MILLIARDS ($B)
 */
function parseValueOwnedBillions(str) {
    if (!str) return 0;
    const s = String(str)
        .replace(/\$/g, '')
        .replace(/,/g, '')
        .trim();

    const m = s.match(/([\d.]+)\s*([TBMK])?/i);
    if (!m) return 0;

    let value = parseFloat(m[1]) || 0;
    const suffix = (m[2] || 'B').toUpperCase();

    if (suffix === 'T') value *= 1000;       // Trillions → Billions
    else if (suffix === 'M') value /= 1000;  // Millions → Billions
    else if (suffix === 'K') value /= 1_000_000;
    // B = déjà en billions

    return value;
}

/**
 * Valide un ticker (1-6 lettres majuscules, optionnel .X)
 */
function isValidTicker(str) {
    return /^[A-Z]{1,6}(\.[A-Z])?$/.test(str);
}

/**
 * Valide les données d'un stock parsé
 */
function validateStock(stock) {
    const errors = [];
    
    if (!stock.ticker || !isValidTicker(stock.ticker)) {
        errors.push(`Ticker invalide: ${stock.ticker}`);
    }
    if (stock.total_holders < 0 || stock.total_holders > 50000) {
        errors.push(`Total holders suspect: ${stock.total_holders}`);
    }
    if (stock.value_owned_billions < 0) {
        errors.push(`Value négative: ${stock.value_owned_billions}`);
    }
    
    return errors;
}

// ============== PARSER PRINCIPAL ==============

function parseInstitutionalText() {
    const textarea = document.getElementById('inst-paste');
    const preview = document.getElementById('json-preview');
    const raw = textarea.value.trim();

    if (!raw) {
        alert('❌ Rien à parser');
        return;
    }

    // Nettoyage des lignes
    const lines = raw
        .split('\n')
        .map(l => l.replace(/\r/g, '').trim())
        .filter(l => l.length > 0);

    // Cherche la ligne d'en-tête "Stock  Company Name ..."
    let startIdx = 0;
    for (let i = 0; i < Math.min(lines.length, 10); i++) {
        const lower = lines[i].toLowerCase();
        if (lower.includes('stock') && lower.includes('company')) {
            startIdx = i + 1;
            break;
        }
    }

    institutionalStocks = [];
    let parseErrors = 0;
    let validationWarnings = [];
    let rank = 1;

    // Format attendu par bloc (vertical) :
    // L0: Ticker (NVDA)
    // L1: Company Name
    // L2: "1374    659    565" (stats)
    // L3: "$ 2.73T" (value)
    // L4: "Technology" (sector)
    // L5: "$86,62" (52W min) → ignoré
    // L6: "$212,19" (52W max) → ignoré

    for (let i = startIdx; i < lines.length; ) {
        const line = lines[i];
        if (!line) { i++; continue; }

        // Détecte un ticker pur
        if (!isValidTicker(line)) {
            i++;
            continue;
        }

        const ticker = line.toUpperCase();

        // Vérif qu'on a assez de lignes pour un bloc minimal
        if (i + 4 >= lines.length) {
            parseErrors++;
            break;
        }

        const companyName = lines[i + 1] || '';
        const statsLine   = lines[i + 2] || '';
        const valueLine   = lines[i + 3] || '';
        const sectorLine  = lines[i + 4] || '';

        // Stats : "1374    659    565"
        const statsParts = statsLine.split(/\s+/).filter(Boolean);
        const totalHolders = parseIntSafe(statsParts[0]);
        const mediumStakes = parseIntSafe(statsParts[1]);
        const largeStakes  = parseIntSafe(statsParts[2]);

        const valueOwnedB = parseValueOwnedBillions(valueLine);
        
        // Nettoyage du secteur (éviter de capturer un prix)
        let sector = sectorLine;
        if (sector.startsWith('$')) {
            sector = ''; // C'est probablement le 52W range
        }

        const stock = {
            rank: rank++,
            ticker,
            company_name: companyName,
            total_holders: totalHolders,
            medium_stakes: mediumStakes,
            large_stakes: largeStakes,
            value_owned_billions: Math.round(valueOwnedB * 100) / 100,
            sector
        };

        // Validation
        const errors = validateStock(stock);
        if (errors.length > 0) {
            validationWarnings.push(`${ticker}: ${errors.join(', ')}`);
        }

        institutionalStocks.push(stock);

        // On saute le bloc :
        // 5 lignes "utiles" + éventuellement 2 lignes de 52W range
        let step = 5;
        if (i + 6 < lines.length &&
            /^\$/.test(lines[i + 5]) &&
            /^\$/.test(lines[i + 6])) {
            step = 7; // skip 52W range
        }
        i += step;
    }

    // Sauvegarde localStorage
    saveToLocalStorage();

    // Génération du JSON
    const jsonData = generateInstitutionalJSON();
    preview.textContent = JSON.stringify(jsonData, null, 2);

    updateInstitutionalStats();
    renderInstitutionalTable();
    updateProgressBar(100);

    document.getElementById('tablePanel').hidden = institutionalStocks.length === 0;

    // Feedback
    let msg = `✅ ${institutionalStocks.length} stocks parsés`;
    if (parseErrors > 0) {
        msg += `\n⚠️ ${parseErrors} blocs ignorés (format incomplet)`;
    }
    if (validationWarnings.length > 0 && validationWarnings.length <= 5) {
        msg += `\n⚠️ Warnings: ${validationWarnings.join('; ')}`;
    } else if (validationWarnings.length > 5) {
        msg += `\n⚠️ ${validationWarnings.length} warnings de validation (voir console)`;
        console.warn('Validation warnings:', validationWarnings);
    }
    
    console.log(msg);
    if (parseErrors > 0 || validationWarnings.length > 0) {
        alert(msg);
    }
}

// ============== JSON GENERATION ==============

function generateInstitutionalJSON() {
    const today = new Date().toISOString().split('T')[0];

    const sectorsCount = {};
    let totalValueB = 0;
    let totalHolders = 0;
    let totalLargeStakes = 0;

    institutionalStocks.forEach(row => {
        totalValueB += row.value_owned_billions || 0;
        totalHolders += row.total_holders || 0;
        totalLargeStakes += row.large_stakes || 0;
        if (row.sector) {
            sectorsCount[row.sector] = (sectorsCount[row.sector] || 0) + 1;
        }
    });

    const sectorDistribution = Object.entries(sectorsCount)
        .sort((a, b) => b[1] - a[1])
        .map(([sector, count]) => ({
            sector,
            count,
            percentage: institutionalStocks.length
                ? ((count / institutionalStocks.length) * 100).toFixed(1) + '%'
                : '0.0%'
        }));

    // Top 10 par value owned
    const topByValue = [...institutionalStocks]
        .sort((a, b) => b.value_owned_billions - a.value_owned_billions)
        .slice(0, 10)
        .map(s => ({ ticker: s.ticker, value_billions: s.value_owned_billions }));

    // Top 10 par nombre de holders
    const topByHolders = [...institutionalStocks]
        .sort((a, b) => b.total_holders - a.total_holders)
        .slice(0, 10)
        .map(s => ({ ticker: s.ticker, holders: s.total_holders }));

    return {
        metadata: {
            last_updated: today,
            source: "Institutional Tracker - SmartMoney Scraper",
            description: "Top stocks owned by hedge funds / institutional investors",
            total_rows: institutionalStocks.length
        },
        summary: {
            total_stocks: institutionalStocks.length,
            total_value_owned_billions: Math.round(totalValueB * 10) / 10,
            total_large_stakes: totalLargeStakes,
            average_holders_per_stock: institutionalStocks.length
                ? Math.round(totalHolders / institutionalStocks.length)
                : 0,
            top_sector: sectorDistribution[0]?.sector || null
        },
        highlights: {
            top_by_value: topByValue,
            top_by_holders: topByHolders
        },
        sector_distribution: sectorDistribution,
        top_stocks: institutionalStocks
    };
}

// ============== STATS / TABLE ==============

function updateInstitutionalStats() {
    const tickers = institutionalStocks.length;
    const totalValueB = institutionalStocks.reduce(
        (sum, s) => sum + (s.value_owned_billions || 0), 0
    );
    const totalHolders = institutionalStocks.reduce(
        (sum, s) => sum + (s.total_holders || 0), 0
    );
    const totalLargeStakes = institutionalStocks.reduce(
        (sum, s) => sum + (s.large_stakes || 0), 0
    );
    const avgHolders = tickers ? totalHolders / tickers : 0;

    const sectorsCount = {};
    institutionalStocks.forEach(s => {
        if (!s.sector) return;
        sectorsCount[s.sector] = (sectorsCount[s.sector] || 0) + 1;
    });
    const topSector = Object.entries(sectorsCount)
        .sort((a, b) => b[1] - a[1])[0]?.[0] || '—';

    document.getElementById('statTickers').textContent = tickers;
    document.getElementById('statTotalValue').textContent = totalValueB >= 1000 
        ? `$${(totalValueB / 1000).toFixed(1)}T` 
        : `$${totalValueB.toFixed(1)}B`;
    document.getElementById('statAvgHolders').textContent = avgHolders.toFixed(0);
    document.getElementById('statTopSector').textContent = topSector;
    document.getElementById('statLargeStakes').textContent = totalLargeStakes.toLocaleString();
}

function renderInstitutionalTable() {
    const tbody = document.getElementById('stocksBody');
    if (!tbody) return;

    tbody.innerHTML = institutionalStocks.map(row => {
        const valueDisplay = row.value_owned_billions >= 1000
            ? `$${(row.value_owned_billions / 1000).toFixed(2)}T`
            : `$${row.value_owned_billions.toFixed(1)}B`;
        
        return `
            <tr>
                <td>${row.rank}</td>
                <td><a class="ticker-link" href="https://finance.yahoo.com/quote/${row.ticker}" target="_blank">${row.ticker}</a></td>
                <td>${row.company_name}</td>
                <td>${row.total_holders.toLocaleString()}</td>
                <td>${row.medium_stakes.toLocaleString()}</td>
                <td>${row.large_stakes.toLocaleString()}</td>
                <td>${valueDisplay}</td>
                <td>${row.sector || '—'}</td>
            </tr>
        `;
    }).join('');
}

function updateProgressBar(percent) {
    const bar = document.getElementById('progressBar');
    if (bar) bar.style.width = `${percent}%`;
}

// ============== LOCALSTORAGE ==============

function saveToLocalStorage() {
    localStorage.setItem('institutionalStocksData', JSON.stringify(institutionalStocks));
}

function loadFromLocalStorage() {
    const saved = localStorage.getItem('institutionalStocksData');
    if (saved) {
        institutionalStocks = JSON.parse(saved);
        updateInstitutionalStats();
        renderInstitutionalTable();
        document.getElementById('tablePanel').hidden = institutionalStocks.length === 0;
        
        const jsonData = generateInstitutionalJSON();
        document.getElementById('json-preview').textContent = JSON.stringify(jsonData, null, 2);
        updateProgressBar(100);
        
        alert(`✅ ${institutionalStocks.length} stocks chargés depuis la sauvegarde`);
    } else {
        alert('❌ Aucune sauvegarde trouvée');
    }
}

// ============== DOWNLOAD ==============

function downloadInstitutionalJSON() {
    const data = generateInstitutionalJSON();
    if (!data.top_stocks || data.top_stocks.length === 0) {
        alert('⚠️ Aucun stock à sauvegarder');
        return;
    }

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const today = new Date().toISOString().split('T')[0];
    a.href = url;
    a.download = `top_institutional_stocks_${today}.json`;
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

    const jsonData = generateInstitutionalJSON();
    if (!jsonData.top_stocks || jsonData.top_stocks.length === 0) {
        alert('⚠️ Aucun stock à sauvegarder');
        return;
    }

    const today = new Date().toISOString().split('T')[0];
    const filename = `top_institutional_${today}.json`;
    const filePath = `${GITHUB_CONFIG.basePath}/${filename}`;

    const content = btoa(unescape(encodeURIComponent(JSON.stringify(jsonData, null, 2))));

    const statusDiv = document.getElementById('github-status');
    statusDiv.textContent = '⏳ Push en cours vers GitHub...';
    statusDiv.className = 'github-status pending';

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
            message: `🏦 Update institutional stocks ${today} - ${jsonData.top_stocks.length} stocks`,
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

        if (err.message && err.message.includes('Bad credentials')) {
            localStorage.removeItem('github_token');
            alert('❌ Token invalide. Réessaie.');
        } else {
            alert(`❌ Erreur push GitHub: ${err.message}`);
        }
    }
}

// ============== CLEAR ==============

function clearInstitutionalAll() {
    if (!confirm('⚠️ Effacer toutes les données ?')) return;
    
    document.getElementById('inst-paste').value = '';
    document.getElementById('json-preview').textContent = '// Le JSON apparaîtra ici après parsing...';
    document.getElementById('github-status').className = 'github-status';
    document.getElementById('tablePanel').hidden = true;
    institutionalStocks = [];
    updateInstitutionalStats();
    updateProgressBar(0);
    localStorage.removeItem('institutionalStocksData');
}

// ============== INIT ==============

console.log('🏦 Institutional Tracker - SmartMoney Scraper');
console.log('📋 Colle le tableau "Top 100 stocks owned by hedge funds" et clique Parser');
