#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCX NEXT v1.4.3 - 구역별 위험지수 배치도 (단순화 버전)

원 배치도(v1.4.3)의 점선 원(작업반경 중첩)·화살표(동선 흐름)·점선 경계·범례선을 모두 제거하고,
13개 세부구역 박스에 아래 6개 항목만 표기한다.

    구역명  /  위험지수  /  아차  /  경보  /  혼재슬롯  /  미조치

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

# 박스 안에 들어가는 짧은 구역명
SHORT = {
    "A1": "1동 코어·벽체", "A2": "슬래브·타설 작업면", "A3": "양중·호이스트 거점",
    "A4": "펌프카·레미콘 연결", "B1": "메인게이트 차량·보행", "B2": "일반자재 하역장",
    "B3": "자재 적치장", "C1": "포디움 외장", "C2": "커튼월 적치·TC-02 양중",
    "C3": "이동식크레인(MC-01)", "D1": "지하램프(공용통로)", "D2": "지하2층 설비",
    "D3": "지하3층 토목·방수",
}

CMAP = LinearSegmentedColormap.from_list(
    "risk", ["#1B7F4B", "#63A85C", "#C9C24A", "#E8952F", "#BE2B22"])
NORM = Normalize(vmin=0, vmax=70)

INK, SUBINK, PAPER = "#12212B", "#4A5A66", "#FAFBFC"
CARD_FC, CARD_EC = "#FFFFFF", "#CFD9DF"

# 표기 지표 (라벨, 컬럼)
CHIPS = [("아차", "NearMiss"), ("경보", "Alerts"),
         ("혼재슬롯", "MixedSlot"), ("미조치", "Unclosed")]

# ---------------------------------------------------------------- 레이아웃
# 5열 그리드. x 시작 4 / 22 / 40 / 58 / 76, 폭 16.6, 열 간격 1.4
COLS = [4.0, 22.0, 40.0, 58.0, 76.0]
CW = 16.6
WIDE = CW * 2 + 1.4           # 2열 폭 34.6

ROW_TOP = (71.0, 11.0)        # 게이트 스트립 (북측 도로 바로 아래)
ROW_1 = (50.0, 19.5)          # 지상 북측
ROW_2 = (28.5, 19.5)          # 지상 남측 / 포디움
ROW_3 = (5.0, 21.5)           # 지하

LAYOUT = {
    # 북측 (게이트)
    "B1": (COLS[2], ROW_TOP[0], CW * 3 + 2.8, ROW_TOP[1]),
    # 1행 : 1동 북측 / 물류
    "A3": (COLS[0], ROW_1[0], CW, ROW_1[1]),
    "A4": (COLS[1], ROW_1[0], CW, ROW_1[1]),
    "B2": (COLS[2], ROW_1[0], CW, ROW_1[1]),
    "B3": (COLS[3], ROW_1[0], CW, ROW_1[1]),
    # 2행 : 1동 남측 / 포디움 외장
    "A1": (COLS[0], ROW_2[0], CW, ROW_2[1]),
    "A2": (COLS[1], ROW_2[0], CW, ROW_2[1]),
    "C1": (COLS[2], ROW_2[0], CW, ROW_2[1]),
    "C2": (COLS[3], ROW_2[0], CW, ROW_2[1]),
    "C3": (COLS[4], ROW_2[0], CW, ROW_2[1]),
    # 3행 : 지하
    "D1": (COLS[2], ROW_3[0], CW, ROW_3[1]),
    "D2": (COLS[3], ROW_3[0], CW, ROW_3[1]),
    "D3": (COLS[4], ROW_3[0], CW, ROW_3[1]),
}


# ---------------------------------------------------------------- 유틸
def ink_on(risk):
    r, g, b, _ = CMAP(NORM(risk))
    return "#FFFFFF" if (0.299 * r + 0.587 * g + 0.114 * b) < 0.52 else INK


def rrect(ax, x, y, w, h, fc, ec="none", lw=0.0, r=1.0, a=1.0, z=4):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0,rounding_size={r}",
                                facecolor=fc, edgecolor=ec, linewidth=lw,
                                alpha=a, zorder=z))


def chips(ax, x, y, w, h, zone, fs_val, fs_lab):
    """아차 / 경보 / 혼재슬롯 / 미조치 4칸"""
    gap = 0.6
    cw = (w - gap * 3) / 4.0
    for i, (label, field) in enumerate(CHIPS):
        cx = x + i * (cw + gap)
        rrect(ax, cx, y, cw, h, "#FFFFFF", a=0.92, r=0.6, z=6)
        val = int(getattr(M[zone], field))
        ax.text(cx + cw / 2, y + h * 0.63, f"{val:,}", ha="center", va="center",
                fontsize=fs_val, fontweight="bold", color=INK, zorder=7)
        ax.text(cx + cw / 2, y + h * 0.22, label, ha="center", va="center",
                fontsize=fs_lab, color=SUBINK, zorder=7)


# ---------------------------------------------------------------- 구역 박스
def draw_zone(ax, zone, box):
    x, y, w, h = box
    m = M[zone]
    risk = float(m.RiskIndex)
    tc = ink_on(risk)

    rrect(ax, x + 0.3, y - 0.4, w, h, "#0D1B24", a=0.09, r=1.2, z=3)      # 그림자
    rrect(ax, x, y, w, h, CMAP(NORM(risk)), "#FFFFFF", 1.4, 1.2, 1.0, 4)   # 본체

    if h >= 15:                                      # ---- 표준 박스
        ax.text(x + 1.4, y + h - 2.9, zone, fontsize=19, fontweight="bold",
                color=tc, va="center", zorder=7)
        ax.text(x + 1.5, y + h - 5.9, SHORT[zone], fontsize=8.4, color=tc,
                va="center", zorder=7)
        ax.text(x + w / 2, y + h - 8.5, "위험지수", ha="center", va="center",
                fontsize=7.0, color=tc, alpha=0.9, zorder=7)
        ax.text(x + w / 2, y + h - 12.0, f"{risk:.1f}", ha="center", va="center",
                fontsize=27, fontweight="bold", color=tc, zorder=7)
        chips(ax, x + 0.9, y + 1.0, w - 1.8, 4.8, zone, 11.0, 6.4)

    else:                                            # ---- 게이트 스트립(B1)
        ax.text(x + 1.5, y + h - 3.1, zone, fontsize=19, fontweight="bold",
                color=tc, va="center", zorder=7)
        ax.text(x + 1.6, y + h - 6.6, SHORT[zone], fontsize=8.4, color=tc,
                va="center", zorder=7)
        ax.text(x + 1.6, y + h - 9.0, "메인게이트 (단일 출입구 · 차량/보행 공유)",
                fontsize=6.6, color=tc, alpha=0.9, va="center", zorder=7)
        cx = x + 24.0
        ax.text(cx, y + h - 2.6, "위험지수", ha="center", va="center",
                fontsize=7.0, color=tc, alpha=0.9, zorder=7)
        ax.text(cx, y + h - 6.6, f"{risk:.1f}", ha="center", va="center",
                fontsize=27, fontweight="bold", color=tc, zorder=7)
        chips(ax, x + w - 1.2 - 22.0, y + 1.2, 22.0, 8.6, zone, 13.0, 7.2)


# ---------------------------------------------------------------- 보조 카드
def card(ax, x, y, w, h):
    rrect(ax, x, y, w, h, CARD_FC, CARD_EC, 0.9, 1.0, 0.97, 4)


def totals_card(ax, x, y, w, h):
    """전체 총계"""
    card(ax, x, y, w, h)
    ax.text(x + 1.4, y + h - 2.2, "현장 전체 (13개 세부구역 합계)", fontsize=9.0,
            fontweight="bold", color=INK, va="center", zorder=6)
    ax.text(x + w - 1.4, y + h - 2.2, "분석기간 2026-10-05 ~ 10-31",
            fontsize=6.8, color=SUBINK, ha="right", va="center", zorder=6)
    tot = [("아차", int(df.NearMiss.sum())), ("경보", int(df.Alerts.sum())),
           ("혼재슬롯", int(df.MixedSlot.sum())), ("미조치", int(df.Unclosed.sum()))]
    gap, cw = 0.8, (w - 2.8 - 0.8 * 3) / 4.0
    for i, (lab, val) in enumerate(tot):
        cx = x + 1.4 + i * (cw + gap)
        rrect(ax, cx, y + 1.0, cw, h - 4.4, "#EEF3F6", r=0.6, z=5)
        ax.text(cx + cw / 2, y + 1.0 + (h - 4.4) * 0.62, f"{val:,}", ha="center",
                va="center", fontsize=12.5, fontweight="bold", color=INK, zorder=6)
        ax.text(cx + cw / 2, y + 1.0 + (h - 4.4) * 0.22, lab, ha="center",
                va="center", fontsize=6.8, color=SUBINK, zorder=6)


def legend_card(ax, x, y, w, h):
    """색상 스케일 + 등급"""
    card(ax, x, y, w, h)
    ax.text(x + 1.3, y + h - 2.2, "위험지수 색상 (0~100)", fontsize=8.6,
            fontweight="bold", color=INK, va="center", zorder=6)
    # 수평 그라데이션 바
    bx, by, bw, bh = x + 1.3, y + h - 6.6, w - 2.6, 2.4
    n = 120
    for i in range(n):
        ax.add_patch(Rectangle((bx + bw * i / n, by), bw / n + 0.02, bh,
                               facecolor=CMAP(i / (n - 1)), edgecolor="none", zorder=5))
    ax.add_patch(Rectangle((bx, by), bw, bh, facecolor="none",
                           edgecolor="#8FA0AA", linewidth=0.7, zorder=6))
    for v in (0, 15, 30, 50, 70):
        xp = bx + bw * v / 70.0
        ax.text(min(max(xp, bx + 0.6), bx + bw - 0.9), by - 0.5,
                "70+" if v == 70 else str(v), ha="center", va="top",
                fontsize=6.2, color=SUBINK, zorder=6)
    grades = [("매우낮음", "< 15", 7), ("낮음", "15 – 30", 22),
              ("보통", "30 – 50", 40), ("높음", "50 – 70", 60),
              ("매우높음", "≥ 70", 70)]
    for i, (g, rng, rep) in enumerate(grades):
        gy = y + h - 10.2 - i * 1.95
        ax.add_patch(Rectangle((x + 1.4, gy - 0.6), 1.6, 1.2,
                               facecolor=CMAP(NORM(rep)), edgecolor="none", zorder=6))
        ax.text(x + 3.5, gy, g, fontsize=6.8, color=INK, va="center", zorder=6)
        ax.text(x + w - 1.4, gy, rng, fontsize=6.6, color=SUBINK, ha="right",
                va="center", zorder=6)


def defs_card(ax, x, y, w, h):
    """지표 정의 + 위험지수 산식"""
    card(ax, x, y, w, h)
    ax.text(x + 1.4, y + h - 2.2, "표기 항목 정의", fontsize=9.0,
            fontweight="bold", color=INK, va="center", zorder=6)
    defs = [
        ("위험지수", "혼재슬롯률 30% · 경보 25% · 미조치 20% · 아차 15% · 잔여위험도 10%"),
        ("", "→ 지표별 min-max 정규화(0~1) 가중합 ×100  (0~100)"),
        ("아차", "아차사고 보고 건수  (10_near_miss_reports)"),
        ("경보", "근접경보 발생 합계  (04_camera_object_log)"),
        ("혼재슬롯", "작업자·장비 동시 존재 1시간 슬롯 수  (구역당 230슬롯)"),
        ("미조치", "점검 Open·In Progress + 아차 Monitoring·In Progress"),
    ]
    for i, (k, v) in enumerate(defs):
        yy = y + h - 5.2 - i * 2.55
        if k:
            ax.text(x + 1.5, yy, k, fontsize=7.6, fontweight="bold", color=INK,
                    va="center", zorder=6)
        ax.text(x + 7.6, yy, v, fontsize=7.0, color=SUBINK, va="center", zorder=6)
    ax.text(x + 1.5, y + 1.5,
            "※ 원 배치도의 점선 원(작업반경) · 화살표(동선) 는 제거하고 구역별 수치만 표기",
            fontsize=6.4, color="#7E8E99", va="center", zorder=6)


# ---------------------------------------------------------------- 메인
def main():
    fig = plt.figure(figsize=(17.0, 11.6), dpi=200)
    fig.patch.set_facecolor(PAPER)
    ax = fig.add_axes([0.015, 0.035, 0.97, 0.885])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 93)
    ax.axis("off")

    # 현장 외곽
    rrect(ax, 3.2, 3.0, 90.0, 86.0, "#EFF3F5", "#0D1B24", 2.0, 1.4, 1.0, 1)

    # 북측 도시도로 · 외부 보호보행통로
    rrect(ax, 4.0, 84.6, 88.4, 3.6, "#3F7D4E", "none", 0, 0.5, 1.0, 2)
    ax.text(4.9, 86.4, "북측 도시도로 · 인접 상가", ha="left", va="center",
            fontsize=8.8, color="white", zorder=3)
    ax.text(91.5, 86.4, "외부 보호보행통로 (상시 개방 · 폐쇄 불가)", ha="right",
            va="center", fontsize=8.8, color="white", fontweight="bold", zorder=3)

    # 구역 박스
    for zone, box in LAYOUT.items():
        draw_zone(ax, zone, box)

    # 보조 카드 (빈 구획 활용)
    totals_card(ax, COLS[0], ROW_TOP[0], WIDE, ROW_TOP[1])
    legend_card(ax, COLS[4], ROW_1[0], CW, ROW_1[1])
    defs_card(ax, COLS[0], ROW_3[0], WIDE, ROW_3[1])

    # 제목
    fig.text(0.5, 0.968, "SCX NEXT 가상 도심지 복합시설  |  구역별 위험지수 배치도",
             ha="center", va="center", fontsize=21.5, fontweight="bold", color=INK)
    fig.text(0.5, 0.940,
             "구역명 · 위험지수 · 아차 · 경보 · 혼재슬롯 · 미조치   (분석기간 2026-10-05 ~ 10-31, 13개 세부구역)",
             ha="center", va="center", fontsize=10.4, color=SUBINK)

    # 각주
    fig.text(0.03, 0.012,
             "※ 교육·경연용 가상 데이터. 실제 현장·기업과 무관하며 협력사는 코드로 표기. "
             "원천기록 Excel과 분석용 CSV는 동일 데이터이므로 중복 합산하지 않음.",
             ha="left", va="center", fontsize=7.2, color=SUBINK)

    for ext in ("png", "svg"):
        fig.savefig(os.path.join(OUT, f"risk_map.{ext}"),
                    facecolor=fig.get_facecolor(), bbox_inches="tight",
                    pad_inches=0.22)
    print("saved:", os.path.join(OUT, "risk_map.png"))


if __name__ == "__main__":
    main()
