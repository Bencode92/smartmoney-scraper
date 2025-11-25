/**
 * Dataroma Grand Portfolio Collector
 * Version: 1.0.0 (Secure)
 * 
 * Améliorations vs version standard:
 * - Token GitHub en mémoire uniquement (pas localStorage)
 * - Validation des données avant push
 * - Parsing robuste avec gestion d'erreurs
 * - Feedback utilisateur détaillé
 */

// ============ CONFIGURATION ============
const GITHUB_CONFIG = {
    owner: 'Bencode92',
    repo: 'smartmoney-scraper',
    branch: 'main',
    basePath: 'data/raw/dataroma/grand-portfolio'
};

// Token en mémoire uniquement (sécurité)
let sessionToken = null;

// Données parsées
let parsedStocks = [];

// ============ GITHUB TOKEN (SECURE) ============
function getGitHubToken() {
    if (!sessionToken) {
        sessionToken = prompt(
            '🔑 GitHub Personal Access Token\n\n' +
            'Le token ne sera PAS sauvegardé (session uniquement).\n' +
            'Permissions requises: repo (full control)'
        );
    }
    return sessionToken;
}

function clearToken() {
    sessionToken = null;
    showStatus('githubStatus', 'info', '🔑 Token effacé de la mémoire');
}

// ============ PARSING ============
function parseData() {
    const input = document.getElementById('rawInput').value.trim();
    
    if (!input) {
        showStatus('parseStatus', 'error', '❌ Aucune donnée à parser');
        return;
    }
    
    const lines = input.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    parsedStocks = [];
    const errors = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        
        // Skip header
        if (line.toLowerCase().startsWith('symbol') || line.toLowerCase().includes('stock\t')) {
            continue;
        }
        
        const result = parseLine(line, i + 1);
        
        if (result.success) {
            parsedStocks.push(result.data);
        } else {
            errors.push(result.error);
        }
    }
    
    if (parsedStocks.length === 0) {
        showStatus('parseStatus', 'error', `❌ Aucun stock parsé. Erreurs: ${errors.slice(0, 3).join(', ')}`);
        return;
    }
    
    // Validation
    const validation = validateData(parsedStocks);
    displayValidation(validation);
    
    // Stats
    updateStats();
    
    // Preview
    displayPreview();
    
    // Show actions
    document.getElementById('statsGrid').style.display = 'grid';
    document.getElementById('validationCard').style.display = 'block';
    document.getElementById('previewCard').style.display = 'block';
    document.getElementById('actionsCard').style.display = 'block';
    
    const warningCount = errors.length;
    if (warningCount > 0) {
        showStatus('parseStatus', 'warning', 
            `⚠️ ${parsedStocks.length} stocks parsés, ${warningCount} lignes ignorées`);
    } else {
        showStatus('parseStatus', 'success', 
            `✅ ${parsedStocks.length} stocks parsés avec succès`);
    }
}

function parseLine(line, lineNum) {
    // Format attendu: Symbol \t Stock \t % \t Buys \t Hold Price \t Current Price \t 52W Low \t % Above \t 52W High
    const cols = line.split('\t');
    
    if (cols.length < 9) {
        return { success: false, error: `Ligne ${lineNum}: colonnes insuffisantes (${cols.length}/9)` };
    }
    
    try {
        const symbol = cols[0].trim().toUpperCase();
        
        // Validation symbol (1-5 lettres, peut avoir un point comme BRK.B)
        if (!/^[A-Z]{1,5}(\.[A-Z])?$/.test(symbol)) {
            return { success: false, error: `Ligne ${lineNum}: symbol invalide "${symbol}"` };
        }
        
        const stock = {
            symbol: symbol,
            company_name: cols[1].trim(),
            portfolio_weight: parseFloat(cols[2]) || 0,
            buys_6m: parseInt(cols[3]) || 0,
            hold_price: parseMoney(cols[4]),
            current_price: parseMoney(cols[5]),
            low_52w: parseMoney(cols[6]),
            pct_above_52w_low: parseFloat(cols[7]) || 0,
            high_52w: parseMoney(cols[8]),
            buys_tier: calculateTier(parseInt(cols[3]) || 0)
        };
        
        return { success: true, data: stock };
        
    } catch (e) {
        return { success: false, error: `Ligne ${lineNum}: ${e.message}` };
    }
}

function parseMoney(str) {
    if (!str) return 0;
    // Remove $, spaces, commas
    const clean = str.replace(/[$,\s]/g, '').trim();
    const value = parseFloat(clean);
    return isNaN(value) ? 0 : value;
}

function calculateTier(buys) {
    if (buys >= 8) return 'A';
    if (buys >= 6) return 'B';
    if (buys >= 3) return 'C';
    return 'D';
}

// ============ VALIDATION ============
function validateData(stocks) {
    const checks = [];
    
    // Check 1: Minimum stocks
    checks.push({
        name: 'Minimum 5 stocks',
        pass: stocks.length >= 5,
        detail: `${stocks.length} stocks`
    });
    
    // Check 2: All have valid symbols
    const validSymbols = stocks.filter(s => s.symbol && s.symbol.length >= 1).length;
    checks.push({
        name: 'Symbols valides',
        pass: validSymbols === stocks.length,
        detail: `${validSymbols}/${stocks.length}`
    });
    
    // Check 3: All have company names
    const validNames = stocks.filter(s => s.company_name && s.company_name.length > 2).length;
    checks.push({
        name: 'Noms compagnies',
        pass: validNames === stocks.length,
        detail: `${validNames}/${stocks.length}`
    });
    
    // Check 4: Portfolio weights sum reasonable (should be < 2 for % format)
    const totalWeight = stocks.reduce((sum, s) => sum + s.portfolio_weight, 0);
    checks.push({
        name: 'Poids portfolio cohérents',
        pass: totalWeight > 0.1 && totalWeight < 5,
        detail: `Total: ${totalWeight.toFixed(3)}`
    });
    
    // Check 5: All have buys >= 1
    const validBuys = stocks.filter(s => s.buys_6m >= 1).length;
    checks.push({
        name: 'Buys valides (≥1)',
        pass: validBuys === stocks.length,
        detail: `${validBuys}/${stocks.length}`
    });
    
    // Check 6: Prices are positive
    const validPrices = stocks.filter(s => s.current_price > 0).length;
    checks.push({
        name: 'Prix actuels > 0',
        pass: validPrices === stocks.length,
        detail: `${validPrices}/${stocks.length}`
    });
    
    return {
        checks,
        allPass: checks.every(c => c.pass),
        passCount: checks.filter(c => c.pass).length,
        totalChecks: checks.length
    };
}

function displayValidation(validation) {
    const list = document.getElementById('validationList');
    list.innerHTML = validation.checks.map(c => `
        <li class="${c.pass ? 'pass' : 'fail'}">
            ${c.pass ? '✅' : '❌'} ${c.name} <span style="color: var(--text-muted);">(${c.detail})</span>
        </li>
    `).join('');
}

// ============ DISPLAY ============
function updateStats() {
    const tierA = parsedStocks.filter(s => s.buys_tier === 'A').length;
    const tierB = parsedStocks.filter(s => s.buys_tier === 'B').length;
    const avgBuys = parsedStocks.reduce((sum, s) => sum + s.buys_6m, 0) / parsedStocks.length;
    
    document.getElementById('statStocks').textContent = parsedStocks.length;
    document.getElementById('statTierA').textContent = tierA;
    document.getElementById('statTierB').textContent = tierB;
    document.getElementById('statAvgBuys').textContent = avgBuys.toFixed(1);
}

function displayPreview() {
    const tbody = document.getElementById('previewBody');
    tbody.innerHTML = parsedStocks.map(s => `
        <tr>
            <td><strong>${s.symbol}</strong></td>
            <td>${s.company_name}</td>
            <td>${(s.portfolio_weight * 100).toFixed(2)}%</td>
            <td>${s.buys_6m}</td>
            <td class="tier-${s.buys_tier.toLowerCase()}">${s.buys_tier}</td>
            <td>$${s.hold_price.toFixed(2)}</td>
            <td>$${s.current_price.toFixed(2)}</td>
            <td>$${s.low_52w.toFixed(2)}</td>
            <td class="${s.pct_above_52w_low > 20 ? 'positive' : ''}">${s.pct_above_52w_low.toFixed(2)}%</td>
            <td>$${s.high_52w.toFixed(2)}</td>
        </tr>
    `).join('');
}

// ============ JSON GENERATION ============
function generateJSON() {
    const today = new Date().toISOString().split('T')[0];
    
    return {
        metadata: {
            source: 'Dataroma',
            dataset: 'Grand Portfolio - Superinvestor Consensus',
            url: 'https://www.dataroma.com/m/g/portfolio.php',
            as_of: today,
            description: 'Top holdings across superinvestors with recent buys',
            collector_version: '1.0.0'
        },
        summary: {
            total_stocks: parsedStocks.length,
            tier_a_count: parsedStocks.filter(s => s.buys_tier === 'A').length,
            tier_b_count: parsedStocks.filter(s => s.buys_tier === 'B').length,
            min_buys: Math.min(...parsedStocks.map(s => s.buys_6m)),
            max_buys: Math.max(...parsedStocks.map(s => s.buys_6m)),
            avg_buys: (parsedStocks.reduce((sum, s) => sum + s.buys_6m, 0) / parsedStocks.length).toFixed(2)
        },
        stocks: parsedStocks
    };
}

function toggleJSONPreview() {
    const preview = document.getElementById('jsonPreview');
    if (preview.style.display === 'none' || !preview.style.display) {
        preview.style.display = 'block';
        preview.textContent = JSON.stringify(generateJSON(), null, 2);
    } else {
        preview.style.display = 'none';
    }
}

// ============ DOWNLOAD ============
function downloadJSON() {
    if (parsedStocks.length === 0) {
        showStatus('githubStatus', 'error', '❌ Aucune donnée à télécharger');
        return;
    }
    
    const jsonData = generateJSON();
    const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const today = new Date().toISOString().split('T')[0];
    a.href = url;
    a.download = `GP_consensus_${today}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    showStatus('githubStatus', 'success', '📥 Fichier téléchargé');
}

// ============ GITHUB PUSH ============
async function pushToGitHub() {
    // Validation
    if (parsedStocks.length === 0) {
        showStatus('githubStatus', 'error', '❌ Aucune donnée à pusher');
        return;
    }
    
    const validation = validateData(parsedStocks);
    if (!validation.allPass) {
        const proceed = confirm(
            `⚠️ Validation incomplète (${validation.passCount}/${validation.totalChecks} checks).\n\n` +
            'Voulez-vous quand même pusher?'
        );
        if (!proceed) return;
    }
    
    // Token
    const token = getGitHubToken();
    if (!token) {
        showStatus('githubStatus', 'error', '❌ Token requis');
        return;
    }
    
    const jsonData = generateJSON();
    const today = new Date().toISOString().split('T')[0];
    const filename = `GP_consensus_${today}.json`;
    const filePath = `${GITHUB_CONFIG.basePath}/${filename}`;
    
    // Encode base64
    const jsonString = JSON.stringify(jsonData, null, 2);
    const content = btoa(unescape(encodeURIComponent(jsonString)));
    
    showStatus('githubStatus', 'info', '⏳ Push en cours...');
    
    try {
        // Check if file exists
        let sha = null;
        const checkUrl = `https://api.github.com/repos/${GITHUB_CONFIG.owner}/${GITHUB_CONFIG.repo}/contents/${filePath}?ref=${GITHUB_CONFIG.branch}`;
        
        const checkResp = await fetch(checkUrl, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        });
        
        if (checkResp.ok) {
            const existing = await checkResp.json();
            sha = existing.sha;
        }
        
        // Push
        const putUrl = `https://api.github.com/repos/${GITHUB_CONFIG.owner}/${GITHUB_CONFIG.repo}/contents/${filePath}`;
        
        const body = {
            message: `📊 Update Dataroma Grand Portfolio ${today} - ${parsedStocks.length} stocks`,
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
            throw new Error(result.message || 'GitHub API error');
        }
        
        showStatus('githubStatus', 'success', 
            `✅ Push réussi! <a href="${result.content.html_url}" target="_blank" style="color: var(--accent);">Voir sur GitHub</a>`);
        
    } catch (err) {
        console.error('GitHub push error:', err);
        
        if (err.message && err.message.includes('Bad credentials')) {
            sessionToken = null;
            showStatus('githubStatus', 'error', '❌ Token invalide. Cliquez sur "Reset Token" et réessayez.');
        } else {
            showStatus('githubStatus', 'error', `❌ Erreur: ${err.message}`);
        }
    }
}

// ============ UI HELPERS ============
function showStatus(elementId, type, message) {
    const el = document.getElementById(elementId);
    el.className = `status ${type}`;
    el.innerHTML = message;
}

function clearInput() {
    document.getElementById('rawInput').value = '';
    document.getElementById('parseStatus').className = 'status';
    document.getElementById('statsGrid').style.display = 'none';
    document.getElementById('validationCard').style.display = 'none';
    document.getElementById('previewCard').style.display = 'none';
    document.getElementById('actionsCard').style.display = 'none';
    parsedStocks = [];
}

function loadExample() {
    document.getElementById('rawInput').value = `Symbol\tStock\t%\tBuys\tHold Price*\tCurrent Price\t52W Low\t% Above 52W Low\t52W High
FISV\tFiserv Inc.\t0.110\t9\t$128.93\t$60.67\t$59.56\t1.86\t$238.59
UNH\tUnited Health Group Inc.\t0.077\t9\t$342.30\t$319.05\t$233.13\t36.85\t$609.61
V\tVisa Inc.\t0.133\t8\t$341.38\t$329.30\t$297.39\t10.73\t$374.11
AMZN\tAmazon.com Inc.\t0.132\t8\t$219.57\t$226.28\t$161.38\t40.22\t$258.60
META\tMeta Platforms Inc.\t0.076\t8\t$734.48\t$613.05\t$479.11\t27.96\t$795.71
NVDA\tNVIDIA Corp.\t0.066\t8\t$186.58\t$182.55\t$86.61\t110.77\t$212.19
MSFT\tMicrosoft Corp.\t0.134\t7\t$517.95\t$474.00\t$342.95\t38.21\t$553.50
BRK.B\tBerkshire Hathaway CL B\t0.096\t6\t$502.62\t$507.81\t$440.10\t15.39\t$542.07
DIS\tWalt Disney Co.\t0.022\t6\t$114.95\t$101.94\t$79.76\t27.81\t$124.69
TSM\tTaiwan Semiconductor S.A.\t0.011\t6\t$267.59\t$284.64\t$133.34\t113.47\t$311.00`;
}

// ============ INIT ============
console.log('📊 Dataroma Grand Portfolio Collector v1.0.0');
console.log('🔒 Security: Token in memory only (not persisted)');
console.log('✅ Validation: Data checks before push');
