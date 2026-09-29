/* One-shot, reference-style pastel reveals; file:// safe, no dependencies. */
(() => {
  'use strict';
  const panels = [...document.querySelectorAll('[data-color-reveal]')];
  if (!panels.length || !('IntersectionObserver' in window)) return;

  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  let revealObserver;
  let visibilityObserver;

  function observeReveals() {
    if (revealObserver) revealObserver.disconnect();
    if (preference.matches) return;
    // Percentage root margins use viewport width, even on the vertical axis.
    const bottomMargin = Math.round(window.innerHeight * .3);
    revealObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting || entry.boundingClientRect.top <= window.innerHeight * .7) {
          entry.target.classList.add('is-revealed');
          revealObserver.unobserve(entry.target);
        }
      }
    }, {rootMargin: `0px 0px -${bottomMargin}px 0px`});
    for (const panel of panels) {
      if (!panel.classList.contains('is-revealed')) revealObserver.observe(panel);
    }
  }

  function configure() {
    if (revealObserver) revealObserver.disconnect();
    if (visibilityObserver) visibilityObserver.disconnect();
    document.documentElement.classList.toggle('home-motion-ready', !preference.matches);
    if (preference.matches) {
      // Also settle a running transition when the preference changes live.
      for (const panel of panels) panel.classList.add('is-revealed');
      return;
    }
    visibilityObserver = new IntersectionObserver(entries => {
      for (const entry of entries) entry.target.classList.toggle('is-on-screen', entry.isIntersecting);
    });
    for (const panel of panels) visibilityObserver.observe(panel);
    observeReveals();
  }

  preference.addEventListener('change', configure);
  window.addEventListener('resize', observeReveals, {passive:true});
  configure();
})();
