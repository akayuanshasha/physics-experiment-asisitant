"""摄谱仪与单色仪实验：多表计算与九幅谱图的辅助处理。"""

from io import BytesIO

from head import *
from optics_common import *
from PIL import Image, ImageDraw, ImageEnhance, ImageOps, UnidentifiedImageError
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks


def name():
    return "摄谱仪与单色仪"


IMAGE_GROUPS = {
    "he": ("氦灯", ("he_left", "he_middle", "he_right")),
    "hg": ("汞灯", ("hg_left", "hg_middle", "hg_right")),
    "na": ("钠灯", ("na_left", "na_middle", "na_right")),
}


def schema():
    standard_sample = [
        {"source": "He", "line_label": "蓝线", "pixel_x": 180, "wavelength_nm": 447.1},
        {"source": "He", "line_label": "蓝绿线", "pixel_x": 455, "wavelength_nm": 501.6},
        {"source": "He", "line_label": "黄线", "pixel_x": 885, "wavelength_nm": 587.6},
        {"source": "He", "line_label": "红线", "pixel_x": 1286, "wavelength_nm": 667.8},
        {"source": "He", "line_label": "深红线", "pixel_x": 1480, "wavelength_nm": 706.5},
    ]
    unknown_sample = [
        {"source": "Hg", "line_label": "紫线", "pixel_x": 120, "reference_nm": 435.8},
        {"source": "Hg", "line_label": "绿线", "pixel_x": 687, "reference_nm": 546.1},
        {"source": "Hg", "line_label": "黄双线中心", "pixel_x": 884, "reference_nm": 577.0},
        {"source": "Na", "line_label": "黄双线中心", "pixel_x": 945, "reference_nm": 589.3},
    ]
    scan_sample = []
    for wavelength in np.arange(570.0, 611.0, 2.0):
        intensity = 0.08 + 0.92 * math.exp(-0.5 * ((wavelength - 589.3) / 3.5) ** 2)
        scan_sample.append({
            "measured_nm": float(wavelength),
            "signal": round(float(intensity), 6),
            "reference": "",
        })
    return {
        "schema_version": 2,
        "description": (
            "本页分为摄谱仪和单色仪两条流程。摄谱仪流程要求氦、汞、钠三种光源各上传左/中/右三张谱图；"
            "系统完成增强、拼接和候选谱线峰检测，峰位仍需结合原图人工复核后填入定标表。"
        ),
        "parameters": [
            {
                "id": "part", "label": "实验内容", "type": "select", "default": "spectrograph",
                "required": True,
                "options": [
                    {"value": "spectrograph", "label": "实验一：摄谱仪（谱图与波长定标）"},
                    {"value": "monochromator", "label": "实验二：单色仪（校准与光谱扫描）"},
                ],
            },
            {
                "id": "calibration_degree", "label": "摄谱仪定标多项式次数", "type": "select", "default": "2",
                "condition": {"parameter": "part", "equals": "spectrograph"},
                "options": [
                    {"value": "1", "label": "一次定标"},
                    {"value": "2", "label": "二次定标（建议）"},
                ],
            },
            {
                "id": "scan_mode", "label": "单色仪扫描类型", "type": "select", "default": "emission",
                "condition": {"parameter": "part", "equals": "monochromator"},
                "options": [
                    {"value": "emission", "label": "发射光谱"},
                    {"value": "absorption", "label": "吸收光谱（需要参考光强）"},
                ],
            },
        ],
        "image_upload": {
            "title": "摄谱仪九幅谱图辅助处理",
            "condition": {"parameter": "part", "equals": "spectrograph"},
            "description": (
                "按同一拍摄方向依次选择左段、中段、右段。支持 PNG/JPG/BMP/TIFF；每张不超过12 MB。"
                "自动峰仅用于初筛，请根据拼接图和强度曲线人工确认峰位。"
            ),
            "slots": [
                {"id": "he_left", "label": "氦灯—左段"}, {"id": "he_middle", "label": "氦灯—中段"},
                {"id": "he_right", "label": "氦灯—右段"}, {"id": "hg_left", "label": "汞灯—左段"},
                {"id": "hg_middle", "label": "汞灯—中段"}, {"id": "hg_right", "label": "汞灯—右段"},
                {"id": "na_left", "label": "钠灯—左段"}, {"id": "na_middle", "label": "钠灯—中段"},
                {"id": "na_right", "label": "钠灯—右段"},
            ],
        },
        "tables": [
            {
                "id": "spectrograph_standard", "title": "表1  摄谱仪标准谱线定标", "required": True,
                "condition": {"parameter": "part", "equals": "spectrograph"},
                "min_rows": 3, "initial_rows": 5,
                "description": "像素坐标应来自氦灯拼接图中人工复核后的峰中心；标准波长查阅指导书或可靠谱线表。",
                "columns": [
                    {"id": "source", "label": "光源"}, {"id": "line_label", "label": "谱线标识"},
                    {"id": "pixel_x", "label": "峰中心像素x", "unit": "px"},
                    {"id": "wavelength_nm", "label": "标准波长", "unit": "nm"},
                ],
                "sample": standard_sample,
            },
            {
                "id": "spectrograph_unknown", "title": "表2  汞灯/钠灯待测谱线", "required": True,
                "condition": {"parameter": "part", "equals": "spectrograph"},
                "min_rows": 1, "initial_rows": 4,
                "columns": [
                    {"id": "source", "label": "光源"}, {"id": "line_label", "label": "谱线标识"},
                    {"id": "pixel_x", "label": "峰中心像素x", "unit": "px"},
                    {"id": "reference_nm", "label": "参考波长（可空）", "unit": "nm"},
                ],
                "sample": unknown_sample,
            },
            {
                "id": "monochromator_calibration", "title": "表1  单色仪波长校准", "required": True,
                "condition": {"parameter": "part", "equals": "monochromator"},
                "min_rows": 3, "initial_rows": 5,
                "description": "用已知谱线记录单色仪读数，拟合“标准波长 = a×仪器读数+b”。",
                "columns": [
                    {"id": "measured_nm", "label": "单色仪读数", "unit": "nm"},
                    {"id": "standard_nm", "label": "标准波长", "unit": "nm"},
                ],
                "sample": [
                    {"measured_nm": 435.2, "standard_nm": 435.8},
                    {"measured_nm": 500.9, "standard_nm": 501.6},
                    {"measured_nm": 545.3, "standard_nm": 546.1},
                    {"measured_nm": 576.2, "standard_nm": 577.0},
                    {"measured_nm": 588.5, "standard_nm": 589.3},
                ],
            },
            {
                "id": "monochromator_scan", "title": "表2  单色仪扫描数据", "required": True,
                "condition": {"parameter": "part", "equals": "monochromator"},
                "min_rows": 8, "initial_rows": 21,
                "description": "发射光谱只填信号；吸收光谱还须填相同波长处的参考光强。",
                "columns": [
                    {"id": "measured_nm", "label": "单色仪读数", "unit": "nm"},
                    {"id": "signal", "label": "信号光强"},
                    {"id": "reference", "label": "参考光强（吸收时必填）"},
                ],
                "sample": scan_sample,
            },
        ],
    }


def _safe_image(file_storage, label):
    raw = file_storage.read(12 * 1024 * 1024 + 1)
    if not raw:
        raise OpticsInputError(f"{label}没有读取到图像内容")
    if len(raw) > 12 * 1024 * 1024:
        raise OpticsInputError(f"{label}超过12 MB，请先压缩图像")
    try:
        image = Image.open(BytesIO(raw))
        if image.format not in {"PNG", "JPEG", "BMP", "TIFF"}:
            raise OpticsInputError(f"{label}仅支持PNG、JPG、BMP或TIFF格式")
        if image.width < 40 or image.height < 40:
            raise OpticsInputError(f"{label}尺寸过小，至少需要40×40像素")
        if image.width * image.height > 40_000_000:
            raise OpticsInputError(f"{label}像素数超过4000万，请缩小图像后再上传")
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.load()
    except OpticsInputError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise OpticsInputError(f"{label}不是可识别的图像文件") from exc
    return image


def _normalize_panel(image, target_height):
    width = max(1, round(image.width * target_height / image.height))
    panel = image.resize((width, target_height), Image.Resampling.LANCZOS)
    panel = ImageEnhance.Contrast(panel).enhance(1.25)
    panel = ImageOps.autocontrast(panel, cutoff=0.5)
    return panel


def _stitch_and_detect(images, labels, workpath, prefix, title):
    target_height = min(900, min(image.height for image in images))
    panels = [_normalize_panel(image, target_height) for image in images]
    separator = 6
    total_width = sum(panel.width for panel in panels) + separator * (len(panels) - 1)
    stitched = Image.new("RGB", (total_width, target_height), (10, 10, 10))
    seams = []
    cursor = 0
    for index, panel in enumerate(panels):
        stitched.paste(panel, (cursor, 0))
        cursor += panel.width
        if index < len(panels) - 1:
            seams.append(cursor + separator // 2)
            cursor += separator

    gray = np.asarray(stitched.convert("L"), dtype=float)
    profile = np.percentile(gray, 95, axis=0)
    smoothed = gaussian_filter1d(profile, sigma=max(1.2, total_width / 1600.0))
    background = gaussian_filter1d(smoothed, sigma=max(12.0, total_width / 45.0))
    corrected = np.maximum(smoothed - background, 0.0)
    for seam in seams:
        corrected[max(0, seam - 8):min(total_width, seam + 9)] = 0.0
    peak_height = float(np.max(corrected))
    if peak_height <= 0:
        peaks = np.asarray([], dtype=int)
        properties = {"prominences": np.asarray([], dtype=float)}
    else:
        peaks, properties = find_peaks(
            corrected,
            distance=max(5, total_width // 120),
            prominence=max(1.0, peak_height * 0.07),
        )
        if len(peaks) == 0:
            peaks, properties = find_peaks(
                corrected,
                distance=max(5, total_width // 150),
                prominence=max(0.5, peak_height * 0.025),
            )
    if len(peaks) > 30:
        keep = np.argsort(properties["prominences"])[-30:]
        peaks = np.sort(peaks[keep])

    annotated = stitched.copy()
    draw = ImageDraw.Draw(annotated)
    for peak in peaks:
        draw.line((int(peak), 0, int(peak), target_height - 1), fill=(255, 70, 70), width=2)
    annotated_name = f"exp37_{prefix}_stitched_peaks.png"
    annotated.save(Path(workpath) / annotated_name, format="PNG", optimize=True)

    configure_plotting()
    fig, ax = plt.subplots(figsize=(11.0, 4.2))
    x = np.arange(total_width)
    ax.plot(x, corrected, color="#4472C4", linewidth=1.2, label="扣除缓变背景后的强度")
    if len(peaks):
        ax.scatter(peaks, corrected[peaks], color="#E74C3C", s=28, zorder=3, label="候选谱线峰")
        for peak in peaks:
            ax.annotate(str(int(peak)), (peak, corrected[peak]), xytext=(0, 6), textcoords="offset points",
                        ha="center", fontsize=7, rotation=90)
    for seam in seams:
        ax.axvline(seam, color="#999999", linestyle="--", alpha=0.45)
    ax.set_xlabel("拼接图横向像素坐标 x / px")
    ax.set_ylabel("相对强度 / a.u.")
    ax.set_title(f"{title}拼接谱图的候选峰检测")
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(loc="upper right")
    profile_name = save_figure(fig, workpath, f"exp37_{prefix}_profile.png")
    return {
        "peaks": [int(value) for value in peaks],
        "width": total_width,
        "height": target_height,
        "charts": [
            {"filename": annotated_name, "title": f"{title}左/中/右拼接图（红线为候选峰）"},
            {"filename": profile_name, "title": f"{title}强度剖面与候选峰"},
        ],
        "labels": labels,
    }


def process_images(workpath, files, _form=None):
    """处理氦、汞、钠各三幅谱图；结果用于人工复核，不替代谱线判读。"""
    try:
        missing = []
        loaded = {}
        slot_labels = {
            slot["id"]: slot["label"]
            for slot in schema()["image_upload"]["slots"]
        }
        for slot_id, label in slot_labels.items():
            storage = files.get(slot_id)
            if storage is None or not getattr(storage, "filename", ""):
                missing.append(label)
                continue
            loaded[slot_id] = _safe_image(storage, label)
        if missing:
            raise OpticsInputError("请补齐9张谱图，尚缺：" + "、".join(missing))

        charts = []
        summary = []
        for prefix, (title, slot_ids) in IMAGE_GROUPS.items():
            result = _stitch_and_detect(
                [loaded[slot_id] for slot_id in slot_ids],
                [slot_labels[slot_id] for slot_id in slot_ids],
                workpath,
                prefix,
                title,
            )
            charts.extend(result["charts"])
            peak_text = "、".join(str(value) for value in result["peaks"]) or "未检出明显峰"
            summary.append(
                f"{title}：拼接尺寸{result['width']}×{result['height']} px；候选峰x = {peak_text}"
            )
        return {
            "code": 0,
            "summary": summary,
            "warnings": [
                "自动峰值受曝光、裁剪、图像重叠和拼接接缝影响；请对照拼接图人工复核后，再把峰中心填入定标表。"
            ],
            "charts": charts,
        }
    except Exception as exc:
        return error_result(exc)


def _optional_numeric(rows, key, label):
    values = []
    any_value = False
    for index, row in enumerate(rows, 1):
        raw = row.get(key, "")
        if raw == "":
            values.append(np.nan)
            continue
        any_value = True
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise OpticsInputError(f"{label}第{index}行不是有效数字：{raw}") from exc
        if not np.isfinite(value):
            raise OpticsInputError(f"{label}第{index}行必须是有限数字")
        values.append(value)
    return np.asarray(values, dtype=float), any_value


def _handle_spectrograph(workpath, payload):
    degree = get_parameter(payload, "calibration_degree", 2, cast=int)
    standards = get_rows(payload, "spectrograph_standard", required=True, min_rows=3)
    unknowns = get_rows(payload, "spectrograph_unknown", required=True, min_rows=1)
    x = numeric_column(standards, "pixel_x", "标准谱线像素")
    wavelength = numeric_column(standards, "wavelength_nm", "标准波长")
    if len(np.unique(x)) < degree + 1:
        raise OpticsInputError(f"{degree}次定标至少需要{degree + 1}个不同的像素坐标")
    coeff = np.polyfit(x, wavelength, degree)
    fitted = np.polyval(coeff, x)
    residual = wavelength - fitted
    ss_total = float(np.sum((wavelength - np.mean(wavelength)) ** 2))
    r2 = 1.0 - float(np.sum(residual ** 2)) / ss_total if ss_total > 0 else 1.0

    unknown_x = numeric_column(unknowns, "pixel_x", "待测谱线像素")
    estimated = np.polyval(coeff, unknown_x)
    references, has_references = _optional_numeric(unknowns, "reference_nm", "参考波长")
    errors = estimated - references if has_references else np.full_like(estimated, np.nan)
    summary = [
        f"采用{degree}次多项式完成像素—波长定标，R²={r2:.8f}，最大定标残差={np.max(np.abs(residual)):.6g} nm",
    ]
    for row, value, error in zip(unknowns, estimated, errors):
        text = f"{row.get('source', '')} {row.get('line_label', '')}：λ={value:.4f} nm"
        if np.isfinite(error):
            text += f"，相对参考值偏差={error:+.4f} nm"
        summary.append(text)
    warnings = []
    if np.any(unknown_x < np.min(x)) or np.any(unknown_x > np.max(x)):
        warnings.append("部分待测峰位超出标准谱线定标区间，结果属于外推，可靠性较低。")
    if np.max(np.abs(residual)) > 1.0:
        warnings.append("定标最大残差超过1 nm，请检查谱线对应关系、峰中心和拼接坐标。")

    doc = create_document(name(), "实验一：摄谱仪")
    equation = "λ = " + " + ".join(
        f"({value:.8g})x^{degree-index}" for index, value in enumerate(coeff)
    )
    add_key_values(doc, "定标模型", [("定标方程", equation), ("决定系数R²", f"{r2:.8f}")])
    add_table(doc, "表1  标准谱线定标", ["光源", "谱线", "x/px", "标准λ/nm", "拟合λ/nm", "残差/nm"], [
        [row.get("source", ""), row.get("line_label", ""), f"{x[i]:.3f}", f"{wavelength[i]:.4f}",
         f"{fitted[i]:.4f}", f"{residual[i]:+.4f}"]
        for i, row in enumerate(standards)
    ])
    add_table(doc, "表2  待测谱线", ["光源", "谱线", "x/px", "计算λ/nm", "参考λ/nm", "偏差/nm"], [
        [row.get("source", ""), row.get("line_label", ""), f"{unknown_x[i]:.3f}", f"{estimated[i]:.4f}",
         (f"{references[i]:.4f}" if np.isfinite(references[i]) else ""),
         (f"{errors[i]:+.4f}" if np.isfinite(errors[i]) else "")]
        for i, row in enumerate(unknowns)
    ])
    add_summary(doc, summary)
    add_text_section(doc, "谱线观察记录", get_text(payload, "observations"))
    add_text_section(doc, "误差与讨论", get_text(payload, "discussion"))

    configure_plotting()
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
    order = np.argsort(x)
    dense_x = np.linspace(float(np.min(x)), float(np.max(x)), 400)
    axes[0].scatter(x, wavelength, color="#4472C4", label="标准谱线")
    axes[0].plot(dense_x, np.polyval(coeff, dense_x), color="#E74C3C", label=f"{degree}次定标")
    axes[0].scatter(unknown_x, estimated, marker="x", s=55, color="#2ECC71", label="待测谱线")
    axes[0].set_xlabel("峰中心像素 x / px")
    axes[0].set_ylabel("波长 λ / nm")
    axes[0].set_title("摄谱仪像素—波长定标")
    axes[0].legend()
    axes[1].axhline(0, color="#777777", linewidth=1)
    axes[1].plot(x[order], residual[order], "o-", color="#9B59B6")
    axes[1].set_xlabel("峰中心像素 x / px")
    axes[1].set_ylabel("定标残差 / nm")
    axes[1].set_title("标准谱线定标残差")
    for ax in axes:
        ax.grid(True, linestyle="--", alpha=0.3)
    chart = save_figure(fig, workpath, "exp37_spectrograph_calibration.png")
    return finish_report(doc, workpath, name(), summary, [{"filename": chart, "title": "摄谱仪波长定标与残差"}], warnings)


def _handle_monochromator(workpath, payload):
    scan_mode = get_parameter(payload, "scan_mode", "emission", cast=str)
    calibration = get_rows(payload, "monochromator_calibration", required=True, min_rows=3)
    scan = get_rows(payload, "monochromator_scan", required=True, min_rows=8)
    measured_cal = numeric_column(calibration, "measured_nm", "校准仪器读数")
    standard_cal = numeric_column(calibration, "standard_nm", "校准标准波长")
    fit = linear_fit(measured_cal, standard_cal)
    measured = numeric_column(scan, "measured_nm", "扫描仪器读数")
    signal = numeric_column(scan, "signal", "扫描信号")
    if np.any(signal < 0):
        raise OpticsInputError("扫描信号不能为负数")
    corrected_wavelength = fit["slope"] * measured + fit["intercept"]
    order = np.argsort(corrected_wavelength)
    corrected_wavelength = corrected_wavelength[order]
    signal = signal[order]
    warnings = []
    summary = [
        f"单色仪校准：λ标准={fit['slope']:.8f}×λ读数{fit['intercept']:+.6f} nm，R²={fit['r2']:.8f}"
    ]
    reference, has_reference = _optional_numeric(scan, "reference", "参考光强")
    reference = reference[order]
    if scan_mode == "absorption":
        if not has_reference or np.any(~np.isfinite(reference)):
            raise OpticsInputError("吸收光谱模式下，每一行都必须填写参考光强")
        if np.any(reference <= 0):
            raise OpticsInputError("参考光强必须大于0")
        transmittance = np.clip(signal / reference, 1e-12, None)
        spectrum_y = -np.log10(transmittance)
        y_label = "吸光度 A"
        spectrum_title = "单色仪吸收光谱"
    else:
        spectrum_y = signal
        y_label = "相对光强 / a.u."
        spectrum_title = "单色仪发射光谱"

    smooth = gaussian_filter1d(spectrum_y, sigma=1.0) if len(spectrum_y) >= 5 else spectrum_y
    amplitude = float(np.max(smooth) - np.min(smooth))
    peaks, properties = find_peaks(
        smooth,
        distance=max(1, len(smooth) // 20),
        prominence=max(amplitude * 0.06, 1e-12),
    )
    if len(peaks):
        prominent = peaks[np.argsort(properties["prominences"])[-min(10, len(peaks)):]]
        prominent = prominent[np.argsort(corrected_wavelength[prominent])]
        summary.append("主要候选峰：" + "、".join(f"{corrected_wavelength[index]:.3f} nm" for index in prominent))
    else:
        prominent = np.asarray([], dtype=int)
        warnings.append("扫描数据中未检测到明显峰，请检查步长、扫描范围和信噪比。")

    doc = create_document(name(), "实验二：单色仪")
    add_table(doc, "表1  波长校准", ["仪器读数/nm", "标准波长/nm", "拟合波长/nm", "残差/nm"], [
        [f"{measured_cal[i]:.4f}", f"{standard_cal[i]:.4f}", f"{fit['predicted'][i]:.4f}", f"{fit['residuals'][i]:+.4f}"]
        for i in range(len(measured_cal))
    ])
    scan_headers = ["校正波长/nm", "信号光强"]
    scan_rows = []
    if scan_mode == "absorption":
        scan_headers.extend(["参考光强", "吸光度A"])
        scan_rows = [
            [f"{corrected_wavelength[i]:.4f}", f"{signal[i]:.6g}", f"{reference[i]:.6g}", f"{spectrum_y[i]:.6g}"]
            for i in range(len(signal))
        ]
    else:
        scan_rows = [[f"{corrected_wavelength[i]:.4f}", f"{signal[i]:.6g}"] for i in range(len(signal))]
    add_table(doc, "表2  扫描结果", scan_headers, scan_rows)
    add_summary(doc, summary)
    add_text_section(doc, "谱线观察记录", get_text(payload, "observations"))
    add_text_section(doc, "误差与讨论", get_text(payload, "discussion"))

    configure_plotting()
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
    axes[0].scatter(measured_cal, standard_cal, color="#4472C4", label="校准点")
    cal_x = np.linspace(float(np.min(measured_cal)), float(np.max(measured_cal)), 200)
    axes[0].plot(cal_x, fit["slope"] * cal_x + fit["intercept"], color="#E74C3C", label="线性校准")
    axes[0].set_xlabel("单色仪读数 / nm")
    axes[0].set_ylabel("标准波长 / nm")
    axes[0].set_title("单色仪波长校准")
    axes[0].legend()
    axes[1].plot(corrected_wavelength, spectrum_y, "o-", markersize=3.5, color="#2E86C1")
    if len(prominent):
        axes[1].scatter(corrected_wavelength[prominent], spectrum_y[prominent], color="#E74C3C", s=32, zorder=3)
    axes[1].set_xlabel("校正波长 / nm")
    axes[1].set_ylabel(y_label)
    axes[1].set_title(spectrum_title)
    for ax in axes:
        ax.grid(True, linestyle="--", alpha=0.3)
    chart = save_figure(fig, workpath, "exp37_monochromator.png")
    return finish_report(doc, workpath, name(), summary, [{"filename": chart, "title": spectrum_title}], warnings)


def handle_structured(workpath, payload):
    try:
        part = get_parameter(payload, "part", "spectrograph", True, cast=str)
        if part == "spectrograph":
            return _handle_spectrograph(workpath, payload)
        if part == "monochromator":
            return _handle_monochromator(workpath, payload)
        raise OpticsInputError("实验内容选择不正确")
    except Exception as exc:
        return error_result(exc)


def handle(workpath, extension):
    """保留旧单表入口；新版网页使用 handle_structured。"""
    return 1
