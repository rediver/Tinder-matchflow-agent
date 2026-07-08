/**
 * TinderGPT — frontend app
 *
 * Structure:
 *   App      – tab registry & routing
 *   api      – fetch helper (same-origin, no CORS needed)
 *   Control  – ⚙ Control tab
 *   Prompts  – ✏ Prompts tab
 *   Arch     – 🌐 Architecture tab
 *
 * To add a new tab:
 *   1. Add <template id="tpl-mytab"> … </template> in index.html
 *   2. App.register({ id:'mytab', label:'My Tab', init(el){…} })
 */

// ── API helper ───────────────────────────────────────────────
const api = {
  async get(path) {
    const r = await fetch(path);
    const text = await r.text();
    return { ok: r.ok, status: r.status, text };
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const text = await r.text();
    return { ok: r.ok, status: r.status, text };
  },
};

// ── Tab system ───────────────────────────────────────────────
const App = (() => {
  const tabs = [];       // { id, label, init, onShow }
  const instances = {};  // id → DOM element (lazy)
  let current = null;

  function register(tab) {
    tabs.push(tab);
  }

  function _buildHeader() {
    const nav = document.getElementById('tabs');
    tabs.forEach(t => {
      const btn = document.createElement('button');
      btn.className = 'tab-btn';
      btn.textContent = t.label;
      btn.dataset.tab = t.id;
      btn.addEventListener('click', () => show(t.id));
      nav.appendChild(btn);
    });
  }

  function show(id) {
    const main = document.getElementById('main');

    // deactivate previous
    if (current) {
      main.querySelector(`[data-page="${current}"]`)?.classList.remove('active');
      document.querySelector(`.tab-btn[data-tab="${current}"]`)?.classList.remove('active');
    }

    // lazy-init page from template
    if (!instances[id]) {
      const tpl = document.getElementById(`tpl-${id}`);
      const page = document.createElement('div');
      page.className = 'tab-page';
      page.dataset.page = id;
      page.appendChild(tpl.content.cloneNode(true));
      main.appendChild(page);
      instances[id] = page;
      tabs.find(t => t.id === id)?.init?.(page);
    }

    instances[id].classList.add('active');
    document.querySelector(`.tab-btn[data-tab="${id}"]`)?.classList.add('active');
    tabs.find(t => t.id === id)?.onShow?.(instances[id]);
    current = id;
  }

  function init() {
    _buildHeader();
    if (tabs.length) show(tabs[0].id);
  }

  return { register, show, init };
})();

// ── Control tab ──────────────────────────────────────────────
const Control = {
  _log: null,

  _append(cls, msg) {
    const ts = new Date().toLocaleTimeString();
    this._log.innerHTML += `<br><span class="${cls}">[${ts}] ${msg}</span>`;
    this._log.scrollTop = this._log.scrollHeight;
  },

  async _call(path) {
    this._append('dim', `→ ${path}`);
    try {
      const { ok, status, text } = await api.get(path);
      this._append(ok ? 'ok' : 'err', `${status}  ${text.slice(0, 140)}`);
    } catch (e) {
      this._append('err', `ERROR: ${e.message}`);
    }
  },

  init(el) {
    this._log = el.querySelector('#c-log');

    // simple data-call buttons
    el.querySelectorAll('[data-call]').forEach(btn => {
      btn.addEventListener('click', () => this._call(btn.dataset.call));
    });

    // buttons with dynamic values
    const fns = {
      respondNewLimit: () => this._call(`/respond_new?limit=${el.querySelector('#c-limit').value}`),
      respondNr:       () => this._call(`/respond/${el.querySelector('#c-rnr').value}`),
      respondId:       () => {
        const id = el.querySelector('#c-cid').value.trim();
        if (id) this._call(`/respond/${id}`);
      },
      openerNr:        () => this._call(`/opener/${el.querySelector('#c-onr').value}`),
      batchOpeners:    () => this._call(`/batch_openers/${el.querySelector('#c-bnr').value}`),
    };
    el.querySelectorAll('[data-call-fn]').forEach(btn => {
      btn.addEventListener('click', () => fns[btn.dataset.callFn]?.());
    });

    el.querySelector('#c-clear-log').addEventListener('click', () => {
      this._log.innerHTML = '<span class="dim">— log —</span>';
    });
  },
};

// ── Prompts tab ──────────────────────────────────────────────
const Prompts = {
  _data: {},
  _key: null,
  _el: null,

  DESCS: {
    opener:          'Generates opening message from bio + user_context.',
    analyzer:        'Analyzes conversation → step1/step2 + detects contact.',
    commander_step1: 'Chooses step1 tactic: Bond | Attractive guy image | Storytelling.',
    commander_step2: 'Chooses step2 tactic: Meeting | Comfort | Ask for contact.',
    writer:          'Writes message. Has: messages, summary, rules, commander_tags+reasoning, user_context.',
    user_context:    'Your background: who you are, interests, stories, exclusions.',
  },

  async load() {
    const { ok, text } = await api.get('/prompts');
    if (!ok) return;
    this._data = JSON.parse(text);
    const list = this._el.querySelector('#p-list');
    list.innerHTML = '';
    Object.keys(this._data).forEach(k => {
      const b = document.createElement('button');
      b.className = 'pb'; b.id = `pb-${k}`;
      b.textContent = this._data[k].label;
      b.addEventListener('click', () => this.select(k));
      list.appendChild(b);
    });
    this.select(Object.keys(this._data)[0]);
  },

  select(key) {
    this._el.querySelectorAll('.pb').forEach(b => b.classList.remove('active'));
    this._el.querySelector(`#pb-${key}`)?.classList.add('active');
    this._key = key;
    this._el.querySelector('#p-title').textContent = this._data[key].label;
    this._el.querySelector('#p-desc').textContent  = this.DESCS[key] || '';
    this._el.querySelector('#p-textarea').value    = this._data[key].content;
    this._el.querySelector('#p-status').textContent = '';
  },

  async save() {
    if (!this._key) return false;
    const content = this._el.querySelector('#p-textarea').value;
    const st = this._el.querySelector('#p-status');
    st.textContent = 'Saving…'; st.style.color = '#555';
    const { ok, text } = await api.post('/prompts', { name: this._key, content });
    const d = JSON.parse(text);
    if (d.saved) this._data[this._key].content = content;
    st.textContent = d.saved ? `✓ ${new Date().toLocaleTimeString()}` : `✗ ${text}`;
    st.style.color = d.saved ? '#4caf50' : '#ff5252';
    return d.saved;
  },

  init(el) {
    this._el = el;
    el.querySelector('#p-save').addEventListener('click', () => this.save());
    el.querySelector('#p-save-reload').addEventListener('click', async () => {
      if (await this.save()) {
        await api.get('/reload');
        this._el.querySelector('#p-status').textContent += '  ↺ reloaded';
      }
    });
    this.load();
  },

  // called from Architecture tab to jump to a specific prompt
  openPrompt(key) {
    App.show('prompts');
    // select after tab is shown
    requestAnimationFrame(() => {
      if (Object.keys(this._data).length) this.select(key);
      else this.load().then(() => this.select(key));
    });
  },
};

// ── Architecture tab ─────────────────────────────────────────
const Arch = {
  _loaded: false,
  _el: null,

  init(el) {
    this._el = el;

    // clickable cards → jump to prompt editor
    el.querySelectorAll('.card.click[data-prompt]').forEach(card => {
      card.addEventListener('click', () => Prompts.openPrompt(card.dataset.prompt));
    });

    // pipeline config
    el.querySelector('#a-save').addEventListener('click', () => this._savePipeline());
    el.querySelector('#a-save-reload').addEventListener('click', async () => {
      await this._savePipeline();
      await api.get('/reload');
      el.querySelector('#a-status').textContent += ' ↺';
    });
  },

  onShow(el) {
    if (this._loaded) return;
    this._loaded = true;
    api.get('/pipeline').then(({ text }) => {
      // /pipeline returns a JSON-encoded string; parse once to get raw JSON text
      try { el.querySelector('#a-pltx').value = JSON.parse(text); }
      catch { el.querySelector('#a-pltx').value = text; }
    });
  },

  async _savePipeline() {
    const content = this._el.querySelector('#a-pltx').value;
    const st = this._el.querySelector('#a-status');
    st.textContent = 'Saving…'; st.style.color = '#555';
    const { text } = await api.post('/pipeline', { content });
    const d = JSON.parse(text);
    st.textContent = d.saved ? `✓ ${new Date().toLocaleTimeString()}` : '✗';
    st.style.color = d.saved ? '#4caf50' : '#ff5252';
  },
};

// ── Stats tab ────────────────────────────────────────────────
const Stats = {
  _el: null,
  _timer: null,

  _ROWS: [
    ['model',        'Model'],
    ['language',     'Language'],
    ['city',         'City'],
    ['browser_url',  'Browser URL'],
    ['last_action',  'Last action'],
  ],

  async fetch() {
    const { ok, text } = await api.get('/stats');
    if (!ok) return;
    const d = JSON.parse(text);
    this._render(d);
  },

  _render(d) {
    const el = this._el;

    // top cards
    const running = d.driver === 'running';
    el.querySelector('#s-dot').className       = 'stat-dot ' + (running ? 'on' : 'off');
    el.querySelector('#s-driver-val').textContent = d.driver;
    el.querySelector('#s-uptime').textContent   = d.uptime;
    el.querySelector('#s-msgs').textContent     = d.messages_sent;
    el.querySelector('#s-calls').textContent    = d.api_calls;

    // detail table
    const tbody = el.querySelector('#s-table tbody');
    tbody.innerHTML = this._ROWS
      .map(([key, label]) => {
        const val = d[key] ?? '—';
        return `<tr><td>${label}</td><td>${val}</td></tr>`;
      })
      .join('');

    // timestamp
    el.querySelector('#s-ts').textContent = 'last: ' + new Date().toLocaleTimeString();
  },

  _startAuto() {
    this._stopAuto();
    this._timer = setInterval(() => this.fetch(), 5000);
  },
  _stopAuto() {
    if (this._timer) { clearInterval(this._timer); this._timer = null; }
  },

  init(el) {
    this._el = el;
    el.querySelector('#s-refresh').addEventListener('click', () => this.fetch());
    el.querySelector('#s-auto').addEventListener('change', e => {
      e.target.checked ? this._startAuto() : this._stopAuto();
    });
    this.fetch();
    this._startAuto();
  },
};

// ── Pending tab ───────────────────────────────────────────────
const Pending = {
  _el: null,

  init(el) {
    this._el = el;
    el.querySelector('#pend-scan').addEventListener('click', () => this.scan());
    el.querySelector('#pend-select-all').addEventListener('change', e => this._toggleAll(e.target.checked));
    el.querySelector('#pend-bulk-respond').addEventListener('click', () => this._bulkRespond());
  },

  // ─ scan ───────────────────────────────────────────────
  async scan() {
    const el  = this._el;
    const n   = parseInt(el.querySelector('#pend-n').value, 10) || 5;
    const st  = el.querySelector('#pend-st');
    const list = el.querySelector('#pend-list');
    const sum  = el.querySelector('#pend-summary');

    st.textContent = `⏳ Scanning ${n} conversations…`;
    st.style.color = '#888';
    list.innerHTML = '';
    sum.style.display = 'none';
    el.querySelector('#pend-select-all').checked = false;
    el.querySelector('#pend-bulk-st').textContent = '';
    this._updateBulkBtn();

    try {
      const { ok, text } = await api.get(`/pending?n=${n}`);
      if (!ok) throw new Error(`HTTP ${JSON.parse(text)?.detail ?? text}`);
      const d = JSON.parse(text);

      st.textContent = `✓ done (${new Date().toLocaleTimeString()})`;
      st.style.color = '#4caf50';

      sum.style.display = 'block';
      el.querySelector('#pend-found').textContent =
        d.found > 0
          ? `${d.found} pending repl${d.found === 1 ? 'y' : 'ies'} out of ${d.scanned} scanned`
          : `All caught up — no pending replies in first ${d.scanned} conversations ✓`;

      d.pending.forEach(item => list.appendChild(this._buildCard(item)));
    } catch(e) {
      st.textContent = `✗ ${e.message}`;
      st.style.color = '#ff5252';
    }
  },

  // ─ select all / none ────────────────────────────────
  _toggleAll(checked) {
    this._el.querySelectorAll('.pend-chk:not(:disabled)').forEach(chk => {
      chk.checked = checked;
      chk.closest('.pend-card').classList.toggle('selected', checked);
    });
    this._updateBulkBtn();
  },

  _updateBulkBtn() {
    const selected = this._el.querySelectorAll('.pend-chk:checked').length;
    const btn = this._el.querySelector('#pend-bulk-respond');
    this._el.querySelector('#pend-sel-count').textContent = selected;
    btn.disabled = selected === 0;

    // sync select-all checkbox state
    const all  = this._el.querySelectorAll('.pend-chk:not(:disabled)').length;
    const sa   = this._el.querySelector('#pend-select-all');
    sa.indeterminate = selected > 0 && selected < all;
    sa.checked = all > 0 && selected === all;
  },

  // ─ bulk respond ──────────────────────────────────────
  async _bulkRespond() {
    const checked = [...this._el.querySelectorAll('.pend-chk:checked')];
    if (!checked.length) return;

    const bst = this._el.querySelector('#pend-bulk-st');
    this._el.querySelector('#pend-bulk-respond').disabled = true;
    bst.style.color = '#888';
    bst.textContent = `Responding to ${checked.length}…`;

    let done = 0, errors = 0;
    for (const chk of checked) {
      const pos = chk.dataset.pos;
      const card = chk.closest('.pend-card');
      const st = card.querySelector(`#pas-${pos}`);
      st.textContent = '⏳'; st.style.color = '#888';

      const { ok } = await api.get(`/respond/${pos}`);
      if (ok) {
        st.textContent = '✓'; st.style.color = '#4caf50';
        card.classList.add('pend-done');
        chk.disabled = true;
        done++;
      } else {
        st.textContent = '✗'; st.style.color = '#ff5252';
        chk.checked = false;
        card.classList.remove('selected');
        errors++;
      }
      this._updateBulkBtn();
    }

    bst.textContent = errors
      ? `✓ ${done} sent, ✗ ${errors} errors`
      : `✓ ${done} sent`;
    bst.style.color = errors ? '#ff9800' : '#4caf50';
  },

  // ─ card builder ───────────────────────────────────────
  _buildCard(item) {
    const div = document.createElement('div');
    div.className = 'pend-card';
    div.id = `pc-${item.position}`;

    const previewHtml = item.preview
      .split('\n')
      .map(l => {
        if (l.startsWith('You:'))  return `<span style="color:#668">${l}</span>`;
        if (l.startsWith('Girl:')) return `<span style="color:#8a9">${l}</span>`;
        return `<span>${l}</span>`;
      })
      .join('<br>');

    div.innerHTML = `
      <div class="pend-name">
        <input type="checkbox" class="pend-chk" id="chk-${item.position}" data-pos="${item.position}">
        <label for="chk-${item.position}" style="cursor:pointer;flex:1">${item.name}</label>
        <span class="pend-pos">#${item.position}</span>
      </div>
      <div class="pend-msg">${this._esc(item.last_message)}</div>
      <div class="pend-preview" id="pv-${item.position}">${previewHtml}</div>
      <div class="pend-actions">
        <button class="pend-respond" data-pos="${item.position}">↩ Respond</button>
        <button class="pend-toggle"  data-pos="${item.position}">▼ history</button>
        <span class="pend-act-status status" id="pas-${item.position}"></span>
      </div>
    `;

    // checkbox toggles card highlight + updates bulk button
    div.querySelector('.pend-chk').addEventListener('change', e => {
      div.classList.toggle('selected', e.target.checked);
      this._updateBulkBtn();
    });

    // single Respond
    div.querySelector('.pend-respond').addEventListener('click', async (e) => {
      const pos = e.currentTarget.dataset.pos;
      const st  = div.querySelector(`#pas-${pos}`);
      st.textContent = 'responding…'; st.style.color = '#888';
      const { ok } = await api.get(`/respond/${pos}`);
      if (ok) {
        st.textContent = '✓ sent'; st.style.color = '#4caf50';
        div.classList.add('pend-done');
        const chk = div.querySelector('.pend-chk');
        chk.disabled = true; chk.checked = false;
        this._updateBulkBtn();
      } else {
        st.textContent = '✗ error'; st.style.color = '#ff5252';
      }
    });

    // Toggle history
    div.querySelector('.pend-toggle').addEventListener('click', (e) => {
      const pv = div.querySelector(`#pv-${item.position}`);
      const open = pv.classList.toggle('open');
      e.currentTarget.textContent = open ? '▲ history' : '▼ history';
    });

    return div;
  },

  _esc(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  },
};

// ── Register tabs & boot ─────────────────────────────────────
App.register({ id: 'control', label: '⚙ Control',      init: el => Control.init(el) });
App.register({ id: 'prompts', label: '✏ Prompts',       init: el => Prompts.init(el) });
App.register({ id: 'arch',    label: '🌐 Architecture', init: el => Arch.init(el), onShow: el => Arch.onShow(el) });
App.register({ id: 'stats',   label: '📊 Stats',        init: el => Stats.init(el) });
App.register({ id: 'pending', label: '📥 Pending',      init: el => Pending.init(el) });

document.addEventListener('DOMContentLoaded', () => App.init());
