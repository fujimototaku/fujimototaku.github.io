(() => {
  const box = document.querySelector('[data-wiki-news]');
  if (!box) return;

  const titleEl = box.querySelector('[data-wiki-title]');
  const extractEl = box.querySelector('[data-wiki-extract]');
  const linkEl = box.querySelector('[data-wiki-link]');
  const imageEl = box.querySelector('[data-wiki-image]');
  const button = box.querySelector('[data-wiki-refresh]');
  const metaEl = box.querySelector('[data-wiki-meta]');
  const cacheKey = 'fujimototaku:useless-wikipedia:v1';

  const text = {
    unknownTitle: box.dataset.wikiUnknownTitle || '題名不明',
    unknownText: box.dataset.wikiUnknownText || '説明すら特にありません。',
    meta: box.dataset.wikiMetaText || '日本語版Wikipediaから無作為に選出',
    loadingTitle: box.dataset.wikiLoadingTitle || 'どうでもいい記事を捜索中…',
    loadingText: box.dataset.wikiLoadingText || '百科事典の奥地を徘徊しています。',
    errorTitle: box.dataset.wikiErrorTitle || '本日はどうでもいいニュースなし',
    errorText: box.dataset.wikiErrorText || 'Wikipediaとの通信に失敗しました。たぶんどうでもいいです。'
  };

  const todayKey = () => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  };

  const trimText = (value, max = 220) => {
    const clean = String(value || '').replace(/\s+/g, ' ').trim();
    return clean.length > max ? `${clean.slice(0, max).trim()}…` : clean;
  };

  const render = (article) => {
    titleEl.textContent = article.title || text.unknownTitle;
    extractEl.textContent = trimText(article.extract || text.unknownText);
    linkEl.href = article.fullurl || `https://ja.wikipedia.org/wiki/${encodeURIComponent(article.title || '')}`;
    linkEl.hidden = false;

    if (article.thumbnail?.source) {
      imageEl.src = article.thumbnail.source;
      imageEl.alt = `${article.title || text.unknownTitle}の画像`;
      imageEl.hidden = false;
    } else {
      imageEl.hidden = true;
      imageEl.removeAttribute('src');
    }

    metaEl.textContent = text.meta;
  };

  const setLoading = () => {
    titleEl.textContent = text.loadingTitle;
    extractEl.textContent = text.loadingText;
    linkEl.hidden = true;
    imageEl.hidden = true;
    metaEl.textContent = '';
  };

  const fetchRandomArticle = async () => {
    const url = new URL('https://ja.wikipedia.org/w/api.php');
    const params = {
      action: 'query',
      format: 'json',
      origin: '*',
      generator: 'random',
      grnnamespace: '0',
      grnlimit: '1',
      grnfilterredir: 'nonredirects',
      prop: 'extracts|info|pageimages',
      exintro: '1',
      explaintext: '1',
      inprop: 'url',
      pithumbsize: '220'
    };

    Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`Wikipedia API ${response.status}`);

    const data = await response.json();
    const pages = Object.values(data?.query?.pages || {});
    if (!pages.length) throw new Error('No random Wikipedia page returned');
    return pages[0];
  };

  const load = async ({ force = false } = {}) => {
    setLoading();

    if (!force) {
      try {
        const cached = JSON.parse(localStorage.getItem(cacheKey) || 'null');
        if (cached?.date === todayKey() && cached?.article) {
          render(cached.article);
          return;
        }
      } catch (_) {}
    }

    try {
      const article = await fetchRandomArticle();
      render(article);
      try {
        localStorage.setItem(cacheKey, JSON.stringify({ date: todayKey(), article }));
      } catch (_) {}
    } catch (error) {
      console.error('Wikipedia random article failed:', error);
      titleEl.textContent = text.errorTitle;
      extractEl.textContent = text.errorText;
      linkEl.hidden = true;
      imageEl.hidden = true;
      metaEl.textContent = '';
    }
  };

  button?.addEventListener('click', () => load({ force: true }));
  load();
})();
