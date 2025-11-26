/**
 * Dataroma S&P500 Grid Collector
 * Version: 2.0.0
 * 
 * Features:
 * - Dual-metric: Ownership + 6M Buys
 * - Zero-value support (white cells)
 * - Custom numeric values per ticker (TICKER:value format)
 * - Composite scoring with bonus
 * - S&P500 ticker validation
 * - Auto-save to localStorage
 * - Secure token handling (session only)
 * - Dynamic block table UI
 */

// ============ CONFIGURATION ============
const GITHUB_CONFIG = {
    owner: 'Bencode92',
    repo: 'smartmoney-scraper',
    branch: 'main',
    basePath: 'data/raw/dataroma/sp500-grid'
};

// ============ S&P500 VALIDATION ============
// Liste officielle S&P500 (mise à jour régulièrement)
const SP500_TICKERS = new Set([
    'A','AAL','AAPL','ABBV','ABNB','ABT','ACGL','ACN','ADBE','ADI','ADM','ADP','ADSK','AEE','AEP','AES','AFL','AIG','AIZ','AJG',
    'AKAM','ALB','ALGN','ALL','ALLE','AMAT','AMCR','AMD','AME','AMGN','AMP','AMT','AMZN','ANET','ANSS','AON','AOS','APA','APD','APH',
    'APTV','ARE','ATO','AVB','AVGO','AVY','AWK','AXON','AXP','AZO','BA','BAC','BALL','BAX','BBWI','BBY','BDX','BEN','BF.A','BF.B',
    'BG','BIIB','BIO','BK','BKNG','BKR','BLDR','BLK','BMY','BR','BRK.A','BRK.B','BRO','BSX','BWA','BX','BXP','C','CAG','CAH',
    'CARR','CAT','CB','CBOE','CBRE','CCI','CCL','CDNS','CDW','CE','CEG','CF','CFG','CHD','CHRW','CHTR','CI','CINF','CL','CLX',
    'CMA','CMCSA','CME','CMG','CMI','CMS','CNC','CNP','COF','COO','COP','COR','COST','CPAY','CPB','CPRT','CPT','CRL','CRM','CRWD',
    'CSCO','CSGP','CSX','CTAS','CTLT','CTRA','CTSH','CTVA','CVS','CVX','CZR','D','DAL','DD','DECK','DFS','DG','DGX','DHI','DHR',
    'DIS','DLR','DLTR','DOC','DOV','DOW','DPZ','DRI','DTE','DUK','DVA','DVN','DXCM','EA','EBAY','ECL','ED','EFX','EG','EIX',
    'EL','ELV','EMN','EMR','ENPH','EOG','EPAM','EQIX','EQR','EQT','ES','ESS','ETN','ETR','ETSY','EVRG','EW','EXC','EXPD','EXPE',
    'EXR','F','FANG','FAST','FCX','FDS','FDX','FE','FFIV','FI','FICO','FIS','FITB','FLT','FMC','FOX','FOXA','FRT','FSLR','FTNT',
    'FTV','GD','GDDY','GE','GEHC','GEN','GEV','GILD','GIS','GL','GLW','GM','GNRC','GOOG','GOOGL','GPC','GPN','GRMN','GS','GWW',
    'HAL','HAS','HBAN','HCA','HD','HES','HIG','HII','HLT','HOLX','HON','HPE','HPQ','HRL','HSIC','HST','HSY','HUBB','HUM','HWM',
    'IBM','ICE','IDXX','IEX','IFF','ILMN','INCY','INTC','INTU','INVH','IP','IPG','IQV','IR','IRM','ISRG','IT','ITW','IVZ','J',
    'JBHT','JBL','JCI','JKHY','JNJ','JNPR','JPM','K','KDP','KEY','KEYS','KHC','KIM','KKR','KLAC','KMB','KMI','KMX','KO','KR',
    'KVUE','L','LDOS','LEN','LH','LHX','LIN','LKQ','LLY','LMT','LNT','LOW','LRCX','LULU','LUV','LVS','LW','LYB','LYV','MA',
    'MAA','MAR','MAS','MCD','MCHP','MCK','MCO','MDLZ','MDT','MET','META','MGM','MHK','MKC','MKTX','MLM','MMC','MMM','MNST','MO',
    'MOH','MOS','MPC','MPWR','MRK','MRNA','MRO','MS','MSCI','MSFT','MSI','MTB','MTCH','MTD','MU','NCLH','NDAQ','NDSN','NEE','NEM',
    'NFLX','NI','NKE','NOC','NOW','NRG','NSC','NTAP','NTRS','NUE','NVDA','NVR','NWS','NWSA','NXPI','O','ODFL','OKE','OMC','ON',
    'ORCL','ORLY','OTIS','OXY','PANW','PARA','PAYC','PAYX','PCAR','PCG','PEG','PEP','PFE','PFG','PG','PGR','PH','PHM','PKG','PLD',
    'PLTR','PM','PNC','PNR','PNW','PODD','POOL','PPG','PPL','PRU','PSA','PSX','PTC','PWR','PYPL','QCOM','QRVO','RCL','REG','REGN',
    'RF','RJF','RL','RMD','ROK','ROL','ROP','ROST','RSG','RTX','RVTY','SBAC','SBUX','SCHW','SHW','SJM','SLB','SMCI','SNA','SNPS',
    'SO','SOLV','SPG','SPGI','SRE','STE','STLD','STT','STX','STZ','SWK','SWKS','SYF','SYK','SYY','T','TAP','TDG','TDY','TECH',
    'TEL','TER','TFC','TFX','TGT','TJX','TMO','TMUS','TPR','TRGP','TRMB','TROW','TRV','TSCO','TSLA','TSN','TT','TTWO','TXN','TXT',
    'TYL','UAL','UBER','UDR','UHS','ULTA','UNH','UNP','UPS','URI','USB','V','VFC','VICI','VLO','VLTO','VMC','VRSK','VRSN','VRTX',
    'VST','VTR','VTRS','VZ','WAB','WAT','WBA','WBD','WDC','WEC','WELL','WFC','WM','WMB','WMT','WRB','WST','WTW','WY','WYNN',
    'XEL','XOM','XYL','YUM','ZBH','ZBRA','ZTS'
]);

// Aliases pour les classes d'actions
const TICKER_ALIASES = {
    'BRK-A': 'BRK.A', 'BRK-B': 'BRK.B', 'BRKA': 'BRK.A', 'BRKB': 'BRK.B',
    'BF-A': 'BF.A', 'BF-B': 'BF.B', 'BFA': 'BF.A', 'BFB': 'BF.B'
};

function normalizeTicker(ticker) {
    const upper = ticker.toUpperCase().trim();
    return TICKER_ALIASES[upper] || upper;
}

function isValidSP500Ticker(ticker) {
    const normalized = normalizeTicker(ticker);
    return SP500_TICKERS.has(normalized);
}

// ============ SESSION STATE ============
let sessionToken = null;
let ownershipData = [];      // { ticker, rank, score, raw_value }
let buysData = [];           // { ticker, rank, score, raw_value }
let ownershipZeroData = [];  // tickers explicitement = 0
let buysZeroData = [];       // tickers explicitement = 0
let compositeData = [];      // merged results
let invalidTickers = [];     // tickers non-S&P500 détectés

// ============ AUTO-SAVE ============
const STORAGE_KEY = 'sp500_grid_draft_v2';

function autoSave() {
    try {
        const state = {
            ownershipData,
            buysData,
            ownershipZeroData,
            buysZeroData,
            inputOwnership: document.getElementById('inputOwnership')?.value || '',
            inputBuys: document.getElementById('inputBuys')?.value || '',
            inputOwnershipZero: document.getElementById('inputOwnershipZero')?.value || '',
            inputBuysZero: document.getElementById('inputBuysZero')?.value || '',
            ownershipBlocks: getBlocksData('ownershipBlocks'),
            buysBlocks: getBlocksData('buysBlocks'),
            savedAt: new Date().toISOString()
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
        console.warn('Auto-save failed:', e);
    }
}

function getBlocksData(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return [];
    const rows = container.querySelectorAll('.block-row');
    return Array.from(rows).map(row => ({
        value: row.querySelector('.block-value')?.value || '',
        tickers: row.querySelector('.block-tickers')?.value || ''
    }));
}

function restoreFromStorage() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (!saved) return false;
        
        const state = JSON.parse(saved);
        const savedDate = new Date(state.savedAt);
        const hoursSince = (Date.now() - savedDate.getTime()) / (1000 * 60 * 60);
        
        // Ne restaurer que si < 24h
        if (hoursSince > 24) {
            localStorage.removeItem(STORAGE_KEY);
            return false;
        }
        
        // Restaurer les données
        ownershipData = state.ownershipData || [];
        buysData = state.buysData || [];
        ownershipZeroData = state.ownershipZeroData || [];
        buysZeroData = state.buysZeroData || [];
        
        // Restaurer les inputs
        if (state.inputOwnership) {
            const el = document.getElementById('inputOwnership');
            if (el) el.value = state.inputOwnership;
        }
        if (state.inputBuys) {
            const el = document.getElementById('inputBuys');
            if (el) el.value = state.inputBuys;
        }
        if (state.inputOwnershipZero) {
            const el = document.getElementById('inputOwnershipZero');
            if (el) el.value = state.inputOwnershipZero;
        }
        if (state.inputBuysZero) {
            const el = document.getElementById('inputBuysZero');
            if (el) el.value = state.inputBuysZero;
        }
        
        // Restaurer les blocs
        restoreBlocks('ownershipBlocks', state.ownershipBlocks);
        restoreBlocks('buysBlocks', state.buysBlocks);
        
        calculateComposite();
        updateState();
        
        console.log(`📦 Brouillon restauré (${hoursSince.toFixed(1)}h)`);
        return true;
    } catch (e) {
        console.warn('Restore failed:', e);
        return false;
    }
}

function restoreBlocks(containerId, blocksData) {
    if (!blocksData || blocksData.length === 0) return;
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Vider et recréer
    container.innerHTML = '';
    blocksData.forEach((block, idx) => {
        const row = createBlockRow(block.value, block.tickers);
        container.appendChild(row);
    });
}

function createBlockRow(value = '', tickers = '') {
    const row = document.createElement('div');
    row.className = 'block-row';
    row.innerHTML = `
        <input class="block-value" type="text" placeholder="0,01" value="${escapeHtml(value)}">
        <textarea class="block-tickers" placeholder="YUM BRO BXP">${escapeHtml(tickers)}</textarea>
        <button type="button" class="btn btn-xs btn-icon" onclick="removeBlockRow(this)">✕</button>
    `;
    return row;
}

// Auto-save toutes les 30s
setInterval(autoSave, 30000);

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

// ============ UI HELPERS ============
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showStatus(elementId, type, message, allowHtml = false) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.className = `status ${type}`;
    if (allowHtml) {
        el.innerHTML = message;
    } else {
        el.textContent = message;
    }
}

function toggleZeroSection(type) {
    const content = document.getElementById(`zeroContent${type.charAt(0).toUpperCase() + type.slice(1)}`);
    const arrow = document.getElementById(`arrow${type.charAt(0).toUpperCase() + type.slice(1)}Zero`);
    if (!content || !arrow) return;
    const toggle = arrow.parentElement;
    content.classList.toggle('open');
    toggle.classList.toggle('open');
}

// ============ BLOCK TABLE HELPERS ============
function buildTextFromBlocks(containerId, isPercent) {
    const container = document.getElementById(containerId);
    if (!container) return '';
    
    const rows = container.querySelectorAll('.block-row');
    const blocks = [];

    rows.forEach(row => {
        const valueInput = row.querySelector('.block-value');
        const tickersInput = row.querySelector('.block-tickers');
        if (!valueInput || !tickersInput) return;

        const rawValue = valueInput.value.trim();
        const rawTickers = tickersInput.value.trim().toUpperCase();
        if (!rawValue && !rawTickers) return;

        const tickers = rawTickers.split(/[\s,;]+/).filter(Boolean).join(' ');
        if (!tickers) return;

        let prefix = '';
        if (rawValue) {
            let v = rawValue.replace(',', '.');
            prefix = isPercent ? `${v}% ` : `${v} `;
        }
        blocks.push(prefix + tickers);
    });

    return blocks.join('\n');
}

function addBlockRow(type) {
    const containerId = type === 'ownership' ? 'ownershipBlocks' : 'buysBlocks';
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const row = createBlockRow();
    container.appendChild(row);
}

function removeBlockRow(btn) {
    const row = btn.closest('.block-row');
    const container = row && row.parentElement;
    if (!row || !container) return;

    const rows = container.querySelectorAll('.block-row');
    if (rows.length <= 1) {
        row.querySelector('.block-value').value = '';
        row.querySelector('.block-tickers').value = '';
    } else {
        row.remove();
    }
}

function prepareOwnershipAndParse() {
    const blockText = buildTextFromBlocks('ownershipBlocks', true);
    const textareaEl = document.getElementById('inputOwnership');
    const existingText = textareaEl.value.trim();
    
    // Combiner blocs + textarea
    if (blockText && existingText) {
        textareaEl.value = blockText + '\n' + existingText;
    } else if (blockText) {
        textareaEl.value = blockText;
    }
    parseOwnership();
}

function prepareBuysAndParse() {
    const blockText = buildTextFromBlocks('buysBlocks', false);
    const textareaEl = document.getElementById('inputBuys');
    const existingText = textareaEl.value.trim();
    
    if (blockText && existingText) {
        textareaEl.value = blockText + '\n' + existingText;
    } else if (blockText) {
        textareaEl.value = blockText;
    }
    parseBuys();
}

// ============ PARSING HELPERS ============
function parseTickers(text) {
    if (!text || !text.trim()) return [];
    
    const tickers = text
        .toUpperCase()
        .split(/[\s,;]+/)
        .map(t => normalizeTicker(t.trim()))
        .filter(t => t.length >= 1 && t.length <= 6)
        .filter(t => /^[A-Z.]+$/.test(t));
    
    return [...new Set(tickers)];
}

function parseMetricText(text) {
    if (!text || !text.trim()) return [];
    
    const tokens = text
        .toUpperCase()
        .split(/[\s,;]+/)
        .map(t => t.trim())
        .filter(t => t.length > 0);

    const items = [];
    const indexByTicker = new Map();
    let currentGroupValue = null;
    invalidTickers = [];

    const addOrUpdate = (ticker, value) => {
        const cleanTicker = normalizeTicker(ticker.trim());
        if (!/^[A-Z.]{1,6}$/.test(cleanTicker)) return;

        // Validation S&P500
        if (!isValidSP500Ticker(cleanTicker)) {
            if (!invalidTickers.includes(cleanTicker)) {
                invalidTickers.push(cleanTicker);
            }
            return;
        }

        const v = Number.isFinite(value) && value >= 0 ? value : null;
        const existingIdx = indexByTicker.get(cleanTicker);

        if (existingIdx === undefined) {
            items.push({ ticker: cleanTicker, value: v });
            indexByTicker.set(cleanTicker, items.length - 1);
        } else if (v !== null) {
            items[existingIdx].value = v;
        }
    };

    for (const token of tokens) {
        const numMatch = token.match(/^([-+]?\d*[\.,]?\d+)%?$/);
        if (numMatch) {
            let v = parseFloat(numMatch[1].replace(',', '.'));
            currentGroupValue = (!Number.isFinite(v) || v < 0) ? null : v;
            continue;
        }

        const pairMatch = token.match(/^([A-Z.\-]{1,8})[:=]([-+]?\d*[\.,]?\d+)$/);
        if (pairMatch) {
            const ticker = pairMatch[1];
            let v = parseFloat(pairMatch[2].replace(',', '.'));
            if (!Number.isFinite(v) || v < 0) v = null;
            addOrUpdate(ticker, v);
            continue;
        }

        if (/^[A-Z.\-]{1,8}$/.test(token)) {
            addOrUpdate(token, currentGroupValue);
            continue;
        }
    }

    return items;
}

function calculateScore(rank, total) {
    return Math.round((1 - Math.log(rank) / Math.log(total + 1)) * 100);
}

// ============ PARSING OWNERSHIP ============
function parseOwnership() {
    const text = document.getElementById('inputOwnership').value;
    const entries = parseMetricText(text);
    
    if (entries.length === 0) {
        let msg = '❌ Aucun ticker S&P500 valide';
        if (invalidTickers.length > 0) {
            msg += ` (ignorés: ${invalidTickers.slice(0, 5).join(', ')}${invalidTickers.length > 5 ? '...' : ''})`;
        }
        showStatus('statusOwnership', 'error', msg);
        return;
    }

    const tickers = entries.map(e => e.ticker);
    const conflicts = tickers.filter(t => ownershipZeroData.includes(t));
    if (conflicts.length > 0) {
        ownershipZeroData = ownershipZeroData.filter(t => !conflicts.includes(t));
    }

    const explicitValues = entries
        .map(e => e.value)
        .filter(v => v != null && Number.isFinite(v) && v >= 0);

    const hasCustomValues = explicitValues.length > 0;
    const maxValue = hasCustomValues ? Math.max(...explicitValues) : 0;

    ownershipData = entries.map((item, idx) => {
        const rank = idx + 1;
        let score;
        let raw = null;

        if (hasCustomValues && item.value != null && Number.isFinite(item.value)) {
            raw = item.value;
            score = maxValue > 0 ? Math.round((item.value / maxValue) * 100) : 0;
        } else {
            score = calculateScore(rank, entries.length);
        }

        return { ticker: item.ticker, rank, score, raw_value: raw };
    });

    const customCount = ownershipData.filter(d => d.raw_value !== null).length;
    let msg = `✅ ${ownershipData.length} tickers S&P500 parsés`;
    if (customCount > 0) msg += ` (${customCount} avec valeur)`;
    if (conflicts.length > 0) msg += ` | ${conflicts.length} retirés de 0%`;
    if (invalidTickers.length > 0) msg += ` | ⚠️ ${invalidTickers.length} hors S&P500`;
    
    showStatus('statusOwnership', 'success', msg);
    updateState();
    calculateComposite();
    autoSave();
}

function parseOwnershipZero() {
    const text = document.getElementById('inputOwnershipZero').value;
    const tickers = parseTickers(text).filter(isValidSP500Ticker);
    
    if (tickers.length === 0) {
        showStatus('statusOwnership', 'error', '❌ Aucun ticker S&P500 valide');
        return;
    }
    
    const existingTickers = new Set(ownershipData.map(d => d.ticker));
    const conflicts = tickers.filter(t => existingTickers.has(t));
    
    if (conflicts.length > 0) {
        showStatus('statusOwnership', 'warning', 
            `⚠️ ${conflicts.length} tickers ignorés (déjà dans liste >0)`);
    }
    
    ownershipZeroData = tickers.filter(t => !existingTickers.has(t));
    
    document.getElementById('badgeOwnershipZero').textContent = ownershipZeroData.length;
    showStatus('statusOwnership', 'success', `🧊 ${ownershipZeroData.length} tickers marqués 0%`);
    updateState();
    calculateComposite();
    autoSave();
}

// ============ PARSING BUYS ============
function parseBuys() {
    const text = document.getElementById('inputBuys').value;
    const entries = parseMetricText(text);
    
    if (entries.length === 0) {
        let msg = '❌ Aucun ticker S&P500 valide';
        if (invalidTickers.length > 0) {
            msg += ` (ignorés: ${invalidTickers.slice(0, 5).join(', ')}${invalidTickers.length > 5 ? '...' : ''})`;
        }
        showStatus('statusBuys', 'error', msg);
        return;
    }

    const tickers = entries.map(e => e.ticker);
    const conflicts = tickers.filter(t => buysZeroData.includes(t));
    if (conflicts.length > 0) {
        buysZeroData = buysZeroData.filter(t => !conflicts.includes(t));
    }

    const explicitValues = entries
        .map(e => e.value)
        .filter(v => v != null && Number.isFinite(v) && v >= 0);

    const hasCustomValues = explicitValues.length > 0;
    const maxValue = hasCustomValues ? Math.max(...explicitValues) : 0;

    buysData = entries.map((item, idx) => {
        const rank = idx + 1;
        let score;
        let raw = null;

        if (hasCustomValues && item.value != null && Number.isFinite(item.value)) {
            raw = item.value;
            score = maxValue > 0 ? Math.round((item.value / maxValue) * 100) : 0;
        } else {
            score = calculateScore(rank, entries.length);
        }

        return { ticker: item.ticker, rank, score, raw_value: raw };
    });

    const customCount = buysData.filter(d => d.raw_value !== null).length;
    let msg = `✅ ${buysData.length} tickers S&P500 parsés`;
    if (customCount > 0) msg += ` (${customCount} avec valeur)`;
    if (conflicts.length > 0) msg += ` | ${conflicts.length} retirés de 0 buy`;
    if (invalidTickers.length > 0) msg += ` | ⚠️ ${invalidTickers.length} hors S&P500`;
    
    showStatus('statusBuys', 'success', msg);
    updateState();
    calculateComposite();
    autoSave();
}

function parseBuysZero() {
    const text = document.getElementById('inputBuysZero').value;
    const tickers = parseTickers(text).filter(isValidSP500Ticker);
    
    if (tickers.length === 0) {
        showStatus('statusBuys', 'error', '❌ Aucun ticker S&P500 valide');
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
    autoSave();
}

// ============ COMPOSITE CALCULATION ============
function calculateComposite() {
    const hasData =
        ownershipData.length > 0 ||
        buysData.length > 0 ||
        ownershipZeroData.length > 0 ||
        buysZeroData.length > 0;
    
    if (!hasData) {
        compositeData = [];
        updateUI();
        return;
    }
    
    const ownershipMap = new Map(ownershipData.map(d => [d.ticker, d]));
    const buysMap = new Map(buysData.map(d => [d.ticker, d]));
    const ownershipZeroSet = new Set(ownershipZeroData);
    const buysZeroSet = new Set(buysZeroData);
    
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
        
        const ownershipEntry = inOwnership ? ownershipMap.get(ticker) : null;
        const buysEntry = inBuys ? buysMap.get(ticker) : null;

        const ownershipRank = ownershipEntry ? ownershipEntry.rank : null;
        const buysRank = buysEntry ? buysEntry.rank : null;
        const ownershipScore = ownershipEntry ? ownershipEntry.score : 0;
        const buysScore = buysEntry ? buysEntry.score : 0;
        const ownershipRaw = ownershipEntry ? ownershipEntry.raw_value : null;
        const buysRaw = buysEntry ? buysEntry.raw_value : null;
        
        let compositeScore = 0;
        let bonus = false;
        
        if (inOwnership && inBuys) {
            compositeScore = (ownershipScore + buysScore) / 2;
            if (ownershipRank <= 50 && buysRank <= 50) {
                compositeScore *= 1.2;
                bonus = true;
            }
        } else if (inOwnership && !inBuys && !isZeroBuys) {
            compositeScore = ownershipScore * 0.5;
        } else if (!inOwnership && inBuys && !isZeroOwnership) {
            compositeScore = buysScore * 0.5;
        } else if (inOwnership && isZeroBuys) {
            compositeScore = ownershipScore * 0.3;
        } else if (isZeroOwnership && inBuys) {
            compositeScore = buysScore * 0.4;
        }
        
        compositeData.push({
            ticker,
            ownership_rank: ownershipRank,
            buys_rank: buysRank,
            ownership_score: ownershipScore,
            buys_score: buysScore,
            ownership_raw_value: ownershipRaw,
            buys_raw_value: buysRaw,
            ownership_zero: isZeroOwnership,
            buys_zero: isZeroBuys,
            composite_score: Math.round(compositeScore),
            in_both: inOwnership && inBuys,
            bonus
        });
    });
    
    compositeData.sort((a, b) => b.composite_score - a.composite_score);
    updateUI();
}

// ============ UI UPDATES ============
function updateState() {
    document.getElementById('dotOwnership').classList.toggle('loaded', ownershipData.length > 0);
    document.getElementById('countOwnership').textContent = ownershipData.length;
    
    document.getElementById('dotOwnershipZero').classList.toggle('loaded', ownershipZeroData.length > 0);
    document.getElementById('countOwnershipZero').textContent = ownershipZeroData.length;
    document.getElementById('badgeOwnershipZero').textContent = ownershipZeroData.length;
    
    document.getElementById('dotBuys').classList.toggle('loaded', buysData.length > 0);
    document.getElementById('countBuys').textContent = buysData.length;
    
    document.getElementById('dotBuysZero').classList.toggle('loaded', buysZeroData.length > 0);
    document.getElementById('countBuysZero').textContent = buysZeroData.length;
    document.getElementById('badgeBuysZero').textContent = buysZeroData.length;
    
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
    
    const inBoth = compositeData.filter(d => d.in_both);
    const top50Both = inBoth.filter(d => d.ownership_rank <= 50 && d.buys_rank <= 50);
    const customValuesCount = compositeData.filter(d => 
        d.ownership_raw_value !== null || d.buys_raw_value !== null
    ).length;
    
    document.getElementById('statTotal').textContent = compositeData.length;
    document.getElementById('statBoth').textContent = inBoth.length;
    document.getElementById('statTop50Both').textContent = top50Both.length;
    document.getElementById('statCustomValues').textContent = customValuesCount;
    document.getElementById('statZeroOwnership').textContent = ownershipZeroData.length;
    document.getElementById('statZeroBuys').textContent = buysZeroData.length;
    
    if (inBoth.length > 0) {
        document.getElementById('compositeCard').style.display = 'block';
        
        const tbody = document.getElementById('compositeBody');
        tbody.innerHTML = inBoth
            .sort((a, b) => b.composite_score - a.composite_score)
            .slice(0, 50)
            .map((d, idx) => `
                <tr class="${d.bonus ? 'composite-high' : ''}">
                    <td>${idx + 1}</td>
                    <td class="ticker">${escapeHtml(d.ticker)}</td>
                    <td class="${d.ownership_rank <= 20 ? 'rank-top' : d.ownership_rank <= 50 ? 'rank-mid' : ''}">
                        #${d.ownership_rank}
                    </td>
                    <td style="color: var(--text-muted);">
                        ${d.ownership_raw_value !== null ? d.ownership_raw_value : '-'}
                    </td>
                    <td class="${d.buys_rank <= 20 ? 'rank-top' : d.buys_rank <= 50 ? 'rank-mid' : ''}">
                        #${d.buys_rank}
                    </td>
                    <td style="color: var(--text-muted);">
                        ${d.buys_raw_value !== null ? d.buys_raw_value : '-'}
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
    const hasCustomOwnership = ownershipData.some(d => d.raw_value !== null);
    const hasCustomBuys = buysData.some(d => d.raw_value !== null);
    
    return {
        metadata: {
            source: 'Dataroma',
            dataset: 'S&P500 Grid - Superinvestor Rankings',
            url: 'https://www.dataroma.com/m/g/portfolio_b.php',
            as_of: today,
            description: 'S&P500 stocks ranked by superinvestor ownership and recent buying activity',
            collector_version: '2.0.0',
            includes_zero_data: ownershipZeroData.length > 0 || buysZeroData.length > 0,
            includes_custom_values: hasCustomOwnership || hasCustomBuys,
            sp500_validated: true
        },
        summary: {
            total_unique_tickers: compositeData.length,
            ownership_count: ownershipData.length,
            ownership_zero_count: ownershipZeroData.length,
            ownership_with_custom_values: ownershipData.filter(d => d.raw_value !== null).length,
            buys_6m_count: buysData.length,
            buys_zero_count: buysZeroData.length,
            buys_with_custom_values: buysData.filter(d => d.raw_value !== null).length,
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
                ownership_raw_value: d.ownership_raw_value,
                buys_rank: d.buys_rank,
                buys_raw_value: d.buys_raw_value,
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

// ============ GITHUB PUSH WITH RETRY ============
async function pushToGitHub(retries = 3) {
    if (compositeData.length === 0) {
        showStatus('githubStatus', 'error', '❌ Aucune donnée');
        return;
    }
    
    const warnings = [];
    if (ownershipData.length === 0) warnings.push('Ownership vide');
    if (buysData.length === 0) warnings.push('6M Buys vide');
    
    if (warnings.length > 0) {
        const proceed = confirm(`⚠️ Attention:\n- ${warnings.join('\n- ')}\n\nContinuer?`);
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
    
    for (let attempt = 1; attempt <= retries; attempt++) {
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
            
            const customCount = compositeData.filter(d => 
                d.ownership_raw_value !== null || d.buys_raw_value !== null
            ).length;
            
            const body = {
                message: `📊 Update S&P500 Grid ${today} - ${compositeData.length} tickers (${customCount} custom, ${ownershipZeroData.length + buysZeroData.length} zeros)`,
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
            
            // Succès - effacer le brouillon
            localStorage.removeItem(STORAGE_KEY);
            
            showStatus('githubStatus', 'success', 
                `✅ Push réussi! <a href="${result.content.html_url}" target="_blank" style="color: var(--accent);">Voir sur GitHub</a>`,
                true);
            return;
            
        } catch (err) {
            console.error(`GitHub push attempt ${attempt}/${retries} error:`, err);
            
            if (err.message && err.message.includes('Bad credentials')) {
                sessionToken = null;
                showStatus('githubStatus', 'error', '❌ Token invalide');
                return;
            }
            
            if (attempt < retries) {
                const delay = Math.pow(2, attempt) * 1000;
                showStatus('githubStatus', 'warning', `⚠️ Tentative ${attempt}/${retries} échouée. Retry dans ${delay/1000}s...`);
                await new Promise(r => setTimeout(r, delay));
            } else {
                showStatus('githubStatus', 'error', `❌ Erreur après ${retries} tentatives: ${err.message}`);
            }
        }
    }
}

// ============ HELPERS ============
function clearInput(type) {
    if (type === 'ownership') {
        document.getElementById('inputOwnership').value = '';
        document.getElementById('inputOwnershipZero').value = '';
        document.getElementById('statusOwnership').className = 'status';
        // Clear blocks
        const container = document.getElementById('ownershipBlocks');
        if (container) {
            container.innerHTML = '';
            container.appendChild(createBlockRow());
        }
    } else {
        document.getElementById('inputBuys').value = '';
        document.getElementById('inputBuysZero').value = '';
        document.getElementById('statusBuys').className = 'status';
        const container = document.getElementById('buysBlocks');
        if (container) {
            container.innerHTML = '';
            container.appendChild(createBlockRow());
        }
    }
    autoSave();
}

function resetAll() {
    if (!confirm('🗑️ Effacer toutes les données?')) return;
    
    ownershipData = [];
    buysData = [];
    ownershipZeroData = [];
    buysZeroData = [];
    compositeData = [];
    invalidTickers = [];
    
    document.getElementById('inputOwnership').value = '';
    document.getElementById('inputOwnershipZero').value = '';
    document.getElementById('inputBuys').value = '';
    document.getElementById('inputBuysZero').value = '';
    document.getElementById('statusOwnership').className = 'status';
    document.getElementById('statusBuys').className = 'status';
    document.getElementById('githubStatus').className = 'status';
    
    // Reset blocks
    ['ownershipBlocks', 'buysBlocks'].forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.innerHTML = '';
            container.appendChild(createBlockRow());
        }
    });
    
    localStorage.removeItem(STORAGE_KEY);
    
    updateState();
    updateUI();
}

// ============ INIT ============
document.addEventListener('DOMContentLoaded', () => {
    console.log('📊 S&P500 Grid Collector v2.0.0');
    console.log('✅ Validation S&P500 active (' + SP500_TICKERS.size + ' tickers)');
    console.log('💾 Auto-save activé');
    
    // Restaurer le brouillon si existant
    const restored = restoreFromStorage();
    if (restored) {
        showStatus('githubStatus', 'info', '📦 Brouillon restauré automatiquement');
    }
});
