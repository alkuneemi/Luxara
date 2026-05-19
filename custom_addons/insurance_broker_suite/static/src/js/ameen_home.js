/* ══════════════════════════════════════════════════════════════════
   AMEEN INSURANCE PORTAL — HOME PAGE JS
   Animations, counters, navbar effects, particle effects
   ══════════════════════════════════════════════════════════════════ */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        initNavbar();
        initCounters();
        initScrollAnimations();
        initParticles();
        initHamburger();
        initSmoothScroll();
    });

    /* ── Navbar scroll effect ── */
    function initNavbar() {
        var nav = document.getElementById('ameenNav');
        if (!nav) return;
        window.addEventListener('scroll', function() {
            if (window.scrollY > 20) {
                nav.classList.add('scrolled');
            } else {
                nav.classList.remove('scrolled');
            }
        }, { passive: true });
    }

    /* ── Animated counters ── */
    function initCounters() {
        var nums = document.querySelectorAll('.ameen-stat-num');
        if (!nums.length) return;

        var observed = false;
        var observer = new IntersectionObserver(function(entries) {
            if (observed) return;
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    observed = true;
                    nums.forEach(function(el) {
                        animateCounter(el);
                    });
                }
            });
        }, { threshold: 0.3 });

        if (nums[0]) observer.observe(nums[0]);
    }

    function animateCounter(el) {
        var target = parseInt(el.getAttribute('data-count'), 10);
        var duration = 2000;
        var start = performance.now();

        function update(now) {
            var elapsed = now - start;
            var progress = Math.min(elapsed / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.floor(eased * target).toLocaleString('ar-EG');
            if (progress < 1) requestAnimationFrame(update);
            else el.textContent = target.toLocaleString('ar-EG');
        }

        requestAnimationFrame(update);
    }

    /* ── Scroll animations ── */
    function initScrollAnimations() {
        var animEls = document.querySelectorAll(
            '.ameen-service-card, .ameen-value-card, .ameen-testimonial, .ameen-step, .ameen-trust-item'
        );

        var observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

        animEls.forEach(function(el, i) {
            el.style.opacity = '0';
            el.style.transform = 'translateY(28px)';
            el.style.transition = 'opacity 0.6s ease ' + (i * 0.07) + 's, transform 0.6s ease ' + (i * 0.07) + 's';
            observer.observe(el);
        });
    }

    /* ── Particle dots in hero ── */
    function initParticles() {
        var container = document.getElementById('particles');
        if (!container) return;

        var COUNT = 22;
        for (var i = 0; i < COUNT; i++) {
            var dot = document.createElement('div');
            var size = Math.random() * 4 + 2;
            var x = Math.random() * 100;
            var y = Math.random() * 100;
            var delay = Math.random() * 8;
            var dur = 6 + Math.random() * 6;
            var opacity = Math.random() * 0.3 + 0.05;

            dot.style.cssText = [
                'position:absolute',
                'width:' + size + 'px',
                'height:' + size + 'px',
                'background:rgba(132,207,255,' + opacity + ')',
                'border-radius:50%',
                'left:' + x + '%',
                'top:' + y + '%',
                'animation:ameen-float ' + dur + 's ease-in-out ' + delay + 's infinite',
                'pointer-events:none'
            ].join(';');

            container.appendChild(dot);
        }
    }

    /* ── Hamburger menu ── */
    function initHamburger() {
        var btn = document.getElementById('ameenHamburger');
        var links = document.querySelector('.ameen-nav-links');
        if (!btn || !links) return;

        btn.addEventListener('click', function() {
            var isOpen = links.style.display === 'flex';
            if (isOpen) {
                links.style.display = '';
                links.style.flexDirection = '';
            } else {
                links.style.display = 'flex';
                links.style.flexDirection = 'column';
                links.style.position = 'absolute';
                links.style.top = '72px';
                links.style.left = '0';
                links.style.right = '0';
                links.style.background = 'white';
                links.style.padding = '16px 24px';
                links.style.boxShadow = '0 8px 32px rgba(52,75,155,0.12)';
                links.style.zIndex = '999';
            }
        });
    }

    /* ── Smooth scroll for anchor links ── */
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(function(a) {
            a.addEventListener('click', function(e) {
                var id = this.getAttribute('href').slice(1);
                var target = document.getElementById(id);
                if (!target) return;
                e.preventDefault();
                var offset = 80;
                var y = target.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top: y, behavior: 'smooth' });
            });
        });
    }

})();
