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
    function nonEmptyRows(tableId) {
        return inputs(tableId).filter(function (row) {
            var editable = row.filter(function (cell) { return !cell.readOnly; });
            var candidates = editable.length ? editable : row;
            return candidates.some(function (cell) { return cell.value.trim() !== ''; });
        }).map(function (row) { return row.map(function (cell) { return cell.value.trim(); }); });
    }

    function applyPreviewTables(previewTables) {
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
        updateTableStatuses();
    }

    function requestPreview() {
        if (!schema() || schema().preview_enabled !== true || typeof window.collectStructuredPayload !== 'function') return;
        clearTimeout(previewTimer);
        previewTimer = setTimeout(function () {
            var requestId = ++previewSequence;
            fetchJSON('/api/' + context.id + '/preview', window.collectStructuredPayload()).then(function (result) {
                if (requestId !== previewSequence || !result || result.code !== 0 || !result.tables) return;
                applyPreviewTables(result.tables);
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
            clear.type = 'button'; clear.className = 'table-action-button remove'; clear.textContent = '🧹 清空本表';
            clear.addEventListener('click', function () { clearTable(table.id); });
            controls.appendChild(clear);
            if (table.chart) {
                var chart = document.createElement('button');
                chart.type = 'button'; chart.className = 'table-action-button chart'; chart.textContent = '📈 生成本表图像';
                chart.addEventListener('click', function () { runTableChart(table.id); });
                controls.appendChild(chart);
            }
            var analysis = document.createElement('button');
            analysis.type = 'button'; analysis.className = 'table-action-button analysis'; analysis.textContent = '🔍 分析本表异常';
            analysis.addEventListener('click', function () { runTableAbnormal(table.id); });
            controls.appendChild(analysis);
            var status = document.createElement('span');
            status.className = 'draft-status'; status.id = 'table-status-' + table.id; status.textContent = '未填写';
            controls.appendChild(status);
        });

        var submitGroup = document.getElementById('submitBtn') && document.getElementById('submitBtn').parentElement;
        if (submitGroup && !document.getElementById('draftStatus')) {
            var charts = (schema().tables || []).filter(function (table) { return !!table.chart; });
            if (charts.length > 1) {
                var allCharts = document.createElement('button');
                allCharts.type = 'button'; allCharts.className = 'btn btn-secondary'; allCharts.textContent = '📊 生成全部配置图像';
                allCharts.addEventListener('click', runAllCharts);
                submitGroup.insertBefore(allCharts, submitGroup.firstChild);
            }
            var clearDraft = document.createElement('button');
            clearDraft.type = 'button'; clearDraft.className = 'btn btn-secondary'; clearDraft.textContent = '🗑️ 清空本实验草稿';
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
        return {columns: columns, data: rows, config: config, experiment_name: context.name + ' — ' + table.title, save_name: 'chart_' + context.id + '_' + table.id + '.png'};
    }

    function renderCharts() {
        var list = Object.keys(chartByTable).map(function (key) { return chartByTable[key]; });
        var gallery = document.getElementById('chartGallery');
        gallery.innerHTML = '';
        list.forEach(function (chart) {
            var figure = document.createElement('figure'), link = document.createElement('a'), image = document.createElement('img'), caption = document.createElement('figcaption');
            link.href = chart.chart_url; link.target = '_blank'; link.rel = 'noopener';
            image.src = chart.chart_url + '?t=' + Date.now(); image.alt = chart.title; link.appendChild(image); figure.appendChild(link);
            caption.textContent = chart.title + (chart.fit_result ? '；' + chart.fit_result.equation + '，R²=' + chart.fit_result.R2 : '');
            figure.appendChild(caption); gallery.appendChild(figure);
        });
        document.getElementById('chartImage').style.display = 'none';
        document.getElementById('chartInfo').style.display = 'none';
        document.getElementById('chartArea').style.display = list.length ? 'block' : 'none';
        window.lastChartInfo = {charts: list.map(function (item) {
            return {title: item.title, chart_url: item.chart_url, chart_path: item.chart_path, x_label: item.x_label, y_label: item.y_label, fit_result: item.fit_result};
        })};
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

    function runAllCharts() {
        var tables = (schema().tables || []).filter(function (table) { return table.chart && nonEmptyRows(table.id).length >= 2; });
        if (!tables.length) { window.showToast('没有达到绘图条件的数据表'); return; }
        window.showLoading('正在依次生成 ' + tables.length + ' 张实验图像…');
        var chain = Promise.resolve();
        tables.forEach(function (table) { chain = chain.then(function () { return runTableChart(table.id, true); }); });
        chain.then(function () {
            window.hideLoading(); window.showToast('全部图表生成完成');
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
                    pdf.href = result.pdf_url + '?download=1'; pdf.style.display = 'inline-block';
                    frame.src = result.pdf_url; preview.style.display = 'block';
                } else {
                    pdf.style.display = 'none'; frame.removeAttribute('src'); preview.style.display = 'none';
                }
                var tip = document.getElementById('reportCompileTip');
                tip.textContent = result.pdf_error || (!result.pdf_url ? '当前电脑未能编译 PDF，可下载 TEX 源码后使用本地 LaTeX 或 Overleaf 编译。' : '');
                tip.style.display = tip.textContent ? 'block' : 'none';
                document.getElementById('reportArea').style.display = 'block';
                document.getElementById('reportArea').scrollIntoView({behavior: 'smooth'});
                window.showToast(result.pdf_url ? '报告与 PDF 生成完成' : '报告源码生成完成');
            }).catch(function (error) { window.hideLoading(); window.showToast(error.message, 5000); });
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
