#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCX NEXT v1.4.3 - 미션 2. 위험·간섭구역 분석
입력 : data/*.csv (분석용 CSV, 통합 Excel과 중복 합산하지 않음)
출력 : out/mission2/*.png, out/mission2/*.csv, out/mission2/summary.json

분석 구성
 (1) 작업자·장비 충돌 가능성 : 구역×시간대 충돌노출지수(CEI)
 (2) 장비·공종·자재 반입 간섭 : 크레인 상호, 레미콘×일반반입, 하역 동시점유, 양중×하역 등
 (3) 위험작업 집중 시간·구역 : 시간대 프로파일, 요일×시간 히트맵, 대표일 타임라인
 (4) 공정대기·작업중단 병목 : 대기 원인 파레토, 크레인 대기, 공정편차 연쇄
※ 가중치·임계값 등 분석자가 설정한 값은 모두 [가정]으로 표기한다.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.lines import Line2D

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "out", "mission2")
os.makedirs(OUT, exist_ok=True)

plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

SUBZONES = ["A1", "A2", "A3", "A4", "B1", "B2", "B3",
            "C1", "C2", "C3", "D1", "D2", "D3"]
ZNAME = {"A1": "코어·벽체", "A2": "슬래브·타설", "A3": "양중·호이스트",
         "A4": "펌프카·레미콘", "B1": "메인게이트", "B2": "하역장",
         "B3": "적치장", "C1": "포디움 외장", "C2": "커튼월·TC-02",
         "C3": "이동식크레인", "D1": "지하램프", "D2": "B2F 설비",
         "D3": "B3F 토목·방수"}
HOURS = list(range(7, 17))
CMAP = LinearSegmentedColormap.from_list(
    "risk", ["#F4F7F5", "#CFE3C8", "#F2D46B", "#EE9A3A", "#C8322A"])
INK = "#17232D"
WIND_FACTOR = {"TC-01": 1.35, "TC-02": 1.25, "MC-01": 1.15}   # 안내서 v1.4.3 (교육용 가정)
WIND_LIMIT = {"TC-01": 12.0, "TC-02": 12.0, "MC-01": 10.0}


def load(name):
    return pd.read_csv(os.path.join(DATA, name), encoding="utf-8-sig")


def norm(s):
    s = s.astype(float)
    lo, hi = s.min(), s.max()
    return (s - lo) / (hi - lo) if hi > lo else s * 0


def overlap_min(s1, e1, s2, e2):
    s, e = max(s1, s2), min(e1, e2)
    return (e - s).total_seconds() / 60 if e > s else 0.0


# ----------------------------------------------------------------- load
cam = load("04_camera_object_log.csv")
dl = load("05_delivery_log.csv")
lf = load("06_lifting_log.csv")
eq = load("07_equipment_log.csv")
ra = load("08_risk_assessment.csv")
insp = load("09_inspection_action_log.csv")
nm = load("10_near_miss_reports.csv")
ptw = load("11_work_permits.csv")
tbm = load("12_tbm_log.csv")
wx = load("13_weather_hourly.csv")
wk = load("02_daily_work_plan.csv")
ms = load("01_master_schedule.csv")
gate = load("03_gate_attendance.csv")
env = load("14_environment_complaints.csv")

for c in ["Reserved_Start", "Reserved_End", "Arrival_Time", "Gate_In_Time",
          "Unload_Start_Time", "Unload_End_Time", "Gate_Out_Time"]:
    dl[c] = pd.to_datetime(dl[c])
for c in ["Planned_Start", "Planned_End", "Actual_Start", "Actual_End"]:
    lf[c] = pd.to_datetime(lf[c])
nm["t"] = pd.to_datetime(nm["Occurrence_DateTime"])
nm["Date"] = nm["t"].dt.strftime("%Y-%m-%d")
nm["h"] = nm["t"].dt.hour
cam["h"] = cam["Slot_Start"].str[11:13].astype(int)
cam["Subzone"] = cam["Subzone"].str.strip().str.upper()

lifts = lf[lf["Status"] == "완료"].copy()          # 보류·취소는 실적 제외 (안내서)
gen = dl[dl["Delivery_Size_Class"] == "대형"].copy()
rmc = dl[dl["Delivery_Size_Class"] == "연속타설"].copy()
POUR_DAYS = sorted(rmc["Date"].unique())
DAYS = sorted(cam["Date"].unique())
N_DAYS = len(DAYS)

summary = {"analysis_days": N_DAYS, "pour_days": POUR_DAYS}

# ================================================================ (1) CEI
# 장비 = 지게차 + 굴착기 + 트럭 + 크레인가동(0/1)  → 사람×장비 동시노출
cam["EQ"] = (cam["Forklift_Count"] + cam["Excavator_Count"]
             + cam["Truck_Count"] + cam["Crane_Active"])
cam["expo"] = cam["People_Count"] * cam["EQ"]
cam["mixed"] = ((cam["People_Count"] > 0) & (cam["EQ"] > 0)).astype(int)

zh = cam.groupby(["Subzone", "h"]).agg(
    slots=("expo", "size"), expo=("expo", "mean"), mixed=("mixed", "mean"),
    alerts=("Proximity_Alert_Count", "sum"), people=("People_Count", "mean"),
    equip=("EQ", "mean")).reset_index()
nm_zh = nm.groupby(["Subzone", "h"]).size().rename("nm").reset_index()
zh = zh.merge(nm_zh, on=["Subzone", "h"], how="left").fillna({"nm": 0})
zh["alert_rate"] = zh["alerts"] / zh["slots"]
# [가정] CEI 가중치: 노출강도 35 / 근접경보율 35 / 혼재비율 15 / 아차사고 15
W_CEI = {"노출강도(사람×장비)": 0.35, "근접경보율": 0.35, "혼재비율": 0.15, "아차사고": 0.15}
zh["CEI"] = 100 * (0.35 * norm(zh["expo"]) + 0.35 * norm(zh["alert_rate"])
                   + 0.15 * zh["mixed"] + 0.15 * norm(zh["nm"]))
zh["CEI"] = zh["CEI"].round(1)
zh.to_csv(os.path.join(OUT, "t1_zone_hour_CEI.csv"), index=False, encoding="utf-8-sig")
cei = zh.pivot(index="Subzone", columns="h", values="CEI").reindex(SUBZONES)
alert_pv = zh.pivot(index="Subzone", columns="h", values="alerts").reindex(SUBZONES)

zone_tot = cam.groupby("Subzone").agg(
    alerts=("Proximity_Alert_Count", "sum"), mixed_rate=("mixed", "mean"),
    expo=("expo", "mean"), peak_people=("People_Count", "max")).reindex(SUBZONES)
zone_tot["near_miss"] = nm.groupby("Subzone").size().reindex(SUBZONES).fillna(0).astype(int)
zone_tot["CEI_mean"] = cei.mean(axis=1).round(1)
zone_tot["CEI_peak"] = cei.max(axis=1)
zone_tot["peak_hour"] = cei.idxmax(axis=1)
zone_tot = zone_tot.sort_values("CEI_mean", ascending=False)
zone_tot.round(3).to_csv(os.path.join(OUT, "t2_zone_collision_rank.csv"), encoding="utf-8-sig")
top_cells = zh.sort_values("CEI", ascending=False).head(12)
summary["CEI_weights_assumption"] = W_CEI
summary["CEI_top_cells"] = top_cells[["Subzone", "h", "CEI", "expo", "alerts", "mixed"]].round(2).to_dict("records")
summary["zone_rank"] = zone_tot.reset_index()[["Subzone", "CEI_mean", "CEI_peak", "peak_hour",
                                               "alerts", "mixed_rate", "near_miss"]].round(3).to_dict("records")

# D1 단계 전·후 (C07)
d1 = cam[cam["Subzone"] == "D1"].copy()
d1["phase"] = np.where(d1["Date"] < "2026-10-13", "①10/05~10/12 토목우선", "②10/13~ 장비·설비 통과")
d1_phase = d1.groupby("phase").agg(days=("Date", "nunique"), people=("People_Count", "mean"),
                                   excavator=("Excavator_Count", "mean"),
                                   forklift=("Forklift_Count", "mean"),
                                   alerts=("Proximity_Alert_Count", "sum"))
d1_phase["alerts_per_day"] = d1_phase["alerts"] / d1_phase["days"]
summary["D1_phase"] = d1_phase.round(2).reset_index().to_dict("records")

# B1 : 타설일 vs 비타설일
b1 = cam[cam["Subzone"] == "B1"]
b1_day = b1.groupby("Date").agg(alerts=("Proximity_Alert_Count", "sum"), trk=("Truck_Count", "max"))
summary["B1_alerts_per_day_pour"] = round(b1_day.loc[b1_day.index.isin(POUR_DAYS), "alerts"].mean(), 2)
summary["B1_alerts_per_day_nonpour"] = round(b1_day.loc[~b1_day.index.isin(POUR_DAYS), "alerts"].mean(), 2)

# ============================================================ (2) 간섭 분석
inter = []          # 개별 간섭 이벤트

# I1. TC-01 × TC-02 동시 양중 (C10 : B3·C1 중첩구역 동시선회 금지)
def crane_pairs(a_id, b_id, code, label):
    A = lifts[lifts["Equipment_ID"] == a_id]
    B = lifts[lifts["Equipment_ID"] == b_id]
    for _, a in A.iterrows():
        for _, b in B[B["Date"] == a["Date"]].iterrows():
            m = overlap_min(a["Actual_Start"], a["Actual_End"], b["Actual_Start"], b["Actual_End"])
            if m > 0:
                s = max(a["Actual_Start"], b["Actual_Start"])
                nm_hit = nm[(nm["Related_Event_ID"].isin([a["Lift_ID"], b["Lift_ID"]]))
                            | ((nm["t"] >= s) & (nm["t"] <= min(a["Actual_End"], b["Actual_End"]))
                               & nm["Equipment_ID"].isin([a_id, b_id]))]
                inter.append(dict(code=code, type=label, Date=a["Date"], start=s.strftime("%H:%M"),
                                  minutes=m, A=f'{a["Lift_ID"]}({a_id} {a["Source_Subzone"]}→{a["Target_Subzone"]})',
                                  B=f'{b["Lift_ID"]}({b_id} {b["Source_Subzone"]}→{b["Target_Subzone"]})',
                                  zones=f'{a["Target_Subzone"]}/{b["Target_Subzone"]}',
                                  near_miss=",".join(nm_hit["NearMiss_ID"]) if len(nm_hit) else ""))

crane_pairs("TC-01", "TC-02", "I1", "TC-01×TC-02 동시양중(C10)")
crane_pairs("MC-01", "TC-02", "I2", "MC-01×TC-02 동시양중(C3↔C1 인접)")

# I3. 레미콘 연속타설 창 × 일반 대형반입 (B1 단일게이트 공유, C02/C09)
pour_win = rmc.groupby("Date").agg(s=("Gate_In_Time", "min"), e=("Gate_Out_Time", "max"))
for dt, w in pour_win.iterrows():
    g = gen[(gen["Date"] == dt) & (gen["Gate_In_Time"] < w["e"]) & (gen["Gate_Out_Time"] > w["s"])]
    for _, r in g.iterrows():
        inter.append(dict(code="I3", type="레미콘 타설창×일반반입(B1 공유)", Date=dt,
                          start=r["Gate_In_Time"].strftime("%H:%M"),
                          minutes=overlap_min(r["Gate_In_Time"], r["Gate_Out_Time"], w["s"], w["e"]),
                          A=f'타설창 {w["s"]:%H:%M}~{w["e"]:%H:%M}',
                          B=f'{r["Delivery_ID"]}({r["Material_Category"]})', zones="B1/B2/A4",
                          near_miss=""))
rm_gap = rmc.sort_values("Gate_In_Time").groupby("Date")["Gate_In_Time"].diff().dt.total_seconds() / 60
summary["rmc_gap"] = dict(mean=round(rm_gap.mean(), 1), min=float(rm_gap.min()), max=float(rm_gap.max()),
                          below12=int((rm_gap < 12).sum()), above15=int((rm_gap > 15).sum()),
                          n=int(rm_gap.notna().sum()))

# I4. B2 하역장 동시 점유 ≥3대 (C08)
b2_conc = []
for dt, g in gen.groupby("Date"):
    t = pd.date_range(f"{dt} 08:00", f"{dt} 17:00", freq="1min")
    cnt = np.zeros(len(t))
    for _, r in g.iterrows():
        cnt += ((t >= r["Gate_In_Time"]) & (t < r["Gate_Out_Time"]))
    b2_conc.append(dict(Date=dt, trucks=len(g), max_conc=int(cnt.max()),
                        min_ge2=int((cnt >= 2).sum()), min_ge3=int((cnt >= 3).sum())))
    if cnt.max() >= 3:
        s = t[np.argmax(cnt >= 3)]
        inter.append(dict(code="I4", type="B2 하역 동시점유 ≥3대(C08)", Date=dt, start=s.strftime("%H:%M"),
                          minutes=float((cnt >= 3).sum()), A=f"동시 최대 {int(cnt.max())}대",
                          B=f"당일 {len(g)}대", zones="B2/B3", near_miss=""))
b2_conc = pd.DataFrame(b2_conc)
b2_conc.to_csv(os.path.join(OUT, "t4_B2_concurrency_daily.csv"), index=False, encoding="utf-8-sig")

# I5. TC-01 양중 × B2 트럭 체류 (C04 : TC-01 반경이 B1·B2 영향)
for _, a in lifts[lifts["Equipment_ID"] == "TC-01"].iterrows():
    g = gen[(gen["Date"] == a["Date"]) & (gen["Gate_In_Time"] < a["Actual_End"])
            & (gen["Gate_Out_Time"] > a["Actual_Start"])]
    for _, r in g.iterrows():
        inter.append(dict(code="I5", type="TC-01 양중×B2 하역 동시(C04)", Date=a["Date"],
                          start=max(a["Actual_Start"], r["Gate_In_Time"]).strftime("%H:%M"),
                          minutes=overlap_min(a["Actual_Start"], a["Actual_End"], r["Gate_In_Time"], r["Gate_Out_Time"]),
                          A=f'{a["Lift_ID"]}({a["Source_Subzone"]}→{a["Target_Subzone"]})',
                          B=f'{r["Delivery_ID"]}({r["Material_Category"]})', zones="A3/B2", near_miss=""))

# I6. 강풍 보류일 반입 미조정 (풍속 보류 ↔ 반입계획 미연동)
wind_days = sorted(lf.loc[lf["Hold_Reason"] == "풍속 기준 초과", "Date"].unique())
for dt in wind_days:
    g = gen[gen["Date"] == dt]
    held = lf[(lf["Date"] == dt) & (lf["Status"] != "완료")]
    inter.append(dict(code="I6", type="강풍 양중보류일 반입 그대로 진행", Date=dt, start="-",
                      minutes=0.0, A=f"양중 보류·취소 {len(held)}건",
                      B=f"대형반입 {len(g)}대 ({','.join(g['Material_Category'])})", zones="B2/B3/A3/C2",
                      near_miss=""))

# I7. D2 동시 공종 (설비·전기·화기, SL-03, FL-02)
d2 = wk[wk["Subzone"] == "D2"].groupby("Date").agg(n_tasks=("Task_ID", "nunique"),
                                                    workers=("Actual_Workers", "sum"),
                                                    tasks=("Task_ID", lambda x: ",".join(sorted(x))))
d2_multi = d2[d2["n_tasks"] >= 3]
for dt, r in d2_multi.iterrows():
    inter.append(dict(code="I7", type="D2 3개 이상 공종 동시작업", Date=dt, start="-", minutes=0.0,
                      A=r["tasks"], B=f'{int(r["workers"])}명', zones="D2",
                      near_miss=",".join(nm[(nm["Date"] == dt) & (nm["Subzone"] == "D2")]["NearMiss_ID"])))

inter = pd.DataFrame(inter)
inter.to_csv(os.path.join(OUT, "t3_interference_events.csv"), index=False, encoding="utf-8-sig")
inter_sum = inter.groupby(["code", "type"]).agg(events=("Date", "size"), days=("Date", "nunique"),
                                                minutes=("minutes", "sum")).reset_index()
inter_sum["near_miss_linked"] = inter.groupby("code")["near_miss"].apply(
    lambda s: ",".join(sorted({x for v in s for x in v.split(",") if x}))).values
inter_sum.to_csv(os.path.join(OUT, "t3_interference_summary.csv"), index=False, encoding="utf-8-sig")
summary["interference"] = inter_sum.to_dict("records")
summary["B2_conc_days_ge3"] = b2_conc.loc[b2_conc["max_conc"] >= 3, "Date"].tolist()
summary["wind_days"] = wind_days

# 작업허가 공백 (허가 대상 작업유형 대비)
pe = ptw.assign(scope=ptw["Scope_Task_IDs"].str.split(",")).explode("scope")
pe["scope"] = pe["scope"].str.strip()
cov = set(zip(pe["Date"], pe["scope"]))
ex_days = eq[eq["Equipment_ID"].isin(["EX-01", "EX-02"])].groupby(["Date", "Task_ID"]).size().reset_index()
ex_gap = [(d, t) for d, t in zip(ex_days["Date"], ex_days["Task_ID"]) if (d, t) not in cov]
sl3 = eq[eq["Equipment_ID"] == "SL-03"]
sl3_gap = [(d, t) for d, t in zip(sl3["Date"], sl3["Task_ID"]) if (d, t) not in cov]
summary["permit_gap"] = {"굴착기 가동일 중 굴착허가 없음": len(ex_gap), "굴착 공백 예": ex_gap[:6],
                         "SL-03(지하 고소작업대) 가동일 중 고소허가 없음": len(sl3_gap),
                         "SL-03 가동일": int(len(sl3))}

# ===================================================== (3) 시간대 프로파일
prof = pd.DataFrame(index=HOURS)
prof["alerts"] = cam.groupby("h")["Proximity_Alert_Count"].sum()
for z in ["B1", "B2", "D1", "A4", "C2"]:
    prof[f"alerts_{z}"] = cam[cam["Subzone"] == z].groupby("h")["Proximity_Alert_Count"].sum()
prof = prof.fillna(0)


def minutes_by_hour(df, s_col, e_col, day_norm=True):
    out = pd.Series(0.0, index=HOURS)
    for _, r in df.iterrows():
        for h in HOURS:
            hs = r[s_col].normalize() + pd.Timedelta(hours=h)
            out[h] += overlap_min(r[s_col], r[e_col], hs, hs + pd.Timedelta(hours=1))
    return out / (N_DAYS if day_norm else 1)


for cid in ["TC-01", "TC-02", "MC-01"]:
    prof[f"lift_{cid}"] = minutes_by_hour(lifts[lifts["Equipment_ID"] == cid], "Actual_Start", "Actual_End")
prof["b2_truck_min"] = minutes_by_hour(gen, "Gate_In_Time", "Gate_Out_Time")
prof["rmc_truck_min"] = minutes_by_hour(rmc, "Gate_In_Time", "Gate_Out_Time", day_norm=False) / len(POUR_DAYS)
prof["lift_starts"] = lifts.groupby(lifts["Actual_Start"].dt.hour).size().reindex(HOURS).fillna(0)
prof["near_miss"] = nm.groupby("h").size().reindex(HOURS).fillna(0)
prof["people_site"] = cam.groupby(["Date", "h"])["People_Count"].sum().groupby("h").mean()
prof.round(2).to_csv(os.path.join(OUT, "t5_hourly_profile.csv"), encoding="utf-8-sig")
summary["lift_starts_by_hour"] = prof["lift_starts"].astype(int).to_dict()
summary["lift_13h_share"] = round(prof.loc[13, "lift_starts"] / prof["lift_starts"].sum(), 3)

gate_tot = gate.groupby(["Date", "Time_Slot"])[["Entry_Count", "Exit_Count"]].sum().groupby("Time_Slot").mean()
summary["gate_by_slot"] = gate_tot.round(1).to_dict("index")

# 요일 × 시간 고위험 활동 (양중 착수 + 근접경보 + 아차사고 + 화기허가작업 시작 제외)
DOW = ["월", "화", "수", "목", "금", "토"]
lifts["dow"] = lifts["Actual_Start"].dt.dayofweek
lifts["h"] = lifts["Actual_Start"].dt.hour
cam["dow"] = pd.to_datetime(cam["Date"]).dt.dayofweek
nm["dow"] = nm["t"].dt.dayofweek
days_per_dow = pd.Series(pd.to_datetime(DAYS).dayofweek).value_counts().reindex(range(6))
act = (lifts.groupby(["dow", "h"]).size().rename("lift")
       .to_frame()
       .join(cam.groupby(["dow", "h"])["Proximity_Alert_Count"].sum().rename("alert"), how="outer")
       .join(nm.groupby(["dow", "h"]).size().rename("nm"), how="outer").fillna(0))
act["score"] = act["lift"] + act["alert"] + 3 * act["nm"]     # [가정] 아차사고 가중 3
act_pv = act["score"].unstack().reindex(index=range(6), columns=HOURS).fillna(0)
act_pv = act_pv.div(days_per_dow.values, axis=0)                # 요일별 일수 보정
summary["dow_days"] = dict(zip(DOW, days_per_dow.tolist()))
summary["dow_score_per_day"] = dict(zip(DOW, act_pv.sum(axis=1).round(2).tolist()))

# 위험성평가 고위험(초기 ≥15) 작업의 시간대 분포 → 작업일보 기준
hi_tasks = set(ra.loc[ra["Initial_Risk_Score"] >= 15, "Task_ID"])
wk_hi = wk[wk["Task_ID"].isin(hi_tasks)]
summary["high_risk_task_rows_by_dow"] = wk_hi.groupby(pd.to_datetime(wk_hi["Date"]).dt.dayofweek).size().rename(
    index=dict(enumerate(DOW))).to_dict()

# ===================================================== (4) 병목 분석
wk["wait_wh"] = wk["Crew_Waiting_Minutes"] * wk["Actual_Workers"] / 60
CAUSE_MAP = {"강풍 양중 보류로 대기": "강풍 양중보류", "강풍 양중 보류": "강풍 양중보류",
             "강풍으로 오전 양중 보류": "강풍 양중보류", "강풍으로 마스트 양중 보류": "강풍 양중보류",
             "작업면 인계 지연": "작업면 인계 지연", "자재반입 확인 대기": "자재반입 확인 대기",
             "양중순서 조정으로 대기": "양중순서(슬롯) 조정"}
wk["cause"] = wk["Daily_Remark"].map(CAUSE_MAP)
wait = wk[wk["Crew_Waiting_Minutes"] > 0].groupby("cause").agg(
    rows=("Date", "size"), minutes=("Crew_Waiting_Minutes", "sum"), worker_hours=("wait_wh", "sum")
).sort_values("worker_hours", ascending=False)
wait["share"] = wait["worker_hours"] / wait["worker_hours"].sum()
wait.round(2).to_csv(os.path.join(OUT, "t6_crew_wait_by_cause.csv"), encoding="utf-8-sig")
wait_task = wk[wk["Crew_Waiting_Minutes"] > 0].groupby(["Task_ID", "Subzone"]).agg(
    minutes=("Crew_Waiting_Minutes", "sum"), worker_hours=("wait_wh", "sum")).sort_values("worker_hours", ascending=False)
summary["crew_wait_total"] = dict(minutes=int(wk["Crew_Waiting_Minutes"].sum()),
                                  worker_hours=round(wk["wait_wh"].sum(), 1))
summary["crew_wait_by_cause"] = wait.round(3).reset_index().to_dict("records")

# 장비 대기 (크레인 vs 기타), 강풍일 분리
eq["wind_day"] = eq["Date"].isin(wind_days)
eq["wait_ratio"] = eq["Waiting_Minutes"] / (eq["Operation_Minutes"] + eq["Waiting_Minutes"])
eqw = eq.groupby("Equipment_ID").agg(days=("Date", "size"), op=("Operation_Minutes", "sum"),
                                     wait=("Waiting_Minutes", "sum"), maint=("Maintenance_Minutes", "sum"))
eqw["wait_ratio"] = eqw["wait"] / (eqw["op"] + eqw["wait"])
eqw_norm = eq[~eq["wind_day"]].groupby("Equipment_ID")["wait_ratio"].mean()
eqw["wait_ratio_excl_wind"] = eqw_norm
eqw["wind_wait"] = eq[eq["wind_day"]].groupby("Equipment_ID")["Waiting_Minutes"].sum()
eqw = eqw.fillna(0).sort_values("wait_ratio", ascending=False)
eqw.round(3).to_csv(os.path.join(OUT, "t7_equipment_wait.csv"), encoding="utf-8-sig")
notes = pd.crosstab(eq["Equipment_ID"], eq["Notes"])
notes.to_csv(os.path.join(OUT, "t7b_equipment_wait_notes.csv"), encoding="utf-8-sig")
summary["equipment_wait"] = eqw.round(3).reset_index().to_dict("records")
summary["equipment_notes_total"] = eq["Notes"].value_counts().to_dict()

# 양중 보류 / 반입→양중 지연 (적치 체류)
x = lifts.merge(dl[["Delivery_ID", "Unload_End_Time"]], left_on="Related_Delivery_ID",
                right_on="Delivery_ID", how="left")
x["lag"] = (x["Actual_Start"] - x["Unload_End_Time"]).dt.total_seconds() / 60
summary["unload_to_lift_lag_median"] = x.groupby("Equipment_ID")["lag"].median().round(0).to_dict()
summary["unload_to_lift_lag_nextday"] = int((x["lag"] > 600).sum())
summary["lift_holds"] = lf[lf["Status"] != "완료"].groupby("Hold_Reason").size().to_dict()

# 풍속 : 작업판단 풍속 재계산 검증
wx["h"] = wx["Time"].str[:2].astype(int)
for cid, f in WIND_FACTOR.items():
    wx[cid] = (wx["Wind_mps"] * f + 1e-9).round(1)
wx_ex = {cid: int((wx[cid] >= WIND_LIMIT[cid]).sum()) for cid in WIND_FACTOR}
summary["wind_exceed_hours"] = wx_ex
import decimal
def _r1(x):   # 사사오입(ROUND_HALF_UP), 안내서 규칙
    return float(decimal.Decimal(str(round(x, 4))).quantize(decimal.Decimal("0.1"), rounding=decimal.ROUND_HALF_UP))
chk = lf.copy()
chk["h"] = chk["Actual_Start"].fillna(chk["Planned_Start"]).dt.hour      # 작업 시작시각(보류는 계획시각) 정시
chk = chk.merge(wx[["Date", "h", "Wind_mps"]], on=["Date", "h"], how="left", suffixes=("", "_ground"))
chk["calc"] = [_r1(w * WIND_FACTOR[e]) for w, e in zip(chk["Wind_mps_ground"], chk["Equipment_ID"])]
summary["wind_recalc_mismatch"] = int((abs(chk["calc"] - chk["Wind_mps"]) > 0.05).sum())
summary["wind_hold_all_justified"] = bool((chk.loc[chk["Hold_Reason"] == "풍속 기준 초과", "Wind_mps"]
                                            >= chk.loc[chk["Hold_Reason"] == "풍속 기준 초과", "Wind_Limit_mps"]).all())

# 공정 편차 연쇄
ms_v = ms[["Task_ID", "Subzone", "Task_Name", "Predecessor", "Planned_Finish", "Forecast_Finish",
           "Forecast_Variance_Days", "Delay_Reason_Code", "Status_AsOf_2026_10_31"]]
ms_v.to_csv(os.path.join(OUT, "t8_schedule_variance.csv"), index=False, encoding="utf-8-sig")
delay = ms[ms["Forecast_Variance_Days"] > 0].groupby("Delay_Reason_Code")["Forecast_Variance_Days"].agg(
    ["count", "sum"]).sort_values("sum", ascending=False)
summary["delay_code_days"] = delay.reset_index().to_dict("records")

# TBM 미참석
tm = tbm.merge(wk[["Date", "Task_ID", "Actual_Workers"]], on=["Date", "Task_ID"])
tm["gap"] = tm["Actual_Workers"] - tm["Attendance_Count"]
summary["tbm_missing_by_zone"] = tm.groupby("Subzone")["gap"].sum().sort_values(ascending=False).to_dict()
summary["tbm_missing_total"] = int(tm["gap"].sum())

# 품질 이슈
summary["quality"] = {
    "delivery_source_doc_dup": dl[dl["Source_Document_No"].duplicated(keep=False)][["Delivery_ID", "Source_Document_No"]].to_dict("records"),
    "delivery_unload_end_missing": dl[dl["Unload_End_Time"].isna()]["Delivery_ID"].tolist(),
    "delivery_reserved_start_outside_window": gen[~gen["Reserved_Start"].apply(
        lambda t: (9 <= t.hour + t.minute / 60 <= 11) or (14 <= t.hour + t.minute / 60 <= 16))]["Delivery_ID"].tolist(),
    "delivery_early_or_late_over_30min": gen.loc[((gen["Reserved_Start"] - gen["Arrival_Time"]).dt.total_seconds().abs() > 1800),
                                                 "Delivery_ID"].tolist(),
    "inspection_closed_missing": int(insp["Closed_DateTime"].isna().sum()),
}

# ================================================================ FIGURES
def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------- FIG 1 : 구역×시간대 충돌노출지수 히트맵
fig = plt.figure(figsize=(15, 8.4))
gs = fig.add_gridspec(1, 2, width_ratios=[5.2, 1.25], wspace=0.04)
ax = fig.add_subplot(gs[0])
im = ax.imshow(cei.values, cmap=CMAP, vmin=0, vmax=max(70, np.nanmax(cei.values)), aspect="auto")
ax.set_xticks(range(len(HOURS)), [f"{h:02d}시" for h in HOURS], fontsize=10)
ax.set_yticks(range(len(SUBZONES)), [f"{z}  {ZNAME[z]}" for z in SUBZONES], fontsize=10.5)
for i, z in enumerate(SUBZONES):
    for j, h in enumerate(HOURS):
        v = cei.loc[z, h]
        a = int(alert_pv.loc[z, h])
        if v >= 3:
            ax.text(j, i - 0.12, f"{v:.0f}", ha="center", va="center", fontsize=10.5,
                    fontweight="bold", color="white" if v >= 48 else INK)
        if a > 0:
            ax.text(j, i + 0.27, f"경보{a}", ha="center", va="center", fontsize=7,
                    color="white" if v >= 48 else "#5A2A20")
for _, r in nm.iterrows():
    if r["h"] in HOURS:
        ax.plot(HOURS.index(r["h"]) + 0.36, SUBZONES.index(r["Subzone"]) - 0.32, marker="^",
                ms=6.5, color="#7A1FA2", mec="white", mew=0.6)
for y in [3.5, 6.5, 9.5]:
    ax.axhline(y, color="white", lw=2.4)
ax.axvline(4.5, color="#90A4AE", lw=1, ls=":")
ax.text(4.5, -0.75, "점심 12~13시(양중 미실시)", ha="center", fontsize=8.5, color="#607D8B")
for (x0, x1, lab) in [(1.5, 4.5, "오전 반입창 09~11시"), (6.5, 9.5, "오후 반입창 14~16시")]:
    ax.annotate("", xy=(x0, 13.05), xytext=(x1, 13.05), annotation_clip=False,
                arrowprops=dict(arrowstyle="<->", color="#1565C0", lw=1.3))
    ax.text((x0 + x1) / 2, 13.5, lab, ha="center", va="center", fontsize=9, color="#1565C0")
ax.set_title("① 구역×시간대 작업자·장비 충돌노출지수(CEI, 0~100)   ▲ = 아차사고 발생 시각",
             fontsize=14, fontweight="bold", loc="left", pad=26)
cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
cb.set_label("CEI", fontsize=9)
axb = fig.add_subplot(gs[1], sharey=ax)
vals = cei.mean(axis=1)
cols = [CMAP(min(v / 45, 1)) for v in vals]
axb.barh(range(len(SUBZONES)), vals, color=cols, edgecolor="#455A64", lw=0.5)
for i, v in enumerate(vals):
    axb.text(v + 0.8, i, f"{v:.1f}", va="center", fontsize=9.5, fontweight="bold" if v > 20 else None)
axb.set_title("구역 평균 CEI", fontsize=11, fontweight="bold")
axb.tick_params(axis="y", left=False, labelleft=False)
axb.set_xlim(0, vals.max() * 1.3)
axb.spines[["top", "right"]].set_visible(False)
fig.text(0.01, -0.035,
         "CEI[가정] = 100×(0.35·노출강도 정규화 + 0.35·근접경보율 정규화 + 0.15·혼재비율 + 0.15·아차사고 정규화).  "
         "노출강도 = 사람수×(지게차+굴착기+트럭+크레인가동) 슬롯 평균.  원천: 04 CCTV(2,990슬롯), 10 아차사고(25건).\n"
         "CCTV 값은 시간구간 최대 동시검출값이며 Proximity_Alert는 교육용 가상 이벤트로 위험도 정답값이 아님. 구역당 23일×10슬롯=230슬롯.",
         fontsize=8.3, color="#455A64")
save(fig, "fig1_zone_hour_CEI_heatmap.png")

# ---------- FIG 2 : 시간대별 위험 집중 프로파일
fig, axs = plt.subplots(3, 1, figsize=(14, 10.5), sharex=True,
                        gridspec_kw=dict(height_ratios=[1.15, 1.1, 0.9], hspace=0.12))
x = np.array(HOURS)
ax = axs[0]
bottom = np.zeros(len(HOURS))
for z, c in [("B2", "#C8322A"), ("B1", "#EE9A3A"), ("D1", "#6D4C41"), ("A4", "#1565C0"), ("C2", "#7A1FA2")]:
    v = prof[f"alerts_{z}"].values
    ax.bar(x, v, bottom=bottom, color=c, width=0.62, label=f"{z} {ZNAME[z]}", edgecolor="white", lw=0.5)
    bottom += v
for xi, v in zip(x, bottom):
    if v:
        ax.text(xi, v + 0.8, f"{int(v)}", ha="center", fontsize=9.5, fontweight="bold")
ax2 = ax.twinx()
ax2.plot(x, prof["near_miss"], "^-", color="#7A1FA2", lw=1.6, ms=8, label="아차사고(건)")
ax2.set_ylim(0, prof["near_miss"].max() * 1.6)
ax2.set_ylabel("아차사고 건수", color="#7A1FA2")
ax.set_ylabel("근접경보 합계(23일)")
ax.set_ylim(0, bottom.max() * 1.25)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, ncol=6, fontsize=8.8, loc="upper left", frameon=False)
ax.set_title("② 시간대별 위험 집중 프로파일 — 근접경보·아차사고 / 양중 / 차량 체류", fontsize=14,
             fontweight="bold", loc="left")

ax = axs[1]
for cid, c in [("TC-01", "#C8322A"), ("TC-02", "#1565C0"), ("MC-01", "#2E7D32")]:
    ax.plot(x, prof[f"lift_{cid}"], "o-", color=c, lw=2, label=f"{cid} 인양 분/일")
ax.bar(x, prof["lift_starts"], color="#B0BEC5", width=0.55, alpha=0.6, label="양중 착수 건수(23일 합)")
for xi, v in zip(x, prof["lift_starts"]):
    if v:
        ax.text(xi, v + 0.5, f"{int(v)}", ha="center", fontsize=8.8, color="#37474F")
ax.axvspan(12.6, 13.6, color="#FFCDD2", alpha=0.45)
ax.text(13.1, prof["lift_starts"].max() * 1.12,
        f"13시 집중: 완료양중 {int(prof.loc[13,'lift_starts'])}/{int(prof['lift_starts'].sum())}건"
        f"({summary['lift_13h_share']*100:.0f}%)\nTC-01×TC-02 동시양중 8건 중 4건", ha="center",
        fontsize=9, color="#B71C1C", fontweight="bold")
ax.set_ylabel("분 / 건")
ax.set_ylim(0, prof["lift_starts"].max() * 1.45)
ax.legend(ncol=4, fontsize=8.8, loc="upper left", frameon=False)

ax = axs[2]
ax.fill_between(x, prof["b2_truck_min"], step="mid", color="#EE9A3A", alpha=0.55, label="B2 대형반입 트럭 체류(분/일)")
ax.plot(x, prof["rmc_truck_min"], "s-", color="#1565C0", lw=2, label="A4 레미콘 체류(분/타설일)")
for (a, b) in [(9, 11), (14, 16)]:
    ax.axvspan(a - 0.5, b + 0.5, color="#E3F2FD", alpha=0.5, zorder=0)
ax.set_ylabel("분")
ax.set_xticks(x, [f"{h:02d}시" for h in HOURS])
ax.legend(ncol=3, fontsize=8.8, loc="upper right", frameon=False)
g7 = summary["gate_by_slot"]
ax.text(6.85, prof["b2_truck_min"].max() * 0.95,
        f"출역 피크(03): 06:30-07:00 입장 {g7['06:30-07:00']['Entry_Count']:.0f}명·07:00-07:30 "
        f"{g7['07:00-07:30']['Entry_Count']:.0f}명 / 16:30-17:00 퇴장 {g7['16:30-17:00']['Exit_Count']:.0f}명(일평균)\n"
        "→ 작업자 출입 피크와 대형반입(09시~)은 시간상 분리됨. B1 위험은 반입창 내 차량 적체의 영향이 큼(해석)",
        fontsize=8.6, color="#37474F", va="top")
save(fig, "fig2_hourly_risk_profile.png")

# ---------- FIG 3 : 요일×시간 고위험 활동 히트맵
fig, ax = plt.subplots(figsize=(12, 4.4))
im = ax.imshow(act_pv.values, cmap=CMAP, aspect="auto")
ax.set_xticks(range(len(HOURS)), [f"{h:02d}시" for h in HOURS])
ax.set_yticks(range(6), [f"{d}({n}일)" for d, n in zip(DOW, days_per_dow)])
for i in range(6):
    for j in range(len(HOURS)):
        v = act_pv.values[i, j]
        if v >= 0.3:
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=9,
                    color="white" if v > act_pv.values.max() * 0.65 else INK)
fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01).set_label("일평균 점수")
ax.set_title("③ 요일×시간 고위험 활동 집중도 (일수 보정)  점수[가정] = 양중착수 + 근접경보 + 3×아차사고",
             fontsize=12.5, fontweight="bold", loc="left")
save(fig, "fig3_dow_hour_heatmap.png")

# ---------- FIG 4 : 대표일 타임라인 (간섭 시각화)
REP = [("2026-10-14", "크레인 상호간섭일 (TC-01×TC-02 동시양중 2회 + 아차 NM-0010)"),
       ("2026-10-19", "1차 연속타설일 (레미콘 12대 × 일반반입 3대, B1 공유)"),
       ("2026-10-27", "강풍 보류일 (양중 보류 3건·크레인 300분 대기, 반입 4대 그대로)")]
fig, axs = plt.subplots(3, 1, figsize=(15, 11), gridspec_kw=dict(hspace=0.5))
LANES = ["TC-01", "TC-02", "MC-01", "B2 트럭", "레미콘(A4)", "풍속 초과"]
for ax, (dt, title) in zip(axs, REP):
    base = pd.Timestamp(dt)
    def hx(t): return (t - base).total_seconds() / 3600
    for i, ln in enumerate(LANES):
        ax.axhspan(i - 0.45, i + 0.45, color="#F5F7F8" if i % 2 else "white", zorder=0)
    cols = {"TC-01": "#C8322A", "TC-02": "#1565C0", "MC-01": "#2E7D32"}
    for i, cid in enumerate(["TC-01", "TC-02", "MC-01"]):
        for _, r in lf[(lf["Date"] == dt) & (lf["Equipment_ID"] == cid)].iterrows():
            if r["Status"] == "완료":
                ax.barh(i, hx(r["Actual_End"]) - hx(r["Actual_Start"]), left=hx(r["Actual_Start"]),
                        height=0.62, color=cols[cid], edgecolor="white")
                ax.text((hx(r["Actual_Start"]) + hx(r["Actual_End"])) / 2, i, r["Target_Subzone"],
                        ha="center", va="center", fontsize=7, color="white")
            else:
                ax.barh(i, hx(r["Planned_End"]) - hx(r["Planned_Start"]), left=hx(r["Planned_Start"]),
                        height=0.62, color="white", edgecolor=cols[cid], hatch="///", lw=1)
    g = gen[gen["Date"] == dt].sort_values("Gate_In_Time")
    for k, (_, r) in enumerate(g.iterrows()):
        off = (k % 3 - 1) * 0.22
        ax.barh(3 + off, hx(r["Gate_Out_Time"]) - hx(r["Gate_In_Time"]), left=hx(r["Gate_In_Time"]),
                height=0.2, color="#EE9A3A", edgecolor="#8D4B00", lw=0.4)
        ax.text(hx(r["Gate_In_Time"]), 3 + off, r["Material_Category"], fontsize=6.4, va="center",
                ha="right", color="#6D3A00")
    rr = rmc[rmc["Date"] == dt]
    for _, r in rr.iterrows():
        ax.barh(4, hx(r["Gate_Out_Time"]) - hx(r["Gate_In_Time"]), left=hx(r["Gate_In_Time"]),
                height=0.55, color="#64B5F6", edgecolor="#0D47A1", lw=0.4)
    w = wx[wx["Date"] == dt]
    for _, r in w.iterrows():
        if r["TC-01"] >= 12:
            ax.barh(5, 1, left=r["h"], height=0.55, color="#9E9E9E", alpha=0.75)
            ax.text(r["h"] + 0.5, 5, f'{r["TC-01"]:.0f}', ha="center", va="center", fontsize=7, color="white")
    ev = inter[(inter["Date"] == dt) & inter["code"].isin(["I1", "I2"])]
    for _, r in ev.iterrows():
        s = hx(pd.Timestamp(f"{dt} {r['start']}"))
        ax.axvspan(s, s + r["minutes"] / 60, color="#FF1744", alpha=0.18, zorder=0.5)
    for _, r in nm[nm["Date"] == dt].iterrows():
        ax.axvline(hx(r["t"]), color="#7A1FA2", lw=1.6, ls="--")
        ax.text(hx(r["t"]), 5.75, f'▼{r["NearMiss_ID"]} {r["Subzone"]}', fontsize=7.8, color="#7A1FA2",
                ha="center", fontweight="bold")
    ax.set_yticks(range(len(LANES)), LANES, fontsize=9)
    ax.set_xlim(7, 17); ax.set_ylim(-0.6, 6.1)
    ax.set_xticks(range(7, 18), [f"{h:02d}" for h in range(7, 18)], fontsize=8.5)
    ax.axvspan(12, 13, color="#ECEFF1", zorder=0.2)
    ax.invert_yaxis()
    ax.set_title(f"{dt} ({DOW[pd.Timestamp(dt).dayofweek]})  {title}", fontsize=11.5, fontweight="bold", loc="left")
handles = [Patch(color="#C8322A", label="TC-01 양중(라벨=목표구역)"), Patch(color="#1565C0", label="TC-02 양중"),
           Patch(color="#2E7D32", label="MC-01 양중"),
           Patch(facecolor="white", edgecolor="#555", hatch="///", label="보류·취소(계획시각)"),
           Patch(color="#EE9A3A", label="B2 대형반입 체류(입문~출문)"), Patch(color="#64B5F6", label="레미콘 체류"),
           Patch(color="#9E9E9E", label="TC-01 보정풍속 ≥12m/s (값 표시)"),
           Patch(color="#FF1744", alpha=0.25, label="크레인 동시양중 구간"),
           Line2D([0], [0], color="#7A1FA2", ls="--", label="아차사고")]
fig.legend(handles=handles, ncol=5, loc="lower center", fontsize=8.6, frameon=False, bbox_to_anchor=(0.5, 0.0))
fig.suptitle("④ 대표일 간섭 타임라인 — 장비·공종·자재반입이 같은 시각에 겹치는 구간", fontsize=14,
             fontweight="bold", x=0.01, ha="left", y=0.95)
fig.subplots_adjust(bottom=0.09)
save(fig, "fig4_representative_day_timeline.png")

# ---------- FIG 5 : 간섭 매트릭스 (자원 × 자원)
RES = ["TC-01", "TC-02", "MC-01", "레미콘·PC-01", "B2 하역(지게차)", "B3 적치", "작업자(하부·통로)", "D2 설비공종"]
M = pd.DataFrame(0.0, index=RES, columns=RES)
LBL = pd.DataFrame("", index=RES, columns=RES)
def setm(a, b, v, lab):
    M.loc[a, b] = M.loc[b, a] = v
    LBL.loc[a, b] = LBL.loc[b, a] = lab
isum = inter_sum.set_index("code")
setm("TC-01", "TC-02", isum.loc["I1", "minutes"], f'I1 동시양중\n{int(isum.loc["I1","events"])}건·{int(isum.loc["I1","minutes"])}분\nNM-0010')
setm("MC-01", "TC-02", isum.loc["I2", "minutes"], f'I2 동시양중\n{int(isum.loc["I2","events"])}건·{int(isum.loc["I2","minutes"])}분')
setm("레미콘·PC-01", "B2 하역(지게차)", isum.loc["I3", "minutes"], f'I3 B1공유\n일반 {int(isum.loc["I3","events"])}대·{int(isum.loc["I3","minutes"])}분')
setm("TC-01", "B2 하역(지게차)", isum.loc["I5", "minutes"], f'I5 반경내 하역\n{int(isum.loc["I5","events"])}건·{int(isum.loc["I5","minutes"])}분')
setm("B2 하역(지게차)", "B3 적치", isum.loc["I4", "minutes"], f'I4 ≥3대 점유\n{int(isum.loc["I4","days"])}일·{int(isum.loc["I4","minutes"])}분')
b3_mixed = int(cam[(cam["Subzone"] == "B3")]["mixed"].sum())
setm("B3 적치", "작업자(하부·통로)", b3_mixed, f"B3 혼재\n{b3_mixed}/230슬롯\n적치높이 지적5")
b2_alert = int(zone_tot.loc["B2", "alerts"])
setm("B2 하역(지게차)", "작업자(하부·통로)", b2_alert * 2, f"B2 근접경보\n{b2_alert}건\nNM-0005·0006")
setm("TC-01", "작업자(하부·통로)", 120, "배제구역 접근\nNM-0007·0009·0010\n(A1·A2)")
setm("레미콘·PC-01", "작업자(하부·통로)", 90, "A4 교행\nNM-0001~0003")
setm("D2 설비공종", "작업자(하부·통로)", 110,
     f"D2 동시공종≥3\n{len(d2_multi)}일·NM 4건\n미조치 11")
setm("TC-02", "작업자(하부·통로)", 60, "신호수 시야\nNM-0012\nSIGNAL_VIEW 4")
fig, ax = plt.subplots(figsize=(12.5, 10))
mask = np.triu(np.ones_like(M.values, dtype=bool), k=0)
Mv = np.where(mask, np.nan, M.values)
ax.imshow(Mv, cmap=CMAP, vmin=0, vmax=max(200, np.nanmax(Mv) * 0.8))
for i in range(len(RES)):
    for j in range(len(RES)):
        if i > j and LBL.iloc[i, j]:
            ax.text(j, i, LBL.iloc[i, j], ha="center", va="center", fontsize=8.6, color=INK, fontweight="bold")
        if i == j:
            ax.text(j, i, RES[i], ha="center", va="center", fontsize=9, color="#455A64", rotation=0)
ax.set_xticks(range(len(RES)), RES, rotation=30, ha="right", fontsize=9.5)
ax.set_yticks(range(len(RES)), RES, fontsize=9.5)
ax.set_title("⑤ 장비·공종·자재반입 간섭 매트릭스 (색 = 간섭 분·건 규모[상대값])", fontsize=13.5,
             fontweight="bold", loc="left")
for sp in ax.spines.values():
    sp.set_visible(False)
fig.text(0.02, 0.005, "색 기준: 장비·반입 간 셀 = 겹친 분(t3), B2-작업자 = 근접경보×2, B3-작업자 = 혼재슬롯 수, "
         "그 외 작업자 관련 셀은 아차사고·지적 건수 기반 정성 순위[가정]. 숫자 라벨이 근거값임.", fontsize=8.3, color="#455A64")
save(fig, "fig5_interference_matrix.png")

# ---------- FIG 6 : 병목 파레토 + 장비대기 + 공정편차 연쇄
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], hspace=0.42, wspace=0.25)
ax = fig.add_subplot(gs[0, 0])
cw = wait["worker_hours"]
ax.bar(range(len(cw)), cw.values, color=["#C8322A", "#EE9A3A", "#F2C94C", "#90A4AE"][:len(cw)])
cum = cw.cumsum() / cw.sum() * 100
ax2 = ax.twinx(); ax2.plot(range(len(cw)), cum.values, "o-", color=INK); ax2.set_ylim(0, 110)
for i, (v, c, m) in enumerate(zip(cw.values, cum.values, wait["minutes"].values)):
    ax.text(i, v + 2, f"{v:.0f} 인시\n({m:.0f}분)", ha="center", fontsize=9)
    ax2.text(i + 0.12, c + 3, f"{c:.0f}%", fontsize=8.5)
ax.set_xticks(range(len(cw)), cw.index, fontsize=9.5)
ax.set_ylabel("작업조 대기 인시(대기분×실투입/60)")
ax.set_ylim(0, cw.max() * 1.3)
ax.set_title(f"⑥-a 작업조 대기 원인 파레토 (총 {summary['crew_wait_total']['worker_hours']:.0f}인시)",
             fontsize=12, fontweight="bold", loc="left")

ax = fig.add_subplot(gs[0, 1])
e2 = eqw.copy()
ax.barh(e2.index, e2["wait_ratio"] * 100, color="#EE9A3A", label="전체 대기율")
ax.barh(e2.index, e2["wait_ratio_excl_wind"] * 100, color="#C8322A", height=0.35, label="강풍일 제외 대기율")
for i, (a, b) in enumerate(zip(e2["wait_ratio"], e2["wait_ratio_excl_wind"])):
    ax.text(a * 100 + 0.8, i, f"{a*100:.0f}% / {b*100:.0f}%", va="center", fontsize=8.5)
ax.invert_yaxis(); ax.set_xlim(0, 62)
ax.set_xlabel("대기분 / (가동분+대기분), %")
ax.legend(fontsize=8.5, frameon=False, loc="lower right")
ax.set_title("⑥-b 장비 대기율 — 크레인 3대가 지게차·고소작업대의 2배 이상", fontsize=12, fontweight="bold", loc="left")

ax = fig.add_subplot(gs[1, :])
chain = ["T001", "T002", "T003", "T004", "T005"]
others = ["T010", "T011", "T012", "T014", "T016", "T018", "T006"]
ms_i = ms.set_index("Task_ID")
xs = {}
for k, t in enumerate(chain):
    xs[t] = (k * 2.6, 1.3)
for k, t in enumerate(others):
    xs[t] = (k * 1.95, -0.35)
for t, (xx, yy) in xs.items():
    r = ms_i.loc[t]
    v = r["Forecast_Variance_Days"]
    c = CMAP(min(v / 3.2, 1) * 0.95 + 0.05)
    ax.add_patch(FancyBboxPatch((xx, yy), 2.0 if t in chain else 1.7, 0.95,
                                boxstyle="round,pad=0.02,rounding_size=0.08", fc=c, ec="#37474F", lw=0.8))
    ax.text(xx + (1.0 if t in chain else 0.85), yy + 0.68, f'{t} {r["Subzone"]}', ha="center", fontsize=9.5, fontweight="bold")
    ax.text(xx + (1.0 if t in chain else 0.85), yy + 0.42, (r["Task_Name"] if len(r["Task_Name"]) <= 11 else r["Task_Name"][:10] + "…"), ha="center", fontsize=7.8)
    ax.text(xx + (1.0 if t in chain else 0.85), yy + 0.14, f'+{v}일 · {r["Delay_Reason_Code"]}', ha="center",
            fontsize=8.4, color="#B71C1C" if v >= 2 else INK, fontweight="bold")
for a, b in zip(chain[:-1], chain[1:]):
    ax.annotate("", xy=(xs[b][0], 1.78), xytext=(xs[a][0] + 2.0, 1.78),
                arrowprops=dict(arrowstyle="-|>", color="#37474F", lw=1.4))
ax.text(0, 2.45, "1동 골조 핵심경로(SS 구획별 연쇄): 양중슬롯(LIFT_SLOT)·자재지연(MAT_DELAY)이 누적되어 "
        "T005 슬래브 타설 예상완료 11/02 (계획 10/29 대비 +3작업일)", fontsize=10.5, fontweight="bold", color="#B71C1C")
ax.text(0, -0.62, "기타 공종 편차: 외장 LIFT_CONFLICT·WIND_HOLD, 지하 SPACE/MEP_CONFLICT, 허가 PERMIT_DELAY",
        fontsize=9.5, color="#37474F")
ax.set_xlim(-0.2, 13.5); ax.set_ylim(-0.8, 2.75); ax.axis("off")
ax.set_title("⑥-c 공정편차 연쇄 (01 종합공정표, 2026-10-31 기준 Forecast_Variance_Days)", fontsize=12,
             fontweight="bold", loc="left")
save(fig, "fig6_bottleneck.png")

# ---------- FIG 7 : 위험·간섭 지도 (배치도 개념 레이아웃)
LAYOUT = {"A3": (4, 52, 16.6, 18), "A4": (22, 52, 16.6, 18), "B2": (40, 52, 16.6, 18),
          "B3": (58, 52, 16.6, 18), "B1": (40, 72, 35.2, 10),
          "A1": (4, 23, 16.6, 25.5), "A2": (22, 23, 16.6, 25.5), "C1": (40, 23, 16.6, 25.5),
          "C2": (58, 23, 16.6, 25.5), "C3": (76, 23, 16.6, 25.5),
          "D1": (40, 4, 16.6, 14), "D2": (58, 4, 16.6, 14), "D3": (76, 4, 16.6, 14)}
fig, ax = plt.subplots(figsize=(19, 11.2))
ax.set_xlim(0, 128); ax.set_ylim(-3, 92); ax.axis("off")
ax.add_patch(FancyBboxPatch((1, 85), 94, 4.5, boxstyle="round,pad=0,rounding_size=0.6", fc="#E8F5E9", ec="#66BB6A"))
ax.text(48, 87.2, "북측 도시도로 · 외부 보호보행통로(상시 개방, C05) — TC-01 상부 선회 금지", ha="center",
        va="center", fontsize=10, color="#2E7D32")
vmax = 45
for z, (x0, y0, w, h) in LAYOUT.items():
    v = zone_tot.loc[z, "CEI_mean"]
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=0.8",
                                fc=CMAP(min(v / vmax, 1)), ec="#37474F", lw=1))
    tc = "white" if v / vmax > 0.72 else INK
    ax.text(x0 + 1, y0 + h - 2.2, f"{z} {ZNAME[z]}", fontsize=10.5, fontweight="bold", color=tc, va="center")
    pk = int(zone_tot.loc[z, "peak_hour"])
    ax.text(x0 + 1, y0 + h - 5.2, f"평균 CEI {v:.1f} · 피크 {pk:02d}시({zone_tot.loc[z,'CEI_peak']:.0f})",
            fontsize=8.2, color=tc, va="center")
    ax.text(x0 + 1, y0 + h - 7.8, f"경보 {int(zone_tot.loc[z,'alerts'])} · 아차 {int(zone_tot.loc[z,'near_miss'])} · "
            f"혼재 {zone_tot.loc[z,'mixed_rate']*100:.0f}%", fontsize=8.2, color=tc, va="center")
# 크레인 위치·반경(개념)
for (cx, cy, r, c, lab, tx, ha) in [(38.5, 50.2, 30, "#C8322A", "TC-01", 37.6, "right"),
                                    (66, 31, 22, "#6A1B9A", "TC-02", 67.2, "left")]:
    ax.add_patch(plt.Circle((cx, cy), r, fill=False, ls="--", lw=1.4, ec=c, alpha=0.75))
    ax.plot(cx, cy, marker="^", ms=12, color=c, zorder=6)
    ax.text(tx, cy, lab, color=c, fontsize=10, fontweight="bold", ha=ha, va="center", zorder=6)
ax.add_patch(plt.Circle((84.3, 33), 6.5, fill=False, ls=":", lw=1.2, ec="#2E7D32"))
ax.text(84.3, 25.2, "MC-01", color="#2E7D32", fontsize=9, ha="center", fontweight="bold")
HOT = [("I1", 57.3, 50.2, "TC-01×TC-02 동시양중 8건·104분\n(B3·C1 중첩구역, C10 위반 소지)\nNM-0010 동시각(10/14 11:33) 발생"),
       ("I3", 72.5, 77.0, "레미콘 타설창(08~10:40) × 일반반입 7대\nB1 경보: 타설일 4.0 vs 비타설일 1.5건/일"),
       ("I5", 39.3, 61.0, "TC-01 양중 × B2 하역 동시\n45건 중 11건(18쌍·276분), C04 반경"),
       ("I4", 57.3, 61.0, "B2 하역 동시점유 ≥3대: 6일·231분\n10시·15시 근접경보 피크(CEI 81·78)"),
       ("I6", 66.0, 54.5, "강풍 보류일 3일(10/15·21·27)\n반입 11대 그대로 → 적치·재양중 적체"),
       ("I2", 75.3, 36.0, "MC-01 × TC-02 동시양중\n10/28 3건·56분 (C3↔C1 인접)"),
       ("I7", 70.0, 6.5, "D2 3개 이상 공종 동시작업 8일\n설비·전기·화기·SL-03 / 아차 4·미조치 11")]
LY = [79, 70.5, 62, 53.5, 45, 32, 12]
for (code, hx_, hy, lab), ly in zip(HOT, LY):
    ax.add_patch(plt.Circle((hx_, hy), 1.75, color="#B71C1C", zorder=7))
    ax.text(hx_, hy, code, ha="center", va="center", color="white", fontsize=8.4, fontweight="bold", zorder=8)
    ax.add_patch(plt.Circle((97.5, ly), 1.75, color="#B71C1C", zorder=7))
    ax.text(97.5, ly, code, ha="center", va="center", color="white", fontsize=8.4, fontweight="bold", zorder=8)
    ax.text(100, ly, lab, fontsize=8.6, color="#3B0D0D", va="center", zorder=8,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#B71C1C", lw=0.8))
    ax.plot([hx_ + 1.75, 95.75], [hy, ly], color="#B71C1C", lw=0.6, alpha=0.45, zorder=6)
ax.annotate("", xy=(48, 18.3), xytext=(75.6, 71), arrowprops=dict(arrowstyle="-|>", color="#2E7D32", lw=1.3, ls="--", alpha=0.6))
ax.text(76, 69.3, "B1→B3 동측→D1\n(10/13~, C07)", fontsize=8, color="#2E7D32")
ax.text(0.5, 0.5, "축척 없는 개념도(배치도 v1.4.3 재구성). 크레인 반경 원은 C04·C10 서술을 표현한 개념 표시이며 거리·면적 근거 아님.\n"
        "색 = 구역 평균 CEI(가정 가중치) · I1~I7 = 간섭 핫스팟(t3_interference_summary.csv).", fontsize=8.4, color="#455A64")
ax.set_title("⑦ 현장 위험·간섭 지도 — 충돌노출지수 + 간섭 핫스팟", fontsize=15, fontweight="bold", loc="left")
save(fig, "fig7_risk_interference_map.png")

with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

print(json.dumps({k: summary[k] for k in ["zone_rank", "interference", "crew_wait_by_cause",
                                          "B1_alerts_per_day_pour", "B1_alerts_per_day_nonpour",
                                          "rmc_gap", "permit_gap", "wind_exceed_hours",
                                          "wind_recalc_mismatch", "wind_hold_all_justified",
                                          "dow_score_per_day", "high_risk_task_rows_by_dow",
                                          "unload_to_lift_lag_median", "lift_holds", "tbm_missing_by_zone",
                                          "D1_phase", "quality", "lift_starts_by_hour"]},
                 ensure_ascii=False, indent=1, default=str))
