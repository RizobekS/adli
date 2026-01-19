(function () {
  function qs(sel) { return document.querySelector(sel); }

  function escapeHtml(str) {
    return String(str)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function getConfig() {
    const el = qs('#adli-modal-config');
    if (!el) return null;
    return {
      urlTemplate: el.dataset.historyUrlTemplate || '',
      loading: el.dataset.i18nLoading || 'Loading...',
      empty: el.dataset.i18nEmpty || 'Empty.',
      error: el.dataset.i18nError || 'Error.',
      title: el.dataset.i18nTitle || 'History',
      close: el.dataset.i18nClose || 'Close',
    };
  }

  const modalRoot = qs('#modal-root');
  if (!modalRoot) return;

  function renderModal(cfg) {
    modalRoot.innerHTML = `
      <div id="historyModal"
           class="fixed inset-0 z-[999] hidden items-center justify-center bg-black/40 backdrop-blur-sm p-4">
        <div id="historyPanel"
             class="w-full max-w-2xl bg-white rounded-2xl shadow-xl border border-gray-200
                    opacity-0 translate-y-3 scale-[0.98] transition duration-200 ease-out">
          <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200">
            <div>
              <div class="text-sm text-gray-500">${escapeHtml(cfg.title)}</div>
              <div id="modalTitle" class="text-lg font-semibold">-</div>
            </div>
            <button type="button" class="text-gray-600 hover:text-gray-900" id="historyCloseX">✕</button>
          </div>

          <div class="px-5 py-4">
            <div id="modalBody" class="space-y-3 text-sm text-gray-700">
              <div class="text-gray-500">${escapeHtml(cfg.loading)}</div>
            </div>
          </div>

          <div class="px-5 py-4 border-t border-gray-200 flex justify-end">
            <button type="button" class="rounded-lg bg-gray-100 px-4 py-2 text-sm hover:bg-gray-200" id="historyCloseBtn">
              ${escapeHtml(cfg.close)}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function escCloseOnce(e) {
    if (e.key === 'Escape') window.closeHistory();
  }

  // глобальные функции, чтобы твой onclick="openHistory('...')" работал
  window.openHistory = function (publicId) {
    const cfg = getConfig();
    if (!cfg || !cfg.urlTemplate) return;

    if (!document.getElementById('historyModal')) renderModal(cfg);

    const modal = document.getElementById('historyModal');
    const panel = document.getElementById('historyPanel');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');

    modal.classList.remove('hidden');
    modal.classList.add('flex');

    requestAnimationFrame(() => {
      panel.classList.remove('opacity-0', 'translate-y-3', 'scale-[0.98]');
      panel.classList.add('opacity-100', 'translate-y-0', 'scale-100');
    });

    modalTitle.textContent = publicId;
    modalBody.innerHTML = `<div class="text-gray-500">${escapeHtml(cfg.loading)}</div>`;

    const url = cfg.urlTemplate.replace("PUBLIC_ID", publicId);

    fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(r => r.json())
      .then(data => {
        const history = data.history || [];
        if (!history.length) {
          modalBody.innerHTML = `<div class="text-gray-500">${escapeHtml(cfg.empty)}</div>`;
          return;
        }

        modalBody.innerHTML = history.map(item => {
          const dt = new Date(item.created_at);
          const when = isNaN(dt) ? item.created_at : dt.toLocaleString();

          const fromTo = (item.from_status || item.to_status)
            ? `<div class="text-xs text-gray-500 mt-1">${escapeHtml(item.from_status || '')} ${item.to_status ? '→ ' + escapeHtml(item.to_status) : ''}</div>`
            : '';

          const comment = item.comment
            ? `<div class="text-gray-700 mt-1">${escapeHtml(item.comment)}</div>`
            : '';

          return `
            <div class="rounded-lg border border-gray-200 p-3 bg-gray-50">
              <div class="flex items-center justify-between gap-2">
                <div class="font-medium">${escapeHtml(item.action || '')}</div>
                <div class="text-xs text-gray-500">${escapeHtml(when)}</div>
              </div>
              ${fromTo}
              ${comment}
            </div>
          `;
        }).join('');
      })
      .catch(() => {
        modalBody.innerHTML = `<div class="text-red-600">${escapeHtml(cfg.error)}</div>`;
      });

    // клики
    modal.onclick = (e) => { if (e.target === modal) window.closeHistory(); };
    document.addEventListener('keydown', escCloseOnce);

    // кнопки
    const closeX = document.getElementById('historyCloseX');
    const closeBtn = document.getElementById('historyCloseBtn');
    if (closeX) closeX.onclick = window.closeHistory;
    if (closeBtn) closeBtn.onclick = window.closeHistory;
  };

  window.closeHistory = function () {
    const modal = document.getElementById('historyModal');
    const panel = document.getElementById('historyPanel');
    if (!modal || !panel) return;

    panel.classList.remove('opacity-100', 'translate-y-0', 'scale-100');
    panel.classList.add('opacity-0', 'translate-y-3', 'scale-[0.98]');

    setTimeout(() => {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
      document.removeEventListener('keydown', escCloseOnce);
    }, 180);
  };
})();
