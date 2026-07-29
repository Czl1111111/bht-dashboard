"""Generate May & June monthly data by aggregating weekly_data.json."""
import json, os, glob

os.chdir(os.path.expanduser("~/bht_data"))

with open('weekly_data.json', 'r', encoding='utf-8') as f:
    wd = json.load(f)
weeks = wd['weeks']

months = {}
for key, w in weeks.items():
    yr = w['year']
    mo = w['month']
    if key == '2026_27':  # W27 spans Jun29-Jul5, assign to July (has real data)
        mo = 7
    mk = f'{yr}{mo:02d}'
    if mk not in months:
        months[mk] = []
    months[mk].append((key, w))

PMAP = {'HX1822':'B09N9815DF','HX1045':'B09N9815DF','HX1053':'B09N9815DF','HX1820':'B09N9815DF','HX1821':'B09N9815DF','HX1599':'B09N9815DF','HX1352':'B09N9815DF','HX1026':'B0C3QMWY9K','HX1025':'B0C3QMWY9K','HX1027':'B0C3QMWY9K','HX1046':'B0C3QMWY9K','HX1819':'B0C3QMWY9K','HX1234':'B09G9RL5D3','HX1233':'B09G9RL5D3','HX1236':'B09G9RL5D3','HX1616':'B09G9RL5D3','HX1235':'B09G9RL5D3','HX1614':'B09G9RL5D3','HX1615':'B09G9RL5D3','HX2091':'B0FN7BFHQY','HX2089':'B0FN7BFHQY','HX2090':'B0FN7BFHQY'}
PNAMES = {'B09N9815DF':'330BHT(盒装)','B0C3QMWY9K':'瓶装BHT','B09G9RL5D3':'袋装BHT','B0FN7BFHQY':'蓝黄BHT'}

# Skip months that already have real Lingxing data (with cost breakdown)
existing_real = set()
for fname in glob.glob('dashboard_data_*.json'):
    with open(fname, 'r', encoding='utf-8') as f:
        d = json.load(f)
    if d.get('cost') and not d.get('_source'):
        existing_real.add(fname.replace('dashboard_data_','').replace('.json',''))

for mk in sorted(months.keys()):
    if mk in existing_real:
        print(f'[SKIP] {mk} - already has real Lingxing data')
        continue
    mw = months[mk]
    yr = int(mk[:4]); mo = int(mk[4:6])
    label = f'{mo}月'

    all_dates = [w['dateRange'] for _, w in mw]
    dmin = min(d.split('~')[0].strip() for d in all_dates)
    dmax = max((d.split('~')[1] if '~' in d else d.split('~')[0]).strip() for d in all_dates)
    date_range = f'{dmin}~{dmax}'

    TS = sum(w['total']['sales'] for _, w in mw)
    TA = sum(w['total']['ad'] for _, w in mw)
    TO = sum(w['total']['orders'] for _, w in mw)
    TP = sum(w['total']['profit'] for _, w in mw)
    margin = round(TP/TS*100, 2) if TS > 0 else 0
    tacos = round(TA/TS*100, 2) if TS > 0 else 0

    parents = {}
    for pid in ['B09N9815DF','B0C3QMWY9K','B09G9RL5D3','B0FN7BFHQY']:
        ps = sum(w['parents'][pid]['s'] for _, w in mw if pid in w['parents'])
        po = sum(w['parents'][pid]['o'] for _, w in mw if pid in w['parents'])
        pa = sum(w['parents'][pid]['ad'] for _, w in mw if pid in w['parents'])
        pp = sum(w['parents'][pid]['pf'] for _, w in mw if pid in w['parents'])
        parents[pid] = {
            'name': PNAMES.get(pid, pid),
            'n': sum(1 for _, w in mw if pid in w['parents']),
            'o': po, 's': ps, 'ad': pa, 'pf': pp,
            'margin': round(pp/ps*100, 2) if ps > 0 else 0,
            'tacos': round(pa/ps*100, 2) if ps > 0 else 0
        }
    # Fix n to be unique SKU count per parent
    pid_sku_counts = {'B09N9815DF': 7, 'B0C3QMWY9K': 5, 'B09G9RL5D3': 7, 'B0FN7BFHQY': 3}
    for pid in parents:
        parents[pid]['n'] = pid_sku_counts.get(pid, parents[pid]['n'])

    # Aggregate SKUs across weeks
    sku_map = {}
    for _, w in mw:
        for s in w['skus']:
            sku = s['sku']
            if sku not in sku_map:
                sku_map[sku] = {
                    'p': s['p'], 'sku': sku, 'name': s['name'],
                    'o': 0, 's': 0, 'ad': 0, 'pf': 0,
                    'bsr_vals': [], 'cvr_sum': 0, 'cvr_wt': 0,
                    'ret_sum': 0, 'ret_wt': 0
                }
            e = sku_map[sku]
            e['o'] += s['o']; e['s'] += s['s']; e['ad'] += s['ad']; e['pf'] += s['pf']
            try:
                b = int(s['bsr']) if s.get('bsr','N/A') != 'N/A' else None
                if b and b > 0: e['bsr_vals'].append(b)
            except: pass
            try:
                cv = float(s.get('cvr','N/A').replace('%','')) if s.get('cvr','N/A') != 'N/A' else 0
                if cv > 0 and s['o'] > 0:
                    e['cvr_sum'] += cv * s['o']; e['cvr_wt'] += s['o']
            except: pass
            try:
                rv = float(s.get('ret','N/A').replace('%','')) if s.get('ret','N/A') != 'N/A' else 0
                if s['o'] > 0:
                    e['ret_sum'] += rv * s['o']; e['ret_wt'] += s['o']
            except: pass

    skus = []
    for sku, e in sku_map.items():
        m = round(e['pf']/e['s']*100, 2) if e['s'] > 0 else 0
        t = round(e['ad']/e['s']*100, 2) if e['s'] > 0 else 0
        bsr = str(min(e['bsr_vals'])) if e['bsr_vals'] else 'N/A'
        cvr = f"{round(e['cvr_sum']/e['cvr_wt'], 2):.2f}%" if e['cvr_wt'] > 0 else 'N/A'
        ret = f"{round(e['ret_sum']/e['ret_wt'], 2):.2f}%" if e['ret_wt'] > 0 else 'N/A'
        skus.append({
            'p': e['p'], 'sku': sku, 'name': e['name'],
            'o': e['o'], 's': e['s'], 'ad': e['ad'], 'pf': e['pf'],
            'margin': f'{m:.2f}%',
            'acos': 'N/A', 'tacos': f'{t:.2f}%' if t > 0 else 'N/A',
            'bsr': bsr, 'cvr': cvr, 'ret': ret,
        })
    skus.sort(key=lambda x: x['s'], reverse=True)

    # Alerts
    alerts = []
    for s in skus:
        try: mv = float(s['margin'].replace('%',''))
        except: mv = 0
        if s['o'] > 400 and mv < 0:
            alerts.append({'l':'red','t':f"{s['sku']}({s['name']}) - 月销量大但亏损",
                'd':f"月销{s['o']:,}单 - 销售额${s['s']:,} - 广告费${s['ad']:,} - TACoS {s['tacos']} - 毛利率{s['margin']}"})
        elif s['o'] <= 3 and s['ad'] > 30:
            alerts.append({'l':'red','t':f"{s['sku']}({s['name']}) - 几乎无单但广告持续烧钱",
                'd':f"月销{s['o']}单 - 广告费${s['ad']:,} - 建议立即暂停广告排查"})

    month_data = {
        'date': date_range, 'gen': '2026-07-28 (from weekly data)',
        'monthKey': mk, 'label': label,
        'total': {
            'margin': margin, 'target': 8.0,
            'sales': TS, 'ad': TA, 'tacos': tacos,
            'orders': TO, 'profit': TP,
            'gap': round(TS*0.08 - TP)
        },
        'parents': parents, 'skus': skus, 'alerts': alerts,
        'cost': None,  # No cost breakdown from weekly source
        '_source': 'weekly_aggregate'
    }

    fname = f'dashboard_data_{mk}.json'
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(month_data, f, ensure_ascii=False, indent=2)
    print(f'[OK] {fname}: {label} | Sales=${TS:,} | Margin={margin}% | {TO:,} orders | {len(skus)} SKUs')

# Update cumulative all_months.json
all_months = {}
for fname in sorted(glob.glob('dashboard_data_*.json')):
    mk = fname.replace('dashboard_data_','').replace('.json','')
    with open(fname, 'r', encoding='utf-8') as f:
        all_months[mk] = json.load(f)
all_months = dict(sorted(all_months.items()))
with open('all_months.json', 'w', encoding='utf-8') as f:
    json.dump(all_months, f, ensure_ascii=False, indent=2)
print(f'\n[OK] all_months.json: {list(all_months.keys())}')
for mk, m in all_months.items():
    cost_note = '(有成本明细)' if m.get('cost') else '(无成本明细-周数据汇总)'
    print(f'  {mk} ({m["label"]}): {m["date"]} | ${m["total"]["sales"]:,} | {m["total"]["margin"]}% {cost_note}')
