/* Motion for the checker. Uses anime.js (MIT, vendored in /static/vendor).
   Original timings and choreography. Everything is skipped when the user asks for reduced
   motion or when the library did not load, and elements are visible by default. */
(function () {
  const A = window.anime;
  const calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ok = !!(A && A.animate && A.stagger) && !calm;
  const ease = 'outCubic';
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

  function hide(els) { els.forEach(e => { e.style.opacity = '0'; }); }

  window.Motion = {
    enabled: ok,

    /* Input page: hero text rises in, cards follow one after another. */
    pageIn() {
      if (!ok) return;
      const hero = $$('.hero .tag, .hero h1, .hero p');
      const cards = $$('.grid .card');
      hide(cards); hide(hero);
      A.animate(hero, { opacity: [0, 1], translateY: [14, 0], duration: 560, delay: A.stagger(90), ease });
      A.animate(cards, { opacity: [0, 1], translateY: [18, 0], duration: 600, delay: A.stagger(110, { start: 150 }), ease });
      $$('.rules li').forEach(li => { li.style.opacity = '0'; });
      A.animate($$('.rules li'), { opacity: [0, 1], translateX: [-8, 0], duration: 420, delay: A.stagger(70, { start: 450 }), ease });
    },

    /* Switching between listing and package input. */
    swap(showEl) {
      if (!ok) return;
      A.animate(showEl, { opacity: [0, 1], translateY: [8, 0], duration: 320, ease });
    },

    /* A line sweeps down the text area while a check runs. Returns a stop function. */
    scan(host) {
      if (!ok) return () => {};
      const line = document.createElement('div');
      line.className = 'scanline';
      host.style.position = 'relative';
      host.appendChild(line);
      const a = A.animate(line, { top: ['2%', '96%'], duration: 900, loop: true, alternate: true, ease: 'inOutSine' });
      return () => { a.pause(); line.remove(); };
    },

    /* Results: banner settles, numbers count up, rows file in, chips pop. */
    resultsIn() {
      if (!ok) return;
      const banner = document.querySelector('.banner');
      const rows = $$('.item');
      const chips = $$('.chip');
      hide([banner]); hide(rows);
      A.animate(banner, { opacity: [0, 1], translateY: [14, 0], scale: [0.985, 1], duration: 520, ease });
      $$('.counts b').forEach((b, i) => {
        const to = parseInt(b.textContent, 10) || 0;
        b.textContent = '0';
        const o = { v: 0 };
        A.animate(o, { v: to, duration: 700, delay: 250 + i * 80, ease, onUpdate: () => { b.textContent = String(Math.round(o.v)); } });
      });
      A.animate(rows, { opacity: [0, 1], translateY: [16, 0], duration: 480, delay: A.stagger(90, { start: 380 }), ease });
      A.animate(chips, { scale: [0.6, 1], duration: 420, delay: A.stagger(90, { start: 520 }), ease: 'outBack' });
    },

    /* Small confirmation when a sample fills the text area. */
    flash(el) {
      if (!ok) return;
      A.animate(el, { backgroundColor: ['#f6ead0', '#ffffff'], duration: 700, ease: 'outQuad' });
    }
  };
})();
