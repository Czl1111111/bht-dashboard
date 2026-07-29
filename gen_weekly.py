"""
Generate weekly_data.json from BHT series weekly source Excel.
Reads from Desktop, writes to bht_data/ folder.
"""
import pandas as pd
import json, os, glob

DESKTOP = os.path.expanduser("~/Desktop")
DATA_DIR = os.path.join(os.path.expanduser("~"), "bht_data")
SRC_DIR = os.path.join(os.path.expanduser("~"), "WPSDrive", "381220911", "WPS云盘", "海杉", "数据分析和基础表", "周数据复盘", "下载的数据表格", "生成数据看板所用到的表格")
os.chdir(DATA_DIR)

SRC_FILES = [
    os.path.join(SRC_DIR, 'BHT系列周数据复盘源数据.xlsx'),
    os.path.join(SRC_DIR, '5月 周18 产品表现-2026.xlsx'),
    os.path.join(DESKTOP, 'BHT系列周数据复盘源数据.xlsx'),
    os.path.join(DESKTOP, '5月 周18 产品表现-2026.xlsx'),
]
dfs = []
for f in SRC_FILES:
    if os.path.exists(f):
        print(f"Reading: {f}")
        dfs.append(pd.read_excel(f))
    else:
        print(f"[SKIP] Not found: {f}")
if not dfs:
    raise SystemExit("No source files found.")
# Concatenate all, later files override earlier for same rows via drop_duplicates
df = pd.concat(dfs, ignore_index=True)
# Keep last occurrence (newer file wins) for duplicate year+week+msku+date combos
dup_cols = [df.columns[0], df.columns[2], df.columns[7], df.columns[4]]
df = df.drop_duplicates(subset=dup_cols, keep='last')
print(f"Total rows after merge: {len(df)}")

TARGET = ['HX1822','HX1045','HX1053','HX1820','HX1821','HX1599','HX1352','HX1026','HX1025','HX1027','HX1046','HX1819','HX1234','HX1233','HX1236','HX1616','HX1235','HX1614','HX1615','HX2091','HX2089','HX2090']
PMAP = {'HX1822':'B09N9815DF','HX1045':'B09N9815DF','HX1053':'B09N9815DF','HX1820':'B09N9815DF','HX1821':'B09N9815DF','HX1599':'B09N9815DF','HX1352':'B09N9815DF','HX1026':'B0C3QMWY9K','HX1025':'B0C3QMWY9K','HX1027':'B0C3QMWY9K','HX1046':'B0C3QMWY9K','HX1819':'B0C3QMWY9K','HX1234':'B09G9RL5D3','HX1233':'B09G9RL5D3','HX1236':'B09G9RL5D3','HX1616':'B09G9RL5D3','HX1235':'B09G9RL5D3','HX1614':'B09G9RL5D3','HX1615':'B09G9RL5D3','HX2091':'B0FN7BFHQY','HX2089':'B0FN7BFHQY','HX2090':'B0FN7BFHQY'}
PNAMES = {'B09N9815DF':'330BHT(盒装)','B0C3QMWY9K':'瓶装BHT','B09G9RL5D3':'袋装BHT','B0FN7BFHQY':'蓝黄BHT'}
# Full product names (weekly source file has truncated names)
SKU_NAMES = {
    'HX1822':'BHT盒装-420pcs','HX1045':'BHT盒装-330pcs','HX1053':'BHT盒装200pcs-4',
    'HX1820':'BHT盒装-80pcs','HX1821':'BHT盒装-120pcs','HX1599':'BHT盒装-580pcs',
    'HX1352':'BHT-蓝黄盒子-660pcs','HX1026':'BHT瓶装-200pcs-红','HX1025':'BHT瓶装-200pcs-蓝',
    'HX1027':'BHT瓶装-120pcs-黄','HX1046':'BHT瓶装-500pcs-白','HX1819':'BHT瓶装-200pcs-三色混装',
    'HX1234':'BHT袋装-500pcs-红','HX1233':'BHT袋装-500pcs-蓝','HX1236':'BHT袋装-250pcs-黄',
    'HX1616':'BHT袋装-500pcs-黄','HX1235':'BHT袋装-500pcs-白','HX1614':'BHT袋装-1000pcs-红',
    'HX1615':'BHT袋装-1000pcs-蓝','HX2091':'BHT-蓝黄盒子-620pcs','HX2089':'BHT-蓝黄盒子-420pcs',
    'HX2090':'BHT-蓝黄盒子-520pcs'
}
SKU_ASINS = {
    'HX1045':'B07Q3JJRY8','HX1822':'B0CZQ3273C','HX1053':'B07RX6QYX5',
    'HX1820':'B0CZPXQ669','HX1821':'B0CZPYMRN7','HX1599':'B0BZNJW1ZF',
    'HX1352':'B09GXNQSHT','HX1026':'B07L29DLGN','HX1025':'B07L21PL37',
    'HX1027':'B07L2B5H15','HX1046':'B07Q6MW79Q','HX1819':'B0CZ3HP1S4',
    'HX1234':'B09B9V5HM5','HX1233':'B09B9K4PLV','HX1236':'B09B9NP9F4',
    'HX1616':'B0C52MS9P2','HX1235':'B09B9PJDRF','HX1614':'B0C5336727',
    'HX1615':'B0C531C3TC','HX2091':'B0FN78ZLS3','HX2089':'B0FN7D6FMY',
    'HX2090':'B0FN7C1DFK'
}

sku_col = df.columns[7]
df_f = df[df[sku_col].isin(TARGET)].copy()

def n(v,d=0):
    try:
        if pd.isna(v): return d
        return float(str(v).replace(',','').replace('%','').replace('$',''))
    except: return d

weekly_data = {}
for (yr, wk), grp in df_f.groupby([df.columns[0], df.columns[2]]):
    yr, wk = int(yr), int(wk)
    mo_val = int(grp.iloc[0,1])
    dates = grp.iloc[:,4].dropna()
    dmin = str(dates.min())[:10]
    dmax = str(dates.max())[:10]

    sales = sum(abs(n(v)) for v in grp.iloc[:,13])
    orders = int(sum(abs(n(v)) for v in grp.iloc[:,11]))  # col[11]=销量
    ad = sum(abs(n(v)) for v in grp.iloc[:,21])
    ad_sales = sum(abs(n(v)) for v in grp.iloc[:,22]) if grp.shape[1] > 22 else 0
    sessions = int(sum(abs(n(v)) for v in grp.iloc[:,8])) if grp.shape[1] > 8 else 0
    # 产品表现: 订单毛利润(col[16]), 订单毛利率(col[35]) 加权平均
    profit = sum(n(v) for v in grp.iloc[:,16])
    weighted_margin_sum = 0.0
    for idx in range(len(grp)):
        row_s = abs(n(grp.iloc[idx,13]))
        m_str = str(grp.iloc[idx,35])
        try: row_m = float(m_str.replace('%','').replace(',',''))
        except: row_m = 0
        weighted_margin_sum += row_s * row_m
    margin = round(weighted_margin_sum/sales, 2) if sales>0 else 0
    tacos = round(ad/sales*100, 2) if sales>0 else 0

    parents = {}
    for pid in ['B09N9815DF','B0C3QMWY9K','B09G9RL5D3','B0FN7BFHQY']:
        sub = grp[grp[sku_col].map(lambda x: PMAP.get(x,'')) == pid]
        ps = sum(abs(n(v)) for v in sub.iloc[:,13])
        po = int(sum(abs(n(v)) for v in sub.iloc[:,11]))  # col[11]=销量
        pa = sum(abs(n(v)) for v in sub.iloc[:,21])
        pp = sum(n(v) for v in sub.iloc[:,16])
        pwms = 0.0
        for idx in range(len(sub)):
            row_s = abs(n(sub.iloc[idx,13]))
            m_str = str(sub.iloc[idx,35])
            try: row_m = float(m_str.replace('%','').replace(',',''))
            except: row_m = 0
            pwms += row_s * row_m
        parents[pid] = {
            'name': PNAMES.get(pid, pid), 'n': sub[sku_col].nunique(),
            'o': po, 's': round(ps), 'ad': round(pa), 'pf': round(pp),
            'margin': round(pwms/ps, 2) if ps>0 else 0,
            'tacos': round(pa/ps*100, 2) if ps>0 else 0
        }

    # Aggregate by SKU within the week (source data is daily-level)
    skus = []
    sku_groups = grp.groupby(sku_col)
    for sku, sgrp in sku_groups:
        s_total = sum(abs(n(v)) for v in sgrp.iloc[:,13])
        o_total = int(sum(abs(n(v)) for v in sgrp.iloc[:,11]))  # col[11]=销量
        a_total = sum(abs(n(v)) for v in sgrp.iloc[:,21])
        # 产品表现: 订单毛利润(col[16]), 订单毛利率(col[35]) & 结算毛利率(col[34]) 加权平均
        p_total = sum(n(v) for v in sgrp.iloc[:,16])
        weighted_m = 0.0
        weighted_settle_m = 0.0
        for idx in range(len(sgrp)):
            row_s = abs(n(sgrp.iloc[idx,13]))
            # 订单毛利率 col[35]
            m_str = str(sgrp.iloc[idx,35])
            try: row_m = float(m_str.replace('%','').replace(',',''))
            except: row_m = 0
            weighted_m += row_s * row_m
            # 结算毛利率 col[34]
            sm_str = str(sgrp.iloc[idx,34])
            try: row_sm = float(sm_str.replace('%','').replace(',',''))
            except: row_sm = 0
            weighted_settle_m += row_s * row_sm
        m = round(weighted_m/s_total, 2) if s_total>0 else 0
        settle_m = round(weighted_settle_m/s_total, 2) if s_total>0 else 0
        first_row = sgrp.iloc[0]

        # TACoS: computed from weekly totals
        sku_tacos = round(a_total/s_total*100, 2) if s_total > 0 else 0

        # ACOS: from ad_spend / ad_sales (col 22 = 广告销售额)
        ad_sales_total = sum(abs(n(v)) for v in sgrp.iloc[:,22]) if sgrp.shape[1] > 22 else 0
        sku_acos = round(a_total/ad_sales_total*100, 2) if ad_sales_total > 0 else 0

        # BSR (小类排名 col[10]): text like "Butt Terminals：9", extract category + rank
        bsr_vals = []
        sku_bsr_cat = ''
        import re
        for v in sgrp.iloc[:,10]:
            try:
                if pd.notna(v):
                    s = str(v)
                    # Extract category name (text before number or colon)
                    cat_match = re.match(r'^([^\d：:]+)', s)
                    if cat_match and not sku_bsr_cat:
                        sku_bsr_cat = cat_match.group(1).strip()
                    digits = re.findall(r'\d+', s)
                    if digits:
                        bv = int(digits[-1])
                        if bv > 0: bsr_vals.append(bv)
            except: pass
        sku_bsr = min(bsr_vals) if bsr_vals else None

        # Sessions (col[8] 访客): for CVR re-calc on aggregation
        sessions_total = int(sum(abs(n(v)) for v in sgrp.iloc[:,8])) if sgrp.shape[1] > 8 else 0

        # CVR (col 39): may be decimal (0.1786=17.86%) or pct string ('20.00%')
        # Detect format: if raw value contains '%', it's already percentage → no ×100
        sku_cvr = 0
        cvr_weight_sum = 0
        for idx in range(len(sgrp)):
            try:
                if sgrp.shape[1] > 39:
                    raw_cvr = sgrp.iloc[idx, 39]
                    if pd.isna(raw_cvr):
                        continue
                    raw_str = str(raw_cvr)
                    is_pct = '%' in raw_str
                    d_cvr = n(raw_cvr)
                    d_ord = int(abs(n(sgrp.iloc[idx, 12])))
                    if d_ord > 0:
                        if is_pct:
                            sku_cvr += d_cvr * d_ord  # already pct, no ×100
                        else:
                            sku_cvr += d_cvr * d_ord  # decimal, ×100 later
                        cvr_weight_sum += d_ord
            except: pass
        if cvr_weight_sum > 0:
            avg_raw = sku_cvr / cvr_weight_sum
            if avg_raw > 1:
                sku_cvr = round(avg_raw, 2)  # already in percentage
            else:
                sku_cvr = round(avg_raw * 100, 2)  # decimal → percentage
        else:
            sku_cvr = 0

        # 广告CVR (col 42) and 自然CVR (col 43): same format detection
        def calc_sub_cvr(col_idx):
            sub_cvr = 0; sub_weight = 0
            for idx in range(len(sgrp)):
                try:
                    if sgrp.shape[1] > col_idx:
                        raw = sgrp.iloc[idx, col_idx]
                        if pd.isna(raw): continue
                        raw_str = str(raw)
                        is_pct = '%' in raw_str
                        d_val = n(raw)
                        d_ord = int(abs(n(sgrp.iloc[idx, 12])))
                        if d_ord > 0:
                            sub_cvr += d_val * d_ord
                            sub_weight += d_ord
                except: pass
            if sub_weight > 0:
                avg_raw = sub_cvr / sub_weight
                return round(avg_raw, 2) if avg_raw > 1 else round(avg_raw * 100, 2)
            return 0
        sku_ad_cvr = calc_sub_cvr(42)
        sku_nat_cvr = calc_sub_cvr(43)

        def pct_str(v, has_data=False):
            if not has_data: return 'N/A'
            if v is None: return 'N/A'
            return f'{v:.2f}%'

        skus.append({
            'p': PMAP.get(sku, ''), 'sku': sku,
            'asin': SKU_ASINS.get(sku, ''),
            'name': SKU_NAMES.get(sku, str(first_row.iloc[3]) if pd.notna(first_row.iloc[3]) else sku),
            'o': o_total, 's': round(s_total), 'ad': round(a_total),
            'ad_sales': round(ad_sales_total), 'sessions': sessions_total, 'pf': round(p_total),
            'margin': f'{m:.2f}%',
            'settle_margin': f'{settle_m:.2f}%',
            'acos': pct_str(sku_acos, sku_acos > 0),
            'tacos': pct_str(sku_tacos, sku_tacos > 0),
            'bsr': f'{sku_bsr_cat} #{sku_bsr}' if sku_bsr and sku_bsr_cat else (str(sku_bsr) if sku_bsr else 'N/A'),
            'cvr': pct_str(sku_cvr, cvr_weight_sum > 0),
            'ad_cvr': pct_str(sku_ad_cvr, sku_ad_cvr > 0),
            'nat_cvr': pct_str(sku_nat_cvr, sku_nat_cvr > 0),
        })
    # Sort by sales descending
    # Sort by parent ASIN order then by sales descending
    ASIN_ORDER = {'B09N9815DF':0,'B0C3QMWY9K':1,'B09G9RL5D3':2,'B0FN7BFHQY':3}
    skus.sort(key=lambda x: (ASIN_ORDER.get(x['p'], 99), -x['s']))

    key = f'{yr}_{wk:02d}'
    weekly_data[key] = {
        'year': yr, 'month': mo_val, 'week': wk,
        'dateRange': f'{dmin} ~ {dmax}',
        'total': {
            'margin': margin, 'target': 8.0,
            'sales': round(sales), 'ad': round(ad),
            'ad_sales': round(ad_sales), 'sessions': sessions,
            'tacos': tacos, 'orders': orders, 'profit': round(profit),
            'gap': round(sales*0.08 - profit)
        },
        'parents': parents, 'skus': skus
    }

# ===== Process weekly order profit files =====
import re
from datetime import datetime

order_files = glob.glob(os.path.join(DESKTOP, '2026.*订单利润.xlsx')) + glob.glob(os.path.join(SRC_DIR, '2026.*订单利润.xlsx'))
print(f"\nProcessing {len(order_files)} weekly order profit files...")

def parse_week_from_filename(fname):
    """Extract ISO week from filename like '2026.07.20-07.26 订单利润.xlsx'"""
    basename = os.path.basename(fname)
    m = re.match(r'(\d{4})\.(\d{2})\.(\d{2})-(\d{2})\.(\d{2})', basename)
    if m:
        y, m1, d1 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        dt = datetime(y, m1, d1)
        iso = dt.isocalendar()
        return iso[0], iso[1]
    return None, None

order_profit_by_week = {}
for f in sorted(order_files):
    yr, wk = parse_week_from_filename(f)
    if yr is None:
        continue
    key = f'{yr}_{wk:02d}'

    df_op = pd.read_excel(f)
    sku_col_op = df_op.columns[3]  # SKU
    df_op_f = df_op[df_op[sku_col_op].isin(TARGET)].copy()

    if len(df_op_f) == 0:
        continue

    total_sales_op = sum(abs(n(v)) for v in df_op_f.iloc[:,12])  # 销售额
    total_profit_op = sum(n(v) for v in df_op_f.iloc[:,5])        # 毛利润 raw
    total_cogs_op = sum(abs(n(v)) for v in df_op_f.iloc[:,28])    # 采购成本
    total_freight_op = sum(abs(n(v)) for v in df_op_f.iloc[:,29]) # 头程成本
    total_platform_op = sum(abs(n(v)) for v in df_op_f.iloc[:,18]) # 平台费
    total_fba_op = sum(abs(n(v)) for v in df_op_f.iloc[:,19])     # FBA发货费
    total_storage_op = sum(abs(n(v)) for v in df_op_f.iloc[:,21]) # 总仓储费
    total_ad_op = sum(abs(n(v)) for v in df_op_f.iloc[:,22])      # 广告花费
    total_promotion_op = sum(abs(n(v)) for v in df_op_f.iloc[:,23]) if df_op_f.shape[1] > 23 else 0  # 推广费
    total_inbound_op = sum(abs(n(v)) for v in df_op_f.iloc[:,27]) if df_op_f.shape[1] > 27 else 0  # 入库配置费

    # 订单利润率 = 各SKU毛利率的加权平均(销售额加权), 与Excel报表显示精度一致
    weighted_margin_sum = 0.0
    for idx in range(len(df_op_f)):
        sku_sales = abs(n(df_op_f.iloc[idx,12]))
        margin_str = str(df_op_f.iloc[idx,6])
        try: sku_margin = float(margin_str.replace('%','').replace(',',''))
        except: sku_margin = 0
        weighted_margin_sum += sku_sales * sku_margin
    order_margin = round(weighted_margin_sum/total_sales_op, 2) if total_sales_op > 0 else 0

    # 5大类成本结构
    cost_groups = [
        {'label':'商品成本',   'items':[{'label':'采购成本','value':round(total_cogs_op)},{'label':'头程成本','value':round(total_freight_op)}]},
        {'label':'平台交易费', 'items':[{'label':'FBA配送费','value':round(total_fba_op)},{'label':'平台佣金','value':round(total_platform_op)}]},
        {'label':'营销费用',   'items':[{'label':'广告费','value':round(total_ad_op)},{'label':'推广费','value':round(total_promotion_op)}]},
        {'label':'库存费用',   'items':[{'label':'仓储费','value':round(total_storage_op)},{'label':'入库配置费','value':round(total_inbound_op)}]},
        {'label':'净利润',     'items':[], 'isProfit':True},
    ]
    for g in cost_groups:
        if g.get('isProfit'): g['value'] = round(total_profit_op)
        else: g['value'] = sum(it['value'] for it in g['items'])

    order_profit_by_week[key] = {
        'orderMargin': order_margin,
        'profit': round(total_profit_op),
        'cost': {'groups': cost_groups, 'sales': round(total_sales_op)}
    }
    print(f"  {key}: sales=${total_sales_op:,.0f}, orderMargin={order_margin}%")

# ===== Process daily settlement profit file (按天) =====
daily_settle_files = glob.glob(os.path.join(DESKTOP, '*结算利润*按天*.xlsx')) + glob.glob(os.path.join(SRC_DIR, '*结算利润*按天*.xlsx'))
print(f"\nProcessing daily settlement profit files...")
settlement_by_week = {}

for f in daily_settle_files:
    print(f"  Reading: {os.path.basename(f)}")
    df_st = pd.read_excel(f, skiprows=1)
    # Column positions in daily settlement file:
    # col[0]=日期, col[4]=SKU, col[10]=销售额, col[38]=毛利润, col[40]=毛利率
    # col[19]=平台费, col[20]=FBA配送费, col[22]=广告费, col[23]=推广费
    # col[24]=FBA仓储费, col[34]=采购成本, col[35]=头程成本
    sku_col_st = df_st.columns[4]
    df_st_f = df_st[df_st[sku_col_st].isin(TARGET)].copy()

    if len(df_st_f) == 0:
        print(f"    No target SKUs found, skipping")
        continue

    # Parse date from col[0], group by ISO week
    def get_iso_week(date_val):
        try:
            if pd.isna(date_val): return None, None
            if isinstance(date_val, pd.Timestamp):
                iso = date_val.isocalendar()
                return iso[0], iso[1]
            # Try string parsing
            import re
            s = str(date_val)[:10]
            m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s)
            if m:
                dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                iso = dt.isocalendar()
                return iso[0], iso[1]
        except: pass
        return None, None

    for idx in range(len(df_st_f)):
        row = df_st_f.iloc[idx]
        yr, wk = get_iso_week(row.iloc[0])
        if yr is None: continue
        key = f'{yr}_{wk:02d}'

        if key not in settlement_by_week:
            settlement_by_week[key] = {'sales':0,'profit':0,'weighted_margin':0,
                                        'platform':0,'fba':0,'ad':0,'promotion':0,
                                        'storage':0,'inbound':0,'cogs':0,'freight':0}

        stk = settlement_by_week[key]
        row_sales = abs(n(row.iloc[10]))
        stk['sales'] += row_sales              # 销售额
        stk['profit'] += n(row.iloc[38])        # 毛利润 raw
        # 加权毛利率累计 (sales * reported margin%)
        margin_str = str(row.iloc[40])  # col[40]=毛利率
        try: row_margin = float(margin_str.replace('%','').replace(',',''))
        except: row_margin = 0
        stk['weighted_margin'] += row_sales * row_margin
        stk['platform'] += abs(n(row.iloc[19]))    # 平台费
        stk['fba'] += abs(n(row.iloc[20]))         # FBA发货费
        stk['ad'] += abs(n(row.iloc[22]))          # 广告费
        stk['promotion'] += abs(n(row.iloc[23])) if df_st_f.shape[1] > 23 else 0  # 推广费
        stk['storage'] += abs(n(row.iloc[24]))     # FBA仓储费
        stk['inbound'] += abs(n(row.iloc[25])) if df_st_f.shape[1] > 25 else 0   # 入库配置费
        stk['cogs'] += abs(n(row.iloc[34]))        # 采购成本
        stk['freight'] += abs(n(row.iloc[35]))     # 头程成本

for key, stk in sorted(settlement_by_week.items()):
    # 结算利润率 = 各SKU每日毛利率的加权平均, 与Excel显示精度一致
    margin = round(stk['weighted_margin']/stk['sales'], 2) if stk['sales'] > 0 else 0
    cost_groups = [
        {'label':'商品成本',   'items':[{'label':'采购成本','value':round(stk['cogs'])},{'label':'头程成本','value':round(stk['freight'])}]},
        {'label':'平台交易费', 'items':[{'label':'FBA配送费','value':round(stk['fba'])},{'label':'平台佣金','value':round(stk['platform'])}]},
        {'label':'营销费用',   'items':[{'label':'广告费','value':round(stk['ad'])},{'label':'推广费','value':round(stk['promotion'])}]},
        {'label':'库存费用',   'items':[{'label':'仓储费','value':round(stk['storage'])},{'label':'入库配置费','value':round(stk['inbound'])}]},
        {'label':'净利润',     'items':[], 'isProfit':True},
    ]
    for g in cost_groups:
        if g.get('isProfit'): g['value'] = round(stk['profit'])
        else: g['value'] = sum(it['value'] for it in g['items'])
    stk['margin'] = margin
    stk['cost'] = {'groups': cost_groups, 'sales': round(stk['sales'])}
    print(f"  {key}: sales=${stk['sales']:,.0f}, settlementMargin={margin}%")

# Merge order profit + settlement profit into weekly data
for key, wd in weekly_data.items():
    # Order profit (from weekly order profit files)
    if key in order_profit_by_week:
        op = order_profit_by_week[key]
        wd['total']['orderMargin'] = op['orderMargin']
        wd['total']['orderProfit'] = op['profit']
        wd['cost'] = op['cost']  # default cost from order profit
    else:
        wd['total']['orderMargin'] = wd['total'].get('margin', 0)
        wd['total']['orderProfit'] = wd['total'].get('profit', 0)

    # Settlement profit (from daily settlement file, aggregated by ISO week)
    if key in settlement_by_week:
        sp = settlement_by_week[key]
        wd['total']['settlementMargin'] = sp['margin']
        wd['total']['settlementProfit'] = round(sp['profit'])
        # Use settlement cost data for cost panel (more comprehensive)
        wd['settlementCost'] = sp['cost']
    else:
        if 'settlementMargin' not in wd['total'] or wd['total']['settlementMargin'] is None:
            wd['total']['settlementMargin'] = None
            wd['total']['settlementProfit'] = None

    # Add CVR (orders / sessions)
    sess = wd['total'].get('sessions', 0)
    ords = wd['total'].get('orders', 0)
    wd['total']['cvr'] = round(ords/sess*100, 2) if sess > 0 else 0

# Build week map from available weeks (sorted)
all_week_keys = sorted(weekly_data.keys())
week_map = {}
for i, wk in enumerate(all_week_keys):
    # Map as 'wXX_N' where XX is month, N is sequential
    m = str(weekly_data[wk]['month']).zfill(2)
    week_map[f'w{m}_{i+1}'] = wk

output = {'weeks': weekly_data, 'map': week_map}
with open('weekly_data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n[OK] {len(weekly_data)} weeks extracted to weekly_data.json")
for k, v in weekly_data.items():
    cost_info = f" | cost:{len(v.get('cost',{}).get('labels',[]))} items" if v.get('cost') else " | cost:N/A"
    print(f"  {k}: {v['dateRange']} | ${v['total']['sales']:,} | orderMargin={v['total'].get('orderMargin',v['total']['margin'])}% | CVR={v['total'].get('cvr',0)}%{cost_info}")
