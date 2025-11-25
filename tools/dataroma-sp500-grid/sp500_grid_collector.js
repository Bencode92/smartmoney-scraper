/**
 * Dataroma S&P500 Grid Collector
 * Version: 1.0.0
 * 
 * Dual-metric collector:
 * - % of total portfolio (ownership)
 * - Last 6 months buys
 * 
 * Features:
 * - Sequential import with state preservation
 * - Composite score calculation
 * - Rank normalization
 * - Secure token handling
 */

// ============ CONFIGURATION ============
const GITHUB_CONFIG = {
    owner: 'Bencode92',
    repo: 'smartmoney-scraper',
    branch: 'main',
    basePath: 'data/raw/dataroma/sp500-grid'
};

// Token en mémoire uniquement
let sessionToken = null;

// Data stores
let ownershipData = [];  // { ticker, rank, score }
let buysData = [];       // { ticker, rank, score }
let compositeData = [];  // { ticker, ownership_rank, buys_rank, composite_score, bonus }

// ============ GITHUB TOKEN ============
function getGitHubToken() {
    if (!sessionToken) {
        sessionToken = prompt(
            '🔑 GitHub Personal Access Token\n\n' +
            'Le token ne sera PAS sauvegardé (session uniquement).'
        );
    }
    return sessionToken;
}

function clearToken() {
    sessionToken = null;
    showStatus('githubStatus', 'info', '🔑 Token effacé');
}

// ============ PARSING ============
function parseTickers(text) {
    if (!text || !text.trim()) return [];
    
    // Split by whitespace (spaces, tabs, newlines)
    const tickers = text
        .toUpperCase()
        .split(/\s+/)
        .map(t => t.trim())
        .filter(t => t.length >= 1 && t.length <= 5)
        .filter(t => /^[A-Z.]+$/.test(t));  // Only letters and dots (BRK.B)
    
    // Remove duplicates while preserving order
    return [...new Set(tickers)];
}

function calculateScore(rank, total) {
    // Normalized score: 100 for rank 1, decreasing
    // Using inverse log scale for better distribution
    return Math.round((1 - Math.log(rank) / Math.log(total + 1)) * 100);
}

function parseOwnership() {
    const text = document.getElementById('inputOwnership').value;
    const tickers = parseTickers(text);
    
    if (tickers.length === 0) {
        showStatus('statusOwnership', 'error', '❌ Aucun ticker valide trouvé');
        return;
    }
    
    ownershipData = tickers.map((ticker, idx) => ({
        ticker,
        rank: idx + 1,
        score: calculateScore(idx + 1, tickers.length)
    }));
    
    showStatus('statusOwnership', 'success', `✅ ${ownershipData.length} tickers parsés`);
    updateState();
    calculateComposite();
}

function parseBuys() {
    const text = document.getElementById('inputBuys').value;
    const tickers = parseTickers(text);
    
    if (tickers.length === 0) {
        showStatus('statusBuys', 'error', '❌ Aucun ticker valide trouvé');
        return;
    }
    
    buysData = tickers.map((ticker, idx) => ({
        ticker,
        rank: idx + 1,
        score: calculateScore(idx + 1, tickers.length)
    }));
    
    showStatus('statusBuys', 'success', `✅ ${buysData.length} tickers parsés`);
    updateState();
    calculateComposite();
}

// ============ COMPOSITE CALCULATION ============
function calculateComposite() {
    if (ownershipData.length === 0 && buysData.length === 0) {
        compositeData = [];
        updateUI();
        return;
    }
    
    // Create lookup maps
    const ownershipMap = new Map(ownershipData.map(d => [d.ticker, d]));
    const buysMap = new Map(buysData.map(d => [d.ticker, d]));
    
    // Find tickers in both lists
    const allTickers = new Set([...ownershipMap.keys(), ...buysMap.keys()]);
    
    compositeData = [];
    
    allTickers.forEach(ticker => {
        const inOwnership = ownershipMap.has(ticker);
        const inBuys = buysMap.has(ticker);
        
        const ownershipRank = inOwnership ? ownershipMap.get(ticker).rank : null;
        const buysRank = inBuys ? buysMap.get(ticker).rank : null;
        const ownershipScore = inOwnership ? ownershipMap.get(ticker).score : 0;
        const buysScore = inBuys ? buysMap.get(ticker).score : 0;
        
        let compositeScore = 0;
        let bonus = false;
        
        if (inOwnership && inBuys) {
            // Average of both scores
            compositeScore = (ownershipScore + buysScore) / 2;
            
            // Bonus: top 50 in both = +20%
            if (ownershipRank <= 50 && buysRank <= 50) {
                compositeScore *= 1.2;
                bonus = true;
            }
        } else if (inOwnership) {
            compositeScore = ownershipScore * 0.5;  // Penalty for single list
        } else {
            compositeScore = buysScore * 0.5;
        }
        
        compositeData.push({
            ticker,
            ownership_rank: ownershipRank,
            buys_rank: buysRank,
            ownership_score: ownershipScore,
            buys_score: buysScore,
            composite_score: Math.round(compositeScore),
            in_both: inOwnership && inBuys,
            bonus
        });
    });
    
    // Sort by composite score descending
    compositeData.sort((a, b) => b.composite_score - a.composite_score);
    
    updateUI();
}

// ============ UI UPDATES ============
function updateState() {
    // Ownership indicator
    const dotOwnership = document.getElementById('dotOwnership');
    const countOwnership = document.getElementById('countOwnership');
    dotOwnership.classList.toggle('loaded', ownershipData.length > 0);
    countOwnership.textContent = ownershipData.length;
    
    // Buys indicator
    const dotBuys = document.getElementById('dotBuys');
    const countBuys = document.getElementById('countBuys');
    dotBuys.classList.toggle('loaded', buysData.length > 0);
    countBuys.textContent = buysData.length;
    
    // Composite indicator
    const dotComposite = document.getElementById('dotComposite');
    const countComposite = document.getElementById('countComposite');
    const inBoth = compositeData.filter(d => d.in_both).length;
    dotComposite.classList.toggle('loaded', inBoth > 0);
    countComposite.textContent = inBoth;
}

function updateUI() {
    const hasData = ownershipData.length > 0 || buysData.length > 0;
    
    document.getElementById('statsGrid').style.display = hasData ? 'grid' : 'none';
    document.getElementById('actionsCard').style.display = hasData ? 'block' : 'none';
    
    if (!hasData) {
        document.getElementById('compositeCard').style.display = 'none';
        return;
    }
    
    // Stats
    const inBoth = compositeData.filter(d => d.in_both);
    const top50Both = inBoth.filter(d => d.ownership_rank <= 50 && d.buys_rank <= 50);
    const ownershipOnly = compositeData.filter(d => d.ownership_rank && !d.buys_rank).length;
    const buysOnly = compositeData.filter(d => !d.ownership_rank && d.buys_rank).length;
    
    document.getElementById('statTotal').textContent = compositeData.length;
    document.getElementById('statBoth').textContent = inBoth.length;
    document.getElementById('statTop50Both').textContent = top50Both.length;
    document.getElementById('statOwnershipOnly').textContent = ownershipOnly;
    document.getElementById('statBuysOnly').textContent = buysOnly;
    
    // Composite table (only show tickers in both lists)
    if (inBoth.length > 0) {
        document.getElementById('compositeCard').style.display = 'block';
        
        const tbody = document.getElementById('compositeBody');
        tbody.innerHTML = inBoth
            .sort((a, b) => b.composite_score - a.composite_score)
            .slice(0, 50)  // Top 50
            .map((d, idx) => `
                <tr class="${d.bonus ? 'composite-high' : ''}">
                    <td>${idx + 1}</td>
                    <td class="ticker">${d.ticker}</td>
                    <td class="${d.ownership_rank <= 20 ? 'rank-top' : d.ownership_rank <= 50 ? 'rank-mid' : ''}">
                        #${d.ownership_rank}
                    </td>
                    <td class="${d.buys_rank <= 20 ? 'rank-top' : d.buys_rank <= 50 ? 'rank-mid' : ''}">
                        #${d.buys_rank}
                    </td>
                    <td><strong>${d.composite_score}</strong></td>
                    <td>${d.bonus ? '⭐ +20%' : ''}</td>
                </tr>
            `).join('');
    } else {
        document.getElementById('compositeCard').style.display = 'none';
    }
}

// ============ JSON GENERATION ============
function generateJSON() {
    const today = new Date().toISOString().split('T')[0];
    
    return {
        metadata: {
            source: 'Dataroma',
            dataset: 'S&P500 Grid - Superinvestor Rankings',
            url: 'https://www.dataroma.com/m/g/portfolio_b.php',
            as_of: today,
            description: 'S&P500 stocks ranked by superinvestor ownership and recent buying activity',
            collector_version: '1.0.0'
        },
        summary: {
            total_unique_tickers: compositeData.length,
            ownership_count: ownershipData.length,
            buys_6m_count: buysData.length,
            in_both_lists: compositeData.filter(d => d.in_both).length,
            top_50_both: compositeData.filter(d => d.in_both && d.ownership_rank <= 50 && d.buys_rank <= 50).length
        },
        sp500_ownership: ownershipData,
        sp500_6m_buys: buysData,
        composite_rankings: compositeData.filter(d => d.in_both).map((d, idx) => ({
            composite_rank: idx + 1,
            ticker: d.ticker,
            ownership_rank: d.ownership_rank,
            buys_rank: d.buys_rank,
            composite_score: d.composite_score,
            top_50_bonus: d.bonus
        }))
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
    if (compositeData.length === 0) {
        showStatus('githubStatus', 'error', '❌ Aucune donnée à télécharger');
        return;
    }
    
    const jsonData = generateJSON();
    const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const today = new Date().toISOString().split('T')[0];
    a.href = url;
    a.download = `SP500_grid_${today}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    showStatus('githubStatus', 'success', '📥 Fichier téléchargé');
}

// ============ GITHUB PUSH ============
async function pushToGitHub() {
    if (compositeData.length === 0) {
        showStatus('githubStatus', 'error', '❌ Aucune donnée à pusher');
        return;
    }
    
    // Validation
    if (ownershipData.length === 0 || buysData.length === 0) {
        const proceed = confirm(
            '⚠️ Une seule métrique est chargée.\n\n' +
            'Recommandé: charger Ownership ET 6M Buys pour le score composite.\n\n' +
            'Continuer quand même?'
        );
        if (!proceed) return;
    }
    
    const token = getGitHubToken();
    if (!token) {
        showStatus('githubStatus', 'error', '❌ Token requis');
        return;
    }
    
    const jsonData = generateJSON();
    const today = new Date().toISOString().split('T')[0];
    const filename = `SP500_grid_${today}.json`;
    const filePath = `${GITHUB_CONFIG.basePath}/${filename}`;
    
    const jsonString = JSON.stringify(jsonData, null, 2);
    const content = btoa(unescape(encodeURIComponent(jsonString)));
    
    showStatus('githubStatus', 'info', '⏳ Push en cours...');
    
    try {
        // Check existing
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
            message: `📊 Update S&P500 Grid ${today} - ${compositeData.length} tickers`,
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
            showStatus('githubStatus', 'error', '❌ Token invalide.');
        } else {
            showStatus('githubStatus', 'error', `❌ Erreur: ${err.message}`);
        }
    }
}

// ============ HELPERS ============
function showStatus(elementId, type, message) {
    const el = document.getElementById(elementId);
    el.className = `status ${type}`;
    el.innerHTML = message;
}

function clearInput(type) {
    if (type === 'ownership') {
        document.getElementById('inputOwnership').value = '';
        document.getElementById('statusOwnership').className = 'status';
    } else {
        document.getElementById('inputBuys').value = '';
        document.getElementById('statusBuys').className = 'status';
    }
}

function resetAll() {
    if (!confirm('🗑️ Effacer toutes les données?')) return;
    
    ownershipData = [];
    buysData = [];
    compositeData = [];
    
    document.getElementById('inputOwnership').value = '';
    document.getElementById('inputBuys').value = '';
    document.getElementById('statusOwnership').className = 'status';
    document.getElementById('statusBuys').className = 'status';
    document.getElementById('githubStatus').className = 'status';
    
    updateState();
    updateUI();
}

// ============ INIT ============
console.log('📊 S&P500 Grid Collector v1.0.0');
console.log('📈 Metrics: Ownership + 6M Buys');
console.log('🎯 Composite score with bonus for top 50 in both');
