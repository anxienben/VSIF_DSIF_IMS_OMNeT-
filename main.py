"""
Total Delay Time (TDT) Calculator  ─ 最終版
三架構：Standard IMS (7)、DSIF (修正版)、VSIF (34)
量測終點：180 Ringing 到達 UE1（7 個 sub-sequence）

【DSIF 公式修正說明】
OMNeT++ 中 eFC 觸發後的行為：
  Request (10%):      送 A-SIF → 等 AS 回應 → session 暫停（影響 delay）
  Notification (50%): 主流繼續走，副本送 A-SIF（不暫停，但佔用 C-SIF 排隊資源）
  Null (40%):         直接跳回 S_CSCF，不送 A-SIF/AS

因此：
  C-SIF 的到達率用 R+N 係數 (4.79n)  — Notification 仍佔用 C-SIF 服務時間
  A-SIF 的到達率用 R only 係數 (3.968n) — 只有 Request 讓 A-SIF 真正排隊等待
  AS    的到達率用 R only 係數 (2.628n) — 只有 Request 讓 AS 真正排隊等待

修正項 = P-CSCF/UE(22次×0.004s) + TLS overhead
  IMS : 22×0.004 + 35×0.0004 = 0.1020s
  DSIF: 22×0.004 + 91×0.0004 = 0.1244s
  VSIF: 22×0.004 + 49×0.0004 = 0.1076s

AS 分母（每個 AS 獨立，不乘 N）：
  IMS  d2 = μ - 13λ
  DSIF d4 = μ - 2.628λ
  VSIF d3 = μ - 5.69λ
"""
import csv, math, os

MU   = 250
N    = 2
K    = 1

CORR_IMS  = 22*0.004 + 35*0.0004   # 0.1020s
CORR_DSIF = 22*0.004 + 91*0.0004   # 0.1244s
CORR_VSIF = 22*0.004 + 49*0.0004   # 0.1076s

DSIF_CSIF_RN = 4.79    # C-SIF: R+N 係數（佔用 C-SIF 排隊）
DSIF_ASIF_R  = 3.968   # A-SIF: R only 係數（真正暫停 session）
DSIF_AS_R    = 2.628   # AS:    R only 係數
VSIF_AS      = 5.69

LAMBDA_START, LAMBDA_END, LAMBDA_STEP = 0.5, 5.0, 0.5

def ims_tdt(l):
    """公式 (7)"""
    d1 = MU - 13*(N+1)*l
    d2 = MU - 13*l
    if d1<=0 or d2<=0: return float('inf')
    return 7*(N+1)/d1 + 7*N/d2 + CORR_IMS

def dsif_tdt(l):
    """DSIF 修正版：C-SIF 用 R+N 負載，A-SIF 和 AS 用 R only"""
    d1 = MU - 13*(N+1)*l
    d2 = MU - (13 + DSIF_CSIF_RN*N)*l   # C-SIF: R+N 到達率
    d3 = MU - DSIF_ASIF_R*l             # A-SIF: R only（不乘 N）
    d4 = MU - DSIF_AS_R*l               # AS:    R only（不乘 N）
    if any(d<=0 for d in [d1,d2,d3,d4]): return float('inf')
    return (7*(N+1)/d1
            + (7 + DSIF_CSIF_RN*N)/d2
            + DSIF_ASIF_R*N/d3
            + DSIF_AS_R*N/d4
            + CORR_DSIF)

def vsif_tdt(l):
    """公式 (34)"""
    d1 = MU - 26*l
    d2 = MU - (13 + VSIF_AS*N)*(l/K)
    d3 = MU - VSIF_AS*l
    if any(d<=0 for d in [d1,d2,d3]): return float('inf')
    return 14/d1 + (7+VSIF_AS*N)/d2 + VSIF_AS*N/d3 + CORR_VSIF

def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TDT_results.csv")
    lambdas=[]; l=LAMBDA_START
    while l<=LAMBDA_END+1e-9: lambdas.append(round(l,2)); l+=LAMBDA_STEP

    rows=[]
    for lam in lambdas:
        i=ims_tdt(lam); d=dsif_tdt(lam); v=vsif_tdt(lam)
        rows.append({"lambda":lam,
            "IMS_TDT":        "" if math.isinf(i) else round(i,6),
            "DSIF_TDT":       "" if math.isinf(d) else round(d,6),
            "VSIF_TDT_(34)":  "" if math.isinf(v) else round(v,6)})

    with open(out,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["lambda","IMS_TDT","DSIF_TDT","VSIF_TDT_(34)"])
        w.writeheader(); w.writerows(rows)

    sim_IMS  = [0.293635,0.305694,0.322371,0.340902,0.358311,0.39163,0.421129,0.463888,0.520997,0.606249]
    sim_DSIF = [0.341457,0.357758,0.377700,0.401225,0.426856,0.458416,0.499842,0.558175,0.631218,0.740117]
    sim_VSIF = [0.248052,0.257298,0.266425,0.277599,0.287257,0.298849,0.313360,0.328555,0.349317,0.368200]

    print("="*80)
    print(f"  修正項：IMS={CORR_IMS:.4f}s  DSIF={CORR_DSIF:.4f}s  VSIF={CORR_VSIF:.4f}s")
    print(f"  DSIF：C-SIF 用 R+N 負載({DSIF_CSIF_RN}n)，A-SIF/AS 用 R only（{DSIF_ASIF_R}n/{DSIF_AS_R}n）")
    print("="*80)
    print(f"{'λ':>4} | {'IMS_f':>9} {'IMS_sim':>9} {'diff':>7} | {'DSIF_f':>9} {'DSIF_sim':>9} {'diff':>7} | {'VSIF_f':>9} {'VSIF_sim':>9} {'diff':>7}")
    print("-"*95)
    for i,l in enumerate(lambdas):
        fi=ims_tdt(l); fd=dsif_tdt(l); fv=vsif_tdt(l)
        si=sim_IMS[i]; sd=sim_DSIF[i]; sv=sim_VSIF[i]
        print(f"{l:4.1f} | {fi:9.4f} {si:9.4f} {fi-si:+7.4f} | {fd:9.4f} {sd:9.4f} {fd-sd:+7.4f} | {fv:9.4f} {sv:9.4f} {fv-sv:+7.4f}")
    print("="*80)
    print(f"\n✅ 結果已儲存：{out}")

if __name__=="__main__": main()