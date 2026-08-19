(function (global) {
    'use strict';

    var markdownRenderer = typeof global.markdownit === 'function'
        ? global.markdownit({
            html: false,
            breaks: true,
            linkify: true,
            typographer: false
        })
        : null;

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = String(text == null ? '' : text);
        return div.innerHTML;
    }

    function protectMath(text) {
        var segments = [];

        function save(segment) {
            var index = segments.length;
            segments.push(segment);
            return 'MATHPLACEHOLDER' + index + 'END';
        }

        var protectedText = String(text == null ? '' : text)
            .replace(/\$\$[\s\S]*?\$\$/g, save)
            .replace(/\\\[[\s\S]*?\\\]/g, save)
            .replace(/\\\([\s\S]*?\\\)/g, save)
            .replace(/\$(?!\$)(?:\\.|[^$\n])+\$/g, save);

        return { text: protectedText, segments: segments };
    }

    function restoreMath(html, segments) {
        return html.replace(/MATHPLACEHOLDER(\d+)END/g, function (_, index) {
            return escapeHtml(segments[Number(index)] || '');
        });
    }

    function renderToHtml(text) {
        if (!markdownRenderer || !global.DOMPurify) {
            return null;
        }

        var protectedResult = protectMath(text);
        var markdownHtml = markdownRenderer.render(protectedResult.text);
        var htmlWithMath = restoreMath(markdownHtml, protectedResult.segments);

        return global.DOMPurify.sanitize(htmlWithMath, {
            USE_PROFILES: { html: true },
            FORBID_TAGS: [
                'script', 'style', 'iframe', 'object', 'embed', 'form',
                'input', 'button', 'img', 'audio', 'video'
            ],
            FORBID_ATTR: [
                'style', 'srcset', 'onerror', 'onclick', 'onload',
                'onmouseover', 'onfocus'
            ]
        });
    }

    function typeset(element) {
        if (!element || !global.MathJax || !global.MathJax.typesetPromise) {
            return Promise.resolve();
        }

        var startupReady = global.MathJax.startup && global.MathJax.startup.promise
            ? global.MathJax.startup.promise
            : Promise.resolve();

        return startupReady.then(function () {
            if (global.MathJax.typesetClear) {
                global.MathJax.typesetClear([element]);
            }
            return global.MathJax.typesetPromise([element]);
        }).catch(function (error) {
            console.error('数学公式渲染失败：', error);
        });
    }

    function renderInto(element, text) {
        if (!element) {
            return Promise.resolve(false);
        }

        var html = renderToHtml(text);
        if (html === null) {
            element.textContent = String(text == null ? '' : text);
            return Promise.resolve(false);
        }

        element.innerHTML = html;
        return typeset(element).then(function () { return true; });
    }

    global.RichTextRenderer = {
        escapeHtml: escapeHtml,
        renderToHtml: renderToHtml,
        renderInto: renderInto,
        typeset: typeset
    };
})(window);
