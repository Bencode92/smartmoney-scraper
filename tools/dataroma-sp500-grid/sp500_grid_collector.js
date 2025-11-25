/**
 * Dataroma S&P500 Grid Collector
 * Version: 1.1.0
 * 
 * Features:
 * - Dual-metric: Ownership + 6M Buys
 * - Zero-value support (white cells)
 * - Composite scoring with bonus
 * - Validation & anti-duplicate checks
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
let ownershipData = [];      // { ticker, rank, score } - tickers > 0
let buysData = [];           // { ticker, rank, score } - tickers > 0
let ownershipZeroData = [];  // tickers explicitement = 0
let buysZeroData = [];       // tickers explicitement = 0
let compositeData = [];      // merged results

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

// ============ UI TOGGLE ============
function toggleZeroSection(type) {
    const content = document.getElementById(`zeroContent${type.charAt(0).toUpperCase() + type.slice(1)}`);
    const arrow = document.getElementById(`arrow${type.charAt(0).toUpperCase() + type.slice(1)}Zero`);
    const toggle = arrow.parentElement;
    
    content.classList.toggle('open');
    toggle.classList.toggle('open');
}

// ============ PARSING ============
function parseTickers(text) {
    if (!text || !text.trim()) return [];
    
    const tickers = text
        .toUpperCase()
        .split(/[\s,;]+/)
        .map(t => t.trim())
        .filter(t => t.length >= 1 && t.length <= 6)
        .filter(t => /^[A-Z.]+$/.test(t));
    
    return [...new Set(tickers)];
}

function calculateScore(rank, total) {
    // Log-normalized score: better distribution than linear
    return Math.round((1 - Math.log(rank) / Math.log(total + 1)) * 100);
}

// --- Ownership ---
function parseOwnership() {
    const text = document.getElementById('inputOwnership').value;
    const tickers = parseTickers(text);
    
    if (tickers.length === 0) {
        showStatus('statusOwnership', 'error', '❌ Aucun ticker valide');
        return;
    }
    
    // Check for conflicts with zero list
    const conflicts = tickers.filter(t => ownershipZeroData.includes(t));
    if (conflicts.length > 0) {
        // Remove conflicts from zero list
        ownershipZeroData = ownershipZeroData.filter(t => !conflicts.includes(t));
        showStatus('statusOwnership', 'warning', 
            `⚠️ ${conflicts.length} tickers retirés de la liste zéro: ${conflicts.slice(0,3).join(', ')}...`);
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

function parseOwnershipZero() {
    const text = document.getElementById('inputOwnershipZero').value;
    const tickers = parseTickers(text);
    
    if (tickers.length === 0) {
        showStatus('statusOwnership', 'error', '❌ Aucun ticker valide');
        return;
    }
    
    // Check for conflicts with >0 list
    const existingTickers = new Set(ownershipData.map(d => d.ticker));
    const conflicts = tickers.filter(t => existingTickers.has(t));
    
    if (conflicts.length > 0) {
        showStatus('statusOwnership', 'warning', 
            `⚠️ ${conflicts.length} tickers ignorés (déjà dans liste >0): ${conflicts.slice(0,3).join(', ')}`);
    }
    
    // Only add non-conflicting tickers
    ownershipZeroData = tickers.filter(t => !existingTickers.has(t));
    
    document.getElementById('badgeOwnershipZero').textContent = ownershipZeroData.length;
    showStatus('statusOwnership', 'success', `🧊 ${ownershipZeroData.length} tickers marqués 0%`);
    updateState();
    calculateComposite();
}

// --- Buys ---
function parseBuys() {
    const text = document.getElementById('inputBuys').value;
    const tickers = parseTickers(text);
    
    if (tickers.length === 0) {
        showStatus('statusBuys', 'error', '❌ Aucun ticker valide');
        return;
    }
    
    // Check for conflicts with zero list
    const conflicts = tickers.filter(t => buysZeroData.includes(t));
    if (conflicts.length > 0) {
        buysZeroData = buysZeroData.filter(t => !conflicts.includes(t));
        showStatus('statusBuys', 'warning', 
            `⚠️ ${conflicts.length} tickers retirés de la liste zéro`);
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

function parseBuysZero() {
    const text = document.getElementById('inputBuysZero').value;
    const tickers = parseTickers(text);
    
    if (tickers.length === 0) {
        showStatus('statusBuys', 'error', '❌ Aucun ticker valide');
        return;
    }
    
    const existingTickers = new Set(buysData.map(d => d.ticker));
    const conflicts = tickers.filter(t => existingTickers.has(t));
    
    if (conflicts.length > 0) {
        showStatus('statusBuys', 'warning', 
            `⚠️ ${conflicts.length} tickers ignorés (déjà dans liste >0)`);
    }
    
    buysZeroData = tickers.filter(t => !existingTickers.has(t));
    
    document.getElementById('badgeBuysZero').textContent = buysZeroData.length;
    showStatus('statusBuys', 'success', `🧊 ${buysZeroData.length} tickers marqués 0 buy`);
    updateState();
    calculateComposite();
}

// ============ COMPOSITE CALCULATION ============
function calculateComposite() {
    const hasData = ownershipData.length > 0 || buysData.length > 0 || 
                    ownershipZeroData.length > 0 || buysZeroData.length > 0;
    
    if (!hasData) {
        compositeData = [];
        updateUI();
        return;
    }
    
    // Create lookup maps
    const ownershipMap = new Map(ownershipData.map(d => [d.ticker, d]));
    const buysMap = new Map(buysData.map(d => [d.ticker, d]));
    const ownershipZeroSet = new Set(ownershipZeroData);
    const buysZeroSet = new Set(buysZeroData);
    
    // All unique tickers
    const allTickers = new Set([
        ...ownershipMap.keys(),
        ...buysMap.keys(),
        ...ownershipZeroSet,
        ...buysZeroSet
    ]);
    
    compositeData = [];
    
    allTickers.forEach(ticker => {
        const inOwnership = ownershipMap.has(ticker);
        const inBuys = buysMap.has(ticker);
        const isZeroOwnership = ownershipZeroSet.has(ticker);
        const isZeroBuys = buysZeroSet.has(ticker);
        
        const ownershipRank = inOwnership ? ownershipMap.get(ticker).rank : null;
        const buysRank = inBuys ? buysMap.get(ticker).rank : null;
        const ownershipScore = inOwnership ? ownershipMap.get(ticker).score : 0;
        const buysScore = inBuys ? buysMap.get(ticker).score : 0;
        
        let compositeScore = 0;
        let bonus = false;
        
        // Calculate composite score
        if (inOwnership && inBuys) {
            // Best case: present in both >0 lists
            compositeScore = (ownershipScore + buysScore) / 2;
            
            // Bonus for top 50 in both
            if (ownershipRank <= 50 && buysRank <= 50) {
                compositeScore *= 1.2;
                bonus = true;
            }
        } else if (inOwnership && !inBuys && !isZeroBuys) {
            // Only in ownership, buys unknown
            compositeScore = ownershipScore * 0.5;
        } else if (!inOwnership && inBuys && !isZeroOwnership) {
            // Only in buys, ownership unknown
            compositeScore = buysScore * 0.5;
        } else if (inOwnership && isZeroBuys) {
            // In ownership but explicitly 0 buys
            compositeScore = ownershipScore * 0.3; // Penalized
        } else if (isZeroOwnership && inBuys) {
            // Explicitly 0 ownership but has buys (unusual)
            compositeScore = buysScore * 0.4;
        }
        // Both zero = score 0 (already default)
        
        compositeData.push({
            ticker,
            ownership_rank: ownershipRank,
            buys_rank: buysRank,
            ownership_score: ownershipScore,
            buys_score: buysScore,
            ownership_zero: isZeroOwnership,
            buys_zero: isZeroBuys,
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
    // Ownership
    document.getElementById('dotOwnership').classList.toggle('loaded', ownershipData.length > 0);
    document.getElementById('countOwnership').textContent = ownershipData.length;
    
    // Ownership Zero
    document.getElementById('dotOwnershipZero').classList.toggle('loaded', ownershipZeroData.length > 0);
    document.getElementById('countOwnershipZero').textContent = ownershipZeroData.length;
    document.getElementById('badgeOwnershipZero').textContent = ownershipZeroData.length;
    
    // Buys
    document.getElementById('dotBuys').classList.toggle('loaded', buysData.length > 0);
    document.getElementById('countBuys').textContent = buysData.length;
    
    // Buys Zero
    document.getElementById('dotBuysZero').classList.toggle('loaded', buysZeroData.length > 0);
    document.getElementById('countBuysZero').textContent = buysZeroData.length;
    document.getElementById('badgeBuysZero').textContent = buysZeroData.length;
    
    // Composite
    const inBoth = compositeData.filter(d => d.in_both).length;
    document.getElementById('dotComposite').classList.toggle('loaded', inBoth > 0);
    document.getElementById('countComposite').textContent = inBoth;
}

function updateUI() {
    const hasData = compositeData.length > 0;
    
    document.getElementById('statsGrid').style.display = hasData ? 'grid' : 'none';
    document.getElementById('actionsCard').style.display = hasData ? 'block' : 'none';
    
    if (!hasData) {
        document.getElementById('compositeCard').style.display = 'none';
        return;
    }
    
    // Stats
    const inBoth = compositeData.filter(d => d.in_both);
    const top50Both = inBoth.filter(d => d.ownership_rank <= 50 && d.buys_rank <= 50);
    const ownershipOnly = compositeData.filter(d => d.ownership_rank && !d.buys_rank && !d.buys_zero).length;
    const buysOnly = compositeData.filter(d => !d.ownership_rank && d.buys_rank && !d.ownership_zero).length;
    
    document.getElementById('statTotal').textContent = compositeData.length;
    document.getElementById('statBoth').textContent = inBoth.length;
    document.getElementById('statTop50Both').textContent = top50Both.length;
    document.getElementById('statOwnershipOnly').textContent = ownershipOnly;
    document.getElementById('statBuysOnly').textContent = buysOnly;
    document.getElementById('statZeroOwnership').textContent = ownershipZeroData.length;
    document.getElementById('statZeroBuys').textContent = buysZeroData.length;
    
    // Composite table
    if (inBoth.length > 0) {
        document.getElementById('compositeCard').style.display = 'block';
        
        const tbody = document.getElementById('compositeBody');
        tbody.innerHTML = inBoth
            .sort((a, b) => b.composite_score - a.composite_score)
            .slice(0, 50)
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
            collector_version: '1.1.0',
            includes_zero_data: ownershipZeroData.length > 0 || buysZeroData.length > 0
        },
        summary: {
            total_unique_tickers: compositeData.length,
            ownership_count: ownershipData.length,
            ownership_zero_count: ownershipZeroData.length,
            buys_6m_count: buysData.length,
            buys_zero_count: buysZeroData.length,
            in_both_lists: compositeData.filter(d => d.in_both).length,
            top_50_both: compositeData.filter(d => d.in_both && d.ownership_rank <= 50 && d.buys_rank <= 50).length
        },
        sp500_ownership: ownershipData,
        sp500_ownership_zero: ownershipZeroData,
        sp500_6m_buys: buysData,
        sp500_buys_zero: buysZeroData,
        composite_rankings: compositeData
            .filter(d => d.composite_score > 0)
            .map((d, idx) => ({
                composite_rank: idx + 1,
                ticker: d.ticker,
                ownership_rank: d.ownership_rank,
                buys_rank: d.buys_rank,
                composite_score: d.composite_score,
                top_50_bonus: d.bonus,
                ownership_zero: d.ownership_zero || false,
                buys_zero: d.buys_zero || false
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
        showStatus('githubStatus', 'error', '❌ Aucune donnée');
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
        showStatus('githubStatus', 'error', '❌ Aucune donnée');
        return;
    }
    
    // Validation warnings
    const warnings = [];
    if (ownershipData.length === 0) warnings.push('Ownership vide');
    if (buysData.length === 0) warnings.push('6M Buys vide');
    
    if (warnings.length > 0) {
        const proceed = confirm(
            `⚠️ Attention:\n- ${warnings.join('\n- ')}\n\nContinuer?`
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
        
        const putUrl = `https://api.github.com/repos/${GITHUB_CONFIG.owner}/${GITHUB_CONFIG.repo}/contents/${filePath}`;
        
        const body = {
            message: `📊 Update S&P500 Grid ${today} - ${compositeData.length} tickers (${ownershipZeroData.length + buysZeroData.length} zeros)`,
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
            showStatus('githubStatus', 'error', '❌ Token invalide');
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
        document.getElementById('inputOwnershipZero').value = '';
        document.getElementById('statusOwnership').className = 'status';
    } else {
        document.getElementById('inputBuys').value = '';
        document.getElementById('inputBuysZero').value = '';
        document.getElementById('statusBuys').className = 'status';
    }
}

function resetAll() {
    if (!confirm('🗑️ Effacer toutes les données?')) return;
    
    ownershipData = [];
    buysData = [];
    ownershipZeroData = [];
    buysZeroData = [];
    compositeData = [];
    
    document.getElementById('inputOwnership').value = '';
    document.getElementById('inputOwnershipZero').value = '';
    document.getElementById('inputBuys').value = '';
    document.getElementById('inputBuysZero').value = '';
    document.getElementById('statusOwnership').className = 'status';
    document.getElementById('statusBuys').className = 'status';
    document.getElementById('githubStatus').className = 'status';
    
    updateState();
    updateUI();
}

// ============ INIT ============
console.log('📊 S&P500 Grid Collector v1.1.0');
console.log('📈 Metrics: Ownership + 6M Buys + Zero support');
console.log('🎯 Composite score with bonus + zero flags');
