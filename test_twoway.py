"""
Total Delay Time (TDT) Calculator
三架構三版本比較：Standard IMS、DSIF、VSIF
量測終點：180 Ringing 到達 UE1（7 個 sub-sequence）

版本說明：
  V1 = 論文原始公式 (7)(23A)(34)：全部用 R+N 係數
  V2 = 論文 Suspended 公式 (7)(23B)(35)：全部用 R only 係數
  V3 = 修正混合版：C-SIF/VSIF 用 R+N，A-SIF/AS 用 R only

修正項（三架構相同）：
  P-CSCF/UE 22次 × 0.004s = 0.088s（不含 TLS）

係數來源（論文）：
  C-SIF R+N  = 4.79  [Table IV / 公式(12)]
  C-SIF R    = 1.34  [Table V  / 公式(18)]
  A-SIF R+N  = 13.24 [公式(16)]
  A-SIF R    = 3.968 [公式(21)]
  AS R+N     = 8.45  [公式(14)]   DSIF
  AS R       = 2.628 [公式(20)]   DSIF
  VSIF R+N   = 5.69  [Table IX / 公式(28)]
  VSIF R     = 2.24  [Table X  / 公式(32)]
"""
import csv, math, os

MU   = 250
N    = 2
K    = 1
CORR = 22 * (1.0 / MU)   # 0.0880s

# DSIF 係數
DSIF_CSIF_RN = 4.79;   DSIF_CSIF_R  = 1.34
DSIF_ASIF_RN = 13.24;  DSIF_ASIF_R  = 3.968
DSIF_AS_RN   = 8.45;   DSIF_AS_R    = 2.628

# VSIF 係數
VSIF_RN = 5.69;  VSIF_R = 2.24

LAMBDA_START, LAMBDA_END, LAMBDA_STEP = 0.5, 5.0, 0.5

# ── IMS 公式 (7) ────────────────────────────────────────────
# 注意：三個版本 IMS 公式相同，AS 分母均為 μ - 13λ（不乘 N）
def ims_tdt(l):
    """公式 (7)：AS 每個獨立，分母 μ - 13λ"""
    d1 = MU - 13*(N+1)*l
    d2 = MU - 13*l
    if d1<=0 or d2<=0: return float('inf')
    return 7*(N+1)/d1 + 7*N/d2 + CORR

# ── DSIF V1：公式 (23A)，R+N 全部 ───────────────────────────
def dsif_v1(l):
    """公式 (23A)：C-SIF R+N / A-SIF R+N / AS R+N"""
    d1 = MU - 13*(N+1)*l
    d2 = MU - (13 + DSIF_CSIF_RN*N)*l
    d3 = MU - (DSIF_CSIF_RN + DSIF_AS_RN)*l   # = (4.79+8.45)λ = 13.24λ
    d4 = MU - DSIF_AS_RN*l
    if any(d<=0 for d in [d1,d2,d3,d4]): return float('inf')
    return (7*(N+1)/d1
            + (7 + DSIF_CSIF_RN*N)/d2
            + DSIF_ASIF_RN*N/d3
            + DSIF_AS_RN*N/d4
            + CORR)

# ── DSIF V2：公式 (23B)，R only 全部 ────────────────────────
def dsif_v2(l):
    """公式 (23B)：C-SIF R / A-SIF R / AS R"""
    d1 = MU - 13*(N+1)*l
    d2 = MU - (13 + DSIF_CSIF_R*N)*l
    d3 = MU - DSIF_ASIF_R*l
    d4 = MU - DSIF_AS_R*l
    if any(d<=0 for d in [d1,d2,d3,d4]): return float('inf')
    return (7*(N+1)/d1
            + (7 + DSIF_CSIF_R*N)/d2
            + DSIF_ASIF_R*N/d3
            + DSIF_AS_R*N/d4
            + CORR)

# ── DSIF V3：修正混合版 ──────────────────────────────────────
def dsif_v3(l):
    """修正版：C-SIF 用 R+N（佔用 C-SIF）/ A-SIF、AS 用 R only（只有 Request 暫停 session）"""
    d1 = MU - 13*(N+1)*l
    d2 = MU - (13 + DSIF_CSIF_RN*N)*l   # C-SIF: R+N
    d3 = MU - DSIF_ASIF_R*l             # A-SIF: R only
    d4 = MU - DSIF_AS_R*l               # AS:    R only
    if any(d<=0 for d in [d1,d2,d3,d4]): return float('inf')
    return (7*(N+1)/d1
            + (7 + DSIF_CSIF_RN*N)/d2
            + DSIF_ASIF_R*N/d3
            + DSIF_AS_R*N/d4
            + CORR)

# ── VSIF V1：公式 (34)，R+N 全部 ────────────────────────────
def vsif_v1(l):
    """公式 (34)：VSIF R+N / AS R+N"""
    d1 = MU - 26*l
    d2 = MU - (13 + VSIF_RN*N)*(l/K)
    d3 = MU - VSIF_RN*l
    if any(d<=0 for d in [d1,d2,d3]): return float('inf')
    return 14/d1 + (7+VSIF_RN*N)/d2 + VSIF_RN*N/d3 + CORR

# ── VSIF V2：公式 (35)，R only 全部 ─────────────────────────
def vsif_v2(l):
    """公式 (35)：VSIF R / AS R"""
    d1 = MU - 26*l
    d2 = MU - (13 + VSIF_R*N)*(l/K)
    d3 = MU - VSIF_R*l
    if any(d<=0 for d in [d1,d2,d3]): return float('inf')
    return 14/d1 + (7+VSIF_R*N)/d2 + VSIF_R*N/d3 + CORR

# ── VSIF V3：修正混合版 ──────────────────────────────────────
def vsif_v3(l):
    """修正版：VSIF 用 R+N（佔用 VSIF）/ AS 用 R only（只有 Request 暫停 session）"""
    d1 = MU - 26*l
    d2 = MU - (13 + VSIF_RN*N)*(l/K)   # VSIF: R+N
    d3 = MU - VSIF_R*l                  # AS:   R only
    if any(d<=0 for d in [d1,d2,d3]): return float('inf')
    return 14/d1 + (7+VSIF_RN*N)/d2 + VSIF_R*N/d3 + CORR

# ── 主程式 ──────────────────────────────────────────────────
def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TDT_results.csv")
    lambdas = []
    l = LAMBDA_START
    while l <= LAMBDA_END + 1e-9:
        lambdas.append(round(l, 2))
        l += LAMBDA_STEP

    fields = [
        "lambda",
        "IMS_TDT",
        "DSIF_V1_(23A)", "DSIF_V2_(23B)", "DSIF_V3_mixed",
        "VSIF_V1_(34)",  "VSIF_V2_(35)",  "VSIF_V3_mixed",
    ]

    rows = []
    for lam in lambdas:
        def f(v): return "" if math.isinf(v) else round(v, 6)
        rows.append({
            "lambda":         lam,
            "IMS_TDT":        f(ims_tdt(lam)),
            "DSIF_V1_(23A)":  f(dsif_v1(lam)),
            "DSIF_V2_(23B)":  f(dsif_v2(lam)),
            "DSIF_V3_mixed":  f(dsif_v3(lam)),
            "VSIF_V1_(34)":   f(vsif_v1(lam)),
            "VSIF_V2_(35)":   f(vsif_v2(lam)),
            "VSIF_V3_mixed":  f(vsif_v3(lam)),
        })

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # ── 列印對照表 ───────────────────────────────────────────
    print("=" * 90)
    print(f"  修正項 = 22 × 0.004s = {CORR:.4f}s（P-CSCF/UE，無 TLS）")
    print(f"  V1 = 論文原始 (23A)/(34)：R+N 全部")
    print(f"  V2 = 論文 Suspended (23B)/(35)：R only 全部")
    print(f"  V3 = 修正混合：C-SIF/VSIF 用 R+N，A-SIF/AS 用 R only")
    print("=" * 90)
    print(f"{'λ':>4}  {'IMS':>8}  {'DSIF_V1':>9} {'DSIF_V2':>9} {'DSIF_V3':>9}  {'VSIF_V1':>9} {'VSIF_V2':>9} {'VSIF_V3':>9}")
    print("-" * 90)
    for r in rows:
        def g(k): return f"{r[k]:9.4f}" if r[k] != "" else f"{'∞':>9}"
        print(f"{r['lambda']:>4.1f}  {g('IMS_TDT'):>8}  "
              f"{g('DSIF_V1_(23A)')} {g('DSIF_V2_(23B)')} {g('DSIF_V3_mixed')}  "
              f"{g('VSIF_V1_(34)')} {g('VSIF_V2_(35)')} {g('VSIF_V3_mixed')}")
    print("=" * 90)
    print(f"\n✅ 結果已儲存：{out}")

if __name__ == "__main__":
    main()


# ── DSIF V4：C-SIF 雙向 R+N（去程＋回程）──────────────────
def dsif_v4(l):
    """
    DSIF V4：C-SIF 雙向到達率版本

    推導邏輯：
      C-SIF 為 B2BUA，每一個送往 A-SIF 的封包（去程）
      A-SIF 處理完後必定回傳一個封包給 C-SIF（回程）。
      因此 C-SIF 的實際到達率 = 去程 + 回程：

        去程係數（論文 Table IV）: 4.79
        回程係數（= 去程，每封去必有回）: 4.79
        雙向總係數: 4.79 + 4.79 = 9.58

        λ_CSIF = (13 + 9.58n)λ          ← 分母（C-SIF 真實負載）

      分子仍用去程 4.79n（只有去程造成 session 等待，影響 delay）：
        C-SIF 分子: 7 + 4.79n

      A-SIF、AS 維持 V3 的 R only 係數（3.968、2.628）。
    """
    d1 = MU - 13*(N+1)*l
    d2 = MU - (13 + 9.58*N)*l   # C-SIF 雙向：去程(4.79n) + 回程(4.79n)
    d3 = MU - DSIF_ASIF_R*l     # A-SIF: R only
    d4 = MU - DSIF_AS_R*l       # AS:    R only
    if any(d<=0 for d in [d1,d2,d3,d4]): return float('inf')
    return (7*(N+1)/d1
            + (7 + DSIF_CSIF_RN*N)/d2   # 分子保留 4.79n（去程貢獻）
            + DSIF_ASIF_R*N/d3
            + DSIF_AS_R*N/d4
            + CORR)