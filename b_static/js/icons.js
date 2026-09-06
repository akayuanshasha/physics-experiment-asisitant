/* 与 templates/_icons.html 配套的动态 SVG 图标。 */
(function () {
    'use strict';
    var OPEN = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
    var CLOSE = '</svg>';
    function wrap(paths) { return OPEN + paths + CLOSE; }

    var paths = {
        clipboard: '<rect x="8" y="2.5" width="8" height="4" rx="1"/><path d="M16 4.5h2a2 2 0 0 1 2 2V20a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2h2"/>',
        plus: '<path d="M12 5v14M5 12h14"/>',
        minus: '<path d="M5 12h14"/>',
        trash: '<path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6h14zM10 11v6M14 11v6"/>',
        chart: '<path d="M3 3v18h18"/><path d="m7 14 4-4 3 3 5.5-6.5"/>',
        search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
        robot: '<rect x="4" y="8" width="16" height="12" rx="2.2"/><path d="M12 8V4M10 4h4M9.5 13.5h.01M14.5 13.5h.01M9.5 16.5h5"/>',
        download: '<path d="M12 3v12m-5-5 5 5 5-5M4 21h16"/>',
        upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
        paperclip: '<path d="m20.5 11.5-8.6 8.6a5 5 0 0 1-7.1-7.1l9.1-9.1a3.5 3.5 0 0 1 5 5l-9.2 9.2a2 2 0 1 1-2.8-2.8l8.5-8.5"/>',
        copy: '<rect x="9" y="9" width="11.5" height="11.5" rx="2"/><path d="M5.5 15H4.8A1.8 1.8 0 0 1 3 13.2V4.8A1.8 1.8 0 0 1 4.8 3h8.4A1.8 1.8 0 0 1 15 4.8v.7"/>',
        book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20V2.5H6.5A2.5 2.5 0 0 0 4 5v14.5z"/>',
        sigma: '<path d="M17.5 7V5H6.5l6.2 7-6.2 7h11v-2"/>',
        image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.7"/><path d="m21 15.5-4.5-4.5L7 20"/>',
        zap: '<path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z"/>',
        'file-text': '<path d="M14 2.5H6a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8.5z"/><path d="M14 2.5v6h6M8.5 13.5H15M8.5 17h4.5"/>',
        send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
        refresh: '<path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/>',
        user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-3.9 3.6-6.5 8-6.5s8 2.6 8 6.5"/>',
        eraser: '<path d="m7 21-4.3-4.3a1.5 1.5 0 0 1 0-2.1L13.6 3.6a1.5 1.5 0 0 1 2.1 0l4.7 4.7a1.5 1.5 0 0 1 0 2.1L11 19.9"/><path d="M7 21h10M9.5 8.5l6 6"/>',
        'chevron-down': '<path d="m6 9 6 6 6-6"/>',
        'check-circle': '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.6 2.6L16.5 9"/>'
    };

    window.AppIcons = {};
    Object.keys(paths).forEach(function (name) {
        window.AppIcons[name] = wrap(paths[name]);
    });
})();
