"""Write the analyst deliverables: issues CSV and Excel, concentration tables, rule catalogue, chart."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

from .rules import RISK_FLAGS, RULES  # noqa: E402

FILL = {"error": "F8D7DA", "warning": "FFF3CD"}
HEAD = PatternFill("solid", fgColor="1F3A5F")


def rule_catalogue() -> pd.DataFrame:
    return pd.DataFrame([r.__dict__ for r in RULES + RISK_FLAGS]).rename(columns={"id": "rule_id"})


def _style(ws, widths: Dict[str, int], wrap: set, freeze: str = "A2") -> None:
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = HEAD
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for i, c in enumerate(ws[1], 1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(c.value, 14)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=ws.cell(1, c.column).value in wrap)
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions


def write_excel(path: Path, issues: pd.DataFrame, summary: pd.DataFrame, groups: pd.DataFrame, countries: pd.DataFrame,
                functions: pd.DataFrame, flags: pd.DataFrame, catalogue: pd.DataFrame) -> None:
    analyst = issues.copy()
    analyst["analyst_status"] = ""
    analyst["analyst_comment"] = ""
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        summary.to_excel(xw, sheet_name="Summary", index=False)
        analyst.to_excel(xw, sheet_name="Issues", index=False)
        flags.to_excel(xw, sheet_name="Risk flags", index=False)
        groups.to_excel(xw, sheet_name="Concentration - groups", index=False)
        countries.to_excel(xw, sheet_name="Concentration - countries", index=False)
        functions.to_excel(xw, sheet_name="Critical functions", index=False)
        catalogue.to_excel(xw, sheet_name="Rules", index=False)
        wb = xw.book
        _style(wb["Summary"], {"metric": 44, "value": 18, "detail": 70}, {"detail"})
        ws = wb["Issues"]
        _style(ws, {"severity": 10, "rule_id": 9, "template": 9, "row": 6, "key": 30, "column": 8, "value": 22,
                    "message": 60, "fix": 60, "eba_ref": 26, "basis": 13, "analyst_status": 14, "analyst_comment": 26},
               {"message", "fix", "key", "value", "eba_ref"})
        for r in range(2, ws.max_row + 1):
            sev = ws.cell(r, 1).value
            ws.cell(r, 1).fill = PatternFill("solid", fgColor=FILL.get(sev, "FFFFFF"))
        _style(wb["Risk flags"], {"flag_id": 9, "subject": 40, "value": 22, "threshold": 10, "description": 46,
                                  "suggested_action": 70}, {"description", "suggested_action", "subject"})
        ws = wb["Concentration - groups"]
        _style(ws, {"group_id": 24, "group_name": 36, "spend_eur": 14, "spend_share": 12}, set())
        for r in range(2, ws.max_row + 1):
            ws.cell(r, 6).number_format = "#,##0"; ws.cell(r, 7).number_format = "0.0%"
        ws = wb["Concentration - countries"]
        _style(ws, {"basis": 30, "spend_eur": 14, "spend_share": 12}, set())
        for r in range(2, ws.max_row + 1):
            ws.cell(r, 6).number_format = "#,##0"; ws.cell(r, 7).number_format = "0.0%"
        ws = wb["Critical functions"]
        _style(ws, {"function_id": 11, "function_name": 30, "entity_lei": 24, "spend_eur": 14}, set())
        for r in range(2, ws.max_row + 1):
            ws.cell(r, 7).number_format = "#,##0"
        _style(wb["Rules"], {"rule_id": 9, "name": 48, "category": 20, "severity": 10, "templates": 30, "eba_ref": 44,
                             "basis": 13, "fix": 70}, {"name", "templates", "eba_ref", "fix"})


def chart(path: Path, groups: pd.DataFrame, countries: pd.DataFrame) -> None:
    g = groups.head(10).iloc[::-1]
    c = countries[countries["basis"] == "ultimate parent headquarters"].head(8).iloc[::-1]
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.2), gridspec_kw={"width_ratios": [1.35, 1]})
    a.barh(g["group_name"].str.slice(0, 36), g["spend_eur"] / 1e6, color="#2F6690")
    for y, (v, cc, n) in enumerate(zip(g["spend_eur"], g["critical_contracts"], g["contracts"])):
        a.text(v / 1e6 + 0.1, y, f"{v / 1e6:.1f}  ({cc}/{n} contracts critical)", va="center", fontsize=8)
    a.set_xlabel("Annual ICT spend, EUR m (illustrative FX)")
    a.set_title("Spend by ultimate-parent group, top 10", loc="left", fontsize=11)
    a.set_xlim(0, g["spend_eur"].max() / 1e6 * 1.55)
    colors = ["#2F6690" if e else "#D1603D" for e in c["in_eu"]]
    b.barh(c["country"], c["spend_share"] * 100, color=colors)
    for y, v in enumerate(c["spend_share"] * 100):
        b.text(v + 0.5, y, f"{v:.1f} %", va="center", fontsize=8)
    b.set_xlabel("Share of ICT spend, %")
    b.set_title("By country of the ultimate parent", loc="left", fontsize=11)
    b.set_xlim(0, c["spend_share"].max() * 100 * 1.2)
    b.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#2F6690"), plt.Rectangle((0, 0), 1, 1, color="#D1603D")],
             labels=["EU", "non-EU"], loc="lower right", frameon=False)
    for ax in (a, b):
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.text(0.01, 0.01, "SYNTHETIC register. Names, amounts and exchange rates are invented.", fontsize=8, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=140)
    plt.close(fig)
