(() => {
  const frame = document.querySelector('.globe-frame');
  const panel = frame?.closest('.globe-panel');
  const layer = document.querySelector('#wiki-live-layer');
  const state = document.querySelector('#wiki-live-state');
  const link = document.querySelector('#wiki-live-link');

  if (!frame || !panel || !layer || !state || !link) return;

  const copy = {
    label: panel.dataset.wikiLiveLabel || 'WIKIPEDIA LIVE',
    connecting: panel.dataset.wikiLiveConnecting || 'WIKIPEDIA LIVE 接続中…',
    connected: panel.dataset.wikiLiveConnected || 'WIKIPEDIA LIVE ●',
    reconnecting: panel.dataset.wikiLiveReconnecting || 'WIKIPEDIA LIVE 再接続中…',
    unsupported: panel.dataset.wikiLiveUnsupported || 'WIKIPEDIA LIVE 非対応',
    template: panel.dataset.wikiLiveTemplate || '「%TITLE%」がいま編集された'
  };

  if (!('EventSource' in window)) {
    state.textContent = copy.unsupported;
    return;
  }

  const streamUrl = 'https://stream.wikimedia.org/v2/stream/recentchange';
  const minimumInterval = 1800;
  let source = null;
  let latestPending = null;
  let releaseTimer = null;
  let hideTimer = null;
  let lastShownAt = 0;

  const articleUrl = (change) => {
    const server = typeof change.server_url === 'string' && change.server_url.startsWith('https://')
      ? change.server_url
      : `https://${change.server_name}`;
    const title = String(change.title || '').replace(/ /g, '_');
    return `${server}/wiki/${encodeURIComponent(title)}`;
  };

  const makePulse = () => {
    const pulse = document.createElement('span');
    pulse.className = 'wiki-live-pulse';
    pulse.style.left = `${10 + Math.random() * 80}%`;
    pulse.style.top = `${10 + Math.random() * 80}%`;
    pulse.style.setProperty('--wiki-live-size', `${8 + Math.random() * 12}px`);
    layer.appendChild(pulse);
    window.setTimeout(() => pulse.remove(), 1700);
  };

  const showChange = (change) => {
    lastShownAt = Date.now();
    const language = String(change.server_name || '').split('.')[0].toUpperCase() || '??';
    const title = String(change.title || '名称不明');

    state.textContent = `${language} ${copy.label}`;
    link.textContent = copy.template.replace('%TITLE%', title);
    link.href = articleUrl(change);
    link.classList.add('is-visible');

    panel.classList.remove('wiki-live-flash');
    void panel.offsetWidth;
    panel.classList.add('wiki-live-flash');

    makePulse();
    window.setTimeout(makePulse, 120);
    window.setTimeout(makePulse, 260);

    if (hideTimer) window.clearTimeout(hideTimer);
    hideTimer = window.setTimeout(() => {
      link.classList.remove('is-visible');
    }, 4300);
  };

  const releaseLatest = () => {
    releaseTimer = null;
    if (!latestPending) return;
    const change = latestPending;
    latestPending = null;
    showChange(change);
  };

  const queueChange = (change) => {
    const elapsed = Date.now() - lastShownAt;
    if (elapsed >= minimumInterval && !releaseTimer) {
      showChange(change);
      return;
    }

    latestPending = change;
    if (!releaseTimer) {
      releaseTimer = window.setTimeout(releaseLatest, Math.max(0, minimumInterval - elapsed));
    }
  };

  const isHumanArticleEdit = (change) => {
    if (!change || change.meta?.domain === 'canary') return false;
    if (typeof change.server_name !== 'string' || !change.server_name.endsWith('.wikipedia.org')) return false;
    if (Number(change.namespace) !== 0) return false;
    if (change.bot === true) return false;
    return change.type === 'edit' || change.type === 'new';
  };

  const disconnect = () => {
    if (!source) return;
    source.close();
    source = null;
    panel.classList.remove('wiki-live-connected');
  };

  const connect = () => {
    if (source || document.hidden) return;

    state.textContent = copy.connecting;
    source = new EventSource(streamUrl);

    source.onopen = () => {
      panel.classList.add('wiki-live-connected');
      state.textContent = copy.connected;
    };

    source.onmessage = (event) => {
      try {
        const change = JSON.parse(event.data);
        if (isHumanArticleEdit(change)) queueChange(change);
      } catch (_) {
        // 壊れたイベントは無視する。
      }
    };

    source.onerror = () => {
      panel.classList.remove('wiki-live-connected');
      state.textContent = copy.reconnecting;
      // EventSource 自身の自動再接続に任せる。
    };
  };

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      disconnect();
    } else {
      connect();
    }
  });

  window.addEventListener('pagehide', disconnect, { once: true });
  connect();
})();
