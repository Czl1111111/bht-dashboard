"""Split combined 5-6月 Lingxing data into separate May & June months.
Distributes cost proportionally based on weekly sales ratio.
"""
import pandas as pd
import json, os, re, glob

DESKTOP = os.path.expanduser("~/Desktop")
DATA_DIR = os.path.join(os.path.expanduser("~"), "bht_data")
os.chdir(DATA_DIR)

# Load existing May & June data from gen_prev_months
with open('dashboard_data_202605.json', 'r', encoding='utf-8') as f:
    may_data = json.load(f)
with open('dashboard_data_202606.json', 'r', encoding='utf-8') as f:
    jun_data = json.load(f)

# Process 5-6月 Lingxing combined files for cost breakdown
f_settle = os.path.join(DESKTOP, '5-6月结算利润.xlsx')
f_order  = os.path.join(DESKTOP, '5-6月订单利润.xlsx')
f_asin   = os.path.join(DESKTOP, '5-6月-ASIN-产品分析.xlsx')

print("Reading combined 5-6月 Lingxing files...")
df_settle = pd.read_excel(f_settle, skiprows=1)
df_order  = pd.read_excel(f_order)
df_asin   = pd.read_excel(f_asin)

S = {'平台费':'平台费','FBA发货费':'FBA配送费','广告费':'广告费','FBA仓储费':'FBA仓储费',
     '入库配置费':'入库配置费','采购成本':'采购成本','头程成本':'头程成本',
     '促销折扣':'促销折扣','收入退款额':'退款金额'}

def n(v, d=0):
    try:
        if pd.isna(v): return d
        return float(str(v).replace(',','').replace('%','').replace('$',''))
    except: return d

TARGET = ['HX1822','HX1045','HX1053','HX1820','HX1821','HX1599','HX1352',
          'HX1026','HX1025','HX1027','HX1046','HX1819',
          'HX1234','HX1233','HX1236','HX1616','HX1235','HX1614','HX1615',
          'HX2091','HX2089','HX2090']

mg = df_settle[df_settle.iloc[:,3].isin(TARGET)] if df_settle.shape[1] > 3 else df_settle

# Extract cost columns
TPF = abs(mg['平台费'].apply(lambda x:n(x)).sum()) if '平台费' in mg.columns else 0
TFBA = abs(mg['FBA发货费'].apply(lambda x:n(x)).sum()) if 'FBA发货费' in mg.columns else 0
TAD = abs(mg['广告费'].apply(lambda x:n(x)).sum()) if '广告费' in mg.columns else 0
TSTO = abs(mg['FBA仓储费'].apply(lambda x:n(x)).sum()) if 'FBA仓储费' in mg.columns else 0
TINB = abs(mg['入库配置费'].apply(lambda x:n(x)).sum()) if '入库配置费' in mg.columns else 0
TCOGS = abs(mg['采购成本'].apply(lambda x:n(x)).sum()) if '采购成本' in mg.columns else 0
TFRT = abs(mg['头程成本'].apply(lambda x:n(x)).sum()) if '头程成本' in mg.columns else 0
TPRM = abs(mg.get('促销折扣', pd.Series([0])).apply(lambda x:n(x)).sum())
TREF = abs(mg.get('收入退款额', pd.Series([0])).apply(lambda x:n(x)).sum())

may_sales = may_data['total']['sales']  # 198,066
jun_sales = jun_data['total']['sales']  # 172,589
total_sales = may_sales + jun_sales  # 370,655
may_ratio = may_sales / total_sales
jun_ratio = jun_sales / total_sales

print(f"May sales: ${may_sales:,} ({may_ratio:.1%})")
print(f"Jun sales: ${jun_sales:,} ({jun_ratio:.1%})")

cost_labels = ['平台佣金','FBA配送费','广告费','采购成本','头程成本','仓储+配置','促销折扣','退款','净利润']

# Build cost for each month
def split_cost(ratio, profit):
    return {
        'labels': cost_labels,
        'values': [
            round(TPF * ratio), round(TFBA * ratio), round(TAD * ratio),
            round(TCOGS * ratio), round(TFRT * ratio),
            round((TSTO + TINB) * ratio), round(TPRM * ratio),
            round(TREF * ratio), round(profit)
        ],
        'source': 'proportional-from-combined'
    }

may_data['cost'] = split_cost(may_ratio, may_data['total']['profit'])
jun_data['cost'] = split_cost(jun_ratio, jun_data['total']['profit'])

# Save
with open('dashboard_data_202605.json', 'w', encoding='utf-8') as f:
    json.dump(may_data, f, ensure_ascii=False, indent=2)
with open('dashboard_data_202606.json', 'w', encoding='utf-8') as f:
    json.dump(jun_data, f, ensure_ascii=False, indent=2)

print(f"\n[OK] May cost: {[round(v) for v in may_data['cost']['values']]}")
print(f"[OK] Jun cost: {[round(v) for v in jun_data['cost']['values']]}")

# Update all_months
all_months = {}
for fname in sorted(glob.glob('dashboard_data_*.json')):
    mk = fname.replace('dashboard_data_','').replace('.json','')
    with open(fname, 'r', encoding='utf-8') as f:
        all_months[mk] = json.load(f)
all_months = dict(sorted(all_months.items()))
with open('all_months.json', 'w', encoding='utf-8') as f:
    json.dump(all_months, f, ensure_ascii=False, indent=2)

for mk, m in all_months.items():
    cost_note = '(有成本)' if m.get('cost') else '(无成本)'
    print(f"  {mk}: ${m['total']['sales']:,} | {m['total']['margin']}% {cost_note}")
