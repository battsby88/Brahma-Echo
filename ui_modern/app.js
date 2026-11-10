/**
 * Brahma Echo — Modern Claymorphism UI
 * Zero dependencies, vanilla ES modules, WebSocket integration
 */

// ==========================================================================
// State Management
// ==========================================================================
const State = {
  theme: 'light',
  sidebarCollapsed: false,
  ws: null,
  wsUrl: 'ws://localhost:8000/ws',
  reconnectInterval: 5000,
  autoReconnect: true,
  connected: false,
  metrics: {
    cpu: [],
    ram: [],
    voice: [],
    tools: []
  },
  toolLogs: [],
  skills: [],
  currentPage: 'dashboard',
  activeChart: 'cpu',
  voiceState: 'idle',
  listening: false,
  reducedMotion: false,
  voiceResponse: true,
  offlineCache: true
};

// ==========================================================================
// Utility Functions
// ==========================================================================
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

const fmtTime = (ms) => `${ms < 1000 ? ms + 'ms' : (ms / 1000).toFixed(1) + 's'}`;
const fmtPercent = (n) => `${Math.round(n)}%`;
const nowISO = () => new Date().toISOString();
const nowTime = () => new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

function debounce(fn, ms) {
  let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function throttle(fn, ms) {
  let last = 0; return (...args) => { const now = Date.now(); if (now - last >= ms) { last = now; fn(...args); } };
}

function createSVG(html) {
  const div = document.createElement('div');
  div.innerHTML = html.trim();
  return div.firstElementChild;
}

function toast(message, type = 'info', duration = 3000) {
  const container = $('#toastContainer');
  const el = document.createElement('div');
  el.className = `clay-card tooltip`;
  el.style.cssText = 'padding:12px 16px;min-width:280px;max-width:360px;display:flex;align-items:center;gap:12px;animation:slideIn 0.3s;';
  el.innerHTML = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;color:${type === 'error' ? 'var(--accent-error)' : type === 'success' ? 'var(--accent-success)' : 'var(--accent-primary)'};">
      ${type === 'error' ? '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>' :
        type === 'success' ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>' :
        '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>'}
    </svg>
    <span style="flex:1;font-size:0.875rem;">${message}</span>
  `;
  container.appendChild(el);
  setTimeout(() => { el.style.animation = 'slideIn 0.3s reverse'; setTimeout(() => el.remove(), 300); }, duration);
}

// ==========================================================================
// Theme Management
// ==========================================================================
const Theme = {
  init() {
    const saved = localStorage.getItem('theme');
    const system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    this.apply(saved || system);
    $('#themeSelect').value = saved || 'system';
  },
  apply(theme) {
    if (theme === 'system') {
      theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', theme);
    State.theme = theme;
    localStorage.setItem('theme', theme);
    this.updateIcons();
  },
  updateIcons() {
    $('.icon-sun').style.display = State.theme === 'dark' ? 'block' : 'none';
    $('.icon-moon').style.display = State.theme === 'light' ? 'block' : 'none';
  },
  toggle() {
    this.apply(State.theme === 'light' ? 'dark' : 'light');
  }
};

// ==========================================================================
// WebSocket Connection
// ==========================================================================
const WS = {
  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    try {
      this.ws = new WebSocket(State.wsUrl);
      this.ws.binaryType = 'arraybuffer';
      this.ws.onopen = () => this.onOpen();
      this.ws.onmessage = (e) => this.onMessage(e);
      this.ws.onclose = () => this.onClose();
      this.ws.onerror = (e) => this.onError(e);
    } catch (e) {
      console.error('WS connect failed:', e);
      this.scheduleReconnect();
    }
  },
  onOpen() {
    State.connected = true;
    UI.updateConnectionStatus(true);
    this.send({ type: 'subscribe', channels: ['metrics', 'tools', 'voice', 'system'] });
    toast('Connected to Brahma Echo', 'success');
  },
  onMessage(event) {
    try {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    } catch (e) {
      console.error('WS parse error:', e);
    }
  },
  onClose() {
    State.connected = false;
    UI.updateConnectionStatus(false);
    if (State.autoReconnect) this.scheduleReconnect();
  },
  onError(err) {
    console.error('WS error:', err);
    toast('Connection error', 'error');
  },
  scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      toast('Reconnecting…', 'info');
      this.connect();
    }, State.reconnectInterval);
  },
  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  },
  handleMessage(data) {
    switch (data.type) {
      case 'metrics':
        Metrics.update(data.payload);
        break;
      case 'tool_result':
        ToolLog.add(data.payload);
        break;
      case 'voice_state':
        State.voiceState = data.payload.state;
        UI.updateVoiceState(data.payload);
        break;
      case 'skills':
        State.skills = data.payload;
        Skills.render();
        break;
      case 'system':
        UI.updateSystemInfo(data.payload);
        break;
    }
  }
};

// ==========================================================================
// Metrics / Visualizer
// ==========================================================================
const Metrics = {
  maxPoints: 60,
  update(payload) {
    const t = Date.now();
    if (payload.cpu !== undefined) {
      State.metrics.cpu.push({ t, v: payload.cpu });
      if (State.metrics.cpu.length > this.maxPoints) State.metrics.cpu.shift();
    }
    if (payload.ram !== undefined) {
      State.metrics.ram.push({ t, v: payload.ram });
      if (State.metrics.ram.length > this.maxPoints) State.metrics.ram.shift();
    }
    if (payload.voice !== undefined) {
      State.metrics.voice.push({ t, v: payload.voice });
      if (State.metrics.voice.length > this.maxPoints) State.metrics.voice.shift();
    }
    if (payload.tool !== undefined) {
      State.metrics.tools.push({ t, tool: payload.tool, duration: payload.duration });
      if (State.metrics.tools.length > 50) State.metrics.tools.shift();
    }
    Visualizer.render(State.activeChart);
    UI.updateStats();
  }
};

// ==========================================================================
// Visualizer 2D (SVG Charts)
// ==========================================================================
const Visualizer = {
  colors: {
    cpu: 'var(--accent-primary)',
    ram: 'var(--accent-secondary)',
    voice: 'var(--accent-warning)',
    tools: 'var(--accent-success)'
  },
  render(chart) {
    State.activeChart = chart;
    $$('.chart-btn').forEach(b => b.classList.toggle('active', b.dataset.chart === chart));
    const canvas = $('#visualizerCanvas');
    const data = State.metrics[chart] || [];
    if (!data.length) {
      canvas.innerHTML = '<div class="empty-state" style="height:100%;"><svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg><p class="empty-state-title">No data yet</p><p class="empty-state-desc">Waiting for metrics from Brahma Echo</p></div>';
      return;
    }
    canvas.innerHTML = this.renderChart(chart, data);
  },
  renderChart(type, data) {
    const w = 100%, h = 180;
    const padding = { top: 20, right: 20, bottom: 30, left: 50 };
    const innerW = 100 - (padding.left + padding.right) / (w / 100);
    const innerH = h - padding.top - padding.bottom;
    const maxV = type === 'voice' ? 1 : 100;
    const color = this.colors[type];

    if (type === 'tools') {
      return this.renderTimeline(data, color, innerW, innerH, padding);
    }
    if (type === 'voice') {
      return this.renderWaveform(data, color, innerW, innerH, padding);
    }
    return this.renderSparkline(data, color, maxV, innerW, innerH, padding);
  },
  renderSparkline(data, color, maxV, innerW, innerH, padding) {
    const points = data.map((d, i) => {
      const x = padding.left + (i / (data.length - 1 || 1)) * innerW;
      const y = padding.top + innerH - (d.v / maxV) * innerH;
      return `${x},${y}`;
    }).join(' ');
    const areaPoints = [
      `${padding.left},${padding.top + innerH}`,
      points,
      `${padding.left + innerW},${padding.top + innerH}`
    ].join(' ');

    return `
      <svg class="visualizer-svg" viewBox="0 0 100 ${h}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="sparkline-gradient-${color.replace(/[^a-z]/g,'')}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${color}" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <polygon class="sparkline-area" points="${areaPoints}" fill="url(#sparkline-gradient-${color.replace(/[^a-z]/g,'')})"></polygon>
        <polyline class="sparkline" points="${points}" stroke="${color}"></polyline>
        ${data.map((d, i) => {
          const x = padding.left + (i / (data.length - 1 || 1)) * innerW;
          const y = padding.top + innerH - (d.v / maxV) * innerH;
          return `<circle class="sparkline-point" cx="${x}" cy="${y}" fill="${color}"></circle>`;
        }).join('')}
        <text x="50" y="${padding.top + 16}" text-anchor="middle" font-family="var(--clay-font-mono)" font-size="14" fill="var(--text-primary)" font-weight="700">${Math.round(data[data.length - 1]?.v || 0)}%</text>
        <text x="50" y="${h - 6}" text-anchor="middle" font-size="10" fill="var(--text-tertiary)">${type.toUpperCase()}</text>
      </svg>
    `;
  },
  renderWaveform(data, color, innerW, innerH, padding) {
    const bars = data.map((d, i) => {
      const x = padding.left + (i / (data.length - 1 || 1)) * innerW;
      const h = Math.abs(d.v) * innerH;
      const y = padding.top + innerH - h;
      return `<rect class="waveform-bar${d.v > 0.5 ? ' active' : ''}" x="${x}" y="${y}" width="${Math.max(2, innerW / data.length - 1)}" height="${h}" fill="${color}"></rect>`;
    }).join('');
    return `
      <svg class="visualizer-svg" viewBox="0 0 100 ${h}" preserveAspectRatio="none">
        ${bars}
        <text x="50" y="${padding.top + 16}" text-anchor="middle" font-family="var(--clay-font-mono)" font-size="14" fill="var(--text-primary)" font-weight="700">VOICE</text>
        <text x="50" y="${h - 6}" text-anchor="middle" font-size="10" fill="var(--text-tertiary)">WAVEFORM</text>
      </svg>
    `;
  },
  renderTimeline(data, color, innerW, innerH, padding) {
    const items = data.slice(-10).map((d, i) => {
      const x = padding.left + (i / 9) * innerW;
      const y = padding.top + innerH * 0.5;
      return `
        <g transform="translate(${x},${y})">
          <circle r="6" fill="${color}" opacity="0.2"></circle>
          <circle r="3" fill="${color}"></circle>
          <text x="0" y="${innerH * 0.5 + 20}" text-anchor="middle" font-size="8" fill="var(--text-tertiary)">${d.tool}</text>
          <text x="0" y="${innerH * 0.5 + 32}" text-anchor="middle" font-family="var(--clay-font-mono)" font-size="7" fill="var(--text-tertiary)">${fmtTime(d.duration)}</text>
        </g>
      `;
    }).join('');
    return `
      <svg class="visualizer-svg" viewBox="0 0 100 ${h}" preserveAspectRatio="none">
        <line x1="${padding.left}" y1="${padding.top + innerH * 0.5}" x2="${padding.left + innerW}" y2="${padding.top + innerH * 0.5}" stroke="var(--border-subtle)" stroke-width="1" stroke-dasharray="4,4"></line>
        ${items}
        <text x="50" y="${padding.top + 16}" text-anchor="middle" font-family="var(--clay-font-mono)" font-size="14" fill="var(--text-primary)" font-weight="700">${data.length} tools</text>
        <text x="50" y="${h - 6}" text-anchor="middle" font-size="10" fill="var(--text-tertiary)">TIMELINE</text>
      </svg>
    `;
  },
  // Full page charts
  renderFull(id, type) {
    const canvas = $(`#${id}`);
    const data = State.metrics[type] || [];
    if (!data.length) {
      canvas.innerHTML = '<div class="empty-state" style="height:100%;"><svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg><p class="empty-state-title">No data</p></div>';
      return;
    }
    canvas.innerHTML = this.renderChart(type, data);
  }
};

// ==========================================================================
// Tool Log Component
// ==========================================================================
const ToolLog = {
  maxEntries: 100,
  add(entry) {
    entry.id = Date.now() + Math.random();
    entry.time = nowTime();
    State.toolLogs.unshift(entry);
    if (State.toolLogs.length > this.maxEntries) State.toolLogs.pop();
    this.render();
    this.renderFull();
  },
  render() {
    const list = $('#toolLogList');
    const empty = $('#emptyLogs');
    if (State.toolLogs.length === 0) {
      empty.hidden = false;
      list.innerHTML = '';
      list.appendChild(empty);
      return;
    }
    empty.hidden = true;
    list.innerHTML = State.toolLogs.slice(0, 20).map(e => this.renderEntry(e)).join('');
  },
  renderFull() {
    const list = $('#fullToolLogList');
    if (!list) return;
    if (State.toolLogs.length === 0) {
      list.innerHTML = '<div class="empty-state" style="height:100%;padding:48px;"><svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg><p class="empty-state-title">No tool executions</p></div>';
      return;
    }
    list.innerHTML = State.toolLogs.map(e => this.renderEntry(e)).join('');
  },
  renderEntry(e) {
    const success = e.success !== false;
    return `
      <article class="tool-log-entry" data-id="${e.id}">
        <time class="tool-log-time">${e.time}</time>
        <div class="tool-log-content">
          <div class="tool-log-tool">
            <svg class="tool-log-tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
            <span>${e.tool}</span>
            ${e.args ? `<span class="tool-log-args">${JSON.stringify(e.args).slice(0, 80)}</span>` : ''}
          </div>
          ${e.error ? `<div class="tool-log-result error">Error: ${e.error}</div>` : ''}
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <span class="tool-log-result ${success ? 'success' : 'error'}">${success ? 'Success' : 'Failed'}</span>
          <span class="tool-log-duration">${fmtTime(e.duration || 0)}</span>
        </div>
      </article>
    `;
  },
  clear() {
    State.toolLogs = [];
    this.render();
    this.renderFull();
  }
};

// ==========================================================================
// Command Palette
// ==========================================================================
const CommandPalette = {
  items: [],
  open: false,
  init() {
    this.buildItems();
    $('#commandPaletteTrigger').addEventListener('click', () => this.toggle());
    $('#commandPaletteOverlay').addEventListener('click', (e) => { if (e.target === e.currentTarget) this.close(); });
    $('#commandPaletteInput').addEventListener('input', debounce((e) => this.filter(e.target.value), 80));
    $('#commandPaletteInput').addEventListener('keydown', (e) => this.onKeydown(e));
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); this.toggle(); }
      if (e.key === 'Escape') this.close();
    });
  },
  buildItems() {
    // Tools from TOOL_DECLARATIONS (would be fetched from backend)
    const tools = [
      { id: 'blender_control', title: 'Blender: New Scene', desc: 'Create a new Blender scene', icon: 'cube', action: () => ToolExecutor.execute('blender_control', { action: 'scene_new' }) },
      { id: 'blender_control', title: 'Blender: Add Cube', desc: 'Add a cube primitive', icon: 'cube', action: () => ToolExecutor.execute('blender_control', { action: 'object_add', object_type: 'CUBE' }) },
      { id: 'blender_control', title: 'Blender: Render', desc: 'Render current scene (Cycles)', icon: 'camera', action: () => ToolExecutor.execute('blender_control', { action: 'render', engine: 'CYCLES' }) },
      { id: 'cinema4d_control', title: 'Cinema 4D: Add Cube', desc: 'Add cube primitive', icon: 'cube', action: () => ToolExecutor.execute('cinema4d_control', { action: 'add_primitive', primitive_type: 'cube' }) },
      { id: 'cinema4d_control', title: 'Cinema 4D: MoGraph Cloner', desc: 'Create MoGraph cloner on selected object', icon: 'grid', action: () => ToolExecutor.execute('cinema4d_control', { action: 'mograph_cloner' }) },
      { id: 'cinema4d_control', title: 'Cinema 4D: Redshift Materials', desc: 'Inspect Redshift materials', icon: 'gem', action: () => ToolExecutor.execute('cinema4d_control', { action: 'inspect_redshift_materials' }) },
      { id: 'autocad_control', title: 'AutoCAD: Test Connection', desc: 'Ping AutoCAD MCP', icon: 'link', action: () => ToolExecutor.execute('autocad_control', { action: 'ping' }) },
      { id: 'autocad_control', title: 'AutoCAD: List Tools', desc: 'List all 240+ MCP tools', icon: 'list', action: () => ToolExecutor.execute('autocad_control', { action: 'list_tools' }) },
      { id: 'autocad_control', title: 'AutoCAD: Update Keynote (LT)', desc: 'Renumber keynote headlessly', icon: 'edit', action: () => ToolExecutor.execute('autocad_control', { action: 'lt_update_keynote' }) },
      { id: 'replica_pipeline', title: 'Replica: Full Pipeline', desc: 'Run all 11 skills on target app', icon: 'git-branch', action: () => ToolExecutor.execute('replica_pipeline', { action: 'full_pipeline' }) },
      { id: 'replica_pipeline', title: 'Replica: Recon', desc: 'Reverse-engineer app screens/flows', icon: 'search', action: () => ToolExecutor.execute('replica_pipeline', { action: 'recon' }) },
      { id: 'system_diagnostics', title: 'System: Diagnostics', desc: 'CPU, RAM, battery, disk', icon: 'monitor', action: () => ToolExecutor.execute('system_diagnostics', { action: 'status' }) },
      { id: 'system_diagnostics', title: 'System: RAM Hogs', desc: 'Find top memory consumers', icon: 'memory', action: () => ToolExecutor.execute('system_diagnostics', { action: 'ram_hogs' }) },
      { id: 'system_diagnostics', title: 'System: Brightness', desc: 'Set display brightness', icon: 'sun', action: () => ToolExecutor.execute('system_diagnostics', { action: 'brightness', level: 80 }) },
      { id: 'google_workspace', title: 'Gmail: Unread', desc: 'Check unread emails', icon: 'mail', action: () => ToolExecutor.execute('google_workspace', { service: 'gmail', action: 'unread' }) },
      { id: 'google_workspace', title: 'Calendar: Today', desc: 'List today\'s events', icon: 'calendar', action: () => ToolExecutor.execute('google_workspace', { service: 'calendar', action: 'list' }) },
      { id: 'google_workspace', title: 'Drive: Search', desc: 'Search Google Drive', icon: 'database', action: () => ToolExecutor.execute('google_workspace', { service: 'drive', action: 'search' }) },
      { id: 'browser_control', title: 'Browser: Navigate', desc: 'Go to URL', icon: 'globe', action: () => ToolExecutor.execute('browser_control', { action: 'go_to' }) },
      { id: 'browser_control', title: 'Browser: Screenshot', desc: 'Take page screenshot', icon: 'camera', action: () => ToolExecutor.execute('browser_control', { action: 'screenshot' }) },
      { id: 'file_controller', title: 'Files: Organize Desktop', desc: 'Sort desktop by type/date', icon: 'folder', action: () => ToolExecutor.execute('smart_organizer', { action: 'organize', target: 'desktop' }) },
      { id: 'voice_start', title: 'Voice: Start Listening', desc: 'Activate voice recognition', icon: 'mic', action: () => Voice.toggle() },
    ];

    // Navigation
    const pages = [
      { id: 'nav-dashboard', title: 'Go to Dashboard', desc: 'System overview', icon: 'layout', action: () => UI.navigate('dashboard') },
      { id: 'nav-skills', title: 'Go to Skills', desc: 'All tools & skills', icon: 'box', action: () => UI.navigate('skills') },
      { id: 'nav-visualizer', title: 'Go to Visualizer', desc: 'Charts & metrics', icon: 'bar-chart', action: () => UI.navigate('visualizer') },
      { id: 'nav-tools', title: 'Go to 3D/CAD', desc: 'Blender, C4D, AutoCAD', icon: 'cube', action: () => UI.navigate('tools') },
      { id: 'nav-replica', title: 'Go to Replica', desc: 'App cloning pipeline', icon: 'git-branch', action: () => UI.navigate('replica') },
      { id: 'nav-logs', title: 'Go to Logs', desc: 'Tool execution history', icon: 'file-text', action: () => UI.navigate('logs') },
      { id: 'nav-settings', title: 'Go to Settings', desc: 'Preferences', icon: 'settings', action: () => UI.navigate('settings') },
    ];

    // Settings
    const settings = [
      { id: 'theme-toggle', title: 'Toggle Theme', desc: 'Switch light/dark', icon: 'sun', action: () => Theme.toggle() },
      { id: 'sidebar-toggle', title: 'Toggle Sidebar', desc: 'Collapse/expand', icon: 'sidebar', action: () => UI.toggleSidebar() },
    ];

    this.items = [...tools, ...pages, ...settings].map((item, i) => ({
      ...item,
      shortcut: this.getShortcut(item.id),
      section: item.id.startsWith('nav-') ? 'Navigation' : item.id.includes('_') ? 'Tools' : 'Settings'
    }));
  },
  getShortcut(id) {
    const map = {
      'theme-toggle': '⌘⇧L',
      'sidebar-toggle': '⌘B',
      'voice_start': 'Space',
      'blender_control': 'B',
      'cinema4d_control': 'C',
      'autocad_control': 'A',
    };
    return map[id] || '';
  },
  filter(query) {
    const q = query.toLowerCase().trim();
    const filtered = q ? this.items.filter(i =>
      i.title.toLowerCase().includes(q) ||
      i.desc.toLowerCase().includes(q) ||
      i.id.toLowerCase().includes(q)
    ) : this.items;
    this.render(filtered);
  },
  render(items) {
    const list = $('#commandPaletteList');
    const empty = $('#commandPaletteEmpty');
    if (!items.length) {
      list.innerHTML = '';
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    const sections = {};
    items.forEach(item => {
      (sections[item.section] = sections[item.section] || []).push(item);
    });
    list.innerHTML = Object.entries(sections).map(([section, items]) => `
      <div class="command-palette-section">
        <div class="command-palette-section-title">${section}</div>
        ${items.map((item, i) => `
          <button class="command-palette-item" data-id="${item.id}" role="option" aria-selected="false">
            <svg class="command-palette-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${this.getIcon(item.icon)}</svg>
            <div class="command-palette-item-content">
              <span class="command-palette-item-title">${item.title}</span>
              <span class="command-palette-item-desc">${item.desc}</span>
            </div>
            ${item.shortcut ? `<span class="command-palette-item-shortcut">${item.shortcut}</span>` : ''}
          </button>
        `).join('')}
      </div>
    `).join('');
    this.bindItems();
  },
  bindItems() {
    $$('.command-palette-item').forEach((btn, i) => {
      btn.addEventListener('click', () => this.execute(btn.dataset.id));
      btn.addEventListener('mouseenter', () => this.highlight(i));
    });
  },
  highlight(index) {
    $$('.command-palette-item').forEach((b, i) => b.classList.toggle('highlighted', i === index));
  },
  execute(id) {
    const item = this.items.find(i => i.id === id);
    if (item) {
      item.action();
      this.close();
      toast(`Executed: ${item.title}`, 'success');
    }
  },
  getIcon(name) {
    const icons = {
      cube: '<polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"></polygon><line x1="12" y1="22" x2="12" y2="15.5"></line><polyline points="22 8.5 12 15.5 2 8.5"></polyline>',
      camera: '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="12" r="4"></circle>',
      grid: '<rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect>',
      gem: '<polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"></polygon><line x1="12" y1="22" x2="12" y2="15.5"></line><polyline points="22 8.5 12 15.5 2 8.5"></polyline>',
      link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>',
      'git-branch': '<line x1="6" y1="3" x2="6" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path>',
      monitor: '<rect x="2" y="3" width="20" height="14" rx="2"></rect><path d="M8 21h8M12 17v4"></path>',
      memory: '<rect x="2" y="3" width="20" height="14" rx="2"></rect><path d="M8 21h8M12 17v4"></path>',
      sun: '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>',
      mail: '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline>',
      calendar: '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line>',
      database: '<ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>',
      globe: '<circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>',
      folder: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>',
      search: '<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>',
      edit: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>',
      mic: '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line>',
      layout: '<rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect>',
      box: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line>',
      'bar-chart': '<line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line>',
      settings: '<circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>',
      sidebar: '<line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line>'
    };
    return icons[name] || icons.cube;
  },
  toggle() {
    this.open ? this.close() : this.openPanel();
  },
  openPanel() {
    this.open = true;
    $('#commandPaletteOverlay').classList.add('open');
    $('#commandPaletteInput').value = '';
    this.filter('');
    setTimeout(() => $('#commandPaletteInput').focus(), 50);
  },
  close() {
    this.open = false;
    $('#commandPaletteOverlay').classList.remove('open');
    $('#commandPaletteInput').blur();
  },
  onKeydown(e) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const items = $$('.command-palette-item');
      const current = items.findIndex(b => b.classList.contains('highlighted'));
      const next = current + (e.key === 'ArrowDown' ? 1 : -1);
      if (next >= 0 && next < items.length) this.highlight(next);
    } else if (e.key === 'Enter') {
      const highlighted = $('.command-palette-item.highlighted');
      if (highlighted) this.execute(highlighted.dataset.id);
    }
  }
};

// ==========================================================================
// Skills Renderer
// ==========================================================================
const Skills = {
  render() {
    const grid = $('#skillsGrid');
    if (!grid) return;
    if (!State.skills.length) {
      grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1;"><svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg><p class="empty-state-title">Loading skills…</p><p class="empty-state-desc">Connect to Brahma Echo to fetch skills</p></div>';
      return;
    }
    grid.innerHTML = State.skills.map(s => `
      <article class="skill-card">
        <div class="skill-header">
          <div class="skill-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg></div>
          <div>
            <h3 class="skill-title">${s.name}</h3>
            <p class="skill-desc">${s.description}</p>
          </div>
        </div>
        <div class="skill-tags">
          ${(s.frontmatter?.category ? [s.frontmatter.category] : []).concat(s.frontmatter?.keywords?.slice(0, 4) || []).map(k => `<span class="skill-tag">${k}</span>`).join('')}
        </div>
        <div class="skill-actions">
          <button class="clay-button clay-button--primary" data-skill="${s.name}" data-action="run">Run Skill</button>
          <button class="clay-button clay-button--ghost" data-skill="${s.name}" data-action="view">View Details</button>
        </div>
      </article>
    `).join('');
  }
};

// ==========================================================================
// Tool Executor (calls backend via WebSocket)
// ==========================================================================
const ToolExecutor = {
  async execute(tool, args) {
    const start = Date.now();
    ToolLog.add({ tool, args, duration: 0, pending: true });
    try {
      // Send via WebSocket to backend
      WS.send({
        type: 'execute_tool',
        payload: { tool, args, requestId: Date.now() }
      });
      // Backend will send tool_result via WS
    } catch (e) {
      ToolLog.add({ tool, args, duration: Date.now() - start, success: false, error: e.message });
      toast(`Failed: ${e.message}`, 'error');
    }
  }
};

// ==========================================================================
// Voice Control
// ==========================================================================
const Voice = {
  listening: false,
  toggle() {
    this.listening = !this.listening;
    $('#listenToggle').classList.toggle('pressed', this.listening);
    $('#quickListen').textContent = this.listening ? 'Stop Listening' : 'Start Listening';
    WS.send({ type: 'voice', payload: { action: this.listening ? 'start' : 'stop' } });
    toast(this.listening ? 'Listening…' : 'Stopped listening', this.listening ? 'info' : 'success');
  }
};

// ==========================================================================
// UI Controller
// ==========================================================================
const UI = {
  init() {
    this.bindEvents();
    this.loadSettings();
    Theme.init();
    CommandPalette.init();
    WS.connect();
    this.startVisualizerLoop();
  },
  bindEvents() {
    // Sidebar
    $('#sidebarToggle').addEventListener('click', () => this.toggleSidebar());
    $('#sidebarCollapse').addEventListener('click', () => this.toggleSidebar());

    // Navigation
    $$('.nav-item').forEach(btn => {
      btn.addEventListener('click', () => this.navigate(btn.dataset.page));
    });

    // Theme
    $('#themeToggle').addEventListener('click', () => Theme.toggle());
    $('#themeSelect').addEventListener('change', (e) => Theme.apply(e.target.value));

    // Voice
    $('#listenToggle').addEventListener('click', () => Voice.toggle());
    $('#quickListen').addEventListener('click', () => Voice.toggle());

    // Tool buttons (delegated)
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-tool]');
      if (btn) {
        const tool = btn.dataset.tool;
        const action = btn.dataset.action ? JSON.parse(btn.dataset.action) : {};
        ToolExecutor.execute(tool, action);
      }
      const skillBtn = e.target.closest('[data-skill]');
      if (skillBtn) {
        toast(`Skill: ${skillBtn.dataset.skill} - ${skillBtn.dataset.action}`, 'info');
      }
    });

    // Chart buttons
    $$('.chart-btn').forEach(btn => {
      btn.addEventListener('click', () => Visualizer.render(btn.dataset.chart));
    });

    // Tool log
    $('#clearLogs').addEventListener('click', () => ToolLog.clear());
    $('#clearAllLogs').addEventListener('click', () => ToolLog.clear());
    $('#exportLogs').addEventListener('click', () => this.exportLogs());

    // Replica
    $('#runFullPipeline').addEventListener('click', () => {
      const target = $('#replicaTarget').value.trim();
      if (!target) { toast('Enter target app', 'error'); return; }
      ToolExecutor.execute('replica_pipeline', { action: 'full_pipeline', target_app: target });
    });

    // Settings
    $('#sidebarCollapsedDefault').addEventListener('change', (e) => this.saveSetting('sidebarCollapsed', e.target.checked));
    $('#reducedMotion').addEventListener('change', (e) => this.saveSetting('reducedMotion', e.target.checked));
    $('#autoReconnect').addEventListener('change', (e) => { State.autoReconnect = e.target.checked; this.saveSetting('autoReconnect', e.target.checked); });
    $('#reconnectInterval').addEventListener('change', (e) => { State.reconnectInterval = e.target.value * 1000; this.saveSetting('reconnectInterval', State.reconnectInterval); });
    $('#wsUrl').addEventListener('change', (e) => { State.wsUrl = e.target.value; this.saveSetting('wsUrl', e.target.value); WS.connect(); });
    $('#offlineCache').addEventListener('change', (e) => { State.offlineCache = e.target.checked; this.saveSetting('offlineCache', e.target.checked); });
    $('#telemetry').addEventListener('change', (e) => this.saveSetting('telemetry', e.target.checked));
    $('#voiceResponse').addEventListener('change', (e) => { State.voiceResponse = e.target.checked; this.saveSetting('voiceResponse', e.target.checked); });
    $('#wakeWord').addEventListener('change', (e) => this.saveSetting('wakeWord', e.target.value));
    $('#voiceLang').addEventListener('change', (e) => this.saveSetting('voiceLang', e.target.value));
    $('#clearAllData').addEventListener('click', () => this.clearAllData());

    // Reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.documentElement.style.setProperty('--clay-transition-fast', '0.01ms');
      document.documentElement.style.setProperty('--clay-transition-normal', '0.01ms');
      document.documentElement.style.setProperty('--clay-transition-slow', '0.01ms');
    }
  },
  navigate(page) {
    $$('.page').forEach(p => p.hidden = true);
    $$('.nav-item').forEach(b => b.classList.remove('active'));
    $(`#page-${page}`)?.hidden = false;
    $(`.nav-item[data-page="${page}"]`)?.classList.add('active');
    State.currentPage = page;
    if (page === 'visualizer') {
      ['cpuChart', 'ramChart', 'voiceChart', 'toolsChart'].forEach(id => Visualizer.renderFull(id, id.replace('Chart', '')));
    }
    if (page === 'skills') Skills.render();
    if (page === 'replica') this.renderReplicaSkills();
  },
  renderReplicaSkills() {
    const grid = $('#replicaSkillsGrid');
    if (!grid) return;
    const skills = ['recon', 'architect', 'design', 'build', 'backend', 'test', 'diff', 'entrepreneur', 'brand', 'launch', 'deploy'];
    grid.innerHTML = skills.map(s => `
      <button class="clay-button clay-button--ghost" style="flex:1;justify-content:center;" data-tool="replica_pipeline" data-action='{"action":"${s}"}'>${s}</button>
    `).join('');
  },
  toggleSidebar() {
    State.sidebarCollapsed = !State.sidebarCollapsed;
    $('#appShell').classList.toggle('sidebar-collapsed', State.sidebarCollapsed);
    this.saveSetting('sidebarCollapsed', State.sidebarCollapsed);
  },
  updateConnectionStatus(connected) {
    const dot = $('#statusDot');
    const text = $('#statusText');
    const reconnect = $('#reconnectBtn');
    if (connected) {
      dot.className = 'status-dot connected';
      text.textContent = 'Connected';
      reconnect.hidden = true;
    } else {
      dot.className = 'status-dot error';
      text.textContent = 'Disconnected';
      reconnect.hidden = false;
    }
  },
  updateVoiceState(payload) {
    const state = payload.state;
    $('#voiceState').textContent = state.charAt(0).toUpperCase() + state.slice(1);
    $('#voiceTrend').className = `stat-trend ${state === 'listening' ? 'up' : state === 'speaking' ? 'neutral' : 'neutral'}`;
    $('#voiceTrend').textContent = state === 'listening' ? '● LIVE' : state === 'speaking' ? '🔊' : '—';
  },
  updateSystemInfo(payload) {
    // Handle system info updates
  },
  updateStats() {
    const cpu = State.metrics.cpu[State.metrics.cpu.length - 1];
    const ram = State.metrics.ram[State.metrics.ram.length - 1];
    if (cpu) {
      $('#cpuValue').textContent = fmtPercent(cpu.v);
      $('#cpuTrend').className = `stat-trend ${cpu.v > 70 ? 'down' : cpu.v > 40 ? 'neutral' : 'up'}`;
      $('#cpuTrend').textContent = cpu.v > 70 ? '⚠ HIGH' : cpu.v > 40 ? '● Normal' : '● Low';
    }
    if (ram) {
      $('#ramValue').textContent = fmtPercent(ram.v);
      $('#ramTrend').className = `stat-trend ${ram.v > 80 ? 'down' : ram.v > 50 ? 'neutral' : 'up'}`;
      $('#ramTrend').textContent = ram.v > 80 ? '⚠ HIGH' : ram.v > 50 ? '● Normal' : '● Low';
    }
    $('#toolsCount').textContent = State.toolLogs.length;
  },
  startVisualizerLoop() {
    setInterval(() => {
      if (State.currentPage === 'dashboard') Visualizer.render(State.activeChart);
      if (State.currentPage === 'visualizer') {
        ['cpuChart', 'ramChart', 'voiceChart', 'toolsChart'].forEach(id => Visualizer.renderFull(id, id.replace('Chart', '')));
      }
    }, 2000);
  },
  exportLogs() {
    const data = JSON.stringify(State.toolLogs, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `brahma-logs-${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast('Logs exported', 'success');
  },
  loadSettings() {
    const saved = JSON.parse(localStorage.getItem('brahma_ui_settings') || '{}');
    State.sidebarCollapsed = saved.sidebarCollapsed || false;
    $('#appShell').classList.toggle('sidebar-collapsed', State.sidebarCollapsed);
    State.reducedMotion = saved.reducedMotion || false;
    State.autoReconnect = saved.autoReconnect !== false;
    State.reconnectInterval = saved.reconnectInterval || 5000;
    State.wsUrl = saved.wsUrl || 'ws://localhost:8000/ws';
    State.offlineCache = saved.offlineCache !== false;
    State.voiceResponse = saved.voiceResponse !== false;
    $('#wsUrl').value = State.wsUrl;
    $('#autoReconnect').checked = State.autoReconnect;
    $('#reconnectInterval').value = State.reconnectInterval / 1000;
    $('#offlineCache').checked = State.offlineCache;
    $('#telemetry').checked = saved.telemetry || false;
    $('#voiceResponse').checked = State.voiceResponse;
    $('#wakeWord').value = saved.wakeWord || 'Brahma Echo';
    $('#voiceLang').value = saved.voiceLang || 'en-US';
  },
  saveSetting(key, value) {
    const saved = JSON.parse(localStorage.getItem('brahma_ui_settings') || '{}');
    saved[key] = value;
    localStorage.setItem('brahma_ui_settings', JSON.stringify(saved));
  },
  clearAllData() {
    if (confirm('Clear all settings, cache, and logs?')) {
      localStorage.clear();
      State.toolLogs = [];
      ToolLog.render();
      ToolLog.renderFull();
      toast('All data cleared. Reload page.', 'success');
      setTimeout(() => location.reload(), 1500);
    }
  },
  updateSystemInfo(payload) {}
};

// ==========================================================================
// Service Worker Registration
// ==========================================================================
if ('serviceWorker' in navigator && State.offlineCache) {
  navigator.serviceWorker.register('sw.js').then(reg => {
    console.log('SW registered:', reg.scope);
  }).catch(err => console.log('SW registration failed:', err));
}

// ==========================================================================
// Initialize
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => UI.init());

// Export for debugging
window.BrahmaUI = { State, UI, WS, Metrics, Visualizer, ToolLog, CommandPalette, Skills, ToolExecutor, Voice, Theme };