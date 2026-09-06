(function () {
    'use strict';

    var switcher = document.querySelector('[data-primary-switcher]');
    if (!switcher) return;

    var links = Array.prototype.slice.call(
        switcher.querySelectorAll('[data-switch-target]')
    );

    function setActive(target) {
        switcher.dataset.active = target;
        links.forEach(function (link) {
            var active = link.dataset.switchTarget === target;
            link.classList.toggle('is-active', active);
            if (active) link.setAttribute('aria-current', 'page');
            else link.removeAttribute('aria-current');
        });
    }

    function restoreCurrentPage() {
        switcher.classList.remove('is-switching');
        setActive(switcher.dataset.current);
    }

    links.forEach(function (link) {
        link.addEventListener('click', function (event) {
            if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

            var target = link.dataset.switchTarget;
            if (target === switcher.dataset.current) {
                event.preventDefault();
                return;
            }

            event.preventDefault();
            setActive(target);
            switcher.classList.add('is-switching');

            var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            window.setTimeout(function () {
                window.location.assign(link.href);
            }, reducedMotion ? 0 : 220);
        });
    });

    window.addEventListener('pageshow', restoreCurrentPage);
    restoreCurrentPage();
})();
