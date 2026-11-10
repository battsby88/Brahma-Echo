/**
 * Brahma Echo — Liquid Glassmorphism UI
 * Three-panel layout: Left Nav | Center (Visualizer + Chat) | Right Tools
 * WebSocket integration, chat, voice, command palette
 */

// ==========================================================================
// State Management
// ==========================================================================
const State = {
  theme: 'light',
  leftExpanded: false,
  rightCollapsed: false,
  ws: null,
  wsUrl: 'ws://localhost:8000/ws/modern',
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
  chatMessages: [],
  messageId: 0,
  typing: false,
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

function toast(message, type = 'info', duration = 4000) {
  const container = $('#toastContainer');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `
    <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      ${type === 'error' ? '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>' :
        type === 'success' ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>' :
        type === 'warning' ? '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L21.71 3.86a2 2 0 0 0-3.42-3z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>' :
        '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>'}
    </svg>
    <span class="toast-message">${message}</span>
  `;
  container.appendChild(el);
  setTimeout(() => { 
    el.style.animation = 'toastIn 0.3s reverse'; 
    setTimeout(() => el.remove(), 300); 
  }, duration);
}

// ==========================================================================
// Theme Management
// ==========================================================================
const Theme = {
  init() {
    const saved = localStorage.getItem('theme');
    const system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    this.apply(saved || system);
    $('#themeSelect')?.value = saved || 'system';
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
    const sun = $('.icon-sun');
    const moon = $('.icon-moon');
    if (sun) sun.style.display = State.theme === 'dark' ? 'block' : 'none';
    if (moon) moon.style.display = State.theme === 'light' ? 'block' : 'none';
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
    this.send({ type: 'subscribe', channels: ['metrics', 'tools', 'voice', 'system', 'chat'] });
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
        Chat.addToolResult(data.payload);
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
      case 'chat_message':
        Chat.addMessage(data.payload);
        break;
      case 'chat_response':
        Chat.handleResponse(data.payload);
        break;
    }
  }
};

// ==========================================================================
// Metrics / Visualizer
// ==========================================================================
const Metrics = {
  maxPoints: 80,
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
      if (State.metrics.tools.length > 60) State.metrics.tools.shift();
    }
    Visualizer.render(State.activeChart);
    UI.updateStats();
  }
};

// ==========================================================================
// Visualizer 2D (SVG Charts with Liquid Glass Aesthetic)
// ==========================================================================
const Visualizer = {
  colors: {
    cpu: 'var(--accent-primary)',
    ram: 'var(--accent-secondary)',
    voice: 'var(--accent-warning)',
    tools: 'var(--accent-success)'
  },
  gradients: {
    cpu: 'url(#grad-cpu)',
    ram: 'url(#grad-ram)',
    voice: 'url(#grad-voice)',
    tools: 'url(#grad-tools)'
  },
  render(chart) {
    State.activeChart = chart;
    $$('.chart-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.chart === chart);
      b.setAttribute('aria-pressed', b.dataset.chart === chart);
    });
    const canvas = $('#visualizerCanvas');
    const data = State.metrics[chart] || [];
    if (!data.length) {
      canvas.innerHTML = this.emptyState(chart);
      return;
    }
    canvas.innerHTML = this.renderChart(chart, data);
    this.injectGradients(canvas);
  },
  emptyState(chart) {
    const icons = {
      cpu: '<rect x="2" y="3" width="20" height="14" rx="2"></rect><path d="M8 21h8M12 17v4"></path>',
      ram: '<rect x="2" y="3" width="20" height="14" rx="2"></rect><path d="M8 21h8M12 17v4"></path>',
      voice: '<path d="M12 2a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>',
      tools: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>'
    };
    return `
      <div class="empty-state" style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px;">
        <svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">${icons[chart]}</svg>
        <p class="empty-state-title">${chart.toUpperCase()} Metrics</p>
        <p class="empty-state-desc">Waiting for live data from Brahma Echo</p>
      </div>
    `;
  },
  injectGradients(canvas) {
    const svg = canvas.querySelector('svg');
    if (!svg) return;
    let defs = svg.querySelector('defs');
    if (!defs) {
      defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
      svg.prepend(defs);
    }
    const colors = {
      cpu: 'var(--accent-primary)',
      ram: 'var(--accent-secondary)',
      voice: 'var(--accent-warning)',
      tools: 'var(--accent-success)'
    };
    const color = colors[State.activeChart];
    const gradId = `grad-${State.activeChart}`;
    if (!document.getElementById(gradId)) {
      defs.innerHTML += `
        <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.5"/>
          <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
        </linearGradient>
      `;
    }
  },
  renderChart(type, data) {
    const w = 100, h = 220;
    const padding = { top: 24, right: 24, bottom: 36, left: 56 };
    const innerW = w - padding.left - padding.right;
    const innerH = h - padding.top - padding.bottom;
    const maxV = type === 'voice' ? 1 : 100;
    const color = this.colors[type];
    const grad = this.gradients[type];

    if (type === 'tools') {
      return this.renderTimeline(data, color, innerW, innerH, padding);
    }
    if (type === 'voice') {
      return this.renderWaveform(data, color, innerW, innerH, padding);
    }
    return this.renderSparkline(data, color, maxV, innerW, innerH, padding, grad);
  },
  renderSparkline(data, color, maxV, innerW, innerH, padding, grad) {
    const points = data.map((d, i) => {
      const x = padding.left + (i / Math.max(data.length - 1, 1)) * innerW;
      const y = padding.top + innerH - (d.v / maxV) * innerH;
      return `${x},${y}`;
    }).join(' ');
    const areaPoints = [
      `${padding.left},${padding.top + innerH}`,
      ...points.split(' '),
      `${padding.left + innerW},${padding.top + innerH}`
    ].join(' ');

    return `
      <svg class="visualizer-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" filter="url(#liquid-displace)">
        <defs>
          <linearGradient id="grad-${type}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${color}" stop-opacity="0.4"/>
            <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <polygon class="sparkline-area" points="${areaPoints}" fill="${grad}"></polygon>
        <polyline class="sparkline" points="${points}" stroke="${color}" style="filter:url(#liquid-displace);"></polyline>
        ${data.map((d, i) => {
          const x = padding.left + (i / Math.max(data.length - 1, 1)) * innerW;
          const y = padding.top + innerH - (d.v / maxV) * innerH;
          return `<circle class="sparkline-point" cx="${x}" cy="${y}" fill="${color}" r="4"></circle>`;
        }).join('')}
        <text x="${w/2}" y="${padding.top + 18}" text-anchor="middle" font-family="var(--glass-font-mono)" font-size="16" fill="var(--text-primary)" font-weight="700">${Math.round(data[data.length - 1]?.v || 0)}%</text>
        <text x="${w/2}" y="${h - 8}" text-anchor="middle" font-size="11" fill="var(--text-tertiary)">${type.toUpperCase()}</text>
        <text x="${padding.left}" y="${padding.top + innerH + 20}" font-size="9" fill="var(--text-tertiary)" text-anchor="start">0%</text>
        <text x="${padding.left + innerW}" y="${padding.top + innerH + 20}" font-size="9" fill="var(--text-tertiary)" text-anchor="end">100%</text>
      </svg>
    `;
  },
  renderWaveform(data, color, innerW, innerH, padding) {
    const bars = data.map((d, i) => {
      const x = padding.left + (i / Math.max(data.length - 1, 1)) * innerW;
      const h = Math.abs(d.v) * innerH * 0.8;
      const y = padding.top + innerH - h;
      return `<rect class="waveform-bar${d.v > 0.5 ? ' active' : ''}" x="${x}" y="${y}" width="${Math.max(2, innerW / data.length - 1)}" height="${h}" fill="${color}" rx="2"></rect>`;
    }).join('');
    return `
      <svg class="visualizer-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
        ${bars}
        <text x="${w/2}" y="${padding.top + 18}" text-anchor="middle" font-family="var(--glass-font-mono)" font-size="16" fill="var(--text-primary)" font-weight="700">VOICE</text>
        <text x="${w/2}" y="${h - 8}" text-anchor="middle" font-size="11" fill="var(--text-tertiary)">WAVEFORM</text>
      </svg>
    `;
  },
  renderTimeline(data, color, innerW, innerH, padding) {
    const items = data.slice(-12).map((d, i) => {
      const x = padding.left + (i / 11) * innerW;
      const y = padding.top + innerH * 0.5;
      return `
        <g transform="translate(${x},${y})" style="cursor:pointer;" data-tool="${d.tool}" data-duration="${d.duration}">
          <circle r="7" fill="${color}" opacity="0.15"></circle>
          <circle r="4" fill="${color}"></circle>
          <text x="0" y="${innerH * 0.5 + 22}" text-anchor="middle" font-size="7" fill="var(--text-tertiary)" style="max-width:60px;">${d.tool}</text>
          <text x="0" y="${innerH * 0.5 + 34}" text-anchor="middle" font-family="var(--glass-font-mono)" font-size="6" fill="var(--text-tertiary)">${fmtTime(d.duration)}</text>
        </g>
      `;
    }).join('');
    return `
      <svg class="visualizer-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
        <line x1="${padding.left}" y1="${padding.top + innerH * 0.5}" x2="${padding.left + innerW}" y2="${padding.top + innerH * 0.5}" stroke="var(--glass-border)" stroke-width="1" stroke-dasharray="4,4"></line>
        ${items}
        <text x="${w/2}" y="${padding.top + 18}" text-anchor="middle" font-family="var(--glass-font-mono)" font-size="16" fill="var(--text-primary)" font-weight="700">${data.length} tools</text>
        <text x="${w/2}" y="${h - 8}" text-anchor="middle" font-size="11" fill="var(--text-tertiary)">TIMELINE</text>
      </svg>
    `;
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
  },
  render() {
    const list = $('#toolLogList');
    if (!list) return;
    if (State.toolLogs.length === 0) {
      list.innerHTML = '<div class="empty-state" style="height:100%;padding:48px;"><svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg><p class="empty-state-title">No tool executions yet</p><p class="empty-state-desc">Execute a tool from the dashboard or via voice to see logs here</p></div>';
      return;
    }
    list.innerHTML = State.toolLogs.slice(0, 25).map(e => this.renderEntry(e)).join('');
  },
  renderEntry(e) {
    const success = e.success !== false;
    return `
      <article class="tool-log-entry glass-card" data-id="${e.id}" style="margin-bottom:8px;">
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
  }
};

// ==========================================================================
// Chat Component
// ==========================================================================
const Chat = {
  addMessage(payload) {
    const isUser = payload.role === 'user';
    const msg = {
      id: ++State.messageId,
      role: payload.role,
      content: payload.content,
      time: nowTime(),
      tool: payload.tool,
      toolResult: payload.toolResult
    };
    State.chatMessages.push(msg);
    this.renderMessage(msg);
    this.scrollToBottom();
  },
  addToolResult(result) {
    // Tool results are shown as assistant messages
    this.addMessage({
      role: 'assistant',
      content: result.success ? `✅ ${result.tool} completed in ${fmtTime(result.duration)}` : `❌ ${result.tool} failed: ${result.error}`,
      toolResult: result
    });
  },
  handleResponse(payload) {
    // Handle streaming response
    this.addMessage({
      role: 'assistant',
      content: payload.content
    });
  },
  renderMessage(msg) {
    const list = $('#chatMessages');
    const welcome = $('#welcomeTime');
    if (welcome) {
      welcome.textContent = msg.time;
      welcome.id = '';
    }
    const typing = $('#typingIndicator');
    if (typing) typing.hidden = true;

    const div = document.createElement('div');
    div.className = `chat-message ${msg.role}`;
    div.dataset.id = msg.id;
    
    const avatarIcon = msg.role === 'user' 
      ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'
      : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"></polygon><line x1="12" y1="22" x2="12" y2="15.5"></line><polyline points="22 8.5 12 15.5 2 8.5"></polyline></svg>';
    
    div.innerHTML = `
      <div class="message-avatar">${avatarIcon}</div>
      <div class="message-content">
        <div class="message-text">${this.escapeHtml(msg.content)}</div>
        <time class="message-time">${msg.time}</time>
      </div>
    `;
    list.appendChild(div);
  },
  showTyping() {
    const typing = $('#typingIndicator');
    if (typing) typing.hidden = false;
  },
  hideTyping() {
    const typing = $('#typingIndicator');
    if (typing) typing.hidden = true;
  },
  scrollToBottom() {
    const list = $('#chatMessages');
    if (list) list.scrollTop = list.scrollHeight;
  },
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
  send(text) {
    if (!text.trim()) return;
    this.addMessage({ role: 'user', content: text.trim() });
    WS.send({
      type: 'chat_message',
      payload: { content: text.trim(), messageId: ++State.messageId }
    });
    this.showTyping();
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
    const tools = [
      { id: 'blender_control', title: 'Blender: New Scene', desc: 'Create a new Blender scene', icon: 'cube', action: () => ToolExecutor.execute('blender_control', { action: 'scene_new' }) },
      { id: 'blender_control', title: 'Blender: Add Cube', desc: 'Add a cube primitive', icon: 'cube', action: () => ToolExecutor.execute('blender_control', { action: 'object_add', object_type: 'CUBE' }) },
      { id: 'blender_control', title: 'Blender: Render (Cycles)', desc: 'Render current scene with Cycles', icon: 'camera', action: () => ToolExecutor.execute('blender_control', { action: 'render', engine: 'CYCLES' }) },
      { id: 'cinema4d_control', title: 'Cinema 4D: Add Cube', desc: 'Add cube primitive', icon: 'cube', action: () => ToolExecutor.execute('cinema4d_control', { action: 'add_primitive', primitive_type: 'cube' }) },
      { id: 'cinema4d_control', title: 'Cinema 4D: MoGraph Cloner', desc: 'Create MoGraph cloner on selected object', icon: 'grid', action: () => ToolExecutor.execute('cinema4d_control', { action: 'mograph_cloner' }) },
      { id: 'cinema4d_control', title: 'Cinema 4D: Redshift Materials', desc: 'Inspect Redshift materials', icon: 'gem', action: () => ToolExecutor.execute('cinema4d_control', { action: 'inspect_redshift_materials' }) },
      { id: 'autocad_control', title: 'AutoCAD: Test Connection', desc: 'Ping AutoCAD MCP', icon: 'link', action: () => ToolExecutor.execute('autocad_control', { action: 'ping' }) },
      { id: 'autocad_control', title: 'AutoCAD: List Tools (240+)', desc: 'List all MCP Pro tools', icon: 'list', action: () => ToolExecutor.execute('autocad_control', { action: 'list_tools' }) },
      { id: 'autocad_control', title: 'AutoCAD: Update Keynote (LT)', desc: 'Renumber keynote headlessly', icon: 'edit', action: () => ToolExecutor.execute('autocad_control', { action: 'lt_update_keynote' }) },
      { id: 'replica_pipeline', title: 'Replica: Full Pipeline', desc: 'Run all 11 skills on target app', icon: 'git-branch', action: () => ToolExecutor.execute('replica_pipeline', { action: 'full_pipeline' }) },
      { id: 'replica_pipeline', title: 'Replica: Recon', desc: 'Reverse-engineer app screens/flows', icon: 'search', action: () => ToolExecutor.execute('replica_pipeline', { action: 'recon' }) },
      { id: 'system_diagnostics', title: 'System: Diagnostics', desc: 'CPU, RAM, battery, disk', icon: 'monitor', action: () => ToolExecutor.execute('system_diagnostics', { action: 'status' }) },
      { id: 'system_diagnostics', title: 'System: RAM Hogs', desc: 'Find top memory consumers', icon: 'memory', action: () => ToolExecutor.execute('system_diagnostics', { action: 'ram_hogs' }) },
      { id: 'system_diagnostics', title: 'System: Brightness 80%', desc: 'Set display brightness', icon: 'sun', action: () => ToolExecutor.execute('system_diagnostics', { action: 'brightness', level: 80 }) },
      { id: 'google_workspace', title: 'Gmail: Unread', desc: 'Check unread emails', icon: 'mail', action: () => ToolExecutor.execute('google_workspace', { service: 'gmail', action: 'unread' }) },
      { id: 'google_workspace', title: 'Calendar: Today', desc: 'List today\'s events', icon: 'calendar', action: () => ToolExecutor.execute('google_workspace', { service: 'calendar', action: 'list' }) },
      { id: 'google_workspace', title: 'Drive: Search', desc: 'Search Google Drive', icon: 'database', action: () => ToolExecutor.execute('google_workspace', { service: 'drive', action: 'search' }) },
      { id: 'browser_control', title: 'Browser: Navigate', desc: 'Go to URL', icon: 'globe', action: () => ToolExecutor.execute('browser_control', { action: 'go_to' }) },
      { id: 'browser_control', title: 'Browser: Screenshot', desc: 'Take page screenshot', icon: 'camera', action: () => ToolExecutor.execute('browser_control', { action: 'screenshot' }) },
      { id: 'file_controller', title: 'Files: Organize Desktop', desc: 'Sort desktop by type/date', icon: 'folder', action: () => ToolExecutor.execute('smart_organizer', { action: 'organize', target: 'desktop' }) },
      { id: 'voice_start', title: 'Voice: Start Listening', desc: 'Activate voice recognition', icon: 'mic', action: () => Voice.toggle() },
    ];

    const pages = [
      { id: 'nav-dashboard', title: 'Go to Dashboard', desc: 'System overview', icon: 'layout', action: () => UI.navigate('dashboard') },
      { id: 'nav-visualizer', title: 'Go to Visualizer', desc: 'Charts & metrics', icon: 'bar-chart', action: () => UI.navigate('visualizer') },
      { id: 'nav-chat', title: 'Go to Chat', desc: 'Chat with Brahma', icon: 'message-square', action: () => UI.navigate('chat') },
      { id: 'nav-skills', title: 'Go to Skills', desc: 'All tools & skills', icon: 'box', action: () => UI.navigate('skills') },
      { id: 'nav-3d-cad', title: 'Go to 3D/CAD', desc: 'Blender, C4D, AutoCAD', icon: 'cube', action: () => UI.navigate('3d-cad') },
      { id: 'nav-replica', title: 'Go to Replica', desc: 'App cloning pipeline', icon: 'git-branch', action: () => UI.navigate('replica') },
      { id: 'nav-logs', title: 'Go to Logs', desc: 'Tool execution history', icon: 'file-text', action: () => UI.navigate('logs') },
      { id: 'nav-settings', title: 'Go to Settings', desc: 'Preferences', icon: 'settings', action: () => UI.navigate('settings') },
    ];

    const settings = [
      { id: 'theme-toggle', title: 'Toggle Theme', desc: 'Switch light/dark', icon: 'sun', action: () => Theme.toggle() },
      { id: 'sidebar-toggle', title: 'Toggle Left Sidebar', desc: 'Expand/collapse', icon: 'sidebar', action: () => UI.toggleLeftSidebar() },
      { id: 'right-sidebar-toggle', title: 'Toggle Right Sidebar', desc: 'Show/hide tools', icon: 'panel-right', action: () => UI.toggleRightSidebar() },
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
      'right-sidebar-toggle': '⌘⇧B',
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
      sidebar: '<line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line>',
      'panel-right': '<rect x="3" y="3" width="18" height="18" rx="2"></rect><line x1="15" y1="3" x2="15" y2="21"></line>',
      'message-square': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>'
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
    const grid = $('#skillsList');
    if (!grid) return;
    if (!State.skills.length) {
      grid.innerHTML = '<div class="empty-state" style="padding:48px;"><svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg><p class="empty-state-title">Loading skills…</p><p class="empty-state-desc">Connect to Brahma Echo to fetch skills</p></div>';
      return;
    }
    grid.innerHTML = State.skills.map(s => `
      <div class="skill-item">
        <div class="skill-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg></div>
        <div class="skill-info">
          <div class="skill-name">${s.name}</div>
          <div class="skill-desc">${s.description}</div>
        </div>
        <div class="skill-tags">
          ${(s.frontmatter?.category ? [s.frontmatter.category] : []).concat(s.frontmatter?.keywords?.slice(0, 3) || []).map(k => `<span class="glass-badge glass-badge--neutral" style="font-size:0.6rem;padding:2px 8px;">${k}</span>`).join('')}
        </div>
      </div>
    `).join('');
  }
};

// ==========================================================================
// Tool Executor
// ==========================================================================
const ToolExecutor = {
  async execute(tool, args) {
    const start = Date.now();
    ToolLog.add({ tool, args, duration: 0, pending: true });
    try {
      WS.send({
        type: 'execute_tool',
        payload: { tool, args, requestId: Date.now() }
      });
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
    $('#voiceInputBtn').classList.toggle('pressed', this.listening);
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
    this.renderToolsGrids();
    $('#welcomeTime').textContent = nowTime();
  },
  bindEvents() {
    // Left Sidebar
    $('#sidebarToggle').addEventListener('click', () => this.toggleLeftSidebar());
    $('#sidebarExpand').addEventListener('click', () => this.toggleLeftSidebar());

    // Right Sidebar
    $('#toolsClose').addEventListener('click', () => this.toggleRightSidebar());

    // Navigation
    $$('.nav-item').forEach(btn => {
      btn.addEventListener('click', () => this.navigate(btn.dataset.page));
    });

    // Tools tabs
    $$('.tools-tab').forEach(btn => {
      btn.addEventListener('click', () => this.switchToolsTab(btn.dataset.tab));
    });

    // Theme
    $('#themeToggle').addEventListener('click', () => Theme.toggle());

    // Voice
    $('#listenToggle').addEventListener('click', () => Voice.toggle());
    $('#voiceInputBtn').addEventListener('click', () => Voice.toggle());

    // Chat
    $('#chatForm').addEventListener('submit', (e) => {
      e.preventDefault();
      const input = $('#chatInput');
      const text = input.value.trim();
      if (text) {
        Chat.send(text);
        input.value = '';
        input.style.height = 'auto';
        input.style.height = input.scrollHeight + 'px';
      }
    });

    // Auto-resize textarea
    $('#chatInput').addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 180) + 'px';
    });

    // Chart buttons
    $$('.chart-btn').forEach(btn => {
      btn.addEventListener('click', () => Visualizer.render(btn.dataset.chart));
    });

    // Tool cards (delegated)
    document.addEventListener('click', (e) => {
      const card = e.target.closest('.tool-card');
      if (card) {
        const tool = card.dataset.tool;
        const action = card.dataset.action ? JSON.parse(card.dataset.action) : {};
        ToolExecutor.execute(tool, action);
      }
      const skillBtn = e.target.closest('.skill-item');
      if (skillBtn) {
        toast(`Skill: ${skillBtn.dataset.skill || 'unknown'}`, 'info');
      }
    });

    // Chart buttons in visualizer
    $$('.chart-btn').forEach(btn => {
      btn.addEventListener('click', () => Visualizer.render(btn.dataset.chart));
    });

    // Tool buttons in right sidebar (delegated)
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-tool]');
      if (btn) {
        const tool = btn.dataset.tool;
        const action = btn.dataset.action ? JSON.parse(btn.dataset.action) : {};
        ToolExecutor.execute(tool, action);
      }
    });

    // Reconnect
    $('#reconnectBtn').addEventListener('click', () => WS.connect());

    // Settings
    $('#themeSelect')?.addEventListener('change', (e) => Theme.apply(e.target.value));
    $('#sidebarCollapsedDefault')?.addEventListener('change', (e) => this.saveSetting('leftExpanded', e.target.checked));
    $('#reducedMotion')?.addEventListener('change', (e) => this.saveSetting('reducedMotion', e.target.checked));
    $('#autoReconnect')?.addEventListener('change', (e) => { State.autoReconnect = e.target.checked; this.saveSetting('autoReconnect', e.target.checked); });
    $('#reconnectInterval')?.addEventListener('change', (e) => { State.reconnectInterval = e.target.value * 1000; this.saveSetting('reconnectInterval', State.reconnectInterval); });
    $('#wsUrl')?.addEventListener('change', (e) => { State.wsUrl = e.target.value; this.saveSetting('wsUrl', e.target.value); WS.connect(); });
    $('#offlineCache')?.addEventListener('change', (e) => { State.offlineCache = e.target.checked; this.saveSetting('offlineCache', e.target.checked); });
    $('#telemetry')?.addEventListener('change', (e) => this.saveSetting('telemetry', e.target.checked));
    $('#voiceResponse')?.addEventListener('change', (e) => { State.voiceResponse = e.target.checked; this.saveSetting('voiceResponse', e.target.checked); });
    $('#wakeWord')?.addEventListener('change', (e) => this.saveSetting('wakeWord', e.target.value));
    $('#voiceLang')?.addEventListener('change', (e) => this.saveSetting('voiceLang', e.target.value));
    $('#clearAllData')?.addEventListener('click', () => this.clearAllData());

    // Header search
    $('#headerSearch')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        CommandPalette.openPanel();
        $('#commandPaletteInput').value = e.target.value;
        CommandPalette.filter(e.target.value);
      }
    });

    // Reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.documentElement.style.setProperty('--glass-transition-fast', '0.01ms');
      document.documentElement.style.setProperty('--glass-transition-normal', '0.01ms');
      document.documentElement.style.setProperty('--glass-transition-slow', '0.01ms');
      document.documentElement.style.setProperty('--glass-transition-bounce', '0.01ms');
    }
  },
  navigate(page) {
    $$('.page').forEach(p => p.hidden = true);
    $$('.nav-item').forEach(b => b.classList.remove('active'));
    const target = $(`#page-${page}`);
    if (target) {
      target.hidden = false;
    }
    $(`.nav-item[data-page="${page}"]`)?.classList.add('active');
    State.currentPage = page;
    
    if (page === 'visualizer') {
      ['cpuChart', 'ramChart', 'voiceChart', 'toolsChart'].forEach(id => Visualizer.renderFull(id, id.replace('Chart', '')));
    }
    if (page === 'skills') Skills.render();
    if (page === '3d-cad') this.renderToolsGrids();
    if (page === 'replica') this.renderReplicaSkills();
    if (page === 'chat') $('#chatInput')?.focus();
  },
  switchToolsTab(tab) {
    $$('.tools-tab').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tab);
      b.setAttribute('aria-selected', b.dataset.tab === tab);
    });
    $$('.tools-panel').forEach(p => {
      p.hidden = p.id !== `panel-${tab}`;
      if (!p.hidden) p.classList.add('active');
    });
  },
  toggleLeftSidebar() {
    State.leftExpanded = !State.leftExpanded;
    $('#appShell').classList.toggle('left-expanded', State.leftExpanded);
    $('#sidebarExpand').querySelector('svg').innerHTML = State.leftExpanded 
      ? '<polyline points="9 18 15 12 9 6"></polyline>'
      : '<polyline points="15 18 9 12 15 6"></polyline>';
    this.saveSetting('leftExpanded', State.leftExpanded);
  },
  toggleRightSidebar() {
    State.rightCollapsed = !State.rightCollapsed;
    $('#appShell').classList.toggle('right-collapsed', State.rightCollapsed);
    this.saveSetting('rightCollapsed', State.rightCollapsed);
  },
  updateConnectionStatus(connected) {
    const dot = $('#statusDot');
    const text = $('#statusText');
    const reconnect = $('#reconnectBtn');
    const chatDot = $('#chatStatusDot');
    const chatText = $('#chatStatusText');
    
    if (connected) {
      dot.className = 'status-dot connected';
      text.textContent = 'Connected';
      reconnect.hidden = true;
      chatDot.className = 'status-dot connected';
      chatText.textContent = 'Online';
    } else {
      dot.className = 'status-dot error';
      text.textContent = 'Disconnected';
      reconnect.hidden = false;
      chatDot.className = 'status-dot error';
      chatText.textContent = 'Offline';
    }
  },
  updateVoiceState(payload) {
    const state = payload.state;
    const states = {
      idle: { text: 'Ready', dot: '' },
      listening: { text: '● LISTENING', dot: 'pulse' },
      processing: { text: '⚡ PROCESSING', dot: 'pulse' },
      speaking: { text: '🔊 SPEAKING', dot: '' }
    };
    const s = states[state] || states.idle;
    $('#voiceState').textContent = s.text;
    $('#voiceTrend').className = `stat-trend ${state === 'listening' ? 'up' : 'neutral'}`;
    $('#voiceTrend').textContent = state === 'listening' ? '● LIVE' : state === 'speaking' ? '🔊' : '—';
    $('#chatStatusText').textContent = s.text;
    $('#chatStatusDot').className = `status-dot ${state === 'listening' || state === 'processing' ? 'connecting' : 'connected'}`;
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
      if (State.currentPage === 'dashboard' || State.currentPage === 'visualizer') {
        Visualizer.render(State.activeChart);
      }
    }, 2000);
  },
  renderToolsGrids() {
    const grids = {
      cadToolsGrid: [
        { tool: 'blender_control', action: { action: 'scene_new' }, title: 'New Scene', desc: 'Create empty Blender scene', icon: 'file-plus' },
        { tool: 'blender_control', action: { action: 'object_add', object_type: 'CUBE' }, title: 'Add Cube', desc: 'Add cube primitive', icon: 'cube' },
        { tool: 'blender_control', action: { action: 'object_add', object_type: 'SPHERE' }, title: 'Add Sphere', desc: 'Add sphere primitive', icon: 'sphere' },
        { tool: 'blender_control', action: { action: 'render', engine: 'CYCLES' }, title: 'Render Cycles', desc: 'Path-traced render', icon: 'camera' },
        { tool: 'cinema4d_control', action: { action: 'add_primitive', primitive_type: 'cube' }, title: 'C4D: Add Cube', desc: 'Add cube in Cinema 4D', icon: 'cube' },
        { tool: 'cinema4d_control', action: { action: 'mograph_cloner' }, title: 'MoGraph Cloner', desc: 'Create MoGraph cloner', icon: 'grid' },
        { tool: 'cinema4d_control', action: { action: 'inspect_redshift_materials' }, title: 'Redshift Mats', desc: 'Inspect Redshift materials', icon: 'gem' },
        { tool: 'autocad_control', action: { action: 'ping' }, title: 'AutoCAD: Ping', desc: 'Test MCP connection', icon: 'link' },
        { tool: 'autocad_control', action: { action: 'list_tools' }, title: 'List 240+ Tools', desc: 'Show all MCP Pro tools', icon: 'list' },
        { tool: 'autocad_control', action: { action: 'lt_update_keynote' }, title: 'Update Keynote (LT)', desc: 'Renumber keynote headlessly', icon: 'edit' }
      ],
      systemToolsGrid: [
        { tool: 'system_diagnostics', action: { action: 'status' }, title: 'Full Diagnostics', desc: 'CPU, RAM, battery, disk', icon: 'monitor' },
        { tool: 'system_diagnostics', action: { action: 'ram_hogs' }, title: 'RAM Hogs', desc: 'Top memory consumers', icon: 'memory' },
        { tool: 'system_diagnostics', action: { action: 'cpu_hogs' }, title: 'CPU Hogs', desc: 'Top CPU consumers', icon: 'cpu' },
        { tool: 'system_diagnostics', action: { action: 'brightness', level: 80 }, title: 'Brightness 80%', desc: 'Set display brightness', icon: 'sun' },
        { tool: 'system_diagnostics', action: { action: 'battery' }, title: 'Battery Status', desc: 'Health, percentage, state', icon: 'battery' },
        { tool: 'system_diagnostics', action: { action: 'disk' }, title: 'Disk Space', desc: 'Storage usage', icon: 'hard-drive' }
      ],
      workspaceToolsGrid: [
        { tool: 'google_workspace', action: { service: 'gmail', action: 'unread' }, title: 'Gmail: Unread', desc: 'Check unread emails', icon: 'mail' },
        { tool: 'google_workspace', action: { service: 'gmail', action: 'list' }, title: 'Gmail: List', desc: 'List recent emails', icon: 'inbox' },
        { tool: 'google_workspace', action: { service: 'calendar', action: 'list' }, title: 'Calendar: Today', desc: 'List today\'s events', icon: 'calendar' },
        { tool: 'google_workspace', action: { service: 'calendar', action: 'add' }, title: 'Create Event', desc: 'Add calendar event', icon: 'calendar-plus' },
        { tool: 'google_workspace', action: { service: 'drive', action: 'list' }, title: 'Drive: List', desc: 'List Drive files', icon: 'folder' },
        { tool: 'google_workspace', action: { service: 'drive', action: 'search' }, title: 'Drive: Search', desc: 'Search files', icon: 'search' }
      ],
      browserToolsGrid: [
        { tool: 'browser_control', action: { action: 'go_to' }, title: 'Navigate', desc: 'Go to URL', icon: 'globe' },
        { tool: 'browser_control', action: { action: 'screenshot' }, title: 'Screenshot', desc: 'Capture page', icon: 'camera' },
        { tool: 'browser_control', action: { action: 'click' }, title: 'Click Element', desc: 'Click by selector', icon: 'mouse-pointer' },
        { tool: 'browser_control', action: { action: 'fill_form' }, title: 'Fill Form', desc: 'Auto-fill form fields', icon: 'file-text' },
        { tool: 'file_controller', action: { action: 'organize', target: 'desktop' }, title: 'Organize Desktop', desc: 'Sort by type/date', icon: 'folder' },
        { tool: 'smart_organizer', action: { action: 'preview', target: 'desktop' }, title: 'Preview Organize', desc: 'Dry-run desktop sort', icon: 'eye' }
      ],
      voiceToolsGrid: [
        { tool: 'voice_start', action: {}, title: 'Start Listening', desc: 'Activate voice recognition', icon: 'mic' },
        { tool: 'system_diagnostics', action: { action: 'status' }, title: 'Check Mic', desc: 'Test microphone input', icon: 'mic-off' }
      ]
    };

    Object.entries(grids).forEach(([id, tools]) => {
      const grid = $(`#${id}`);
      if (grid) {
        grid.innerHTML = tools.map(t => `
          <button class="tool-card" data-tool="${t.tool}" data-action='${JSON.stringify(t.action)}'>
            <div class="tool-card-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${this.getToolIcon(t.icon)}</svg>
            </div>
            <div class="tool-card-title">${t.title}</div>
            <div class="tool-card-desc">${t.desc}</div>
          </button>
        `).join('');
      }
    });
  },
  getToolIcon(name) {
    const icons = {
      'file-plus': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="12" y1="18" x2="12" y2="12"></line><line x1="9" y1="15" x2="15" y2="15"></line>',
      'cube': '<polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"></polygon><line x1="12" y1="22" x2="12" y2="15.5"></line><polyline points="22 8.5 12 15.5 2 8.5"></polyline>',
      'sphere': '<circle cx="12" cy="12" r="10"></circle><path d="M12 2a10 10 0 0 1 0 20 10 10 0 0 1 0-20"></path><path d="M2 12a10 10 0 0 1 20 0 10 10 0 0 1-20 0"></path>',
      'camera': '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="12" r="4"></circle>',
      'grid': '<rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect>',
      'gem': '<polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"></polygon><line x1="12" y1="22" x2="12" y2="15.5"></line><polyline points="22 8.5 12 15.5 2 8.5"></polyline>',
      'link': '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>',
      'list': '<line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line>',
      'edit': '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>',
      'monitor': '<rect x="2" y="3" width="20" height="14" rx="2"></rect><path d="M8 21h8M12 17v4"></path>',
      'memory': '<rect x="2" y="3" width="20" height="14" rx="2"></rect><path d="M8 21h8M12 17v4"></path>',
      'cpu': '<rect x="2" y="3" width="20" height="14" rx="2"></rect><path d="M8 21h8M12 17v4"></path>',
      'sun': '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>',
      'battery': '<rect x="1" y="1" width="22" height="22" rx="2"></rect><line x1="23" y1="7" x2="23" y2="17"></line><line x1="17" y1="7" x2="17" y2="17"></line>',
      'hard-drive': '<line x1="22" y1="12" x2="2" y2="12"></line><path d="M5.45 5.11L2 12l6 6"></path><path d="M22 19v-2a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v2"></path><circle cx="8" cy="16" r="2"></circle><path d="M16 7v10"></path>',
      'mail': '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline>',
      'inbox': '<path d="M21 13v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V13a2 2 0 0 1 2-2h2"></path><path d="M14 11v6a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-6"></path>',
      'calendar': '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line>',
      'calendar-plus': '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></path><line x1="12" y1="14" x2="12" y2="18"></line><line x1="10" y1="16" x2="14" y2="16"></line>',
      'folder': '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>',
      'search': '<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>',
      'globe': '<circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>',
      'mouse-pointer': '<path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z"></path><path d="M13 13l6 6"></path>',
      'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline>',
      'eye': '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>',
      'mic': '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line>',
      'mic-off': '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line><line x1="1" y1="1" x2="23" y2="23"></line>'
    };
    return icons[name] || icons.cube;
  },
  renderReplicaSkills() {
    const grid = $('#replicaSkillsGrid');
    if (!grid) return;
    const skills = ['recon', 'architect', 'design', 'build', 'backend', 'test', 'diff', 'entrepreneur', 'brand', 'launch', 'deploy'];
    grid.innerHTML = skills.map(s => `
      <button class="glass-btn glass-btn--ghost" style="flex:1;justify-content:center;" data-tool="replica_pipeline" data-action='{"action":"${s}"}'>${s}</button>
    `).join('');
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
    State.leftExpanded = saved.leftExpanded || false;
    $('#appShell').classList.toggle('left-expanded', State.leftExpanded);
    State.rightCollapsed = saved.rightCollapsed || false;
    $('#appShell').classList.toggle('right-collapsed', State.rightCollapsed);
    State.reducedMotion = saved.reducedMotion || false;
    State.autoReconnect = saved.autoReconnect !== false;
    State.reconnectInterval = saved.reconnectInterval || 5000;
    State.wsUrl = saved.wsUrl || 'ws://localhost:8000/ws/modern';
    State.offlineCache = saved.offlineCache !== false;
    State.voiceResponse = saved.voiceResponse !== false;
    $('#wsUrl')?.value = State.wsUrl;
    $('#autoReconnect')?.checked = State.autoReconnect;
    $('#reconnectInterval')?.value = State.reconnectInterval / 1000;
    $('#offlineCache')?.checked = State.offlineCache;
    $('#telemetry')?.checked = saved.telemetry || false;
    $('#voiceResponse')?.checked = State.voiceResponse;
    $('#wakeWord')?.value = saved.wakeWord || 'Brahma Echo';
    $('#voiceLang')?.value = saved.voiceLang || 'en-US';
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
      State.chatMessages = [];
      ToolLog.render();
      Chat.renderMessage({ role: 'assistant', content: 'Hello! I\'m Brahma Echo, your AI assistant. How can I help you today?', time: nowTime() });
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
window.BrahmaUI = { State, UI, WS, Metrics, Visualizer, ToolLog, CommandPalette, Skills, ToolExecutor, Voice, Theme, Chat };