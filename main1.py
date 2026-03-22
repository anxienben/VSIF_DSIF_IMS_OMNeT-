"""
Total Delay Time (TDT) Calculator  ─ 最終版
三架構：Standard IMS (7)、DSIF (修正版)、VSIF (修正版)
量測終點：180 Ringing 到達 UE1（7 個 sub-sequence）

修正項：P-CSCF / UE 節點的固定服務時間（不在公式內，無 TLS）
  UE1=5, UE2=3, P_CSCF1=7, P_CSCF2=7 → 22次 × 1/μ = 22 × 0.004s = 0.088s
  三個架構相同

【DSIF / VSIF eFC 修正說明】
  Request (10%):      送 AS，主流暫停 → 影響 delay
  Notification (50%): 副本平行送 AS，主流繼續 → 佔用 VSIF/C-SIF 但不暫停主流
  Null (40%):         跳過 AS

  VSIF/C-SIF 分母：R+N 係數（佔用 VSIF/C-SIF 服務時間）
  AS 分母：          R only 係數（只有 Request 影響主流 delay）
"""
import csv, math, os

MU   = 250      # 基礎服務率（1/0.004s）
N    = 2        # AS 數量
K    = 1        # VSIF 數量

# 修正項：只有 P-CSCF / UE 的服務時間
CORR = 22 * (1.0 / MU)   # 22 × 0.004s = 0.0880s（三架構均相同）

# DSIF 係數
DSIF_CSIF_RN = 4.79    # C-SIF R+N（佔用 C-SIF）
DSIF_ASIF_R  = 3.968   # A-SIF R only
DSIF_AS_R    = 2.628   # AS    R only

# VSIF 係數
VSIF_RN = 5.69   # VSIF R+N（佔用 VSIF）
VSIF_R  = 2.24   # AS   R only（Suspended，Table XI）

LAMBDA_START, LAMBDA_END, LAMBDA_STEP = 0.5, 5.0, 0.5

def ims_tdt(l):
    """公式 (7)：AS 分母不乘 N"""
    d1 = MU - 13*(N+1)*l
    d2 = MU - 13*l
    if d1<=0 or d2<=0: return float('inf')
    return 7*(N+1)/d1 + 7*N/d2 + CORR

def dsif_tdt(l):
    """DSIF：C-SIF 用 R+N，A-SIF / AS 用 R only"""
    d1 = MU - 13*(N+1)*l
    d2 = MU - (13 + DSIF_CSIF_RN*N)*l
    d3 = MU - DSIF_ASIF_R*l
    d4 = MU - DSIF_AS_R*l
    if any(d<=0 for d in [d1,d2,d3,d4]): return float('inf')
    return (7*(N+1)/d1
            + (7 + DSIF_CSIF_RN*N)/d2
            + DSIF_ASIF_R*N/d3
            + DSIF_AS_R*N/d4
            + CORR)

def vsif_tdt(l):
    """VSIF：VSIF 用 R+N，AS 用 R only"""
    d1 = MU - 26*l
    d2 = MU - (13 + VSIF_RN*N)*(l/K)
    d3 = MU - VSIF_R*l
    if any(d<=0 for d in [d1,d2,d3]): return float('inf')
    return 14/d1 + (7+VSIF_RN*N)/d2 + VSIF_R*N/d3 + CORR

def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TDT_results.csv")
    lambdas=[]; l=LAMBDA_START
    while l<=LAMBDA_END+1e-9: lambdas.append(round(l,2)); l+=LAMBDA_STEP

    rows=[]
    for lam in lambdas:
        i=ims_tdt(lam); d=dsif_tdt(lam); v=vsif_tdt(lam)
        rows.append({"lambda":lam,
            "IMS_TDT":  "" if math.isinf(i) else round(i,6),
            "DSIF_TDT": "" if math.isinf(d) else round(d,6),
            "VSIF_TDT": "" if math.isinf(v) else round(v,6)})

    with open(out,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["lambda","IMS_TDT","DSIF_TDT","VSIF_TDT"])
        w.writeheader(); w.writerows(rows)

    print("="*80)
    print(f"  修正項：三架構均 = 22 × 0.004s = {CORR:.4f}s（P-CSCF/UE，無 TLS）")
    print("="*80)
    print(f"{'λ':>5}  {'IMS_TDT':>12}  {'DSIF_TDT':>12}  {'VSIF_TDT':>12}")
    print("-"*50)
    for r in rows:
        fi=f"{r['IMS_TDT']:>12.6f}"  if r['IMS_TDT']  !="" else f"{'∞':>12}"
        fd=f"{r['DSIF_TDT']:>12.6f}" if r['DSIF_TDT'] !="" else f"{'∞':>12}"
        fv=f"{r['VSIF_TDT']:>12.6f}" if r['VSIF_TDT'] !="" else f"{'∞':>12}"
        print(f"{r['lambda']:>5.1f}  {fi}  {fd}  {fv}")
    print("="*80)
    print(f"\n✅ 結果已儲存：{out}")

if __name__=="__main__": main()