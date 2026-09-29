/* Small progressive enhancements. All content and navigation are built as HTML. */
(() => {
  'use strict';
  // The script's own URL locates the exported site on disk or under a web subpath.
  const siteRoot = new URL('../../', document.currentScript.src);
  const sitePath = path => {
    if (!path.startsWith('/') || path.startsWith('//')) return new URL(path, siteRoot).href;
    const url = new URL(path.slice(1), siteRoot);
    if (url.pathname.endsWith('/')) url.pathname += 'index.html';
    return url.href;
  };
  const header = document.querySelector('.site-header');
  const updateHeader = () => header?.classList.toggle('is-scrolled', window.scrollY > 20);
  window.addEventListener('scroll', updateHeader, { passive: true });
  updateHeader();

  // Hosted projects stay in their own repositories. Direct-file articles keep
  // their local preview until the reader explicitly requests the online app.
  document.querySelectorAll('[data-project-url]').forEach(project => {
    const url = new URL(project.dataset.projectUrl);
    const stage = project.querySelector('.project-stage');
    const preview = project.querySelector('.project-preview');
    const loadButton = project.querySelector('[data-project-load]');
    const closeButton = project.querySelector('[data-project-close]');
    const status = project.querySelector('[data-project-status]');
    let frame, timeout, observer;
    const reset = message => {
      clearTimeout(timeout);
      frame?.remove();
      frame = null;
      preview.hidden = false;
      loadButton.hidden = false;
      loadButton.disabled = false;
      loadButton.textContent = 'Use in this article';
      closeButton.hidden = true;
      status.textContent = message;
      stage.removeAttribute('aria-busy');
    };
    const fail = () => {
      reset('The interactive preview is unavailable. Try again or open the website in a new tab.');
      loadButton.textContent = 'Try again';
    };
    const start = () => {
      if (frame) return;
      observer?.disconnect();
      if (!navigator.onLine) {
        reset('You are offline. The saved preview is available below.');
        return;
      }
      status.textContent = 'Loading interactive preview…';
      loadButton.disabled = true;
      stage.setAttribute('aria-busy', 'true');
      frame = document.createElement('iframe');
      const pendingFrame = frame;
      frame.className = 'project-frame';
      frame.title = project.querySelector('.embed-title').textContent;
      frame.referrerPolicy = 'no-referrer';
      frame.allow = 'fullscreen';
      frame.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads');
      frame.addEventListener('load', () => {
        // A successful load event can also mean a hosted 404. Only a ready
        // response from the actual application replaces the saved preview.
        if (frame === pendingFrame) frame.contentWindow.postMessage({ type: 'type-null:embed-ping' }, url.origin);
      });
      frame.addEventListener('error', () => { if (frame === pendingFrame) fail(); });
      frame.src = url.href;
      stage.append(frame);
      timeout = setTimeout(fail, 8000);
    };
    window.addEventListener('message', event => {
      if (!frame || event.source !== frame.contentWindow || event.origin !== url.origin) return;
      if (event.data?.type === 'type-null:embed-ready') {
        clearTimeout(timeout);
        frame.classList.add('is-ready');
        preview.hidden = true;
        loadButton.hidden = true;
        loadButton.disabled = false;
        closeButton.hidden = false;
        stage.removeAttribute('aria-busy');
        status.textContent = '';
      } else if (event.data?.type === 'type-null:focus-embed' && frame.classList.contains('is-ready')) {
        frame.scrollIntoView({ block: 'start', behavior: 'instant' });
      }
    });
    loadButton.hidden = false;
    loadButton.addEventListener('click', start);
    closeButton.addEventListener('click', () => {
      reset('Interactive preview closed.');
      loadButton.focus();
    });
    window.addEventListener('offline', () => reset('You are offline. The saved preview is available below.'));
    if (/^https?:$/.test(location.protocol) && navigator.onLine && 'IntersectionObserver' in window) {
      observer = new IntersectionObserver(entries => {
        if (entries.some(entry => entry.isIntersecting)) start();
      });
      observer.observe(stage);
    }
  });
  const menu = document.querySelector('.mobile-navigation');
  // The details element keeps the mobile menu usable without JavaScript.
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu?.open && !document.querySelector('dialog[open]')) {
      menu.open = false;
      menu.querySelector('summary').focus();
    }
  });
  document.querySelector('.gnav')?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => { menu.open = false; }));

  const hero = document.querySelector('.home-hero');
  if (hero) {
    const slides = [...hero.querySelectorAll('[data-slide]')];
    const selectors = [...hero.querySelectorAll('[data-slide-to]')];
    const controls = hero.querySelector('.hero-pagination');
    const pause = hero.querySelector('[data-slide-pause]');
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    let current = 0;
    let paused = reducedMotion.matches;
    let timer;
    const show = index => {
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, i) => { slide.hidden = i !== current; });
      selectors.forEach((button, i) => button.setAttribute('aria-pressed', String(i === current)));
    };
    const schedule = () => {
      clearInterval(timer);
      if (!paused && !document.hidden && !hero.matches(':hover') && !hero.contains(document.activeElement)) {
        timer = setInterval(() => show(current + 1), 6000);
      }
    };
    const setPause = value => {
      paused = value;
      pause.setAttribute('aria-label', paused ? 'Play featured slideshow' : 'Pause featured slideshow');
      pause.textContent = paused ? '▷' : 'Ⅱ';
      schedule();
    };
    if (slides.length > 1) {
      controls.hidden = false;
      selectors.forEach((button, i) => button.addEventListener('click', () => { show(i); schedule(); }));
      pause.addEventListener('click', () => setPause(!paused));
      hero.addEventListener('mouseenter', schedule);
      hero.addEventListener('mouseleave', schedule);
      hero.addEventListener('focusin', schedule);
      hero.addEventListener('focusout', () => setTimeout(schedule));
      document.addEventListener('visibilitychange', schedule);
      reducedMotion.addEventListener('change', () => setPause(reducedMotion.matches));
      setPause(paused);
    }
  }
  const topicFilter = document.querySelector('.topic-filter');
  if (topicFilter) topicFilter.hidden = false;
  document.querySelectorAll('[data-filter]').forEach(button => {
    button.addEventListener('click', () => {
      const topic = button.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(item => {
        const selected = item === button;
        item.classList.toggle('is-active', selected);
        item.setAttribute('aria-pressed', String(selected));
      });
      document.querySelector('.home-news-list')?.classList.toggle('is-filtered', topic !== 'all');
      let count = 0;
      document.querySelectorAll('.post-card').forEach(card => {
        card.hidden = topic !== 'all' && card.dataset.topic !== topic;
        if (!card.hidden) count++;
      });
      const status = document.querySelector('.filter-status');
      if (status) status.textContent = `${count} ${count === 1 ? 'post' : 'posts'} shown.`;
    });
  });

  const dialog = document.querySelector('#site-search');
  const field = document.querySelector('#site-search-input');
  const results = document.querySelector('#search-results');
  const searchStatus = document.querySelector('.search-status');
  const searchData = window.TYPE_NULL_SEARCH_INDEX;
  const index = Array.isArray(searchData) ? searchData : searchData?.posts;
  let opener;
  const renderResults = () => {
    if (!Array.isArray(index)) return;
    const query = field.value.trim().toLocaleLowerCase();
    results.replaceChildren();
    if (!query) { searchStatus.textContent = 'Start typing to explore the journal.'; return; }
    const matches = index.filter(post => `${post.title} ${post.description || ''} ${typeof post.topic === 'object' ? post.topic.label : post.topic} ${(post.tags || []).join(' ')} ${post.text || ''}`.toLocaleLowerCase().includes(query));
    searchStatus.textContent = matches.length ? `${matches.length} ${matches.length === 1 ? 'result' : 'results'} for “${field.value.trim()}”` : 'No matches. Try “cards”, “probability”, or “notes”.';
    matches.forEach(post => {
      const link = document.createElement('a');
      link.className = 'search-result';
      link.href = sitePath(post.url);
      const title = document.createElement('strong'); title.textContent = post.title;
      const description = document.createElement('p'); description.textContent = post.description;
      link.append(title, description); results.append(link);
    });
  };
  if (dialog && typeof dialog.showModal === 'function') {
    document.querySelectorAll('[data-search-open]').forEach(button => {
      button.hidden = false;
      button.addEventListener('click', () => {
        opener = button;
        dialog.showModal();
        field.focus();
        if (!Array.isArray(index)) {
          searchStatus.textContent = 'The search index is missing. Browse the topics above, or rebuild the complete site folder.';
          return;
        }
        renderResults();
      });
    });
    document.querySelector('[data-search-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) { const bounds = dialog.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close(); } });
    // Search inputs normally consume the first Escape to clear their value.
    // In this modal, Escape consistently closes it and returns keyboard focus.
    dialog.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !event.isComposing) {
        event.preventDefault();
        dialog.close();
      }
    });
    dialog.addEventListener('close', () => opener?.focus());
    field.addEventListener('input', renderResults);
    document.addEventListener('keydown', event => { if ((event.metaKey || event.ctrlKey) && event.key === 'k') { event.preventDefault(); document.querySelector('[data-search-open]')?.click(); } });
  }

  const shareURL = () => { const canonical = document.querySelector('link[rel="canonical"]')?.href || location.href; const url = new URL(canonical); url.search = location.search; url.hash = location.hash; return url.href; };
  const shareStatus = document.querySelector('.share-status');
  async function copyLink(button) {
    try {
      await navigator.clipboard.writeText(shareURL());
      if (shareStatus) shareStatus.textContent = 'Link copied!';
      const original = button.innerHTML;
      button.textContent = 'Link copied!';
      setTimeout(() => { button.innerHTML = original; }, 2400);
    } catch (_) {
      if (shareStatus) shareStatus.textContent = 'Copy this link: ' + shareURL();
      else window.prompt('Copy this link:', shareURL());
    }
  }
  document.querySelectorAll('[data-copy-link],[data-share]').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', async () => {
      if (button.hasAttribute('data-share') && navigator.share) {
        try { await navigator.share({ title: document.title, url: shareURL() }); } catch (error) { if (error.name !== 'AbortError') await copyLink(button); }
      } else await copyLink(button);
    });
  });
})();
