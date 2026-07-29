"""
BHT Data Pipeline v6 - Multi-month batch support
Scans Desktop for month-prefixed Lingxing exports, processes each month.
Patterns: *结算利润*.xlsx, *订单利润*.xlsx, *产品分析*.xlsx / *产品表现*.xlsx
"""
import pandas as pd
import json, os, re, glob, subprocess, sys

DESKTOP = os.path.expanduser("~/Desktop")
DATA_DIR = os.path.join(os.path.expanduser("~"), "bht_data")
SRC_DIR = os.path.join(os.path.expanduser("~"), "WPSDrive", "381220911", "WPS云盘", "海杉", "数据分析和基础表", "周数据复盘", "下载的数据表格", "生成数据看板所用到的表格")
os.chdir(DATA_DIR)

TARGET = ['HX1822','HX1045','HX1053','HX1820','HX1821','HX1599','HX1352',
          'HX1026','HX1025','HX1027','HX1046','HX1819',
          'HX1234','HX1233','HX1236','HX1616','HX1235','HX1614','HX1615',
          'HX2091','HX2089','HX2090']
PMAP = {'HX1822':'B09N9815DF','HX1045':'B09N9815DF','HX1053':'B09N9815DF','HX1820':'B09N9815DF','HX1821':'B09N9815DF','HX1599':'B09N9815DF','HX1352':'B09N9815DF','HX1026':'B0C3QMWY9K','HX1025':'B0C3QMWY9K','HX1027':'B0C3QMWY9K','HX1046':'B0C3QMWY9K','HX1819':'B0C3QMWY9K','HX1234':'B09G9RL5D3','HX1233':'B09G9RL5D3','HX1236':'B09G9RL5D3','HX1616':'B09G9RL5D3','HX1235':'B09G9RL5D3','HX1614':'B09G9RL5D3','HX1615':'B09G9RL5D3','HX2091':'B0FN7BFHQY','HX2089':'B0FN7BFHQY','HX2090':'B0FN7BFHQY'}
PNAMES = {'B09N9815DF':'330BHT(盒装)','B0C3QMWY9K':'瓶装BHT','B09G9RL5D3':'袋装BHT','B0FN7BFHQY':'蓝黄BHT'}
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

# ===== 1. Find all Lingxing exports and group by month =====
settle_files = glob.glob(os.path.join(DESKTOP, '*结算利润*.xlsx')) + glob.glob(os.path.join(SRC_DIR, '*结算利润*.xlsx'))
order_files = glob.glob(os.path.join(DESKTOP, '*订单利润*.xlsx')) + glob.glob(os.path.join(SRC_DIR, '*订单利润*.xlsx'))
product_files = glob.glob(os.path.join(DESKTOP, '*产品分析*.xlsx')) + glob.glob(os.path.join(DESKTOP, '*产品表现*.xlsx')) + glob.glob(os.path.join(SRC_DIR, '*产品分析*.xlsx')) + glob.glob(os.path.join(SRC_DIR, '*产品表现*.xlsx'))
# Exclude weekly source files (contain "周" in name)
product_files = [f for f in product_files if '周' not in os.path.basename(f)]

# Deduplicate product files
product_files = list(set(product_files))

# Extract month prefix from filename (e.g., "7月" from "7月 结算利润.xlsx")
def extract_month_prefix(fname):
    basename = os.path.basename(fname)
    # Match patterns like "5月", "6月", "7月", "5-6月", "七月" at start
    m = re.match(r'(\d{1,2})\s*月', basename)
    if m:
        return m.group(1)
    m = re.match(r'(\d{1,2})-(\d{1,2})\s*月', basename)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    # Chinese month names
    cn = {'一':'1','二':'2','三':'3','四':'4','五':'5','六':'6','七':'7','八':'8','九':'9','十':'10','十一':'11','十二':'12'}
    for k, v in cn.items():
        if basename.startswith(k):
            return v
    return None

# Group by month prefix
file_groups = {}
for f in settle_files:
    prefix = extract_month_prefix(f)
    if prefix:
        if prefix not in file_groups:
            file_groups[prefix] = {'settle': None, 'order': None, 'product': None}
        file_groups[prefix]['settle'] = f

for f in order_files:
    prefix = extract_month_prefix(f)
    if prefix and prefix in file_groups:
        file_groups[prefix]['order'] = f

for f in product_files:
    prefix = extract_month_prefix(f)
    if prefix and prefix in file_groups:
        file_groups[prefix]['product'] = f

# Filter: only process months with all 3 files
valid_months = {}
for prefix, files in file_groups.items():
    if files['settle'] and files['order'] and files['product']:
        valid_months[prefix] = files
        print(f"  {prefix}月: 结算+订单+产品 [OK]")
    else:
        missing = [k for k, v in files.items() if not v]
        print(f"  {prefix}月: 缺少{missing} [SKIP]")

if not valid_months:
    print("\n[!!] No complete month groups found. Need 3 files per month on Desktop.")
    sys.exit(1)

# ===== 2. Column mappings =====
S = {'日期':'周期','MSKU':'MSKU','ASIN':'ASIN','品名':'品名','SKU':'SKU','销量':'销量',
     '广告销量':'广告销量','销售额':'销售额','买家运费':'买家运费',
     '促销折扣':'促销折扣','平台费':'平台费','FBA发货费':'FBA配送费','广告费':'广告费',
     '推广费':'推广费','FBA仓储费':'FBA仓储费','入库配置费':'入库配置费',
     '采购成本':'采购成本','头程成本':'头程成本','合计成本':'总成本',
     '合计成本占比':'成本占比','毛利润':'毛利润','毛利率':'毛利率','收入退款额':'退款金额'}
O = {'毛利润':'订单毛利润','毛利率':'订单毛利率','总仓储费':'总仓储费','站外推广费':'站外推广费'}
A = {'父ASIN':'父ASIN','Sessions-Total':'会话数','大类排名':'大类排名','小类排名':'小类BSR',
     '订单量':'订单量','销售均价':'均价','净销售额':'净销售额','广告销售额':'广告销售额',
     '展示':'展示量','点击':'点击量',
     '自然点击量':'自然点击量','自然订单量':'自然订单量','SP广告费':'SP广告费',
     'SB广告费':'SB广告费','SBV广告费':'SBV广告费','ACOS':'ACOS','ROAS':'ROAS',
     'TACOS':'TACOS','CVR':'CVR','CPC':'CPC','CTR':'CTR','广告CVR':'广告CVR',
     '自然CVR':'自然CVR','退货率':'退货率'}

def n(v, d=0):
    try:
        if pd.isna(v): return d
        return float(str(v).replace(',','').replace('%','').replace('$',''))
    except: return d

def p(v):
    try:
        if pd.isna(v): return 'N/A'
        s = str(v)
        if '%' in s: return s
        f = float(s)
        return f"{f*100:.2f}%" if abs(f) < 1 else f"{f:.2f}%"
    except: return str(v)

# ===== 3. Process each month =====
for prefix, files in sorted(valid_months.items()):
    print(f"\n{'='*50}")
    print(f"Processing {prefix}月...")

    df_settle = pd.read_excel(files['settle'], skiprows=1)
    df_order = pd.read_excel(files['order'])
    df_asin = pd.read_excel(files['product'])

    date_range = str(df_settle.iloc[0, 0])
    m = re.search(r'(\d{4})-(\d{2})', date_range)
    if m:
        month_key = m.group(1) + m.group(2)
    else:
        month_key = pd.Timestamp.now().strftime('%Y%m')

    # If combined month (e.g., 5-6月), detect from prefix
    if '-' in prefix:
        # Combined month: use first month as key
        month_num = int(prefix.split('-')[0])
        month_key = f"{m.group(1)}{month_num:02d}" if m else pd.Timestamp.now().strftime('%Y') + f"{month_num:02d}"

    label = f"{int(month_key[4:6])}月"
    print(f"  Date: {date_range} -> month_key={month_key} ({label})")

    # Map columns
    st = df_settle[[c for c in S if c in df_settle.columns]].copy()
    st.rename(columns={k: v for k, v in S.items() if k in df_settle.columns}, inplace=True)
    od = df_order[[c for c in O if c in df_order.columns]].copy()
    od.rename(columns={k: v for k, v in O.items() if k in df_order.columns}, inplace=True)
    if 'SKU' in df_order.columns:
        od['SKU'] = df_order['SKU']
    an = df_asin[[c for c in A if c in df_asin.columns]].copy()
    an.rename(columns={k: v for k, v in A.items() if k in df_asin.columns}, inplace=True)
    if 'SKU' in df_asin.columns:
        an['SKU'] = df_asin['SKU']

    mg = st.merge(od[['SKU','订单毛利润','订单毛利率','总仓储费','站外推广费']], on='SKU', how='left')
    mg = mg.merge(an, on='SKU', how='left')
    mg = mg[mg['SKU'].isin(TARGET)]

    if '父ASIN' not in mg.columns or mg['父ASIN'].isna().all():
        mg['父ASIN'] = mg['SKU'].map(PMAP)

    # Build SKU data
    ASIN_ORDER = {'B09N9815DF':0,'B0C3QMWY9K':1,'B09G9RL5D3':2,'B0FN7BFHQY':3}
    skus = []
    for _, r in mg.iterrows():
        skus.append({
            'p': str(r.get('父ASIN', '')), 'sku': str(r.get('SKU', '')),
            'asin': SKU_ASINS.get(str(r.get('SKU', '')), str(r.get('ASIN', ''))),
            'name': str(r.get('品名', '')),
            'o': int(abs(n(r.get('销量', 0)))), 's': round(abs(n(r.get('销售额', 0)))),
            'ad': round(abs(n(r.get('广告费', 0)))),
            'ad_sales': round(abs(n(r.get('广告销售额', 0)))),
            'sessions': int(abs(n(r.get('会话数', 0)))),
            'acos': p(r.get('ACOS', 'N/A')),
            'tacos': p(r.get('TACOS', 'N/A')),
            'margin': p(r.get('订单毛利率', r.get('毛利率', 'N/A'))),
            'settle_margin': p(r.get('毛利率', 'N/A')),
            'bsr': str(r.get('小类BSR', '')), 'cvr': p(r.get('CVR', 'N/A')),
            'ad_cvr': p(r.get('广告CVR', 'N/A')),
            'nat_cvr': p(r.get('自然CVR', 'N/A')),
            'pf': round(n(r.get('毛利润', 0))),
            'fba': round(abs(n(r.get('FBA配送费', 0)))),
            'cogs': round(abs(n(r.get('采购成本', 0)))),
        })

    # Sort by parent ASIN order then by sales descending
    skus.sort(key=lambda x: (ASIN_ORDER.get(x['p'], 99), -x['s']))

    # Parent aggregation
    parents = {}
    for pid in ['B09N9815DF','B0C3QMWY9K','B09G9RL5D3','B0FN7BFHQY']:
        sub = [s for s in skus if s['p'] == pid]
        sa = sum(s['s'] for s in sub); ad = sum(s['ad'] for s in sub)
        ods = sum(s['o'] for s in sub); pf = sum(s['pf'] for s in sub)
        parents[pid] = {
            'name': PNAMES.get(pid, pid), 'n': len(sub),
            'o': ods, 's': sa, 'ad': ad, 'pf': pf,
            'margin': round(pf/sa*100, 2) if sa > 0 else 0,
            'tacos': round(ad/sa*100, 2) if sa > 0 else 0
        }

    TS = sum(p['s'] for p in parents.values())
    TA = sum(p['ad'] for p in parents.values())
    TAS = sum(s['ad_sales'] for s in skus)
    TSESS = sum(s['sessions'] for s in skus)
    TO = sum(p['o'] for p in parents.values())
    TP = sum(p['pf'] for p in parents.values())  # 结算利润的毛利润

    # ===== 结算利润总额 (from df_settle) =====
    settlement_profit = TP
    settlement_sales = TS
    settlement_margin = round(settlement_profit/settlement_sales*100, 2) if settlement_sales > 0 else 0

    # ===== 订单利润总额 (from df_order, filtered to TARGET) =====
    df_order_f = df_order[df_order[df_order.columns[3]].isin(TARGET)].copy()
    order_profit = sum(n(v) for v in df_order_f.iloc[:,5]) if '毛利润' in df_order_f.columns else sum(n(v) for v in df_order_f.iloc[:,5])
    # Try named columns first, fallback to position
    if '销售额' in df_order_f.columns:
        order_sales = sum(abs(n(v)) for v in df_order_f['销售额'])
    else:
        order_sales = sum(abs(n(v)) for v in df_order_f.iloc[:,12]) if df_order_f.shape[1] > 12 else TS
    order_margin = round(order_profit/order_sales*100, 2) if order_sales > 0 else 0

    # ===== 产品表现总额 (from df_asin, filtered to TARGET) =====
    df_product_f = df_asin[df_asin[df_asin.columns[3]].isin(TARGET)].copy() if df_asin.shape[1] > 3 else df_asin[df_asin['SKU'].isin(TARGET)].copy()
    if '订单量' in df_product_f.columns:
        product_orders = int(sum(abs(n(v)) for v in df_product_f['订单量']))
    else:
        product_orders = TO
    if '净销售额' in df_product_f.columns:
        product_sales = sum(abs(n(v)) for v in df_product_f['净销售额'])
    else:
        product_sales = TS
    if 'SP广告费' in df_product_f.columns:
        product_ad = sum(abs(n(v)) for v in df_product_f['SP广告费'])
        if 'SB广告费' in df_product_f.columns:
            product_ad += sum(abs(n(v)) for v in df_product_f['SB广告费'])
        if 'SBV广告费' in df_product_f.columns:
            product_ad += sum(abs(n(v)) for v in df_product_f['SBV广告费'])
    else:
        product_ad = TA

    # Alerts
    alerts = []
    for s in skus:
        try: mv = float(s['margin'].replace('%', ''))
        except: mv = 0
        if s['o'] > 500 and mv < 0:
            alerts.append({'l': 'red', 't': f"{s['sku']}({s['name']}) - 销量大但亏损",
                'd': f"月销{s['o']:,}单 · 销售额${s['s']:,} · 广告费${s['ad']:,} · TACoS {s['tacos']} · 毛利率{s['margin']}"})
        elif s['o'] <= 5 and s['ad'] > 50:
            alerts.append({'l': 'red', 't': f"{s['sku']}({s['name']}) - 几乎无单但广告持续烧钱",
                'd': f"月销{s['o']}单 · 广告费${s['ad']:,} · 建议立即暂停广告排查"})
        elif mv < -20:
            alerts.append({'l': 'red', 't': f"{s['sku']}({s['name']}) - 严重亏损{s['margin']}",
                'd': f"月销{s['o']:,}单 · 广告费${s['ad']:,} · 毛利率{s['margin']}"})

    # Cost breakdown
    TPF = abs(mg['平台费'].apply(lambda x: n(x)).sum()) if '平台费' in mg.columns else round(TS * 0.15)
    TFBA = abs(mg['FBA配送费'].apply(lambda x: n(x)).sum()) if 'FBA配送费' in mg.columns else 0
    TSTO = abs(mg['FBA仓储费'].apply(lambda x: n(x)).sum()) if 'FBA仓储费' in mg.columns else 0
    TINB = abs(mg['入库配置费'].apply(lambda x: n(x)).sum()) if '入库配置费' in mg.columns else 0
    TCOGS = abs(mg['采购成本'].apply(lambda x: n(x)).sum()) if '采购成本' in mg.columns else 0
    TFRT = abs(mg['头程成本'].apply(lambda x: n(x)).sum()) if '头程成本' in mg.columns else 0
    TPRM = abs(mg['促销折扣'].apply(lambda x: n(x)).sum()) if '促销折扣' in mg.columns else 0
    TREF = abs(mg['退款金额'].apply(lambda x: n(x)).sum()) if '退款金额' in mg.columns else 0

    # Cost breakdown - 5大类结构
    TPRM_V = round(TPRM); TREF_V = round(TREF); TAD_V = round(TA)
    cost_groups = [
        {'label':'商品成本',   'items':[{'label':'采购成本','value':round(TCOGS)},{'label':'头程成本','value':round(TFRT)}]},
        {'label':'平台交易费', 'items':[{'label':'FBA配送费','value':round(TFBA)},{'label':'平台佣金','value':round(TPF)}]},
        {'label':'营销费用',   'items':[{'label':'广告费','value':TAD_V}]},
        {'label':'库存费用',   'items':[{'label':'仓储+配置','value':round(TSTO+TINB)}]},
        {'label':'其他费用',   'items':[{'label':'促销折扣','value':TPRM_V},{'label':'退款','value':TREF_V}]},
        {'label':'净利润',     'items':[], 'isProfit':True},
    ]
    for g in cost_groups:
        if g.get('isProfit'): g['value'] = round(TP)
        else: g['value'] = sum(it['value'] for it in g['items'])

    # Also keep flat format for backward compat
    cost_labels = [it['label'] for g in cost_groups for it in g['items']] + ['净利润']
    cost_values = [it['value'] for g in cost_groups for it in g['items']] + [round(TP)]

    month_data = {
        'date': date_range, 'gen': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
        'monthKey': month_key, 'label': label,
        'total': {
            'margin': round(TP/TS*100, 2) if TS > 0 else 0, 'target': 8.0,
            'sales': TS, 'ad': TA, 'ad_sales': TAS, 'sessions': TSESS,
            'tacos': round(TA/TS*100, 2) if TS > 0 else 0,
            'orders': TO, 'profit': TP, 'gap': round(TS*0.08 - TP),
            'settlementMargin': settlement_margin,
            'settlementProfit': round(settlement_profit),
            'orderMargin': order_margin,
            'orderProfit': round(order_profit),
            'cvr': round(TO/TSESS*100, 2) if TSESS > 0 else 0
        },
        'parents': parents, 'skus': skus, 'alerts': alerts,
        'cost': {
            'groups': cost_groups,
            'labels': cost_labels,
            'values': cost_values
        }
    }

    # Save month file
    month_file = f'dashboard_data_{month_key}.json'
    with open(month_file, 'w', encoding='utf-8') as f:
        json.dump(month_data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {month_file} saved")
    print(f"  Sales: ${TS:,.0f} | Ad: ${TA:,.0f} | Margin: {month_data['total']['margin']:.2f}% | Orders: {TO:,}")

# ===== 4. Update all_months.json =====
all_months = {}
for fname in sorted(glob.glob('dashboard_data_*.json')):
    mk = fname.replace('dashboard_data_', '').replace('.json', '')
    with open(fname, 'r', encoding='utf-8') as f:
        all_months[mk] = json.load(f)
all_months = dict(sorted(all_months.items()))
with open('all_months.json', 'w', encoding='utf-8') as f:
    json.dump(all_months, f, ensure_ascii=False, indent=2)

print(f"\n[OK] all_months.json updated: {list(all_months.keys())}")
for mk, m in all_months.items():
    print(f"  {mk}: ${m['total']['sales']:,} | {m['total']['margin']}% | {m['total']['orders']:,} orders")

# ===== 5. Auto-build HTML =====
print("\nBuilding dashboard HTML...")
result = subprocess.run(['python3', os.path.join(DATA_DIR, 'build_html.py')], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("HTML build error:", result.stderr)
