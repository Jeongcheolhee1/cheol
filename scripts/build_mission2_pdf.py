#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""미션 2 시각자료 PDF - A4 세로 2페이지
out/mission2/fig*.png → out/mission2/mission2_figures.pdf
 p.1  2-1 충돌 구역·시간대 / 2-2 간섭구간   : fig1(전폭), fig7(전폭), fig5 | fig4
 p.2  2-3 위험 집중 시각화 / 2-4 병목요인   : fig2(전폭), fig6(전폭), fig3 | 핵심 결론
그림은 원본 해상도로 삽입되어 확대해서 볼 수 있다.
"""
import os

from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
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
W, H = A4                 # 595 × 842 pt (세로)
M = 16                    # 바깥 여백
GAP = 7                   # 셀 간격
HEAD = 30                 # 페이지 제목 띠
FOOT = 15                 # 바닥글
CAP = 21                  # 셀 캡션(2줄)
TAG_H = 14                # 셀 상단 태그줄

# 행 = (높이 비중, [(폭 비중, 셀), ...]) / 셀 = (code, file, title, caption 2줄)
F1 = ("2-1", "fig1_zone_hour_CEI_heatmap.png", "구역×시간대 충돌노출지수(CEI)",
      ["B2 10시(CEI 81)·15시(78), B1 10시(54) 최고위험. 근접경보 164건 중 125건(76%)이 B1·B2,",
       "그중 116건이 대형반입창(09~11·14~15시). B3·D3는 경보 0건이나 상시 혼재(77%·61%)."])
F7 = ("2-2", "fig7_risk_interference_map.png", "현장 위험·간섭 지도 (핫스팟 I1~I7)",
      ["I1 TC-01×TC-02 동시양중 8건·104분(C10, NM-0010 동시 발생), I3 레미콘×일반반입 7대,",
       "I4 B2 ≥3대 동시점유 6일, I5 TC-01 양중×B2 하역 11건, I6 강풍일 반입 11대, I7 D2 공종≥3 8일."])
F5 = ("2-2", "fig5_interference_matrix.png", "간섭 매트릭스",
      ["크레인 상호·반입-하역-적치·크레인-하역·작업자-장비",
       "간섭을 자원 쌍별 정리. 셀 라벨 = 근거값(건·분)."])
F4 = ("2-2", "fig4_representative_day_timeline.png", "대표일 간섭 타임라인",
      ["10/14 동시양중+NM-0010 / 10/19 레미콘·일반반입 B1 공유 /",
       "10/27 종일 풍속 초과로 양중 보류, 반입 4대는 진입."])
F2 = ("2-3", "fig2_hourly_risk_profile.png", "시간대별 위험 집중 프로파일",
      ["근접경보 피크 10시(33)·15시(31). 완료양중 99건 중 38%가 13시 착수, 동시양중 8건 중 4건이",
       "13시대. 출역 피크(06:30~07:30)와 대형반입(09시~)은 시간상 분리."])
F6 = ("2-4", "fig6_bottleneck.png", "공정대기·작업중단 병목",
      ["작업조 대기 226인시 중 강풍 양중보류 51%. 크레인 대기율 43~52%(강풍일 제외해도 31~42%).",
       "1동 골조 SS 연쇄 지연 누적 → T005 슬래브 타설 예상완료 11/02(계획 대비 +3작업일)."])
F3 = ("2-3", "fig3_dow_hour_heatmap.png", "요일×시간 고위험 활동 집중도",
      ["요일 차이 작음(일평균 11.5~18.0) → 위험은 시간대에 집중.",
       "점수[가정] = 양중착수 + 근접경보 + 3×아차사고."])
SUM = ("SUM", None, "핵심 결론", None)

PAGES = [
    dict(title="미션 2. 위험·간섭구역 분석 ①  충돌 위험 구역·시간대 / 간섭구간",
         rows=[(1.00, [(1.0, F1)]),
               (0.98, [(1.0, F7)]),
               (0.78, [(0.5, F5), (0.5, F4)])]),
    dict(title="미션 2. 위험·간섭구역 분석 ②  위험작업 집중 / 병목요인",
         rows=[(1.06, [(1.0, F2)]),
               (0.98, [(1.0, F6)]),
               (0.62, [(0.5, F3), (0.5, SUM)])]),
]

SUMMARY = [
    ("2-1", "충돌 위험 구역·시간",
     "B2 하역장 10·15시, B1 게이트 10시 최고위험. A4는 타설 3일 모두 아차사고."),
    ("2-2", "간섭구간",
     "TC-01×TC-02 동시양중(C10) 최우선. 타설일 B1 경보 2.7배. 강풍일 반입 미조정."),
    ("2-3", "위험 집중",
     "요일보다 시간대: 반입창 10·15시 경보, 13시 양중 착수 38%·크레인 동시재개."),
    ("2-4", "병목요인",
     "크레인 양중 용량. 강풍·인계 지연·반입 확인·슬롯 경합 → 골조 연쇄 지연(T005 +3일)."),
]


def wrap(text, font, size, width):
    """글자 단위 줄바꿈(한글 대응)"""
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


def fit(text, font, size, width):
    """한 줄에 들어가도록 글자 크기를 줄인다"""
    while size > 5.8 and pdfmetrics.stringWidth(text, font, size) > width:
        size -= 0.2
    return size


def tag(c, x, y, code):
    c.setFillColor(ACC)
    c.roundRect(x, y - 3, 24, 12, 3, stroke=0, fill=1)
    c.setFillColor(WHITE); c.setFont("NGB", 7.6)
    c.drawCentredString(x + 12, y + 0.4, code)


def header(c, title):
    c.setFillColor(INK); c.rect(0, H - HEAD, W, HEAD, stroke=0, fill=1)
    c.setFillColor(WHITE); c.setFont("NGB", 12)
    c.drawString(M, H - 19.5, title)
    c.setFont("NG", 7.2)
    c.drawRightString(W - M, H - 19, "2026 SCX NEXT AI Lab")


def footer(c, n, total):
    c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(M, FOOT, W - M, FOOT)
    c.setFont("NG", 6); c.setFillColor(SUB)
    c.drawString(M, 6, "SCX NEXT v1.4.3 가상 데이터 · 분석기간 2026-10-05~10-31(23작업일) · 배치도는 축척 없는 개념도 · "
                       "[가정] = 분석자 설정값 · 그림은 원본 해상도(확대 가능) · 안전 최종판단은 현장 관리자")
    c.drawRightString(W - M, 6, f"{n} / {total}")


def figure_cell(c, x, y, w, h, code, fn, title, cap):
    c.setStrokeColor(LINE); c.setLineWidth(0.6); c.setFillColor(WHITE)
    c.roundRect(x, y, w, h, 4, stroke=1, fill=1)
    ty = y + h - TAG_H + 3
    tag(c, x + 5, ty, code)
    c.setFillColor(INK); c.setFont("NGB", 9)
    c.drawString(x + 34, ty, title)
    img_top = y + h - TAG_H - 2
    img_bot = y + CAP + 2
    bw, bh = w - 8, img_top - img_bot
    path = os.path.join(FIG, fn)
    iw, ih = Image.open(path).size
    s = min(bw / iw, bh / ih)
    dw, dh = iw * s, ih * s
    c.drawImage(path, x + (w - dw) / 2, img_bot + (bh - dh) / 2, dw, dh, mask="auto")
    c.setFillColor(PANEL); c.rect(x + 4, y + 3, w - 8, CAP - 3, stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(x + 4, y + 3, 2, CAP - 3, stroke=0, fill=1)
    c.setFillColor(INK)
    size = min(fit(line, "NG", 7.0, w - 18) for line in cap)
    c.setFont("NG", size)
    for k, line in enumerate(cap):
        c.drawString(x + 10, y + CAP - 9.5 - k * 8.5, line)


def summary_cell(c, x, y, w, h):
    c.setFillColor(PANEL); c.setStrokeColor(LINE); c.setLineWidth(0.6)
    c.roundRect(x, y, w, h, 4, stroke=1, fill=1)
    c.setFillColor(INK); c.setFont("NGX", 10.5)
    c.drawString(x + 10, y + h - 18, "핵심 결론")
    c.setStrokeColor(ACC); c.setLineWidth(1.1)
    c.line(x + 10, y + h - 23, x + 60, y + h - 23)
    # 남은 높이에 맞춰 본문 크기 결정
    for fs in [8.0, 7.6, 7.2, 6.8, 6.4]:
        lh = fs * 1.32
        need = sum(11 + len(wrap(b, "NG", fs, w - 46)) * lh + 5 for _, _, b in SUMMARY)
        if need <= h - 34 - 12:
            break
    yy = y + h - 38
    for code, head, body in SUMMARY:
        tag(c, x + 10, yy, code)
        c.setFillColor(INK); c.setFont("NGB", 8.6)
        c.drawString(x + 40, yy, head)
        yy -= 11
        c.setFont("NG", fs); c.setFillColor(HexColor("#2C3A44"))
        for line in wrap(body, "NG", fs, w - 46):
            c.drawString(x + 40, yy, line)
            yy -= lh
        yy -= 5
    c.setFont("NG", 6.2); c.setFillColor(SUB)
    c.drawString(x + 10, y + 7, "CEI = 충돌노출지수[가정 가중치]. 상세: docs/mission2_report.md")


def main():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle("미션 2. 위험·간섭구역 분석 - 시각자료(A4 세로 2p)")
    c.setAuthor("SCX NEXT AI Lab 참가팀")
    total = len(PAGES)
    top = H - HEAD - 6
    bottom = FOOT + 4
    usable_w = W - 2 * M
    for n, page in enumerate(PAGES, 1):
        header(c, page["title"])
        rows = page["rows"]
        avail = top - bottom - GAP * (len(rows) - 1)
        wsum = sum(r[0] for r in rows)
        y = top
        for weight, cells in rows:
            rh = avail * weight / wsum
            y -= rh
            x = M
            cw_avail = usable_w - GAP * (len(cells) - 1)
            for frac, cell in cells:
                cw = cw_avail * frac
                code, fn, title, cap = cell
                if code == "SUM":
                    summary_cell(c, x, y, cw, rh)
                else:
                    figure_cell(c, x, y, cw, rh, code, fn, title, cap)
                x += cw + GAP
            y -= GAP
        footer(c, n, total)
        c.showPage()
    c.save()
    print(OUT)


if __name__ == "__main__":
    main()
