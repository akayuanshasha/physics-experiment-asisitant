# -*- coding: utf-8 -*-
"""
Physics Experiment AI Assistant - Manual Debug Script
=====================================================
Layer-by-layer verification, from low-level tool functions to plugins to full pipeline.
Run: venv/Scripts/python debug_tools.py
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

SEP = "=" * 70
OK  = " [OK] "
INFO= "  -> "


# ============================================================
# Layer 1: Test standalone tool functions in tool_executor.py
# ============================================================
print(SEP)
print("[Layer 1] Testing tool_executor.py standalone functions")
print(SEP)

from tool_executor import (
    compute_statistics, fit_linear, create_chart, generate_report,
    compute_young_modulus, compute_hall_effect
)

# --- 1.1 Statistics ---
print()
print("[1.1] compute_statistics")
data = [0.495, 0.497, 0.496, 0.498, 0.496]
result = compute_statistics(data, "wire_diameter")
eps = 0.001
assert abs(result["mean"] - 0.4964) < eps, "Mean wrong: %s" % result['mean']
assert abs(result["std"] - 0.00114) < eps, "Std wrong: %s" % result['std']
print(OK + "mean=%.4f, std=%.4f, uncertainty=%.4f" % (result["mean"], result["std"], result["uncertainty"]))

# --- 1.2 Linear fit ---
print()
print("[1.2] fit_linear")
x = [0, 0.30, 0.61, 0.89, 1.20, 1.49]
y = [0, 9.8, 19.6, 29.4, 39.2, 49.0]
result = fit_linear(x, y, "elongation(mm)", "force(N)")
assert abs(result["slope"] - 32.81) < 1.0, "Slope wrong: %s" % result['slope']
print(OK + "slope=%.4f, intercept=%.4f, R2=%.4f" % (result["slope"], result["intercept"], result["R²"]))

# --- 1.3 Young modulus ---
print()
print("[1.3] compute_young_modulus")
result = compute_young_modulus(
    force=[0, 9.8, 19.6, 29.4, 39.2, 49.0],
    diameter=[0.495, 0.497, 0.496, 0.498, 0.496],
    length=500.0,
    elongation=[0, 0.30, 0.61, 0.89, 1.20, 1.49]
)
print(OK + "E = %.4f GPa" % result['E_GPa'])

# --- 1.4 Hall effect ---
print()
print("[1.4] compute_hall_effect")
result = compute_hall_effect(
    work_currents=[5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
    hall_voltages=[4.6, 9.1, 13.7, 18.2, 22.8, 27.3],
    excitation_currents=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
)
print(OK + "K_H = %.4f mV/(mA*A)" % result['K_H'])

# --- 1.5 Chart ---
print()
print("[1.5] create_chart")
path = create_chart(x, y, "elongation(mm)", "force(N)", "test chart",
                     fit_type="linear", save_name="debug_test_chart.png")
assert os.path.exists(path), "Chart not generated: %s" % path
print(OK + "chart saved: %s" % path)

# --- 1.6 Report ---
print()
print("[1.6] generate_report")
path = generate_report(
    experiment_name="debug test",
    data_summary="test data",
    results_summary={"fit": {"slope": 32.81, "R2": 0.999}},
    analysis_text="test report",
    chart_paths=[path],
    output_name="debug_test_report.html"
)
assert os.path.exists(path), "Report not generated: %s" % path
print(OK + "report saved: %s" % path)


# ============================================================
# Layer 2: Test plugin calculate methods
# ============================================================
print()
print(SEP)
print("[Layer 2] Testing plugin calculate methods")
print(SEP)

import plugins
from plugins import PluginRegistry
# Explicitly import plugin modules to trigger @PluginRegistry.register decorators
import plugins.young_modulus
import plugins.hall_effect

# --- 2.1 Young modulus plugin ---
print()
print("[2.1] Young modulus plugin")
cref = PluginRegistry.get("杨氏模量（拉伸法）")
if cref is None:
    cref = PluginRegistry.get("YoungModulus")
if cref is None:
    for p in PluginRegistry._plugins.values():
        if '杨氏' in str(p) or 'Young' in str(p.__name__):
            cref = p
            break
assert cref is not None, "Young modulus plugin not found. Available: %s" % PluginRegistry.list_all()
ym_instance = cref()
print(OK + "plugin found: %s" % getattr(ym_instance, 'name', 'unnamed'))

# Demo data from DEMO_DATA.md - use exact Chinese keys the plugin expects
demo_data_ym = {
    "钢丝直径(mm)": [0.495, 0.497, 0.496, 0.498, 0.496],
    "砝码质量(kg)": [0, 1, 2, 3, 4, 5],
    "标尺读数(mm)": [0, 0.30, 0.61, 0.89, 1.20, 1.49],
}
result = ym_instance.calculate(demo_data_ym)
print(OK + "calculation done")
print(INFO + "steps: %s" % json.dumps(result['steps'], ensure_ascii=False))
print(INFO + "final: %s" % json.dumps(result['final'], ensure_ascii=False))

# Verify E has uncertainty (contains +/-)
E_str = str(result['final'].get("杨氏模量 E", ""))
assert "±" in E_str, "E missing uncertainty: %s" % E_str
print(OK + "E has uncertainty: %s" % E_str)

# --- 2.2 Hall effect plugin ---
print()
print("[2.2] Hall effect plugin")
hecref = PluginRegistry.get("霍尔效应")
if hecref is None:
    hecref = PluginRegistry.get("HallEffect")
assert hecref is not None, "Hall effect plugin not found"
he_instance = hecref()
print(OK + "plugin found: %s" % getattr(he_instance, 'name', 'unnamed'))

demo_data_he = {
    "励磁电流(A)": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
    "霍尔电压(mV)": [4.6, 9.1, 13.7, 18.2, 22.8, 27.3],
    "工作电流(mA)": [5.0],
}
result = he_instance.calculate(demo_data_he)
print(OK + "calculation done")
print(INFO + "steps: %s" % json.dumps(result['steps'], ensure_ascii=False))
print(INFO + "final: %s" % json.dumps(result['final'], ensure_ascii=False))
assert "霍尔元件灵敏度 K_H" in result['final'], "Hall result missing K_H"
print(OK + "K_H present")


# ============================================================
# Layer 3: Test plugin generate_chart methods
# ============================================================
print()
print(SEP)
print("[Layer 3] Testing plugin generate_chart methods")
print(SEP)

output_dir = os.path.join(os.path.dirname(__file__), "output")

# --- 3.1 Young modulus chart ---
print()
print("[3.1] Young modulus chart")
ym_result = ym_instance.calculate(demo_data_ym)
ym_charts = ym_instance.generate_chart(demo_data_ym, ym_result, output_dir)
for p in ym_charts:
    assert os.path.exists(p), "Chart not generated: %s" % p
    print(OK + "chart saved: %s" % p)

# --- 3.2 Hall effect chart ---
print()
print("[3.2] Hall effect chart")
he_result = he_instance.calculate(demo_data_he)
he_charts = he_instance.generate_chart(demo_data_he, he_result, output_dir)
for p in he_charts:
    assert os.path.exists(p), "Chart not generated: %s" % p
    print(OK + "chart saved: %s" % p)


# ============================================================
# Layer 4: Test full pipeline (data -> calculate -> chart -> report)
# ============================================================
print()
print(SEP)
print("[Layer 4] Testing full pipeline (data -> calculate -> chart -> report)")
print(SEP)

from tool_executor import generate_report as gen_report

def run_full_experiment(name, plugin, data):
    """Run full pipeline for one experiment: calculate -> chart -> report"""
    print()
    print("  Experiment: %s" % name)

    # 1. calculate
    results = plugin.calculate(data)
    print("    [OK] calculation done")

    # 2. charts
    charts = plugin.generate_chart(data, results, output_dir)
    print("    [OK] charts generated: %s" % charts)

    # 3. report content
    report_content = plugin.get_report_content(data, results)
    print("    [OK] report content generated")

    # 4. HTML report
    safe_name = name.replace("(", "_").replace(")", "").replace(" ", "_")
    report_path = gen_report(
        experiment_name=name,
        data_summary=json.dumps(data, ensure_ascii=False, indent=2),
        results_summary=results.get("final", {}),
        analysis_text=report_content.get("analysis", ""),
        chart_paths=charts,
        output_name="%s_full_report.html" % safe_name
    )
    assert os.path.exists(report_path), "Report not generated: %s" % report_path
    print("    [OK] full report saved: %s" % report_path)
    return report_path

ym_report = run_full_experiment("YoungModulus", ym_instance, demo_data_ym)
he_report = run_full_experiment("HallEffect", he_instance, demo_data_he)


# ============================================================
# Summary
# ============================================================
print()
print(SEP)
print(" ALL DEBUG TESTS PASSED!")
print(SEP)
print("  Generated files in %s/:" % output_dir)
for f in sorted(os.listdir(output_dir)):
    fpath = os.path.join(output_dir, f)
    print("    * %s (%d bytes)" % (f, os.path.getsize(fpath)))
print()
print("  Open the .html files in a browser to view full reports.")