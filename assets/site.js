// Mindfully Priya - small motion layer. Everything here is decoration: the
// page reads the same with this file blocked or with reduced motion on.
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) return;
  document.documentElement.classList.add('motion');

  // Sections ease in as they reach the viewport
  var targets = document.querySelectorAll(
    '.section .wrap > *, .band .wrap > *, .band > .split, .prose-wrap > *, .page-hero-inner > *');
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -8% 0px' });
  targets.forEach(function (el) {
    if (el.getBoundingClientRect().top > window.innerHeight) { el.classList.add('reveal'); io.observe(el); }
  });

  // Hero headline arrives a word at a time
  var h1 = document.querySelector('.home-hero h1');
  if (h1) {
    var words = h1.textContent.trim().split(/\s+/);
    h1.setAttribute('aria-label', h1.textContent.trim());
    h1.innerHTML = words.map(function (w, i) {
      return '<span class="word" aria-hidden="true" style="animation-delay:' + (0.35 + i * 0.07).toFixed(2) + 's">' + w + '</span>';
    }).join(' ');
  }

  leaves(document.querySelector('.home-hero .leaves'));
  breathe(document.querySelector('.breath'));

  // Autumn leaves drifting down over the hero photograph
  function leaves(canvas) {
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var colours = ['#b5703a', '#c98b3c', '#9c4a2a', '#d9a441', '#7f3b22'];
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var W, H, list = [], running = false, last = 0;
    function size() {
      W = canvas.clientWidth; H = canvas.clientHeight;
      canvas.width = W * dpr; canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function leaf(top) {
      return {
        x: Math.random() * W, y: top ? Math.random() * H : -30,
        s: 7 + Math.random() * 9, vy: 18 + Math.random() * 26,
        sway: 20 + Math.random() * 40, phase: Math.random() * 6.28, spin: (Math.random() - .5) * 1.6,
        r: Math.random() * 6.28, c: colours[(Math.random() * colours.length) | 0], a: .55 + Math.random() * .4
      };
    }
    function draw(l) {
      ctx.save();
      ctx.translate(l.x + Math.sin(l.phase) * l.sway, l.y);
      ctx.rotate(l.r);
      ctx.scale(1, .55 + .45 * Math.abs(Math.cos(l.phase * 1.3)));
      ctx.globalAlpha = l.a;
      ctx.fillStyle = l.c;
      ctx.beginPath();
      ctx.moveTo(0, -l.s);
      ctx.bezierCurveTo(l.s * .9, -l.s * .5, l.s * .7, l.s * .6, 0, l.s);
      ctx.bezierCurveTo(-l.s * .7, l.s * .6, -l.s * .9, -l.s * .5, 0, -l.s);
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,.25)';
      ctx.lineWidth = .8;
      ctx.beginPath(); ctx.moveTo(0, -l.s * .8); ctx.lineTo(0, l.s * 1.25); ctx.stroke();
      ctx.restore();
    }
    function tick(t) {
      if (!running) return;
      var dt = Math.min((t - last) / 1000 || 0, .05); last = t;
      ctx.clearRect(0, 0, W, H);
      list.forEach(function (l, i) {
        l.y += l.vy * dt; l.phase += dt * .9; l.r += l.spin * dt;
        if (l.y > H + 30) list[i] = leaf(false);
        draw(l);
      });
      requestAnimationFrame(tick);
    }
    size();
    var count = W < 600 ? 12 : 22;
    for (var i = 0; i < count; i++) list.push(leaf(true));
    window.addEventListener('resize', size);
    new IntersectionObserver(function (e) {
      var was = running;
      running = e[0].isIntersecting;
      if (running && !was) { last = performance.now(); requestAnimationFrame(tick); }
    }).observe(canvas);
  }

  // Guided breath: in for four, out for six, while the section is on screen
  function breathe(el) {
    if (!el) return;
    var label = el.querySelector('.breath-label');
    var count = el.querySelector('.breath-count');
    var timer = null, n = 0;
    var steps = [['Breathe in', 4, 'inhale'], ['Breathe out', 6, 'exhale']];
    function step() {
      var s = steps[n % 2];
      el.classList.remove('inhale', 'exhale'); void el.offsetWidth; el.classList.add(s[2]);
      label.textContent = s[0];
      var left = s[1];
      count.textContent = left;
      clearInterval(timer);
      timer = setInterval(function () {
        left -= 1;
        if (left > 0) { count.textContent = left; }
        else { clearInterval(timer); n += 1; step(); }
      }, 1000);
    }
    new IntersectionObserver(function (e) {
      if (e[0].isIntersecting) { if (!el.classList.contains('on')) { el.classList.add('on'); n = 0; step(); } }
      else { clearInterval(timer); el.classList.remove('on', 'inhale', 'exhale'); label.textContent = 'Breathe in'; count.textContent = ''; }
    }, { threshold: .5 }).observe(el);
  }
})();
