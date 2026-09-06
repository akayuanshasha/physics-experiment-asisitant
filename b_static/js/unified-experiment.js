/* 统一实验页增强：草稿、自动计算、每表绘图/异常分析和 PDF 报告预览。 */
(function () {
    'use strict';

    var context = window.EXPERIMENT_CONTEXT || {id: '', name: ''};
    var draftTimer = null;
    var previewTimer = null;
    var previewSequence = 0;
    var chartByTable = {};
    var initialized = false;

    function schema() { return window.experimentSchema || null; }
    function iconLabel(name, text) {
        return (window.AppIcons && AppIcons[name] ? AppIcons[name] : '') + '<span>' + text + '</span>';
    }
    function tableSchema(tableId) {
        var current = schema();
        return current ? (current.tables || []).find(function (item) { return item.id === tableId; }) : null;
    }
    function draftKey() {
        var revision = schema() ? (schema().schema_revision || 1) : 1;
        return 'physics-experiment-draft:' + context.id + ':v' + revision;
    }
    function inputs(tableId) {
        var body = document.getElementById('schema-body-' + tableId);
        return body ? Array.from(body.querySelectorAll('tr')).map(function (row) {
            return Array.from(row.querySelectorAll('input[data-column-id]'));
        }) : [];
    }
    function setCell(row, index, value) {
        if (!row || !row[index]) return;
        row[index].value = value == null ? '' : value;
        row[index].classList.add('computed-cell');
    }
    function cleanScriptUrl(src) {
        // 仅允许本项目生成的图片路径，拒绝任意 / 相对路径与绝对 URL。
        if (typeof src !== 'string') return null;
        var cleaned = src.trim();
        if (!cleaned) return null;
        var urlWithoutParams = cleaned.split(/[?#]/, 1)[0];
        var prefix = '//' + location.host;
        if (urlWithoutParams.indexOf(prefix) === 0) urlWithoutParams = urlWithoutParams.slice(prefix.length);
        if (urlWithoutParams === location.pathname) return null;   // 相对当前页，拦截
        if (/^https?:\/\//i.test(cleaned) || cleaned.indexOf('//') === 0) return null;
        return (cleaned.indexOf('/api/') === 0 || cleaned.indexOf('/static/') === 0 || cleaned.indexOf('/output') === 0) ? cleaned : null;
    }
    function imageElement(src, alt) {
        var safe = cleanScriptUrl(src);
        if (!safe) return null;
        var image = document.createElement('img');
        image.src = safe;
        if (alt) image.alt = alt;
        image.style.cssText = 'max-width:100%;margin-top:12px;border:1px solid #ddd;border-radius:4px;';
        return image;
    }
    function buildInlineChart(chartSpec, parent) {
        if (!parent || !chartSpec) return;
        var xs = chartSpec.x || chartSpec.xs || [];
        var ys = chartSpec.y || chartSpec.ys || [];
        if (!Array.isArray(xs) || !Array.isArray(ys) || xs.length !== ys.length) return;
        var points = [];
        for (var i = 0; i < xs.length; i += 1) {
            var xv = Number(xs[i]), yv = Number(ys[i]);
            if (isFinite(xv) && isFinite(yv)) points.push([xv, yv]);
        }
        if (points.length < 2) return;
        points.sort(function (a, b) { return a[0] - b[0]; });
        var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 1000 600');
        svg.setAttribute('width', '100%');
        svg.style.cssText = 'height:auto;margin-top:12px;border:1px solid #e3e8f0;border-radius:6px;background:#fff;';
        svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', (chartSpec.title || '数据曲线') + '，共' + points.length + '个数据点');
        var NS = 'http://www.w3.org/2000/svg';
        var originX = 110, originY = 500, w = 830, h = 360;
        var x0 = points[0][0], x1 = points[points.length - 1][0];
        var spread = x1 - x0 || 1;
        var values = points.map(function (p) { return p[1]; });
        var yMax = Math.max.apply(null, values), yMin = Math.min.apply(null, values);
        var pad = (yMax - yMin) * 0.08 || Math.abs(yMax) * 0.08 || 1;
        var yTop = yMax + pad, yBot = yMin - pad;
        if (yTop === yBot) { yTop += 1; yBot -= 1; }
        function sx(x) { return originX + (x - x0) / spread * w; }
        function sy(y) { return originY - (y - yBot) / (yTop - yBot) * h; }
        function el(name, attrs) {
            var node = document.createElementNS(NS, name);
            Object.keys(attrs).forEach(function (key) { node.setAttribute(key, attrs[key]); });
            return node;
        }
        var numTicks = 5;
        var grid = el('g', { stroke: '#eceff5', 'stroke-width': '1' });
        for (var t = 0; t <= numTicks; t += 1) {
            var yv = yBot + (yTop - yBot) * t / numTicks;
            grid.appendChild(el('line', { x1: originX, y1: sy(yv), x2: originX + w, y2: sy(yv) }));
            var lab = el('text', { x: originX - 10, y: sy(yv) + 4, 'text-anchor': 'end', 'font-size': '20', fill: '#8a94a6' });
            lab.textContent = yv.toPrecision(3);
            grid.appendChild(lab);
            var xv = x0 + spread * t / numTicks;
            grid.appendChild(el('line', { x1: sx(xv), y1: originY - h, x2: sx(xv), y2: originY }));
            var xl = el('text', { x: sx(xv), y: originY + 22, 'text-anchor': 'middle', 'font-size': '20', fill: '#8a94a6' });
            xl.textContent = xv.toPrecision(3);
            grid.appendChild(xl);
        }
        svg.appendChild(grid);
        var axis = el('g', { stroke: '#5b6675', 'stroke-width': '2' });
        axis.appendChild(el('line', { x1: originX, y1: originY - h, x2: originX, y2: originY }));
        axis.appendChild(el('line', { x1: originX, y1: originY, x2: originX + w, y2: originY }));
        svg.appendChild(axis);
        var xAxisLabel = el('text', { x: originX + w / 2, y: originY + 52, 'text-anchor': 'middle', 'font-size': '24', fill: '#3a4452' });
        xAxisLabel.textContent = chartSpec.x_label || 'T (°C)';
        svg.appendChild(xAxisLabel);
        var yAxisLabel = el('text', { x: 30, y: originY - h / 2, 'text-anchor': 'middle', 'font-size': '24', fill: '#3a4452', transform: 'rotate(-90 30 ' + (originY - h / 2) + ')' });
        yAxisLabel.textContent = chartSpec.y_label || 'R_T (Ω)';
        svg.appendChild(yAxisLabel);
        var dots = el('g', { fill: '#2563eb' });
        points.forEach(function (p) { dots.appendChild(el('circle', { cx: sx(p[0]), cy: sy(p[1]), r: '5' })); });
        svg.appendChild(dots);
        var pathData = points.map(function (p, index) { return (index ? 'L' : 'M') + sx(p[0]).toFixed(1) + ' ' + sy(p[1]).toFixed(1); }).join(' ');
        svg.appendChild(el('path', { d: pathData, fill: 'none', stroke: '#2563eb', 'stroke-width': '2.5', 'stroke-linejoin': 'round' }));
        var title = el('text', { x: '500', y: '44', 'text-anchor': 'middle', 'font-size': '30', fill: '#1f2a3d' });
        title.textContent = chartSpec.title || 'R-T 特性曲线';
        svg.appendChild(title);
        parent.appendChild(svg);
    }
    function nonEmptyRows(tableId) {
        return inputs(tableId).filter(function (row) {
            var editable = row.filter(function (cell) { return !cell.readOnly; });
            var candidates = editable.length ? editable : row;
            return candidates.some(function (cell) { return cell.value.trim() !== ''; });
        }).map(function (row) { return row.map(function (cell) { return cell.value.trim(); }); });
    }

    function applyPreviewTables(previewTables, fitNotes) {
        (schema().tables || []).forEach(function (table) {
            var inputRows = inputs(table.id);
            var resultRows = previewTables[table.id] || [];
            resultRows.forEach(function (resultRow, rowIndex) {
                var inputRow = inputRows[rowIndex];
                if (!inputRow) return;
                (table.columns || []).forEach(function (column, columnIndex) {
                    if (!column.readonly || !Object.prototype.hasOwnProperty.call(resultRow, column.id)) return;
                    setCell(inputRow, columnIndex, resultRow[column.id]);
                });
            });
        });
        renderFitNotes(fitNotes);
        updateTableStatuses();
    }

    function renderFitNotes(fitNotes) {
        (schema().tables || []).forEach(function (table) {
            var card = document.getElementById('schema-card-' + table.id);
            if (!card) return;
            var boxId = 'fit-notes-' + table.id;
            var box = document.getElementById(boxId);
            var rawLines = fitNotes && fitNotes[table.id];
            var lines = Array.isArray(rawLines) ? rawLines : (typeof rawLines === 'string' ? [rawLines] : []);
            lines = lines.map(function (line) { return String(line); }).filter(function (line) { return line.trim(); });
            if (!lines.length) {
                if (box) box.remove();
                return;
            }
            if (!box) {
                box = document.createElement('div');
                box.id = boxId;
                box.className = 'fit-notes-box';
                card.appendChild(box);
            }
            box.replaceChildren();
            lines.forEach(function (line) {
                var item = document.createElement('div');
                item.className = 'fit-notes-line' + (line.trim().startsWith('⚠') ? ' warn' : '');
                item.textContent = line;
                box.appendChild(item);
            });
            if (window.MathJax && typeof MathJax.typesetPromise === 'function') {
                var previous = window.__fitNotesMathJaxPromise || Promise.resolve();
                window.__fitNotesMathJaxPromise = previous
                    .catch(function () {})
                    .then(function () { return MathJax.typesetPromise([box]); })
                    .catch(function (error) { console.warn('MathJax fit-notes typeset error:', error); });
            }
        });
    }

    function requestPreview() {
        if (!schema() || schema().preview_enabled !== true || typeof window.collectStructuredPayload !== 'function') return;
        clearTimeout(previewTimer);
        previewTimer = setTimeout(function () {
            var requestId = ++previewSequence;
            fetchJSON('/api/' + context.id + '/preview', window.collectStructuredPayload()).then(function (result) {
                if (requestId !== previewSequence || !result || result.code !== 0 || !result.tables) return;
                applyPreviewTables(result.tables, result.fit_notes);
            }).catch(function () {
                /* 输入过程中的暂时无效值不弹窗；最终提交时仍会给出明确错误。 */
            });
        }, 120);
    }

    function recalculate() {
        requestPreview();
        updateTableStatuses();
    }

    function applyColumnMetadata() {
        if (!schema()) return;
        (schema().tables || []).forEach(function (table) {
            inputs(table.id).forEach(function (row) {
                row.forEach(function (input, index) {
                    var column = (table.columns || [])[index] || {};
                    input.readOnly = !!column.readonly;
                    input.tabIndex = column.readonly ? -1 : 0;
                    if (column.type === 'number') input.inputMode = 'decimal';
                });
            });
        });
    }

    function saveDraft() {
        if (!schema() || schema().draft_enabled === false || typeof window.collectStructuredPayload !== 'function') return;
        try {
            localStorage.setItem(draftKey(), JSON.stringify({saved_at: new Date().toISOString(), payload: window.collectStructuredPayload()}));
            var status = document.getElementById('draftStatus');
            if (status) status.textContent = '草稿已自动保存 ' + new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
        } catch (error) {
            var status = document.getElementById('draftStatus');
            if (status) status.textContent = '浏览器未允许保存草稿';
        }
    }

    function installStructuredCollector() {
        window.collectStructuredPayload = function () {
            var payload = {schema_version: 2, parameters: {}, tables: {}};
            (schema().parameters || []).forEach(function (item) {
                var field = document.getElementById('param-' + item.id);
                if (field) payload.parameters[item.id] = field.value.trim();
            });
            (schema().tables || []).forEach(function (table) {
                (table.parameters || []).forEach(function (item) {
                    var field = document.getElementById('param-' + item.id);
                    if (field) payload.parameters[item.id] = field.value.trim();
                });
            });
            (schema().tables || []).forEach(function (table) {
                var card = document.getElementById('schema-table-' + table.id);
                if (!card || card.style.display === 'none') return;
                if (!table.required) {
                    var toggle = document.getElementById('enable-table-' + table.id);
                    if (!toggle || !toggle.checked) return;
                }
                var rows = [];
                inputs(table.id).forEach(function (inputRow) {
                    var editable = inputRow.filter(function (cell) { return !cell.readOnly; });
                    var candidates = editable.length ? editable : inputRow;
                    if (!candidates.some(function (cell) { return cell.value.trim() !== ''; })) return;
                    var row = {};
                    inputRow.forEach(function (cell) { row[cell.dataset.columnId] = cell.value.trim(); });
                    rows.push(row);
                });
                payload.tables[table.id] = rows;
            });
            return payload;
        };
    }

    function scheduleSave() {
        clearTimeout(draftTimer);
        draftTimer = setTimeout(saveDraft, 450);
    }

    function restoreDraft() {
        if (!schema() || schema().draft_enabled === false) return false;
        try {
            var raw = localStorage.getItem(draftKey());
            if (!raw) return false;
            var stored = JSON.parse(raw), payload = stored.payload || stored;
            Object.keys(payload.parameters || {}).forEach(function (id) {
                var element = document.getElementById('param-' + id);
                if (element) element.value = payload.parameters[id];
            });
            (schema().tables || []).forEach(function (table) {
                if (!Object.prototype.hasOwnProperty.call(payload.tables || {}, table.id)) return;
                var body = document.getElementById('schema-body-' + table.id);
                if (!body) return;
                body.innerHTML = '';
                var rows = payload.tables[table.id] || [];
                rows.forEach(function (row) { window.addStructuredRow(table.id, row); });
                if (!rows.length) window.addStructuredRow(table.id);
                if (!table.required && rows.length) window.enableStructuredTable(table.id);
            });
            var status = document.getElementById('draftStatus');
            if (status) status.textContent = '已恢复上次未提交草稿';
            return true;
        } catch (error) {
            return false;
        }
    }

    function clearTable(tableId) {
        var table = tableSchema(tableId), body = document.getElementById('schema-body-' + tableId);
        if (!table || !body) return;
        body.innerHTML = '';
        var count = Math.max(1, table.min_rows || 1);
        for (var i = 0; i < count; i += 1) window.addStructuredRow(tableId);
        applyColumnMetadata();
        recalculate();
        saveDraft();
        window.showToast('已清空“' + table.title + '”');
    }

    function updateTableStatuses() {
        if (!schema()) return;
        (schema().tables || []).forEach(function (table) {
            var chip = document.getElementById('table-status-' + table.id);
            if (!chip) return;
            var count = nonEmptyRows(table.id).length;
            chip.textContent = count ? '已填写 ' + count + ' 行' : '未填写';
            chip.classList.toggle('filled', count > 0);
        });
    }

    function addUnifiedControls() {
        if (!schema()) return;
        (schema().tables || []).forEach(function (table) {
            var card = document.getElementById('schema-table-' + table.id);
            if (!card) return;
            var controls = card.querySelector('.table-action-group');
            if (!controls || controls.dataset.enhanced) return;
            controls.dataset.enhanced = 'true';
            var clear = document.createElement('button');
            clear.type = 'button'; clear.className = 'table-action-button remove'; clear.innerHTML = iconLabel('eraser', '清空本表');
            clear.addEventListener('click', function () { clearTable(table.id); });
            controls.appendChild(clear);
            if (table.chart) {
                var chart = document.createElement('button');
                chart.type = 'button'; chart.className = 'table-action-button chart'; chart.innerHTML = iconLabel('chart', '生成本表图像');
                chart.addEventListener('click', function () { runTableChart(table.id); });
                controls.appendChild(chart);
            }
            var analysis = document.createElement('button');
            analysis.type = 'button'; analysis.className = 'table-action-button analysis'; analysis.innerHTML = iconLabel('search', '分析本表异常');
            analysis.addEventListener('click', function () { runTableAbnormal(table.id); });
            controls.appendChild(analysis);
            if (table.g_calc || table.calc) {
                // calc_placement === 'top'：把「提交计算」并到表格上方工具栏——复用模板
                // 已生成的上方按钮，改用更全的 runTableCalc（/preview + calc_results +
                // 本表参数），结果框置于表格上方；不再在表格下方重复生成按钮。
                if (table.calc_placement === 'top') {
                    var resultBoxTop = document.createElement('div');
                    resultBoxTop.className = 'g-calc-result';
                    resultBoxTop.id = 'g-calc-result-' + table.id;
                    resultBoxTop.style.cssText = 'display:none;margin:10px 0 0;padding:12px 16px;background:#f0f7f0;border-left:4px solid #4CAF50;border-radius:4px;font-size:14px;line-height:1.9;white-space:pre-wrap;';
                    var topCalcBtn = controls.querySelector('.table-action-button.calc');
                    if (topCalcBtn) {
                        // 舍弃模板原本的 calcStructuredTable（/calc-table，不带参数），
                        // 改用 runTableCalc（/preview，带本表参数，结果更全）。
                        topCalcBtn.onclick = null;
                        topCalcBtn.addEventListener('click', function () { runTableCalc(table.id); });
                    }
                    // 结果框插在工具栏之后、数据表之前（表格上方）
                    var toolbarEl = card.querySelector('.schema-table-toolbar');
                    if (toolbarEl && toolbarEl.nextSibling) {
                        card.insertBefore(resultBoxTop, toolbarEl.nextSibling);
                    } else {
                        card.appendChild(resultBoxTop);
                    }
                } else {
                    var gCalc = document.createElement('button');
                    gCalc.type = 'button';
                    gCalc.className = 'table-action-button' + (table.calc ? ' calc' : ' chart');
                    gCalc.innerHTML = iconLabel('sigma', (table.calc && table.calc.label) || '计算 g 及不确定度');
                    gCalc.addEventListener('click', function () { runTableCalc(table.id); });
                    var resultBox = document.createElement('div');
                    resultBox.className = 'g-calc-result'; resultBox.id = 'g-calc-result-' + table.id;
                    resultBox.style.cssText = 'display:none;margin:10px 0 0;padding:12px 16px;background:#f0f7f0;border-left:4px solid #4CAF50;border-radius:4px;font-size:14px;line-height:1.9;white-space:pre-wrap;';
                    var calcFooter = document.createElement('div');
                    calcFooter.className = 'table-calc-footer';
                    calcFooter.appendChild(gCalc);
                    calcFooter.appendChild(resultBox);
                    card.appendChild(calcFooter);  // 放在本表数据表格下方
                }
            }
            var status = document.createElement('span');
            status.className = 'draft-status'; status.id = 'table-status-' + table.id; status.textContent = '未填写';
            controls.appendChild(status);
        });

        var submitGroup = document.getElementById('submitBtn') && document.getElementById('submitBtn').parentElement;
        if (submitGroup && !document.getElementById('draftStatus')) {
            var charts = (schema().tables || []).filter(function (table) { return !!table.chart; });
            if (charts.length >= 1) {
                var allCharts = document.createElement('button');
                allCharts.type = 'button'; allCharts.id = 'allChartsBtn'; allCharts.className = 'btn btn-secondary'; allCharts.innerHTML = iconLabel('chart', '生成所有配置图像');
                allCharts.addEventListener('click', function () { runAllCharts(false); });
                var reportBtn = document.getElementById('aiReportBtn');
                if (reportBtn && reportBtn.parentElement) {
                    reportBtn.parentElement.insertBefore(allCharts, reportBtn);
                    var chartsAndReport = document.createElement('button');
                    chartsAndReport.type = 'button'; chartsAndReport.id = 'chartsAndReportBtn';
                    chartsAndReport.className = 'btn btn-success'; chartsAndReport.style.background = '#16a085'; chartsAndReport.style.color = 'white';
                    chartsAndReport.innerHTML = iconLabel('zap', '一键生成图像并生成报告');
                    chartsAndReport.addEventListener('click', function () { runAllCharts(true); });
                    reportBtn.parentElement.insertBefore(chartsAndReport, reportBtn.nextSibling);
                } else submitGroup.insertBefore(allCharts, submitGroup.firstChild);
            }
            var clearDraft = document.createElement('button');
            clearDraft.type = 'button'; clearDraft.className = 'btn btn-secondary'; clearDraft.innerHTML = iconLabel('trash', '清空本实验草稿');
            clearDraft.addEventListener('click', function () {
                if (!window.confirm('确定清空本实验在当前浏览器中的全部草稿吗？')) return;
                localStorage.removeItem(draftKey());
                window.location.reload();
            });
            submitGroup.appendChild(clearDraft);
            var draftStatus = document.createElement('span');
            draftStatus.id = 'draftStatus'; draftStatus.className = 'draft-status'; draftStatus.textContent = '输入内容将自动保存在本浏览器';
            submitGroup.appendChild(draftStatus);
        }
        // 实验可通过 schema 声明不需要 AI 报告（如仅需计算结果的实验）
        if (schema().report_enabled === false) {
            var hiddenReport = document.getElementById('aiReportBtn');
            if (hiddenReport) hiddenReport.style.display = 'none';
            var hiddenChartsReport = document.getElementById('chartsAndReportBtn');
            if (hiddenChartsReport) hiddenChartsReport.style.display = 'none';
        }
    }

    function fetchJSON(url, payload) {
        return fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)}).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) throw new Error(data.error || data.message || ('请求失败（' + response.status + '）'));
                return data;
            });
        });
    }

    function chartPayload(table) {
        var columns = (table.columns || []).map(function (column) { return column.label + (column.unit ? ' (' + column.unit + ')' : ''); });
        var rows = nonEmptyRows(table.id);
        var xIndex = (table.columns || []).findIndex(function (column) { return column.id === table.chart.x_column; });
        var yIndex = (table.columns || []).findIndex(function (column) { return column.id === table.chart.y_column; });
        var config = Object.assign({}, table.chart, {x_col: xIndex < 0 ? 0 : xIndex, y_col: yIndex < 0 ? 1 : yIndex});
        delete config.x_column; delete config.y_column;
        // 多 y 列模式：把 y_columns（列 ID 列表）映射成 y_cols（列索引列表）
        var yColumns = table.chart.y_columns;
        if (yColumns && yColumns.length) {
            config.y_cols = yColumns.map(function (id) {
                var idx = (table.columns || []).findIndex(function (column) { return column.id === id; });
                return idx < 0 ? 0 : idx;
            });
        }
        delete config.y_columns;
        return {columns: columns, data: rows, config: config, experiment_name: context.name + ' — ' + table.title, save_name: 'chart_' + context.id + '_' + table.id + '.png'};
    }

    function renderCharts() {
        var list = Object.keys(chartByTable).map(function (key) { return chartByTable[key]; });
        console.log('[图表] renderCharts 调用, chartByTable keys:', Object.keys(chartByTable), 'list length:', list.length);
        var gallery = document.getElementById('chartGallery');
        gallery.innerHTML = '';
        list.forEach(function (chart, index) {
            var figure = document.createElement('figure'), link = document.createElement('a'), image = document.createElement('img'), caption = document.createElement('figcaption');
            link.href = chart.chart_url; link.target = '_blank'; link.rel = 'noopener';
            image.src = chart.chart_url + '?t=' + Date.now(); image.alt = chart.title; link.appendChild(image); figure.appendChild(link);
            caption.textContent = chart.title + (chart.fit_result ? '；' + chart.fit_result.equation + '，R²=' + chart.fit_result.R2 : '');
            figure.appendChild(caption);
            // 添加下载按钮
            var downloadBtn = document.createElement('a');
            downloadBtn.href = chart.chart_url;
            downloadBtn.download = 'chart_' + (index + 1) + '.png';
            downloadBtn.className = 'chart-download-btn';
            downloadBtn.innerHTML = iconLabel('download', '下载图表');
            figure.appendChild(downloadBtn);
            gallery.appendChild(figure);
        });
        document.getElementById('chartImage').style.display = 'none';
        document.getElementById('chartInfo').style.display = 'none';
        document.getElementById('chartArea').style.display = list.length ? 'block' : 'none';
        window.lastChartInfo = {charts: list.map(function (item) {
            return {title: item.title, chart_url: item.chart_url, chart_path: item.chart_path, x_label: item.x_label, y_label: item.y_label, fit_result: item.fit_result};
        })};
        console.log('[图表] lastChartInfo 内容:', JSON.stringify(window.lastChartInfo, null, 2));
    }

    function runTableChart(tableId, quiet) {
        var table = tableSchema(tableId);
        if (!table || !table.chart) return Promise.resolve();
        var payload = chartPayload(table);
        if (payload.data.length < 2) {
            if (!quiet) window.showToast('“' + table.title + '”至少需要2行有效数据');
            return Promise.reject(new Error('数据点不足'));
        }
        if (!quiet) window.showLoading('正在生成“' + table.title + '”图像…');
        return fetchJSON('/api/generate-chart', payload).then(function (result) {
            if (!result.success || !result.chart_url) throw new Error(result.error || '图表生成失败');
            chartByTable[tableId] = {
                title: table.chart.title || table.title,
                chart_url: result.chart_url,
                chart_path: result.chart_path || (result.chart_config && result.chart_config.chart_path) || '',
                x_label: result.x_label || table.chart.x_label || '',
                y_label: result.y_label || table.chart.y_label || '',
                fit_result: result.fit_result || null
            };
            renderCharts();
            if (!quiet) {
                window.hideLoading(); window.showToast('图表生成完成');
                document.getElementById('chartArea').scrollIntoView({behavior: 'smooth'});
            }
        }).catch(function (error) {
            if (!quiet) { window.hideLoading(); window.showToast(error.message, 4500); }
            throw error;
        });
    }

    function runAllCharts(thenReport) {
        var tables = (schema().tables || []).filter(function (table) { return table.chart && nonEmptyRows(table.id).length >= 2; });
        if (!tables.length) {
            window.showToast('没有达到绘图条件的数据表');
            if (thenReport) window.generateAIReport();
            return;
        }
        window.showLoading(thenReport ? '正在先生成全部图像，随后自动撰写实验报告…' : '正在依次生成 ' + tables.length + ' 张实验图像…');
        var chain = Promise.resolve();
        tables.forEach(function (table) { chain = chain.then(function () { return runTableChart(table.id, true); }); });
        chain.then(function () {
            window.hideLoading();
            if (thenReport) { window.generateAIReport(); return; }
            window.showToast('全部图表生成完成');
            document.getElementById('chartArea').scrollIntoView({behavior: 'smooth'});
        }).catch(function (error) { window.hideLoading(); window.showToast(error.message, 4500); });
    }

    function renderAbnormal(report) {
        var target = document.getElementById('abnormalReport');
        if (window.RichTextRenderer) window.RichTextRenderer.renderInto(target, report);
        else target.textContent = report;
        document.getElementById('abnormalArea').style.display = 'block';
        document.getElementById('abnormalArea').scrollIntoView({behavior: 'smooth'});
    }

    function runTableCalc(tableId) {
        var table = tableSchema(tableId), box = document.getElementById('g-calc-result-' + tableId);
        if (!table || !(table.g_calc || table.calc)) return;
        // 带 calc 的表允许空数据提交（后端给出进度提示或仅依赖参数的计算结果）
        if (!table.calc && !nonEmptyRows(tableId).length) { window.showToast('请先填写本表数据'); return; }
        if (typeof window.collectStructuredPayload !== 'function') return;
        window.showLoading('正在自动计算…');
        fetchJSON('/api/' + context.id + '/preview', window.collectStructuredPayload()).then(function (result) {
            window.hideLoading();
            if (!result || result.code !== 0) throw new Error('计算失败，请检查数据');
            if (result.tables) applyPreviewTables(result.tables, result.fit_notes);
            var info = ((result.calc_results || result.g_results) || {})[tableId];
            if (!info || !(info.lines || []).length) {
                var messages = result.calc_messages || [];
                throw new Error(messages.length ? messages.join('；') : '无法计算：请检查顶部参数和表格数据是否完整、有效');
            }
            if (box) {
                box.textContent = table.title + '\n' + info.lines.join('\n');
                if (result.chart_url) {
                    var calcChartImg = imageElement(result.chart_url, table.title);
                    if (calcChartImg) box.appendChild(calcChartImg);
                } else if (info.chart) {
                    buildInlineChart(info.chart, box);
                }
                box.style.display = 'block';
                box.scrollIntoView({behavior: 'smooth', block: 'nearest'});
            }
            window.showToast('计算完成');
        }).catch(function (error) { window.hideLoading(); window.showToast(error.message, 4500); });
    }

    function runTableAbnormal(tableId) {
        var table = tableSchema(tableId), rows = nonEmptyRows(tableId);
        if (!table || !rows.length) { window.showToast('请先填写本表数据'); return; }
        window.showLoading('正在分析“' + table.title + '”的数据…');
        fetchJSON('/api/abnormal-detect', {
            experiment_name: context.name + ' — ' + table.title,
            mod_name: context.id,
            columns: (table.columns || []).map(function (column) { return column.label; }),
            data: rows,
            pdf_text: '',
            analysis_hints: (schema().analysis_hints || '') + '\n仅分析当前数据表：' + table.title
        }).then(function (result) {
            window.hideLoading();
            if (!result.report) throw new Error(result.error || '异常分析失败');
            window.lastAbnormalReport = result.report;
            renderAbnormal(result.report);
            window.showToast('异常分析完成');
        }).catch(function (error) { window.hideLoading(); window.showToast(error.message, 4500); });
    }

    function overrideResultRenderers() {
        window.runAbnormalDetect = function () {
            if (!window.lastUserData) { window.showToast('请先提交数据'); return; }
            window.showLoading('正在综合分析全部数据表…');
            fetchJSON('/api/abnormal-detect', {
                experiment_name: context.name,
                mod_name: context.id,
                columns: window.lastUserData.columns || [],
                data: window.lastUserData.data || [],
                tables: window.lastUserData.tables || {},
                pdf_text: '',
                analysis_hints: schema() ? (schema().analysis_hints || '') : ''
            }).then(function (result) {
                window.hideLoading();
                if (!result.report) throw new Error(result.error || '异常分析失败');
                window.lastAbnormalReport = result.report;
                renderAbnormal(result.report);
                window.showToast('异常分析完成');
            }).catch(function (error) { window.hideLoading(); window.showToast(error.message, 4500); });
        };

        window.generateAIReport = function () {
            if (!window.lastUserData) { window.showToast('请先提交数据'); return; }
            console.log('[报告] window.lastChartInfo 内容:', JSON.stringify(window.lastChartInfo, null, 2));
            console.log('[报告] chartByTable keys:', Object.keys(chartByTable));
            window.showLoading('AI 正在生成实验报告并尝试编译 PDF…');
            fetchJSON('/api/generate-report', {
                experiment_name: context.name,
                mod_name: context.id,
                user_data: window.lastUserData,
                calc_results: window.lastCalcResult,
                abnormal_report: window.lastAbnormalReport || '',
                chart_info: window.lastChartInfo
            }).then(function (result) {
                window.hideLoading();
                if (!result.report) throw new Error(result.error || '报告生成失败');
                document.getElementById('reportContent').textContent = result.report;
                var tex = document.getElementById('texDownloadBtn');
                tex.style.display = result.tex_url ? 'inline-block' : 'none'; if (result.tex_url) tex.href = result.tex_url;
                var pdf = document.getElementById('pdfDownloadBtn'), preview = document.getElementById('reportPreview'), frame = document.getElementById('reportPdfFrame');
                if (result.pdf_url) {
                    pdf.href = result.pdf_url + '?download=1'; pdf.style.display = 'inline-flex';
                    // 通过 pdf.js 在线预览，避免部分浏览器在 iframe 内加载 PDF 触发强制下载
                    var enc = encodeURIComponent(result.pdf_url);
                    frame.src = '/static/pdf-viewer.html?file=' + enc + '&name=' + encodeURIComponent(context.name || '');
                    preview.style.display = 'block';
                } else {
                    pdf.style.display = 'none'; frame.removeAttribute('src'); preview.style.display = 'none';
                }
                var tip = document.getElementById('reportCompileTip');
                tip.textContent = result.pdf_error || (!result.pdf_url ? '当前电脑未能编译 PDF，可下载 TEX 源码后使用本地 LaTeX 或 Overleaf 编译。' : '');
                tip.style.display = tip.textContent ? 'block' : 'none';
                document.getElementById('reportArea').style.display = 'block';
                document.getElementById('reportArea').scrollIntoView({behavior: 'smooth'});
                window.showToast(result.pdf_url ? '报告与 PDF 生成完成' : '报告源码生成完成');
            }).catch(function (error) {
                window.hideLoading();
                var msg = error.message || '报告生成失败';
                if (msg.indexOf('timed out') >= 0 || msg.indexOf('timeout') >= 0 || msg.indexOf('超时') >= 0) {
                    alert('⏱️ ' + msg + '\n\n可能原因：\n1. LLM API 服务响应缓慢或暂时不可用\n2. 网络连接不稳定\n\n请稍后重试。');
                } else {
                    alert('❌ ' + msg);
                }
            });
        };
    }

    function wrapMutatingFunctions() {
        ['addStructuredRowFromButton', 'removeStructuredRow', 'fillStructuredTableExample'].forEach(function (name) {
            var original = window[name];
            if (typeof original !== 'function') return;
            window[name] = function () {
                var result = original.apply(this, arguments);
                setTimeout(function () { applyColumnMetadata(); recalculate(); scheduleSave(); }, 0);
                return result;
            };
        });
    }

    function initStructured() {
        if (initialized) return;
        initialized = true;
        addUnifiedControls();
        installStructuredCollector();
        var restored = restoreDraft();
        applyColumnMetadata();
        recalculate();
        wrapMutatingFunctions();
        overrideResultRenderers();
        document.addEventListener('input', function (event) {
            if (!event.target.closest('#structuredWrapper')) return;
            recalculate(); scheduleSave();
        });
        document.addEventListener('change', function (event) {
            if (!event.target.closest('#structuredWrapper')) return;
            recalculate(); scheduleSave();
        });
        if (!restored) saveDraft();
    }

    function initLegacyDraft() {
        if (initialized) return;
        initialized = true;
        overrideResultRenderers();
        var key = 'physics-experiment-draft:' + context.id + ':legacy';
        try {
            var raw = localStorage.getItem(key);
            if (raw) {
                var rows = JSON.parse(raw);
                var body = document.getElementById('tableBody'); body.innerHTML = '';
                rows.forEach(function (values, index) {
                    window.addRowTo(index + 1);
                    Array.from(body.children[index].querySelectorAll('input')).forEach(function (input, column) { input.value = values[column] || ''; });
                });
            }
        } catch (error) {}
        document.getElementById('tableBody').addEventListener('input', function () {
            clearTimeout(draftTimer);
            draftTimer = setTimeout(function () {
                var rows = Array.from(document.querySelectorAll('#tableBody tr')).map(function (row) {
                    return Array.from(row.querySelectorAll('input')).map(function (input) { return input.value; });
                });
                try { localStorage.setItem(key, JSON.stringify(rows)); } catch (error) {}
            }, 450);
        });
    }

    function waitForInterface(attempt) {
        if (window.structuredMode && schema() && document.querySelector('.schema-table-card')) {
            initStructured(); return;
        }
        if (!window.structuredMode && window.tableColumns && window.tableColumns.length && document.getElementById('tableBody').children.length) {
            initLegacyDraft(); return;
        }
        if (attempt < 100) setTimeout(function () { waitForInterface(attempt + 1); }, 100);
    }

    waitForInterface(0);
}());
