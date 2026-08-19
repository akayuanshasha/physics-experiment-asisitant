from head import * # 导入万能头
from structured_support import handle_legacy_single_table, make_schema, make_table

def name():
    return "杨氏模量及泊松比"

def handle(workpath,extension):
    try:
        excelpath=workpath+name()+'.'+extension

        if extension=='csv':
            with open(excelpath,'rb') as f:
                encode=chardet.detect(f.read())["encoding"]
            data=pd.read_csv(excelpath, header=0, encoding=encode)
        else:
            data=pd.read_excel(excelpath, header=0)

        os.remove(excelpath)

        cols = list(data.columns)
        # 识别：F(N力), ΔL(mm纵向应变), ΔD(mm横向应变)
        # 或 σ(N/mm²), ε_long(με), ε_trans(με)
        f_col = [c for c in cols if 'F' in c or '力' in c or '载荷' in c][0] if any('F' in c or '力' in c or '载荷' in c for c in cols) else cols[0]
        dl_col = [c for c in cols if 'ΔL' in c or '纵向' in c or 'e_l' in c.lower()][0] if any('ΔL' in c or '纵向' in c or 'e_l' in c.lower() for c in cols) else (cols[1] if len(cols)>1 else cols[0])
        dd_col = [c for c in cols if 'ΔD' in c or '横向' in c or 'e_t' in c.lower()][0] if any('ΔD' in c or '横向' in c or 'e_t' in c.lower() for c in cols) else (cols[2] if len(cols)>2 else cols[1])

        F = pd.to_numeric(data[f_col], errors='coerce')  # N
        delta_L = pd.to_numeric(data[dl_col], errors='coerce')  # mm 或 με
        delta_D = pd.to_numeric(data[dd_col], errors='coerce')  # mm 或 με

        # 已知参数
        A0 = np.pi * (5.0)**2 / 4  # mm²，默认d₀=5mm
        L0 = 200.0  # mm 标距
        D0 = 5.0  # mm 原始直径

        # 应力 σ = F/A0
        sigma = F / A0  # N/mm² = MPa

        # 纵向应变 ε_long = ΔL/L0
        epsilon_l = delta_L / L0

        # 横向应变 ε_trans = ΔD/D0（注意符号）
        epsilon_t = delta_D / D0

        # 杨氏模量 E = σ/ε → 从 σ-ε 曲线线性段拟合
        # 取前半段（弹性区）
        n_elastic = len(sigma) // 2
        if n_elastic < 2:
            n_elastic = len(sigma)

        # 用最小二乘法拟合 σ = E * ε_l
        x = epsilon_l.iloc[:n_elastic].to_numpy(dtype=float)
        y = sigma.iloc[:n_elastic].to_numpy(dtype=float)
        valid = np.isfinite(x) & np.isfinite(y)
        x, y = x[valid], y[valid]
        if len(x) < 2:
            raise ValueError("弹性区至少需要2组有效载荷与纵向形变数据")
        E_modulus, intercept = np.polyfit(x, y, 1)  # MPa → GPa
        predicted = E_modulus * x + intercept
        residual = np.sum((y - predicted) ** 2)
        total = np.sum((y - np.mean(y)) ** 2)
        r_sq = 1 - residual / total if total > 0 else 1.0

        # 泊松比 ν = -ε_trans / ε_long
        # 需要 ΔL 和 ΔD 同号（都加载时）的区间
        epsilon_l_clip = epsilon_l.replace(0, np.nan)
        epsilon_t_clip = epsilon_t.where(epsilon_l.abs() > 1e-15, np.nan)
        nu = -epsilon_t_clip / epsilon_l_clip
        nu = nu.dropna()
        res_nu = analyse(nu, 0, 0, r'\nu', '', confidence_C=3) if len(nu) > 0 else None

        docu=Document()
        docu.styles['Normal'].font.name = '微软雅黑'
        docu.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

        docu.add_paragraph(name())
        docu.add_paragraph()
        docu.add_paragraph("【Latex代码在下面，请向下翻阅】")
        docu.add_paragraph()

        docu.add_paragraph("试件几何参数：")
        docu.add_paragraph("A₀ = {:.2f} mm², L₀ = {:.1f} mm, D₀ = {:.1f} mm".format(A0, L0, D0))
        docu.add_paragraph()
        docu.add_paragraph("杨氏模量（线性段）E = {:.2f} GPa, R² = {:.4f}".format(E_modulus/1000, r_sq))
        docu.add_paragraph()

        # 数据表格
        table = docu.add_table(rows=min(len(F)+1, 31), cols=6, style='Table Grid')
        for j, h in enumerate(['F (N)', 'ΔL', 'ΔD', 'σ (MPa)', 'ε_l (×10⁻⁶)', 'ν']):
            table.rows[0].cells[j].text = h
        for i in range(min(len(F), 30)):
            table.rows[i+1].cells[0].text = '{:.1f}'.format(F.iloc[i])
            table.rows[i+1].cells[1].text = '{:.4f}'.format(delta_L.iloc[i])
            table.rows[i+1].cells[2].text = '{:.4f}'.format(delta_D.iloc[i])
            table.rows[i+1].cells[3].text = '{:.2f}'.format(sigma.iloc[i])
            table.rows[i+1].cells[4].text = '{:.2f}'.format(epsilon_l.iloc[i]*1e6)
            table.rows[i+1].cells[5].text = '{:.4f}'.format(nu.iloc[i]) if not nu.empty and i < len(nu) else '--'
        docu.add_paragraph()

        if res_nu is not None:
            insert_data(docu, "泊松比 ν", res_nu, "word")
            docu.add_paragraph()

        docu.add_paragraph("【Latex代码】")
        docu.add_paragraph("杨氏模量：E = \\frac{\\sigma}{\\varepsilon}")
        docu.add_paragraph("泊松比：\\nu = -\\frac{\\varepsilon_t}{\\varepsilon_l}")
        if res_nu is not None:
            insert_data(docu, "泊松比 ν", res_nu, "latex")

        docu.save(workpath+name()+".docx")
        return 0
    except:
        traceback.print_exc()
        return 1


def schema():
    sample = [
        [100, 0.025, -0.003], [200, 0.051, -0.005], [300, 0.076, -0.008],
        [400, 0.102, -0.011], [500, 0.127, -0.014], [600, 0.153, -0.017],
        [700, 0.178, -0.020], [800, 0.203, -0.023], [900, 0.229, -0.026], [1000, 0.254, -0.029],
    ]
    table = make_table(
        "table1", "杨氏模量及泊松比测量数据表", ["F", "delta_L", "delta_D"],
        sample=sample, initial_rows=len(sample),
        chart={"x_column": "c0", "y_column": "c1", "x_label": "载荷 F", "y_label": "轴向伸长量 ΔL",
               "title": "轴向形变-载荷关系", "fit": "linear"},
    )
    return make_schema("由轴向和横向形变计算杨氏模量及泊松比。", [table], analysis_hints="检查形变与载荷的线性及横向形变符号。")


def handle_structured(workpath, payload):
    return handle_legacy_single_table(workpath, payload, schema(), name(), handle)
