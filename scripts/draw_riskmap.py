#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCX NEXT v1.4.3 - 구역별 위험지수 히트맵 배치도
원 배치도(v1.4.3)의 점선 원(작업반경 중첩)·화살표(동선 흐름)·범례선을 모두 제거하고,
각 세부구역 박스에 [구역명 / 위험지수 / 아차·경보·혼재·미조치]만 표기한다.

출력: out/risk_map.png, out/risk_map.svg
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import FancyBboxPatch, Rectangle

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(BASE, "out")
os.makedirs(OUT, exist_ok=True)

plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

df = pd.read_csv(os.path.join(OUT, "zone_metrics.csv"), encoding="utf-8-sig")
M = {r.Subzone: r for r in df.itertuples()}

SHORT = {
    "A1": "1동 코어·벽체", "A2": "슬래브·타설", "A3": "양중·호이스트",
    "A4": "펌프카·레미콘", "B1": "메인게이트", "B2": "자재 하역장",
    "B3": "자재 적치장", "C1": "포디움 외장", "C2": "커튼월 양중",
    "C3": "이동식크레인", "D1": "지하램프", "D2": "지하2층 설비",
    "D3": "지하3층 토목",
}

CMAP = LinearSegmentedColormap.from_list(
    "risk", ["#1B7F4B", "#63A85C", "#C9C24A", "#E8952F", "#BE2B22"])
NORM = Normalize(vmin=0, vmax=70)

INK, SUBINK, PAPER = "#12212B", "#4A5A66", "#FAFBFC"
CHIPS = [("아차", "NearMiss", False), ("경보", "Alerts", False),
         ("혼재", "MixedSlot", False), ("미조치", "Unclosed", True)]

# y 1단위 ≈ 6pt  (fig 17x12.2in, ax 높이 0.655)
C1, C2, C3, C4, C5 = 4.0, 22.0, 40.0, 58.0, 76.0
CW = 16.6
LAYOUT = {
    "A3": (C1, 52.0, CW, 18.0), "A4": (C2, 52.0, CW, 18.0),
    "B2": (C3, 52.0, CW, 18.0), "B3": (C4, 52.0, CW, 18.0),
    "B1": (C3, 70.8, CW * 2 + 2.0, 11.6),
    "A1": (C1, 23.0, CW, 25.5), "A2": (C2, 23.0, CW, 25.5),
    "C1": (C3, 23.0, CW, 25.5), "C2": (C4, 23.0, CW, 25.5),
    "C3": (C5, 23.0, CW, 25.5),
    "D1": (C3, 5.0, CW, 13.2), "D2": (C4, 5.0, CW, 13.2),
    "D3": (C5, 5.0, CW, 13.2),
}


def ink_on(risk):
    r, g, b, _ = CMAP(NORM(risk))
    return "#FFFFFF" if (0.299 * r + 0.587 * g + 0.114 * b) < 0.52 else "#12212B"


def rrect(ax, x, y, w, h, fc, ec="none", lw=0.0, r=1.0, a=1.0, z=4):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0,rounding_size={r}",
                                facecolor=fc, edgecolor=ec, linewidth=lw,
                                alpha=a, zorder=z))


def chips(ax, x, y, w, h, zone, fs_val=12.4, fs_lab=7.4):
    gap = 0.7
    cw = (w - gap * 3) / 4.0
    for i, (label, field, emph) in enumerate(CHIPS):
        cx = x + i * (cw + gap)
        rrect(ax, cx, y, cw, h, "#FFFFFF", a=0.90, r=0.6, z=6)
        val = getattr(M[zone], field)
        vc = "#B3261E" if (emph and val >= 5) else INK
        ax.text(cx + cw / 2, y + h * 0.62, f"{val:,}", ha="center", va="center",
                fontsize=fs_val, fontweight="bold", color=vc, zorder=7)
        ax.text(cx + cw / 2, y + h * 0.20, label, ha="center", va="center",
                fontsize=fs_lab, color=SUBINK, zorder=7)


def pill(ax, xr, yc, grade, size):
    ax.text(xr, yc, grade, ha="right", va="center", fontsize=size,
            fontweight="bold", color=INK, zorder=8,
            bbox=dict(boxstyle="round,pad=0.26,rounding_size=0.5",
                      facecolor="#FFFFFF", edgecolor="none", alpha=0.93))


def draw_zone(ax, zone, box):
    x, y, w, h = box
    m = M[zone]
    risk = float(m.RiskIndex)
    tc = ink_on(risk)

    rrect(ax, x + 0.3, y - 0.4, w, h, "#0D1B24", a=0.09, r=1.2, z=3)
    rrect(ax, x, y, w, h, CMAP(NORM(risk)), "#FFFFFF", 1.4, 1.2, 1.0, 4)
    rrect(ax, x, y, w, h, "none", "#0D1B24", 0.8, 1.2, 0.20, 5)

    if h >= 24:                                     # ---- 대형  h=25.5
        ax.text(x + 1.5, y + 21.6, zone, fontsize=21, fontweight="bold",
                color=tc, va="center", zorder=7)
        pill(ax, x + w - 1.3, y + 21.6, m.Grade, 8.0)
        ax.text(x + 1.6, y + 17.4, SHORT[zone], fontsize=8.8, color=tc,
                va="center", zorder=7)
        ax.text(x + w / 2, y + 11.6, f"{risk:.1f}", ha="center", va="center",
                fontsize=30, fontweight="bold", color=tc, zorder=7)
        ax.text(x + w / 2, y + 7.7, "위험지수", ha="center", va="center",
                fontsize=7.4, color=tc, alpha=0.92, zorder=7)
        chips(ax, x + 1.0, y + 1.5, w - 2.0, 5.0, zone, 12.4, 7.4)

    elif h >= 16:                                   # ---- 중형  h=18
        ax.text(x + 1.4, y + 14.9, zone, fontsize=17.5, fontweight="bold",
                color=tc, va="center", zorder=7)
        pill(ax, x + w - 1.2, y + 14.9, m.Grade, 7.5)
        ax.text(x + 1.5, y + 11.7, SHORT[zone], fontsize=8.2, color=tc,
                va="center", zorder=7)
        ax.text(x + w / 2, y + 8.4, f"{risk:.1f}", ha="center", va="center",
                fontsize=20, fontweight="bold", color=tc, zorder=7)
        chips(ax, x + 0.9, y + 1.2, w - 1.8, 4.2, zone, 11.2, 6.9)

    elif h >= 12.5:                                 # ---- 소형 D  h=13.2
        ax.text(x + 1.3, y + 10.4, zone, fontsize=12.5, fontweight="bold",
                color=tc, va="center", zorder=7)
        pill(ax, x + w - 1.2, y + 10.4, m.Grade, 6.9)
        ax.text(x + 1.3, y + 7.6, SHORT[zone], fontsize=7.4
                , color=tc, va="center", zorder=7)
        ax.text(x + w - 1.3, y + 7.5, f"{risk:.1f}", ha="right", va="center",
                fontsize=15, fontweight="bold", color=tc, zorder=7)
        ax.text(x + w - 1.3 - 3.9, y + 7.4, "위험지수", ha="right", va="center",
                fontsize=6.4, color=tc, alpha=0.9, zorder=7)
        chips(ax, x + 0.9, y + 1.1, w - 1.8, 3.9, zone, 9.4, 6.2)

    else:                                           # ---- 스트립 B1  h=11.6
        ax.text(x + 1.5, y + 9.1, zone, fontsize=13.5, fontweight="bold",
                color=tc, va="center", zorder=7)
        ax.text(x + 4.4, y + 9.1, SHORT[zone], fontsize=8.6, color=tc,
                va="center", zorder=7)
        pill(ax, x + w - 1.4, y + 9.1, m.Grade, 7.4)
        ax.text(x + w - 1.4, y + 5.4, f"{risk:.1f}", ha="right", va="center",
                fontsize=15, fontweight="bold", color=tc, zorder=7)
        ax.text(x + w - 1.4 - 3.9, y + 5.3, "위험지수", ha="right", va="center",
                fontsize=6.6, color=tc, alpha=0.9, zorder=7)
        chips(ax, x + 1.5, y + 1.1, 23.0, 4.0, zone, 9.8, 6.5)


def top3_panel(ax, x, y, w, h):
    rrect(ax, x, y, w, h, "#FFFFFF", "#D3DDE3", 0.9, 1.0, 0.96, 4)
    ax.text(x + 1.4, y + h - 2.5, "위험 집중 TOP 3", fontsize=9.4,
            fontweight="bold", color=INK, va="center", zorder=6)
    ax.text(x + w - 1.4, y + h - 2.6, "지수 · 주된 동인", fontsize=6.8,
            color=SUBINK, ha="right", va="center", zorder=6)

    drivers = {"B2": "경보 83 · 혼재 57%", "B3": "혼재 77% · 미조치 4",
               "D2": "미조치 11 · 아차 4"}
    top = df.sort_values("RiskIndex", ascending=False).head(3)
    for i, r in enumerate(top.itertuples()):
        ry = y + h - 4.9 - i * 2.6
        ax.text(x + 1.6, ry, f"{i + 1}", fontsize=8.8, fontweight="bold",
                color=CMAP(NORM(r.RiskIndex)), va="center", zorder=6)
        ax.text(x + 3.0, ry, r.Subzone, fontsize=8.8, fontweight="bold",
                color=INK, va="center", zorder=6)
        ax.text(x + 5.9, ry, SHORT[r.Subzone], fontsize=7.6, color=SUBINK,
                va="center", zorder=6)
        bw = 7.6
        ax.add_patch(Rectangle((x + 12.4, ry - 0.8), bw, 1.6,
                               facecolor="#E7EDF0", edgecolor="none", zorder=5))
        ax.add_patch(Rectangle((x + 12.4, ry - 0.8), bw * r.RiskIndex / 70.0, 1.6,
                               facecolor=CMAP(NORM(r.RiskIndex)),
                               edgecolor="none", zorder=6))
        ax.text(x + 21.4, ry, f"{r.RiskIndex:.1f}", fontsize=8.8,
                fontweight="bold", color=INK, va="center", zorder=6)
        ax.text(x + 25.6, ry, drivers.get(r.Subzone, ""), fontsize=6.6,
                color=SUBINK, va="center", zorder=6)


def main():
    fig = plt.figure(figsize=(17.0, 12.2), dpi=200)
    fig.patch.set_facecolor(PAPER)
    ax = fig.add_axes([0.015, 0.275, 0.97, 0.665])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 96)
    ax.axis("off")

    # 현장 외곽
    rrect(ax, 3.2, 3.0, 90.0, 86.0, "#EFF3F5", "#0D1B24", 2.0, 1.4, 1.0, 1)

    # 북측 외부 보호보행통로
    rrect(ax, 4.0, 84.6, 88.4, 3.6, "#3F7D4E", "none", 0, 0.5, 1.0, 2)
    ax.text(4.9, 86.4, "북측 도시도로 · 인접 상가", ha="left", va="center",
            fontsize=8.8, color="white", zorder=3)
    ax.text(91.5, 86.4, "외부 보호보행통로 (상시 개방 · 폐쇄 불가)", ha="right",
            va="center", fontsize=8.8, color="white", fontweight="bold", zorder=3)

    # 현장 내부 작업구역 경계
    ax.add_patch(Rectangle((4.4, 4.4), 86.4, 78.6, facecolor="none",
                           edgecolor="#A9B8C1", linewidth=1.0,
                           linestyle=(0, (5, 4)), zorder=2))
    ax.text(90.7, 80.9, "현장 내부 작업구역", ha="right", va="center",
            fontsize=7.6, color="#8394A0", zorder=3)

    for zone, box in LAYOUT.items():
        draw_zone(ax, zone, box)

    top3_panel(ax, 4.0, 70.8, 34.6, 11.6)

    # 제목
    fig.text(0.5, 0.973, "SCX NEXT 가상 도심지 복합시설  |  구역별 위험지수 히트맵",
             ha="center", va="center", fontsize=21.5, fontweight="bold", color=INK)
    fig.text(0.5, 0.945,
             "분석기간 2026-10-05 ~ 10-31  ·  13개 세부구역  ·  아차 / 경보 / 혼재슬롯 / 미조치 4개 지표 기반 0~100 지수",
             ha="center", va="center", fontsize=10.4, color=SUBINK)

    # ---------------- 범례
    lx = fig.add_axes([0.030, 0.010, 0.94, 0.250])
    lx.set_xlim(0, 100)
    lx.set_ylim(0, 100)
    lx.axis("off")

    # (1) 색상 스케일
    lx.text(0, 95, "위험지수 색상 스케일", fontsize=9.8, fontweight="bold", color=INK)
    grad = [[i / 200.0] for i in range(201)]
    lx.imshow(grad, extent=(0, 25, 66, 82), aspect="auto", cmap=CMAP,
              norm=Normalize(0, 1), zorder=2)
    lx.add_patch(Rectangle((0, 66), 25, 16, facecolor="none",
                           edgecolor="#8FA0AA", linewidth=0.8, zorder=3))
    for v, lab in [(0, "0"), (15, "15"), (30, "30"), (50, "50"), (70, "70+")]:
        xp = min(v / 70 * 25, 25)
        lx.plot([xp, xp], [66, 62.0], color="#8FA0AA", lw=0.7, zorder=3)
        lx.text(min(max(xp, 1.3), 23.7), 58.0, lab, ha="center", va="top",
                fontsize=7.0, color=SUBINK)
    lx.text(0, 46, "등급  매우낮음 <15 · 낮음 15–30", fontsize=7.2, color=SUBINK)
    lx.text(0, 37, "       보통 30–50 · 높음 50–70 · 매우높음 ≥70",
            fontsize=7.2, color=SUBINK)

    # (2) 지표 정의
    lx.text(30, 95, "지표 정의 (분석기간 누적)", fontsize=9.8, fontweight="bold", color=INK)
    defs = [
        ("아차", "아차사고 보고 건수  ·  10_near_miss_reports"),
        ("경보", "근접경보 발생 합계  ·  04_camera_object_log"),
        ("혼재", "작업자·장비 동시 존재 1시간 슬롯  (구역당 230슬롯)"),
        ("미조치", "점검 Open·In Progress + 아차 Monitoring·In Progress"),
    ]
    for i, (k, v) in enumerate(defs):
        yy = 82 - i * 13.0
        lx.text(30, yy, k, fontsize=8.2, fontweight="bold", color=INK, va="center")
        lx.text(35.2, yy, v, fontsize=7.5, color=SUBINK, va="center")

    # (3) 가중치
    lx.text(70, 95, "위험지수 산출 (가중치)", fontsize=9.8, fontweight="bold", color=INK)
    weights = [("혼재슬롯률", 30), ("경보", 25), ("미조치", 20),
               ("아차사고", 15), ("잔여위험도", 10)]
    xb, total_w = 70.0, 28.0
    for name, wt in weights:
        seg = total_w * wt / 100.0
        lx.add_patch(Rectangle((xb, 72), seg - 0.4, 11, facecolor="#2F5D73",
                               edgecolor="none", zorder=3))
        lx.text(xb + seg / 2 - 0.2, 77.5, f"{wt}%", ha="center", va="center",
                fontsize=7.4, color="white", fontweight="bold", zorder=4)
        lx.text(xb + seg / 2 - 0.2, 69.5, name, ha="center", va="top",
                fontsize=6.3, color=SUBINK, zorder=4)
        xb += seg
    lx.text(70, 60, "지표별 min-max 정규화(0~1) → 가중합 → ×100 (소수 1자리)",
            fontsize=7.4, color=SUBINK)

    # (4) 주석
    lx.plot([0, 98], [29, 29], color="#D5DEE3", lw=0.9)
    notes = [
        "※ 박스 중앙 큰 숫자 = 위험지수(0~100), 우측 상단 = 위험등급, 하단 4칸 = 아차 / 경보 / 혼재 / 미조치 건수.",
        "※ 원 배치도의 점선 원(작업반경 중첩) · 화살표(동선 흐름) · 범례선은 제거하고, 구역별 정량 지표 비교만 남겼습니다.",
        "※ 교육·경연용 가상 데이터입니다. 실제 현장·기업과 무관하며 협력사는 코드로 표기됩니다. 원천기록 Excel과 분석용 CSV는 동일 데이터이므로 중복 합산하지 않았습니다.",
    ]
    for i, t in enumerate(notes):
        lx.text(0, 20 - i * 9.5, t, fontsize=7.3, color=SUBINK)

    for ext in ("png", "svg"):
        fig.savefig(os.path.join(OUT, f"risk_map.{ext}"),
                    facecolor=fig.get_facecolor(), bbox_inches="tight",
                    pad_inches=0.22)
    print("saved:", os.path.join(OUT, "risk_map.png"))


if __name__ == "__main__":
    main()
