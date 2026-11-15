#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCX NEXT v1.4.3 - 구역별 위험지수 산출
입력: data/*.csv (분석용 테이블)
출력: out/zone_metrics.csv, out/metrics_detail.json

정의
- 아차(NearMiss)      : 10_near_miss_reports.csv 건수
- 경보(Alerts)        : 04_camera_object_log.csv Proximity_Alert_Count 합계
- 혼재슬롯(MixedSlot) : 04_camera_object_log.csv 1시간 슬롯 중 사람>0 AND 장비>0 슬롯 수
- 미조치(Unclosed)    : 09_inspection_action_log Status in (Open, In Progress)
                        + 10_near_miss_reports Action_Status in (Monitoring, In Progress)
- 위험지수(RiskIndex) : 5개 지표 min-max 정규화 후 가중합 (0~100)
"""
import json
import os

import pandas as pd

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
os.makedirs(OUT, exist_ok=True)

SUBZONES = ["A1", "A2", "A3", "A4", "B1", "B2", "B3",
            "C1", "C2", "C3", "D1", "D2", "D3"]

ZONE_NAME = {
    "A1": ("1동 코어·벽체", "지상골조 / 철근·형틀"),
    "A2": ("슬래브·타설 작업면", "지상골조 / 타설"),
    "A3": ("양중·호이스트 거점", "가설·양중"),
    "A4": ("펌프카 거치·레미콘 연결", "연속타설 / 차량"),
    "B1": ("메인게이트 차량·보행", "단일 게이트 / 물류"),
    "B2": ("일반자재 하역장", "물류 / 하역"),
    "B3": ("자재 적치장", "물류 / 적치"),
    "C1": ("포디움 외장", "외장 / 고소작업"),
    "C2": ("커튼월 적치·TC-02 양중", "외장·양중 중첩"),
    "C3": ("이동식크레인(MC-01)", "보강철골 양중"),
    "D1": ("지하램프(공용통로)", "토목→설비 통과"),
    "D2": ("지하2층(B2F) 설비", "기계설비"),
    "D3": ("지하3층(B3F) 토목·방수", "토목·방수"),
}


def load(name):
    return pd.read_csv(os.path.join(DATA, name), encoding="utf-8-sig")


def main():
    nm = load("10_near_miss_reports.csv")
    insp = load("09_inspection_action_log.csv")
    cam = load("04_camera_object_log.csv")
    ra = load("08_risk_assessment.csv")
    env = load("14_environment_complaints.csv")

    # --- 아차사고
    nm["Subzone"] = nm["Subzone"].str.strip().str.upper()
    nm_cnt = nm.groupby("Subzone").size()
    nm_unclosed = nm[nm["Action_Status"].astype(str).str.strip() != "Closed"] \
        .groupby("Subzone").size()

    # --- 카메라: 경보 / 혼재슬롯
    cam["Subzone"] = cam["Subzone"].str.strip().str.upper()
    cam["Equip"] = cam[["Forklift_Count", "Excavator_Count", "Truck_Count"]].sum(axis=1)
    cam["Mixed"] = ((cam["People_Count"] > 0) & (cam["Equip"] > 0)).astype(int)
    cam["Total"] = ((cam["People_Count"] > 0) | (cam["Equip"] > 0)).astype(int)
    cam_g = cam.groupby("Subzone").agg(
        slots=("Proximity_Alert_Count", "size"),
        alerts=("Proximity_Alert_Count", "sum"),
        mixed=("Mixed", "sum"),
        active=("Total", "sum"),
        peak_people=("People_Count", "max"),
    )
    cam_g["mixed_rate"] = cam_g["mixed"] / cam_g["slots"]

    # --- 점검: 미조치
    insp["Subzone"] = insp["Subzone"].str.strip().str.upper()
    insp_cnt = insp.groupby("Subzone").size()
    insp_open = insp[insp["Status"].astype(str).str.strip().isin(["Open", "In Progress"])] \
        .groupby("Subzone").size()
    insp_high_open = insp[(insp["Status"].astype(str).str.strip().isin(["Open", "In Progress"]))
                          & (insp["Severity"].astype(str).str.strip() == "High")] \
        .groupby("Subzone").size()

    # --- 잔여위험도
    ra["Subzone"] = ra["Subzone"].str.strip().str.upper()
    ra_g = ra.groupby("Subzone")["Residual_Risk_Score"].mean()

    # --- 민원
    env_by_zone = env.groupby("Zone").size()

    rows = []
    for z in SUBZONES:
        rows.append(dict(
            Subzone=z,
            Name=ZONE_NAME[z][0],
            Sub=ZONE_NAME[z][1],
            NearMiss=int(nm_cnt.get(z, 0)),
            NearMissUnclosed=int(nm_unclosed.get(z, 0)),
            Alerts=int(cam_g["alerts"].get(z, 0)),
            MixedSlot=int(cam_g["mixed"].get(z, 0)),
            Slots=int(cam_g["slots"].get(z, 230)),
            MixedRate=float(cam_g["mixed_rate"].get(z, 0.0)),
            Inspections=int(insp_cnt.get(z, 0)),
            InspOpen=int(insp_open.get(z, 0)),
            InspHighOpen=int(insp_high_open.get(z, 0)),
            Unclosed=int(insp_open.get(z, 0)) + int(nm_unclosed.get(z, 0)),
            Residual=float(ra_g.get(z, 0.0)),
            PeakPeople=int(cam_g["peak_people"].get(z, 0)),
            EnvIssue=int(env_by_zone.get(z[0], 0)),
        ))
    df = pd.DataFrame(rows)

    # ---- 위험지수 (0~100) : 5개 지표 min-max 정규화 가중합
    def norm(s):
        lo, hi = s.min(), s.max()
        if hi == lo:
            return pd.Series(0.0, index=s.index)
        return (s - lo) / (hi - lo)

    COMPONENTS = [
        ("혼재슬롯률", "MixedRate", 0.30),
        ("경보", "Alerts", 0.25),
        ("미조치", "Unclosed", 0.20),
        ("아차사고", "NearMiss", 0.15),
        ("잔여위험도", "Residual", 0.10),
    ]
    score = pd.Series(0.0, index=df.index)
    for label, col, w in COMPONENTS:
        df["n_" + col] = norm(df[col].astype(float))
        # 기여도(0~100 스케일). 합계 = 위험지수
        df["c_" + col] = (df["n_" + col] * w * 100).round(1)
        score += df["n_" + col] * w
    df["RiskIndex"] = (score * 100).round(1)

    # 주된 동인 = 기여도 1위 구성요소
    contrib_cols = ["c_" + col for _, col, _ in COMPONENTS]
    label_of = {("c_" + col): label for label, col, _ in COMPONENTS}
    df["TopDriver"] = df[contrib_cols].idxmax(axis=1).map(label_of)
    df["TopDriverShare"] = (
        df[contrib_cols].max(axis=1) / df["RiskIndex"].replace(0, pd.NA) * 100
    ).fillna(0).round(0)

    # 등급 (위험지수 기준)
    def grade(v):
        if v >= 70:
            return "매우높음"
        if v >= 50:
            return "높음"
        if v >= 30:
            return "보통"
        if v >= 15:
            return "낮음"
        return "매우낮음"

    df["Grade"] = df["RiskIndex"].apply(grade)
    df = df.sort_values("RiskIndex", ascending=False).reset_index(drop=True)

    cols = ["Subzone", "Name", "Sub", "RiskIndex", "Grade", "TopDriver",
            "TopDriverShare", "NearMiss",
            "NearMissUnclosed", "Alerts", "MixedSlot", "MixedRate",
            "Inspections", "InspOpen", "InspHighOpen", "Unclosed",
            "Residual", "PeakPeople", "Slots", "EnvIssue"]
    df[cols].to_csv(os.path.join(OUT, "zone_metrics.csv"),
                    index=False, encoding="utf-8-sig")

    detail = dict(
        weights={k: w for k, _, w in COMPONENTS},
        totals=dict(
            near_miss=int(df.NearMiss.sum()),
            alerts=int(df.Alerts.sum()),
            mixed=int(df.MixedSlot.sum()),
            unclosed=int(df.Unclosed.sum()),
            inspections=int(df.Inspections.sum()),
            slots=int(df.Slots.sum()),
        ),
        zones=df[cols].to_dict(orient="records"),
    )
    with open(os.path.join(OUT, "metrics_detail.json"), "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=2)

    pd.set_option("display.width", 250)
    print(df[["Subzone", "RiskIndex", "Grade", "NearMiss", "Alerts",
              "MixedSlot", "MixedRate", "Unclosed", "Residual"]]
          .to_string(index=False))
    print("\n총계:", detail["totals"])


if __name__ == "__main__":
    main()
