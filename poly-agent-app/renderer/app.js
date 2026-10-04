// PolyAgent - Frontend Application Logic

// ===== STATE =====
let agentEnabled = false;
let currentSport = 'mlb';
let currentCategory = 'sports';
let settings = {
  dailyBudget: 50,
  perTradeMax: 20,
  lossLimit: 50,
  stopLoss: 20,
  takeProfit: 15,
  strategies: { arb: true, edge: true, momentum: false, mm: false },
  lmEndpoint: 'http://localhost:1234',
  pmClientID: '',
  pmAudience: ''
};

// Sample team data (would come from Polymarket API)
const sampleTeams = {
  mlb: [
    { name: 'NY Yankees vs BOS Red Sox', odds: '62%', status: 'live' },
    { name: 'LA Dodgers vs SF Giants', odds: '58%', status: 'upcoming' },
    { name: 'HOU Astros vs TEX Rangers', odds: '45%', status: 'live' },
    { name: 'ATL Braves vs PHI Phillies', odds: '71%', status: 'upcoming' },
    { name: 'CHC Cubs vs STL Cardinals', odds: '39%', status: 'live' }
  ],
  tennis: [
    { name: 'Djokovic vs Alcaraz (Wimbledon)', odds: '54%', status: 'live' },
    { name: 'Sinner vs Medvedev (US Open)', odds: '67%', status: 'upcoming' },
    { name: 'Swiatek vs Sabalenka (Roland Garros)', odds: '48%', status: 'live' }
  ],
  nfl: [
    { name: 'KC Chiefs vs BUF Bills', odds: '52%', status: 'upcoming' },
    { name: 'SF 49ers vs PHI Eagles', odds: '61%', status: 'live' },
    { name: 'DAL Cowboys vs WAS Commanders', odds: '38%', status: 'upcoming' }
  ],
  nba: [
    { name: 'LAL Lakers vs BOS Celtics', odds: '55%', status: 'live' },
    { name: 'GSW Warriors vs MIA Heat', odds: '47%', status: 'upcoming' }
  ],
  nhl: [
    { name: 'EDM Oilers vs COL Avalanche', odds: '63%', status: 'live' },
    { name: 'NYR Rangers vs TBL Lightning', odds: '51%', status: 'upcoming' }
  ],
  ufc: [
    { name: 'UFC 320: Main Event', odds: '44%', status: 'upcoming' },
    { name: 'UFC Fight Night: Co-Main', odds: '58%', status: 'live' }
  ],
  soccer: [
    { name: 'Man City vs Arsenal (EPL)', odds: '62%', status: 'live' },
    { name: 'Real Madrid vs Barcelona (La Liga)', odds: '49%', status: 'upcoming' }
  ]
};

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  renderTeams(currentSport);
  setupEventListeners();
  
  // Check agent status from main process
  ipcRenderer.send('get-agent-status');
});

const ipcRenderer = window.require ? window.require('electron').ipcRenderer : null;

// ===== EVENT LISTENERS =====
function setupEventListeners() {
  // Category buttons
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.dataset.cat;
      updateSportTabs();
    });
  });

  // Sport tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentSport = btn.dataset.sport;
      renderTeams(currentSport);
    });
  });

  // Right panel tabs
  document.querySelectorAll('.ptab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.ptab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      switchPanelTab(btn.dataset.tab);
    });
  });

  // Settings sliders
  ['dailyBudget', 'perTradeMax', 'lossLimit', 'stopLoss', 'takeProfit'].forEach(id => {
    const slider = document.getElementById(id);
    if (slider) {
      slider.addEventListener('input', () => updateSliderDisplay(id));
    }
  });

  // Settings toggle visibility
  document.querySelector('.sidebar-header').addEventListener('click', () => {
    document.getElementById('settingsPanel').classList.toggle('visible');
  });

  // IPC: receive agent status from main process
  if (ipcRenderer) {
    ipcRenderer.on('agent-status-reply', (event, data) => {
      updateAgentStatus(data.enabled);
    });
    
    ipcRenderer.on('agent-message', (event, msg) => {
      addChatMessage(msg.type === 'error' ? 'bot-error' : 'bot', msg.text);
    });

    ipcRenderer.on('show-settings', () => {
      document.getElementById('settingsPanel').classList.toggle('visible');
    });
  }
}

// ===== UI RENDERING =====
function renderTeams(sport) {
  const container = document.getElementById('teamsList');
  const teams = sampleTeams[sport] || [];
  
  container.innerHTML = teams.map((team, i) => `
    <div class="team-row">
      <span class="team-name">${team.name}</span>
      <span class="team-odds">${team.odds}</span>
      <button class="btn-team btn-bet" onclick="betOnTeam('${sport}', ${i})">Bet</button>
      <button class="btn-team btn-add" onclick="addPosition('${sport}', ${i})">Add</button>
      <button class="btn-team btn-cashout" onclick="cashOut('${sport}', ${i})">Cash</button>
      <button class="btn-team btn-auto-team" onclick="autoTradeTeam('${sport}', ${i})">AUTO</button>
    </div>
  `).join('');
}

function updateSportTabs() {
  const tabs = document.getElementById('sportTabs');
  if (currentCategory === 'sports') {
    tabs.style.display = 'flex';
  } else {
    tabs.style.display = 'none';
  }
}

function switchPanelTab(tab) {
  const panel = document.getElementById('positionsPanel');
  if (tab === 'history') {
    panel.innerHTML = `
      <div class="position-item">
        <div class="pos-name">MLB: Yankees vs Red Sox - YES</div>
        <div class="pos-pnl">+$12.50 (+8.3%)</div>
        <small>Entry: $0.62 | Current: $0.70</small>
      </div>
      <div class="position-item">
        <div class="pos-name">Tennis: Djokovic vs Alcaraz - NO</div>
        <div class="pos-pnl negative">-$5.00 (-3.2%)</div>
        <small>Entry: $0.46 | Current: $0.43</small>
      </div>
    `;
  } else {
    panel.innerHTML = '<p class="empty-state">No active positions. Scan markets to find opportunities.</p>';
  }
}

// ===== CHAT =====
function addChatMessage(type, text) {
  const container = document.getElementById('chatMessages');
  const isBot = type === 'bot' || type === 'bot-error';
  
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${isBot ? 'bot-message' : 'msg-user'}`;
  
  if (type === 'bot-error') {
    msgDiv.querySelector?.('.msg-content p:last-child')?.style?.setProperty('color', '#e74c3c');
  }
  
  msgDiv.innerHTML = `
    <div class="msg-avatar">${isBot ? '🤖' : '👤'}</div>
    <div class="msg-content">
      <p>${text.replace(/\n/g, '<br>')}</p>
    </div>
  `;
  
  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
}

function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;
  
  // Add user message
  addChatMessage('user', text);
  input.value = '';
  
  // Send to agent via IPC
  if (ipcRenderer && agentEnabled) {
    ipcRenderer.send('agent-message', text);
    
    // Simulated response for demo (remove when real agent is connected)
    setTimeout(() => simulateResponse(text), 1000);
  } else if (!agentEnabled) {
    addChatMessage('bot-error', '⚠️ Agent is not running. Click "Enable Agent" in Options menu or the ⏹ Stop button to start it.');
  }
}

function simulateResponse(text) {
  const lower = text.toLowerCase();
  
  if (lower.includes('scan') || lower.includes('find')) {
    addChatMessage('bot', `🔍 Scanning ${currentSport.toUpperCase()} markets for opportunities...\n\nFound 3 potential arbitrage opportunities:\n• Yankees vs Red Sox: 2.1% edge on YES leg\n• Dodgers vs Giants: 1.8% edge on totals\n• Astros vs Rangers: 0.9% edge (low confidence)\n\nDaily budget remaining: $${settings.dailyBudget - 15}/day`);
  } else if (lower.includes('budget') || lower.includes('set')) {
    addChatMessage('bot', `✅ Budget updated to $${settings.dailyBudget}/day. Per-trade max: $${settings.perTradeMax}. Stop loss at ${settings.stopLoss}%, take profit at ${settings.takeProfit}%.`);
  } else if (lower.includes('position') || lower.includes('show')) {
    addChatMessage('bot', `📊 Active Positions:\n• MLB Yankees YES: +$12.50 (+8.3%)\n• Tennis Djokovic NO: -$5.00 (-3.2%)\n\nTotal P&L today: +$7.50`);
  } else if (lower.includes('stop')) {
    addChatMessage('bot', '⏹ Agent paused. All active trades remain open. Click Enable to resume.');
    updateAgentStatus(false);
  } else if (lower.includes('enable') || lower.includes('start')) {
    addChatMessage('bot', '✅ Agent enabled! Scanning markets now...');
    updateAgentStatus(true);
  } else {
    addChatMessage('bot', `🤖 I received your message: "${text}"\n\nTry commands like:\n• "scan [sport]" - find opportunities\n• "set budget $X" - adjust limits\n• "show positions" - view trades\n• "stop" - pause agent`);
  }
}

function handleChatKey(e) {
  if (e.key === 'Enter') sendMessage();
}

// ===== TEAM ACTIONS =====
function betOnTeam(sport, index) {
  addChatMessage('user', `Bet on ${sampleTeams[sport][index].name}`);
  setTimeout(() => {
    addChatMessage('bot', `✅ Order placed: YES at $0.${Math.floor(Math.random()*90+10)}\nPosition added to your portfolio.`);
  }, 500);
}

function autoTradeTeam(sport, index) {
  if (!agentEnabled) {
    addChatMessage('bot-error', '⚠️ Enable the agent first (Options → Enable Agent), then try AUTO.');
    return;
  }
  addChatMessage('user', `AUTO: ${sampleTeams[sport][index].name}`);
  setTimeout(() => {
    addChatMessage('bot', `🤖 Auto-trading enabled for "${sampleTeams[sport][index].name}"\n• Strategy: Arbitrage + Edge Detection\n• Max per trade: $${settings.perTradeMax}\n• Will auto-cashout at +${settings.takeProfit}% or stop-loss at -${settings.stopLoss}%`);
  }, 800);
}

function addPosition(sport, index) {
  addChatMessage('user', `Add position: ${sampleTeams[sport][index].name}`);
  setTimeout(() => {
    addChatMessage('bot', `✅ Position added. Monitoring for entry signal...`);
  }, 500);
}

function cashOut(sport, index) {
  addChatMessage('user', `Cash out: ${sampleTeams[sport][index].name}`);
  setTimeout(() => {
    const pnl = (Math.random() * 20 - 5).toFixed(2);
    addChatMessage('bot', `✅ Cashout complete. P&L: $${pnl > 0 ? '+' : ''}${pnl} (${(pnl/10*100).toFixed(1)}%)`);
  }, 600);
}

function autoTradeAll() {
  if (!agentEnabled) {
    addChatMessage('bot-error', '⚠️ Enable the agent first!');
    return;
  }
  addChatMessage('user', 'AUTO ALL: Scan all markets');
  setTimeout(() => {
    addChatMessage('bot', `🤖 Scanning all ${currentSport.toUpperCase()} markets for arbitrage opportunities...\n\nFound ${Math.floor(Math.random()*5+1)} opportunities above threshold.\nStarting auto-trade on highest confidence plays.`);
  }, 1000);
}

function scanMarkets() {
  addChatMessage('user', `Scan all ${currentSport.toUpperCase()} markets`);
  setTimeout(() => {
    addChatMessage('bot', `🔍 Scanned ${sampleTeams[currentSport]?.length || 3} markets.\n\nOpportunities found:\n• Yankees vs Red Sox: YES @ $0.62 (edge: +1.8%)\n• Dodgers vs Giants: Over 8.5 @ $0.54 (edge: +1.2%)\n\nDaily budget used: $${Math.floor(Math.random()*30+10)}/$${settings.dailyBudget}`);
  }, 1500);
}

// ===== SETTINGS =====
function updateSliderDisplay(id) {
  const slider = document.getElementById(id);
  const displayId = id + 'Display';
  const display = document.getElementById(displayId);
  if (display) display.textContent = slider.value;
  
  // Update settings state
  const keyMap = { dailyBudget: 'dailyBudget', perTradeMax: 'perTradeMax', lossLimit: 'lossLimit', stopLoss: 'stopLoss', takeProfit: 'takeProfit' };
  settings[keyMap[id]] = parseInt(slider.value);
}

function saveSettings() {
  settings.lmEndpoint = document.getElementById('lmEndpoint').value;
  settings.pmClientID = document.getElementById('pmClientID').value;
  settings.pmAudience = document.getElementById('pmAudience').value;
  
  // Save to localStorage for persistence
  localStorage.setItem('polyagent-settings', JSON.stringify(settings));
  addChatMessage('bot', '✅ Settings saved! Changes will apply on next agent start.');
}

function loadSettings() {
  const saved = localStorage.getItem('polyagent-settings');
  if (saved) {
    settings = { ...settings, ...JSON.parse(saved) };
    
    // Apply to UI
    document.getElementById('dailyBudget').value = settings.dailyBudget;
    document.getElementById('perTradeMax').value = settings.perTradeMax;
    document.getElementById('lossLimit').value = settings.lossLimit;
    document.getElementById('stopLoss').value = settings.stopLoss;
    document.getElementById('takeProfit').value = settings.takeProfit;
    
    updateSliderDisplay('dailyBudget');
    updateSliderDisplay('perTradeMax');
    updateSliderDisplay('lossLimit');
    updateSliderDisplay('stopLoss');
    updateSliderDisplay('takeProfit');
  }
}

// ===== AGENT CONTROL =====
function updateAgentStatus(enabled) {
  agentEnabled = enabled;
  const statusEl = document.getElementById('agentStatus');
  if (enabled) {
    statusEl.innerHTML = '<span class="status-dot online"></span> Agent: Online';
  } else {
    statusEl.innerHTML = '<span class="status-dot offline"></span> Agent: Offline';
  }
}

function stopAgentUI() {
  addChatMessage('user', 'Stop agent');
  if (ipcRenderer) ipcRenderer.send('agent-toggle', false);
  updateAgentStatus(false);
  addChatMessage('bot', '⏹ Agent stopped.');
}

function connectToAgent() {
  const endpoint = document.getElementById('apiEndpoint').value;
  addChatMessage('bot', `🔗 Connected to ${endpoint}\n\nReady to scan markets. Click Enable in Options menu to start the agent.`);
}

// ===== AUTH MODAL =====
function showAuthTab(tab) {
  document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  
  if (tab === 'signin') {
    document.getElementById('signinForm').style.display = 'block';
    document.getElementById('signupForm').style.display = 'none';
  } else {
    document.getElementById('signinForm').style.display = 'none';
    document.getElementById('signupForm').style.display = 'block';
  }
}

function handleSignIn(e) {
  e.preventDefault();
  const user = document.getElementById('signInUser').value;
  if (user) {
    document.getElementById('authModal').style.display = 'none';
    addChatMessage('bot', `✅ Welcome back, ${user}! PolyAgent is ready.\n\nSet your budget in Settings and click Enable to start trading.`);
  }
}

function handleSignUp(e) {
  e.preventDefault();
  const email = document.getElementById('signUpEmail').value;
  if (email) {
    document.getElementById('authModal').style.display = 'none';
    addChatMessage('bot', `✅ Account created for ${email}!\n\nWelcome to PolyAgent. Set your budget and start trading.`);
  }
}

// ===== IPC (Electron only) =====
if (ipcRenderer) {
  // Listen for agent status updates from main process
  ipcRenderer.on('agent-status', (event, data) => {
    updateAgentStatus(data.enabled);
  });
}
