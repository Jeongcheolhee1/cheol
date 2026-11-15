#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""미션 2 시각자료 PDF (out/mission2/fig*.png → out/mission2/mission2_figures.pdf)"""
import os

from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIG = os.path.join(BASE, "out", "mission2")
OUT = os.path.join(FIG, "mission2_figures.pdf")

FD = "/usr/share/fonts/truetype/nanum/"
pdfmetrics.registerFont(TTFont("NG", FD + "NanumGothic.ttf"))
pdfmetrics.registerFont(TTFont("NGB", FD + "NanumGothicBold.ttf"))
pdfmetrics.registerFont(TTFont("NGX", FD + "NanumGothicExtraBold.ttf"))

INK, SUB, ACC, LINE = HexColor("#17232D"), HexColor("#55636E"), HexColor("#B71C1C"), HexColor("#D5DBE0")
W, H = landscape(A4)
M = 28

SECTIONS = [
    ("2-1", "작업자·장비 충돌 가능성이 높은 구역과 시간대"),
    ("2-2", "장비·공종·자재 반입 간 간섭구간"),
    ("2-3", "위험작업이 집중되는 시간·구역 시각화"),
    ("2-4", "공정대기 또는 작업중단에 영향을 주는 병목요인"),
]

PAGES = [
    ("2-1", "fig1_zone_hour_CEI_heatmap.png", "구역×시간대 충돌노출지수(CEI) 히트맵",
     ["B2 하역장 10시(CEI 81)·15시(78), B1 메인게이트 10시(54)가 최고위험 구간.",
      "근접경보 164건 중 125건(76%)이 B1·B2, 그중 116건이 대형반입창(09~11시·14~15시)에 발생."]),
    ("2-2", "fig7_risk_interference_map.png", "현장 위험·간섭 지도 (충돌노출지수 + 간섭 핫스팟 I1~I7)",
     ["I1 TC-01×TC-02 동시양중 8건·104분(C10 중첩구역, NM-0010 동시 발생), I3 레미콘 타설창×일반반입 7대,",
      "I4 B2 동시점유 ≥3대 6일, I5 TC-01 양중×B2 하역 11건, I6 강풍 보류일 반입 11대, I7 D2 공종≥3 동시 8일."]),
    ("2-2", "fig5_interference_matrix.png", "장비·공종·자재반입 간섭 매트릭스",
     ["크레인 상호(I1·I2), 반입-하역-적치(I3·I4), 크레인-하역(I5), 작업자-장비 간섭을 자원 쌍별로 정리.",
      "셀 라벨이 근거값(건수·분), 색은 상대 규모."]),
    ("2-2", "fig4_representative_day_timeline.png", "대표일 간섭 타임라인 (10/14 · 10/19 · 10/27)",
     ["10/14 동시양중 2회 + NM-0010 / 10/19 레미콘 12대와 일반반입 3대가 B1 공유 /",
      "10/27 종일 풍속 초과로 양중 보류, 그러나 오후 반입 4대 동시 진입."]),
    ("2-3", "fig2_hourly_risk_profile.png", "시간대별 위험 집중 프로파일 (근접경보·아차사고 / 양중 / 차량 체류)",
     ["근접경보 피크 10시(33건)·15시(31건). 완료양중 99건 중 38건(38%)이 13시 착수,",
      "TC-01×TC-02 동시양중 8건 중 4건이 13시대. 출역 피크(06:30~07:30)와 대형반입은 시간상 분리."]),
    ("2-3", "fig3_dow_hour_heatmap.png", "요일×시간 고위험 활동 집중도 (일수 보정)",
     ["요일별 차이는 작음(일평균 11.5~18.0). 위험 집중은 요일보다 시간대(10시·13시·15시)에서 뚜렷함.",
      "점수[가정] = 양중착수 + 근접경보 + 3×아차사고."]),
    ("2-4", "fig6_bottleneck.png", "공정대기·작업중단 병목 (대기 원인 파레토 / 장비 대기율 / 공정편차 연쇄)",
     ["작업조 대기 226인시 중 강풍 양중보류 51%. 크레인 대기율 43~52%(강풍일 제외해도 31~42%).",
      "1동 골조 연쇄 지연 누적 → T005 슬래브 타설 예상완료 11/02(계획 대비 +3작업일)."]),
]
SEC_NAME = dict(SECTIONS)


def footer(c, n, total):
    c.setStrokeColor(LINE); c.setLineWidth(0.6)
    c.line(M, 22, W - M, 22)
    c.setFont("NG", 7.5); c.setFillColor(SUB)
    c.drawString(M, 11, "SCX NEXT v1.4.3 가상 데이터 · 분석기간 2026-10-05~10-31(23작업일) · "
                        "배치도는 축척 없는 개념도 · [가정] 표시는 분석자 설정값")
    c.drawRightString(W - M, 11, f"{n} / {total}")


def cover(c, total):
    c.setFillColor(HexColor("#17232D")); c.rect(0, H - 150, W, 150, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("NG", 12); c.drawString(M + 12, H - 52, "2026 SCX NEXT 청년 스마트건설 AI Lab")
    c.setFont("NGX", 28); c.drawString(M + 12, H - 95, "미션 2. 위험·간섭구역 분석")
    c.setFont("NG", 12); c.drawString(M + 12, H - 122, "시각자료 모음 (그림 7종)")
    y = H - 200
    for code, name in SECTIONS:
        figs = [(i, p) for i, p in enumerate(PAGES) if p[0] == code]
        c.setFillColor(ACC); c.roundRect(M + 12, y - 6, 40, 20, 4, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF")); c.setFont("NGB", 10.5); c.drawCentredString(M + 32, y, code)
        c.setFillColor(INK); c.setFont("NGB", 14); c.drawString(M + 64, y, name)
        yy = y - 22
        for i, p in figs:
            c.setFont("NG", 10.5); c.setFillColor(SUB)
            c.drawString(M + 80, yy, f"p.{i + 2}   {p[2]}")
            yy -= 17
        y = yy - 14
    footer(c, 1, total)


def fig_page(c, idx, page, total):
    code, fn, title, cap = page
    c.setFillColor(ACC); c.roundRect(M, H - M - 16, 40, 20, 4, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF")); c.setFont("NGB", 10.5); c.drawCentredString(M + 20, H - M - 10, code)
    c.setFillColor(SUB); c.setFont("NG", 10.5); c.drawString(M + 50, H - M - 10, SEC_NAME[code])
    c.setFillColor(INK); c.setFont("NGB", 15.5); c.drawString(M, H - M - 40, title)
    c.setStrokeColor(LINE); c.setLineWidth(0.8); c.line(M, H - M - 50, W - M, H - M - 50)

    cap_h = 46
    top = H - M - 58
    bottom = 28 + cap_h
    path = os.path.join(FIG, fn)
    iw, ih = Image.open(path).size
    bw, bh = W - 2 * M, top - bottom
    s = min(bw / iw, bh / ih)
    dw, dh = iw * s, ih * s
    c.drawImage(path, (W - dw) / 2, bottom + (bh - dh) / 2, dw, dh, preserveAspectRatio=True, mask="auto")

    c.setFillColor(HexColor("#F4F6F8")); c.roundRect(M, 28, W - 2 * M, cap_h - 6, 4, stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(M, 28, 3, cap_h - 6, stroke=0, fill=1)
    c.setFillColor(INK); c.setFont("NG", 9.6)
    for k, line in enumerate(cap):
        c.drawString(M + 12, 28 + cap_h - 22 - k * 14, ("▶ " if k == 0 else "   ") + line)
    footer(c, idx + 2, total)


def main():
    total = len(PAGES) + 1
    c = canvas.Canvas(OUT, pagesize=landscape(A4))
    c.setTitle("미션 2. 위험·간섭구역 분석 - 시각자료")
    c.setAuthor("SCX NEXT AI Lab 참가팀")
    cover(c, total); c.showPage()
    for i, p in enumerate(PAGES):
        fig_page(c, i, p, total); c.showPage()
    c.save()
    print(OUT)


if __name__ == "__main__":
    main()
