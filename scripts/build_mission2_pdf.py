#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""미션 2 시각자료 PDF - 2페이지 압축판 (A4 가로, 페이지당 2×2)
out/mission2/fig*.png → out/mission2/mission2_figures.pdf
 p.1  2-1 충돌구역·시간대 / 2-2 간섭구간   : fig1, fig7, fig5, fig4
 p.2  2-3 위험 집중 시각화 / 2-4 병목요인   : fig2, fig3, fig6 + 핵심 결론 박스
그림은 원본 해상도로 삽입되어 확대해서 볼 수 있다.
"""
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

INK, SUB, ACC = HexColor("#17232D"), HexColor("#55636E"), HexColor("#B71C1C")
LINE, PANEL, WHITE = HexColor("#D5DBE0"), HexColor("#F4F6F8"), HexColor("#FFFFFF")
W, H = landscape(A4)
M = 18          # 바깥 여백
GAP = 10        # 셀 간격
HEAD = 34       # 페이지 제목 영역
FOOT = 16       # 바닥글 영역
CAP = 24        # 셀 캡션(2줄) 높이
TAG_H = 15      # 셀 상단 태그줄 높이

PAGES = [
    dict(title="미션 2. 위험·간섭구역 분석 ①  충돌 위험 구역·시간대 / 간섭구간",
         cells=[
             ("2-1", "fig1_zone_hour_CEI_heatmap.png", "구역×시간대 충돌노출지수(CEI)",
              ["B2 10시(CEI 81)·15시(78), B1 10시(54) 최고위험. 근접경보 164건 중",
               "125건(76%)이 B1·B2, 그중 116건이 대형반입창(09~11·14~15시)."]),
             ("2-2", "fig7_risk_interference_map.png", "현장 위험·간섭 지도 (핫스팟 I1~I7)",
              ["I1 TC-01×TC-02 동시양중 8건·104분(C10, NM-0010 동시 발생),",
               "I3 레미콘×일반반입 7대, I4 B2 ≥3대 점유 6일, I6 강풍일 반입 11대."]),
             ("2-2", "fig5_interference_matrix.png", "장비·공종·자재반입 간섭 매트릭스",
              ["크레인 상호(I1·I2)·반입-하역-적치(I3·I4)·크레인-하역(I5)·작업자-장비",
               "간섭을 자원 쌍별로 정리. 셀 라벨 = 근거값(건·분)."]),
             ("2-2", "fig4_representative_day_timeline.png", "대표일 간섭 타임라인 (10/14·10/19·10/27)",
              ["10/14 동시양중 2회+NM-0010 / 10/19 레미콘 12대·일반반입 3대 B1 공유 /",
               "10/27 종일 풍속 초과로 양중 보류, 오후 반입 4대는 그대로 진입."]),
         ]),
    dict(title="미션 2. 위험·간섭구역 분석 ②  위험작업 집중 시간·구역 / 병목요인",
         cells=[
             ("2-3", "fig2_hourly_risk_profile.png", "시간대별 위험 집중 프로파일",
              ["근접경보 피크 10시(33)·15시(31). 완료양중 38%가 13시 착수,",
               "동시양중 8건 중 4건이 13시대. 출역 피크(06:30~07:30)와 반입은 분리."]),
             ("2-3", "fig3_dow_hour_heatmap.png", "요일×시간 고위험 활동 집중도 (일수 보정)",
              ["요일 차이는 작음(일평균 11.5~18.0). 위험은 요일보다 시간대(10·13·15시)에",
               "집중. 점수[가정] = 양중착수 + 근접경보 + 3×아차사고."]),
             ("2-4", "fig6_bottleneck.png", "공정대기·작업중단 병목",
              ["작업조 대기 226인시 중 강풍 51%. 크레인 대기율 43~52%(강풍일 제외 31~42%).",
               "1동 골조 연쇄 지연 → T005 슬래브 타설 예상완료 11/02(+3작업일)."]),
             ("SUM", None, "핵심 결론", None),
         ]),
]

SUMMARY = [
    ("2-1", "충돌 위험 구역·시간",
     "B2 하역장 10시·15시, B1 게이트 10시가 최고위험. B3·D3는 경보 0건이지만 상시 혼재(77%·61%), "
     "A4는 타설 3일 모두 아차사고 발생."),
    ("2-2", "간섭구간",
     "TC-01×TC-02 동시양중(C10) 8건·104분이 최우선. 레미콘 타설창과 일반반입의 B1 공유로 "
     "타설일 B1 경보 2.7배(4.0 vs 1.5건/일). 강풍 보류일에도 반입 계획은 조정되지 않음."),
    ("2-3", "위험 집중",
     "위험은 요일보다 시간대에 집중: 반입창(10시·15시)에 경보, 점심 직후 13시에 양중 착수 38%와 "
     "크레인 동시재개가 몰림."),
    ("2-4", "병목요인",
     "병목은 크레인 양중 용량. 강풍 보류·작업면 인계 지연·자재반입 확인 대기·양중 슬롯 경합이 "
     "A·C 구역 작업조를 대기시키고, 골조 연쇄 지연(T005 +3일)으로 이어짐."),
]


def wrap(text, font, size, width):
    """한글 포함 문자열을 글자 단위로 줄바꿈"""
    lines, cur = [], ""
    for ch in text:
        if pdfmetrics.stringWidth(cur + ch, font, size) > width:
            lines.append(cur)
            cur = ch.lstrip()
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def tag(c, x, y, code):
    c.setFillColor(ACC)
    c.roundRect(x, y - 3, 26, 13, 3, stroke=0, fill=1)
    c.setFillColor(WHITE); c.setFont("NGB", 8)
    c.drawCentredString(x + 13, y + 0.6, code)


def header(c, title, n):
    c.setFillColor(INK); c.rect(0, H - HEAD + 4, W, HEAD - 4, stroke=0, fill=1)
    c.setFillColor(WHITE); c.setFont("NGB", 13.5)
    c.drawString(M, H - 22, title)
    c.setFont("NG", 8.5)
    c.drawRightString(W - M, H - 21.5, "2026 SCX NEXT 청년 스마트건설 AI Lab")


def footer(c, n, total):
    c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(M, FOOT, W - M, FOOT)
    c.setFont("NG", 6.8); c.setFillColor(SUB)
    c.drawString(M, 6, "SCX NEXT v1.4.3 가상 데이터 · 분석기간 2026-10-05~10-31(23작업일) · 배치도는 축척 없는 개념도 · "
                       "[가정] = 분석자 설정값 · 그림은 원본 해상도로 삽입(확대 가능) · 안전 최종판단은 현장 관리자")
    c.drawRightString(W - M, 6, f"{n} / {total}")


def figure_cell(c, x, y, w, h, code, fn, title, cap):
    # 셀 테두리
    c.setStrokeColor(LINE); c.setLineWidth(0.6); c.setFillColor(WHITE)
    c.roundRect(x, y, w, h, 4, stroke=1, fill=1)
    # 태그줄
    ty = y + h - TAG_H + 2
    tag(c, x + 5, ty, code)
    c.setFillColor(INK); c.setFont("NGB", 9.6)
    c.drawString(x + 36, ty, title)
    # 그림
    img_top = y + h - TAG_H - 3
    img_bot = y + CAP + 2
    bw, bh = w - 8, img_top - img_bot
    path = os.path.join(FIG, fn)
    iw, ih = Image.open(path).size
    s = min(bw / iw, bh / ih)
    dw, dh = iw * s, ih * s
    c.drawImage(path, x + (w - dw) / 2, img_bot + (bh - dh) / 2, dw, dh, mask="auto")
    # 캡션
    c.setFillColor(PANEL); c.rect(x + 4, y + 3, w - 8, CAP - 3, stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(x + 4, y + 3, 2, CAP - 3, stroke=0, fill=1)
    c.setFillColor(INK); c.setFont("NG", 7.4)
    for k, line in enumerate(cap):
        c.drawString(x + 10, y + CAP - 10 - k * 9, line)


def summary_cell(c, x, y, w, h):
    c.setFillColor(PANEL); c.setStrokeColor(LINE); c.setLineWidth(0.6)
    c.roundRect(x, y, w, h, 4, stroke=1, fill=1)
    c.setFillColor(INK); c.setFont("NGX", 12)
    c.drawString(x + 12, y + h - 22, "핵심 결론")
    c.setStrokeColor(ACC); c.setLineWidth(1.2)
    c.line(x + 12, y + h - 28, x + 70, y + h - 28)
    yy = y + h - 46
    for code, head, body in SUMMARY:
        tag(c, x + 12, yy, code)
        c.setFillColor(INK); c.setFont("NGB", 9.6)
        c.drawString(x + 44, yy, head)
        yy -= 14
        c.setFont("NG", 8.4); c.setFillColor(HexColor("#2C3A44"))
        for line in wrap(body, "NG", 8.4, w - 56):
            c.drawString(x + 44, yy, line)
            yy -= 11.5
        yy -= 8
    c.setFont("NG", 7); c.setFillColor(SUB)
    c.drawString(x + 12, y + 9, "CEI = 충돌노출지수[가정 가중치]. 상세 근거: docs/mission2_report.md")


def main():
    c = canvas.Canvas(OUT, pagesize=landscape(A4))
    c.setTitle("미션 2. 위험·간섭구역 분석 - 시각자료(2p)")
    c.setAuthor("SCX NEXT AI Lab 참가팀")
    total = len(PAGES)
    cw = (W - 2 * M - GAP) / 2
    ch = (H - HEAD - FOOT - 6 - GAP) / 2
    for n, page in enumerate(PAGES, 1):
        header(c, page["title"], n)
        for i, (code, fn, title, cap) in enumerate(page["cells"]):
            col, row = i % 2, i // 2
            x = M + col * (cw + GAP)
            y = FOOT + 4 + (1 - row) * (ch + GAP)
            if code == "SUM":
                summary_cell(c, x, y, cw, ch)
            else:
                figure_cell(c, x, y, cw, ch, code, fn, title, cap)
        footer(c, n, total)
        c.showPage()
    c.save()
    print(OUT)


if __name__ == "__main__":
    main()
