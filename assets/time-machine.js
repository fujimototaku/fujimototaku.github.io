const machine = document.querySelector('[data-time-machine]');

if (machine) {
  const parseJson = (id) => {
    const node = document.getElementById(id);
    if (!node) return [];
    try {
      const value = JSON.parse(node.textContent || '[]');
      return Array.isArray(value) ? value : [];
    } catch (error) {
      console.error(`Failed to parse ${id}`, error);
      return [];
    }
  };

  const manual = parseJson('tm-manual-data');
  const announcements = parseJson('tm-announcement-data');
  const posts = parseJson('tm-post-data');

  const DAY = 86400000;
  const toDay = (value) => {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
    const ms = Date.parse(`${value}T00:00:00Z`);
    return Number.isFinite(ms) ? Math.floor(ms / DAY) : null;
  };
  const toIso = (day) => new Date(day * DAY).toISOString().slice(0, 10);
  const formatDate = (day) => {
    const [year, month, date] = toIso(day).split('-').map(Number);
    return `${year}年${month}月${date}日`;
  };

  const normalize = (entry) => {
    const date = typeof entry.date === 'string' ? entry.date.slice(0, 10) : '';
    const day = toDay(date);
    if (day === null || !entry.title) return null;
    return {
      date,
      day,
      type: entry.type || 'other',
      source: entry.source || '',
      title: String(entry.title),
      text: entry.text ? String(entry.text) : '',
      url: entry.url ? String(entry.url) : '',
      image: entry.image ? String(entry.image) : ''
    };
  };

  const seen = new Set();
  const entries = [...manual, ...announcements, ...posts]
    .map(normalize)
    .filter(Boolean)
    .filter((entry) => {
      const key = `${entry.date}\u0000${entry.title}\u0000${entry.url}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .sort((a, b) => a.day - b.day || a.title.localeCompare(b.title, 'ja'));

  const dateInput = machine.querySelector('#tm-date');
  const rangeInput = machine.querySelector('#tm-range');
  const selectedLabel = machine.querySelector('#tm-selected-label');
  const readout = machine.querySelector('#tm-readout');
  const results = machine.querySelector('#tm-results');
  const archiveStatus = machine.querySelector('#tm-archive-status');
  const rangeStart = machine.querySelector('#tm-range-start');
  const rangeEnd = machine.querySelector('#tm-range-end');
  const prevButton = machine.querySelector('#tm-prev');
  const randomButton = machine.querySelector('#tm-random');
  const nextButton = machine.querySelector('#tm-next');
  const screen = machine.querySelector('.tm-screen');

  const typeLabels = {
    diary: '日記',
    announcement: 'お知らせ',
    photo: '写真',
    movie: '映画',
    note: 'note',
    x: 'X',
    activity: '活動',
    book: '本',
    place: '場所',
    other: '記録'
  };

  if (!entries.length) {
    if (results) results.innerHTML = '<div class="tm-empty">まだ時系列データがありません。</div>';
    if (readout) readout.textContent = 'NO DATA';
    [dateInput, rangeInput, prevButton, randomButton, nextButton].forEach((node) => {
      if (node) node.disabled = true;
    });
  } else {
    const minDay = entries[0].day;
    const maxDay = entries[entries.length - 1].day;
    let selectedDay = maxDay;

    if (rangeInput) {
      rangeInput.min = '0';
      rangeInput.max = String(Math.max(1, maxDay - minDay));
      rangeInput.step = '1';
    }
    if (rangeStart) rangeStart.textContent = entries[0].date;
    if (rangeEnd) rangeEnd.textContent = entries[entries.length - 1].date;
    if (archiveStatus) {
      archiveStatus.textContent = `観測範囲 ${entries[0].date} → ${entries[entries.length - 1].date} / ${entries.length}件`;
    }

    const escapeHtml = (value) => String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');

    const safeUrl = (value) => {
      if (!value) return '';
      if (value.startsWith('/')) return value;
      try {
        const url = new URL(value, window.location.origin);
        if (['http:', 'https:'].includes(url.protocol)) return url.href;
      } catch (_) {}
      return '';
    };

    const distanceLabel = (entryDay) => {
      const diff = entryDay - selectedDay;
      if (diff === 0) return 'この日';
      return diff < 0 ? `${Math.abs(diff)}日前` : `${diff}日後`;
    };

    const cardHtml = (entry) => {
      const url = safeUrl(entry.url);
      const title = escapeHtml(entry.title);
      const titleHtml = url
        ? `<a href="${escapeHtml(url)}">${title}</a>`
        : title;
      const imageUrl = safeUrl(entry.image);
      return `
        <article class="tm-card ${entry.day === selectedDay ? 'is-exact' : ''}">
          <div class="tm-card-date">
            ${escapeHtml(entry.date)}
            <span class="tm-card-gap">${escapeHtml(distanceLabel(entry.day))}</span>
          </div>
          <div class="tm-card-body">
            <span class="tm-card-type">${escapeHtml(typeLabels[entry.type] || entry.type)}</span>
            <h3>${titleHtml}</h3>
            ${entry.text ? `<p>${escapeHtml(entry.text)}</p>` : ''}
          </div>
          ${imageUrl ? `<img class="tm-card-image" src="${escapeHtml(imageUrl)}" alt="">` : ''}
        </article>`;
    };

    const render = (animate = false) => {
      if (selectedLabel) selectedLabel.textContent = formatDate(selectedDay);
      if (dateInput) dateInput.value = toIso(selectedDay);
      if (rangeInput) {
        const clamped = Math.min(maxDay, Math.max(minDay, selectedDay));
        rangeInput.value = String(clamped - minDay);
      }

      const exact = entries.filter((entry) => entry.day === selectedDay);
      const before = [...entries].reverse().find((entry) => entry.day < selectedDay) || null;
      const after = entries.find((entry) => entry.day > selectedDay) || null;

      if (readout) {
        if (exact.length) {
          readout.textContent = `RECORD FOUND : ${exact.length}`;
        } else if (before && after) {
          readout.textContent = `空白期間 / 前 ${selectedDay - before.day}日 / 次 ${after.day - selectedDay}日`;
        } else if (before) {
          readout.textContent = `最新記録から ${selectedDay - before.day}日後`;
        } else if (after) {
          readout.textContent = `最初の記録まで ${after.day - selectedDay}日`;
        } else {
          readout.textContent = 'NO RECORD';
        }
      }

      const nearby = exact.length
        ? [
            ...exact,
            ...entries
              .filter((entry) => entry.day !== selectedDay)
              .sort((a, b) => Math.abs(a.day - selectedDay) - Math.abs(b.day - selectedDay))
              .slice(0, Math.max(0, 6 - exact.length))
          ]
        : entries
            .slice()
            .sort((a, b) => Math.abs(a.day - selectedDay) - Math.abs(b.day - selectedDay))
            .slice(0, 6);

      if (results) results.innerHTML = nearby.map(cardHtml).join('');

      if (animate && screen && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        screen.classList.remove('tm-jump');
        void screen.offsetWidth;
        screen.classList.add('tm-jump');
      }
    };

    const selectDay = (day, animate = false) => {
      if (!Number.isFinite(day)) return;
      selectedDay = Math.round(day);
      render(animate);
    };

    dateInput?.addEventListener('change', () => {
      const day = toDay(dateInput.value);
      if (day !== null) selectDay(day, true);
    });

    rangeInput?.addEventListener('input', () => {
      selectDay(minDay + Number(rangeInput.value), false);
    });

    rangeInput?.addEventListener('change', () => render(true));

    prevButton?.addEventListener('click', () => {
      const previous = [...entries].reverse().find((entry) => entry.day < selectedDay);
      if (previous) selectDay(previous.day, true);
    });

    nextButton?.addEventListener('click', () => {
      const next = entries.find((entry) => entry.day > selectedDay);
      if (next) selectDay(next.day, true);
    });

    randomButton?.addEventListener('click', () => {
      const randomDay = minDay + Math.floor(Math.random() * (maxDay - minDay + 1));
      selectDay(randomDay, true);
    });

    render(false);
  }
}
