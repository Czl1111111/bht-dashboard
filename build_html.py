"""
Build Weekly_Dashboard.html - Tab-based multi-month dashboard.
Reads all_months.json + weekly_data.json, outputs to Desktop.
Pattern matches index.html (simple tab switching).
"""
import json, os
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.expanduser("~"), "bht_data")
DESKTOP = os.path.expanduser("~/Desktop")
os.chdir(DATA_DIR)

with open('all_months.json', 'r', encoding='utf-8') as f:
    ALL_MONTHS = json.load(f)

try:
    with open('weekly_data.json', 'r', encoding='utf-8') as f:
        WD = json.load(f)
    weekly_weeks = WD.get('weeks', {})
except:
    weekly_weeks = {}

# ===== Build WEEKS array =====
WEEKS = []

for mk in sorted(ALL_MONTHS.keys()):
    md = ALL_MONTHS[mk]
    yr = int(mk[:4])
    mo = int(mk[4:6])
    label = md.get('label', f'{mo}月')

    def get_month_weeks(year, month):
        weeks = []
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        start_week = first_day.isocalendar()[1]
        end_week = last_day.isocalendar()[1]
        start_year = first_day.isocalendar()[0]
        end_year = last_day.isocalendar()[0]
        wk = start_week
        wy = start_year
        while True:
            monday = datetime.strptime(f'{wy}-{wk}-1', '%G-%V-%u')
            sunday = monday + timedelta(days=6)
            if not (sunday < first_day or monday > last_day):
                weeks.append({
                    'year': wy, 'week': wk,
                    'mon': monday.strftime('%m/%d'),
                    'sun': sunday.strftime('%m/%d'),
                    'key': f'{wy}_{wk:02d}',
                })
            if wk == end_week and wy == end_year:
                break
            wk += 1
            if wk > 52:
                wk = 1
                wy += 1
        return weeks

    cal = get_month_weeks(yr, mo)
    for i, cw in enumerate(cal):
        wk_key = cw['key']
        has_real = wk_key in weekly_weeks
        wk_id = f'w{mk}_{i+1}'
        sub = f'{cw["mon"]}-{cw["sun"]}'

        partial = False
        if has_real:
            wdata = weekly_weeks[wk_key]
            dr = wdata.get('dateRange', '')
            if '~' in dr:
                parts = dr.split('~')
                if len(parts) == 2:
                    try:
                        d1 = datetime.strptime(parts[0].strip(), '%Y-%m-%d')
                        d2 = datetime.strptime(parts[1].strip(), '%Y-%m-%d')
                        partial = (d2 - d1).days < 6
                    except:
                        pass

        WEEKS.append({
            'id': wk_id,
            'label': f'{mo}月W{i+1}',
            'sub': sub,
            'monthKey': mk,
            'wkKey': wk_key,
            'hasReal': has_real,
            'partial': partial,
            'est': False,
            'ratio': None,
        })

    # Month summary tab
    WEEKS.append({
        'id': f'month_{mk}',
        'label': f'{label}汇总',
        'sub': md.get('date', ''),
        'monthKey': mk,
        'wkKey': None,
        'hasReal': True,
        'partial': False,
        'est': False,
        'ratio': 1,
    })

# Deduplicate
seen = set()
deduped = []
for w in WEEKS:
    if w['id'] not in seen:
        seen.add(w['id'])
        deduped.append(w)
WEEKS = deduped

# First month tab as default
first_month = next((w for w in WEEKS if w['id'].startswith('month_')), WEEKS[-1])
default_tab = first_month['id']

# ===== Build data JSON strings =====
months_json = json.dumps(ALL_MONTHS, ensure_ascii=False)
weeks_json = json.dumps(WEEKS, ensure_ascii=False)
weekly_json = json.dumps(WD, ensure_ascii=False)

# ===== Build todo week options =====
todo_week_opts = ''
for w in WEEKS:
    if not w['id'].startswith('month_'):
        todo_week_opts += '<option value="' + w['id'] + '">' + w['sub'] + '</option>\n'

# ===== Build month-week separator positions for tab nav =====
# We need to know which week indices need separators between months
month_boundaries = []
last_mo = None
for i, w in enumerate(WEEKS):
    if not w['id'].startswith('month_'):
        if last_mo is not None and w['monthKey'] != last_mo:
            month_boundaries.append(i)
        last_mo = w['monthKey']

# ===== HTML Template parts =====
# Use %% as placeholder for where JSON data gets injected
# The JS code uses regular single quotes; Python will inject data via .replace()

CSS = '''*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:#0f1119;color:#e1e4ea;line-height:1.6;padding:16px}
/* Allow text selection on all data areas */
.kpi-card,.alert-item,.table-wrap td,.table-wrap th,.cost-table td,.cost-table th,.chart-panel h3,.badge{user-select:text;-webkit-user-select:text}
.kpi-card .val{cursor:text}.kpi-card .sub{cursor:text}.kpi-card .lbl{cursor:default}.alert-item .at{cursor:text}.alert-item .ad{cursor:text}
.todo-item .todo-text{user-select:text;-webkit-user-select:text;cursor:text}
.hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:10px}
.hdr h1{font-size:22px;font-weight:700;color:#fff}
.badge{background:#1e2030;border:1px solid #2a2d3e;border-radius:8px;padding:5px 12px;font-size:12px;color:#8b90a0}
.tab-nav{display:flex;gap:3px;margin-bottom:4px;background:#161822;border-radius:10px;padding:3px;width:fit-content;flex-wrap:wrap;max-width:100%}
.tab-btn{padding:6px 13px;border:none;background:transparent;color:#8b90a0;cursor:pointer;border-radius:7px;font-size:11px;font-weight:500;transition:all 0.15s;white-space:nowrap}
.tab-btn.active{background:#7c3aed;color:#fff}
.tab-btn:hover:not(.active){color:#fff;background:#1e2030}
.tab-btn small{display:block;font-size:9px;opacity:0.7;line-height:1.2}
.tab-sep{width:1px;background:#2a2d3e;margin:2px 4px}
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
@media(max-width:900px){.kpi-row{grid-template-columns:repeat(2,1fr)}}
.kpi-card{background:#161822;border:1px solid #232638;border-radius:10px;padding:14px 16px;position:relative}
.kpi-card .lbl{font-size:10px;color:#8b90a0;text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px}
.kpi-card .val{font-size:24px;font-weight:700;color:#fff}
.kpi-card .sub{font-size:11px;margin-top:2px}
.g{color:#22c55e}.r{color:#ef4444}.y{color:#f59e0b}.n{color:#8b90a0}
.dot{position:absolute;top:10px;right:12px;width:7px;height:7px;border-radius:50%}
.dg{background:#22c55e;box-shadow:0 0 6px #22c55e88}
.dr{background:#ef4444;box-shadow:0 0 6px #ef444488}
.dy{background:#f59e0b;box-shadow:0 0 6px #f59e0b88}
.dn{background:#6b7280;box-shadow:0 0 6px #6b728088}
.charts-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:12px;margin-bottom:14px}
.chart-panel{background:#161822;border:1px solid #232638;border-radius:10px;padding:16px;min-width:320px}
.chart-panel h3{font-size:13px;color:#fff;margin-bottom:12px;font-weight:600}
@media(max-width:900px){.charts-row{display:flex;flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;scroll-snap-type:x mandatory;padding-bottom:6px}.charts-row::-webkit-scrollbar{height:4px}.charts-row::-webkit-scrollbar-thumb{background:#2a2d3e;border-radius:2px}.chart-panel{flex:0 0 85vw;scroll-snap-align:start}}
canvas{max-height:300px}
.section-title{font-size:15px;font-weight:700;color:#fff;margin:16px 0 10px}
.alert-item{background:#1a1c2a;border-left:4px solid #ef4444;border-radius:0 10px 10px 0;padding:10px 14px;margin-bottom:6px;display:flex;gap:8px;align-items:flex-start}
.alert-item.warn{border-left-color:#f59e0b}
.alert-item .ai{font-size:15px;flex-shrink:0}
.alert-item .at{font-weight:600;color:#fff;margin-bottom:1px;font-size:13px}
.alert-item .ad{font-size:11px;color:#8b90a0}
.table-wrap{background:#161822;border:1px solid #232638;border-radius:10px;overflow:hidden;margin-bottom:16px}
.table-scroll{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:11px;white-space:nowrap}
thead th{background:#1e2030;color:#8b90a0;font-weight:600;padding:8px 9px;text-align:left;position:sticky;top:0}
tbody td{padding:6px 9px;border-bottom:1px solid #1e2030}
tbody tr:hover{background:#1a1c2a}
.subtot td{font-weight:700;background:#1a1c2a;border-top:2px solid #232638}
.tag{display:inline-block;padding:2px 6px;border-radius:4px;font-size:9px;font-weight:600}
.tgr{background:#ef444420;color:#ef4444}.tgg{background:#22c55e20;color:#22c55e}.tgy{background:#f59e0b20;color:#f59e0b}
.hx-section{background:linear-gradient(135deg,#1a1040,#161822);border:1px solid #7c3aed40;border-radius:10px;padding:16px;margin-bottom:16px}
.hx-section h3{color:#a78bfa;margin-bottom:10px;font-size:15px}
.plan-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:7px}
.plan-item{background:#16182288;border:1px solid #2a2d3e;border-radius:8px;padding:10px}
.plan-item .pp{font-size:9px;font-weight:700;margin-bottom:2px}
.plan-item .pt{font-size:12px;font-weight:600;color:#fff;margin-bottom:2px}
.plan-item .pi{font-size:16px;font-weight:700;color:#22c55e;margin-bottom:2px}
.plan-item .pd{font-size:10px;color:#8b90a0}
/* === BHTZ-style Todos === */
.todo-wrap{margin-bottom:18px}
.todo-wrap h4{font-size:13px;color:#fff;margin:0 0 6px 0;font-weight:700}
.todo-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.todo-hdr h4{margin:0}.todo-fold-btn{font-size:10px;padding:2px 8px;border-radius:4px;border:1px solid #2a2d3e;background:#1e2030;color:#8b90a0;cursor:pointer;font-family:inherit}.todo-fold-btn:hover{color:#fff;border-color:#7c3aed}
.todo-filters{display:flex;gap:4px;margin-bottom:8px;flex-wrap:wrap}
.todo-filters button{font-size:10px;padding:3px 9px;border-radius:5px;border:1px solid #2a2d3e;background:#1e2030;color:#8b90a0;cursor:pointer;font-family:inherit;transition:all .15s}
.todo-filters button:hover{background:#232638;color:#fff}
.todo-filters button.act{background:#7c3aed20;color:#a78bfa;border-color:#7c3aed}
.todo-list{display:flex;flex-direction:column;gap:3px}
.todo-item{display:flex;align-items:center;gap:5px;background:#1a1c2a;border:1px solid #1e2030;border-radius:6px;padding:5px 7px;transition:all .15s}
.todo-item:hover{border-color:#2a2d3e}
.todo-item.lv-0{padding-left:7px}
.todo-item.lv-1{padding-left:24px}
.todo-item.lv-2{padding-left:42px}
.todo-item.lv-urgent{border-left:3px solid #ef4444}
.todo-item.lv-important{border-left:3px solid #f59e0b}
.todo-item.lv-normal{border-left:3px solid #22c55e}
.todo-item.drag-ghost{opacity:.35}
.todo-item.drag-above{border-top:2px solid #7c3aed}
.todo-item.drag-below{border-bottom:2px solid #7c3aed}
.todo-item .grip{cursor:grab;color:#4a4d5e;font-size:10px;padding:0 2px;user-select:none;letter-spacing:-1px;line-height:1;opacity:.4;flex-shrink:0}
.todo-item .grip:hover{opacity:.8}
.todo-item .grip:active{cursor:grabbing}
.todo-item .fold-tgl{flex-shrink:0;cursor:pointer;font-size:9px;padding:0 2px;color:#6b7280;width:12px;text-align:center;line-height:1;user-select:none;border:none;background:none;font-family:inherit}
.todo-item .fold-tgl:hover{color:#fff}
.todo-item .fold-spacer{flex-shrink:0;width:12px}
.todo-item .lv-btn{font-size:9px;padding:2px 4px;border-radius:3px;border:1px solid #2a2d3e;background:#161822;cursor:pointer;font-family:inherit;white-space:nowrap;flex-shrink:0;transition:all .15s}
.todo-item .lv-btn:hover{opacity:.8}
.todo-item .lv-btn.urgent{color:#ef4444;border-color:#ef444466}
.todo-item .lv-btn.important{color:#f59e0b;border-color:#f59e0b66}
.todo-item .lv-btn.normal{color:#22c55e;border-color:#22c55e66}
.todo-item .todo-text{flex:1;font-size:11px;color:#e2e4ea;outline:none;padding:2px 4px;border-radius:3px;min-width:0;word-break:break-word}
.todo-item .todo-text:focus{background:#161822}
.todo-item .todo-text:empty:before{content:'点击输入...';color:#4a4d5e}
.todo-item .sub-btn{flex-shrink:0;cursor:pointer;font-size:9px;padding:2px 4px;border-radius:3px;border:1px solid #2a2d3e;background:#161822;color:#6b7280;font-family:inherit;white-space:nowrap}
.todo-item .sub-btn:hover{color:#a78bfa;border-color:#7c3aed}
.todo-item .del-btn{font-size:11px;cursor:pointer;color:#6b7280;padding:2px 4px;border:none;background:none;flex-shrink:0;opacity:.4;line-height:1}
.todo-item .del-btn:hover{opacity:1;color:#ef4444}
.todo-item .child-count{font-size:9px;color:#6b7280}
.todo-add-wrap{margin-top:6px}
.todo-add-wrap button{font-size:11px;padding:5px 12px;border-radius:5px;border:1px dashed #2a2d3e;background:transparent;color:#8b90a0;cursor:pointer;font-family:inherit;width:100%;text-align:center;transition:all .15s}
.todo-add-wrap button:hover{background:#1e2030;color:#fff;border-color:#7c3aed}
.foot{text-align:center;color:#4a4d5e;font-size:10px;margin-top:16px;padding:10px}
.section-wrap{background:#161822;border:1px solid #232638;border-radius:10px;margin-bottom:12px;overflow:hidden}
.section-wrap.dragging{opacity:0.5;border-color:#7c3aed}
.section-wrap.drag-over{border-color:#7c3aed;box-shadow:0 0 12px #7c3aed40}
.section-header{display:flex;align-items:center;gap:6px;padding:10px 14px;background:#1e2030;cursor:default;user-select:none}
.section-header .section-title{font-size:14px;font-weight:700;color:#fff;margin:0;flex:1}
.drag-handle{cursor:grab;color:#4a4d5e;font-size:16px;padding:2px 4px;line-height:1;transition:color 0.15s}
.drag-handle:hover{color:#a78bfa}
.drag-handle:active{cursor:grabbing}
.section-toggle{background:none;border:none;color:#8b90a0;cursor:pointer;font-size:12px;padding:2px 4px;transition:all 0.15s;line-height:1;width:20px;text-align:center}
.section-toggle:hover{color:#fff}
.section-toggle.collapsed{transform:rotate(-90deg)}
.section-body{transition:all 0.2s ease}
.section-body.collapsed{display:none}
.collapse-all-btn{background:#1e2030;border:1px solid #2a2d3e;border-radius:6px;color:#8b90a0;cursor:pointer;font-size:10px;padding:4px 10px;transition:all 0.15s;white-space:nowrap}
.collapse-all-btn:hover{color:#fff;border-color:#7c3aed}
.cost-tabs{display:flex;gap:3px}
.cost-tab-btn{background:#1e2030;border:1px solid #2a2d3e;border-radius:4px;color:#8b90a0;cursor:pointer;font-size:10px;padding:3px 10px;transition:all 0.15s;font-family:inherit}
.cost-tab-btn:hover{color:#fff;border-color:#7c3aed}
.cost-tab-btn.active{color:#fff;border-color:#7c3aed;background:#7c3aed22}
.cost-chart-wrap{width:100%;height:220px;margin-bottom:8px}
.cost-table-wrap{max-height:360px;overflow-y:auto}
.cost-table{width:100%;border-collapse:collapse;font-size:11px;font-variant-numeric:tabular-nums}
.cost-table th{text-align:left;color:#8b90a0;font-weight:600;padding:5px 10px;border-bottom:1px solid #232638;font-size:10px;position:sticky;top:0;background:#161822;z-index:1}
.cost-table td{padding:5px 10px;border-bottom:1px solid #1a1c2a}
.cost-table tr:hover td{background:#1e203040}
.cost-bar-outer{display:inline-block;width:70px;height:5px;background:#1e2030;border-radius:3px;vertical-align:middle;margin-left:6px;overflow:hidden}
.cost-bar-inner{height:100%;border-radius:3px;transition:width 0.3s}
.cost-empty{color:#8b90a0;font-size:12px;padding:16px;text-align:center}'''

# JavaScript template - use __DATA_PLACEHOLDER__ markers for injection
JS_TEMPLATE = r'''
// ===== DATA =====
var MONTHS_DATA = __MONTHS_DATA__;
var WEEKLY_DATA = __WEEKLY_DATA__;
var WEEKS = __WEEKS__;
var DEFAULT_TAB = "__DEFAULT_TAB__";
var MONTH_BOUNDARIES = __MONTH_BOUNDARIES__;

// ===== STATE =====
var curTab = DEFAULT_TAB;

// ===== TODO SYSTEM (BHTZ-style, dual week/month) =====
var weekTodos=[], monthTodos=[];
var weekTodoFilter='all', monthTodoFilter='all';

function tLoad(k){try{return JSON.parse(localStorage.getItem(k)||'[]')}catch(e){return[]}}
function tSave(k,d){try{localStorage.setItem(k,JSON.stringify(d))}catch(e){}}
function tMaxId(arr){var m=0;function w(a){for(var i=0;i<a.length;i++){if(a[i].id>m)m=a[i].id;if(a[i].children)w(a[i].children)}}w(arr);return m}
function tFind(arr,id){for(var i=0;i<arr.length;i++){if(arr[i].id===id)return{item:arr[i],parent:arr,index:i};if(arr[i].children&&arr[i].children.length>0){var f=tFind(arr[i].children,id);if(f)return f}}return null}
function tDescendant(arr,aid,cid){var f=tFind(arr,aid);if(!f||!f.item.children)return false;for(var i=0;i<f.item.children.length;i++){if(f.item.children[i].id===cid)return true;if(tDescendant(f.item.children,f.item.children[i].id,cid))return true}return false}

function tFoldAll(arr,collapsed){for(var i=0;i<arr.length;i++){arr[i].collapsed=collapsed;if(arr[i].children&&arr[i].children.length)tFoldAll(arr[i].children,collapsed)}}
function toggleTodoFold(type,expand){var list=type==='week'?weekTodos:monthTodos;var key=type==='week'?'bht_week_todos_v2':'bht_month_todos_v2';tFoldAll(list,!expand);tSave(key,list);renderAllTodos()}
function tFlatten(arr,level,filt){
  var r=[];for(var i=0;i<arr.length;i++){var t=arr[i];var self=(filt==='all'||t.priority===filt);if(self)r.push({id:t.id,text:t.text,priority:t.priority,level:level,hasChildren:!!(t.children&&t.children.length>0),collapsed:!!t.collapsed,childCount:t.children?t.children.length:0});if(t.children&&t.children.length>0&&!t.collapsed){var k=tFlatten(t.children,level+1,filt);for(var j=0;j<k.length;j++)r.push(k[j])}}return r}

function genDefaults(isMonth,wd){
  var items=[];
  // For weekly todos, use previous week's data if available
  var prevLabel='';
  if(!isMonth&&window._prevWd&&window._prevWd.skus){
    wd=window._prevWd;
    prevLabel=window._prevWeekLabel||'上周';
  }
  if(!wd||!wd.skus) return items;
  var skus=wd.skus.slice();

  // Sort by priority: negative margin first, then high ACOS, then low CVR
  var urgent=[], important=[], normal=[];
  skus.forEach(function(s){
    var m=parseFloat(s.margin)||0, a=parseFloat(s.acos)||0, c=parseFloat(s.cvr)||0, ad=s.ad||0, o=s.o||0;
    var prefix=isMonth?'月度':'上周';
    if(m<0) urgent.push({sku:s.sku,name:s.name||s.sku,margin:m,acos:a,cvr:c,ad:ad,orders:o});
    else if(m<5||a>35) important.push({sku:s.sku,name:s.name||s.sku,margin:m,acos:a,cvr:c,ad:ad,orders:o});
    else if(c<12) normal.push({sku:s.sku,name:s.name||s.sku,margin:m,acos:a,cvr:c,ad:ad,orders:o});
  });

  var id=isMonth?2000:1000;
  function add(arr,prio,prefix,items){
    items.forEach(function(x){
      var txt='';var sub=[];
      if(x.margin<0){txt=prefix+' '+x.sku+'('+x.name+') 亏损 '+x.margin.toFixed(1)+'% - 排查原因并优化';sub.push({id:++id,text:'分析成本构成: 采购/FBA/广告占比',priority:prio,children:[]});sub.push({id:++id,text:'对比竞品价格,判断提价空间',priority:prio,children:[]});}
      else if(x.acos>35){txt=prefix+' '+x.sku+' 广告ACoS '+x.acos.toFixed(1)+'%过高 - 优化广告投放';sub.push({id:++id,text:'筛选ACoS>40%关键词降bid或否定',priority:prio,children:[]});}
      else if(x.cvr<12){txt=prefix+' '+x.sku+' CVR仅'+x.cvr.toFixed(1)+'% - Listing优化提转化';sub.push({id:++id,text:'检查主图/标题/五点/A+页面',priority:prio,children:[]});}
      else {txt=prefix+' '+x.sku+' 利润率偏低 '+x.margin.toFixed(1)+'% - 持续关注';}
      arr.push({id:++id,text:txt,priority:prio,children:sub,collapsed:false});
    });
  }
  add(items,'urgent',isMonth?'月度-紧急':'上周-紧急',urgent);
  add(items,'important',isMonth?'月度-重要':'上周-重要',important);
  if(!isMonth) normal.forEach(function(x){items.push({id:++id,text:'上周-普通 '+x.sku+' CVR仅'+x.cvr.toFixed(1)+'% - Listing优化提转化',priority:'normal',children:[{id:++id,text:'检查主图/标题/五点/A+页面',priority:'normal',children:[]}]})});
  var pfx=isMonth?'月度':'上周';
  var srcNote=prevLabel?' (数据来源:'+prevLabel+')':'';
  items.push({id:++id,text:pfx+' 整体目标: 利润率达8% (上周'+wd.total.margin.toFixed(1)+'%)'+srcNote,priority:'urgent',children:[
    {id:++id,text:'审查广告预算分配,控制TACoS',priority:'urgent',children:[]},
    {id:++id,text:'排查高退款率SKU,优化品质/包装',priority:'important',children:[]}
  ],collapsed:false});
  if(isMonth){
    items.push({id:++id,text:'8月规划: 补货计划(检查库存覆盖天数)',priority:'important',children:[]});
    items.push({id:++id,text:'8月目标: 保持BSR排名,利润率冲刺9%',priority:'normal',children:[]});
  }
  return items;
}

function renderTodoFilters(containerId,filter,storageKey,todos){
  var el=document.getElementById(containerId);if(!el)return;
  var filters=['all','urgent','important','normal'];
  var labels={all:'全部',urgent:'🔴 紧急',important:'🟡 重要',normal:'🟢 普通'};
  var h='';filters.forEach(function(f){h+='<button class=\"'+(filter===f?'act':'')+'\" data-tf=\"'+f+'\">'+labels[f]+'</button>'});
  el.innerHTML=h;
  el.querySelectorAll('button').forEach(function(b){b.onclick=function(){var nf=this.dataset.tf;if(filter===nf)return;
    if(containerId==='weekTodoFilters'){weekTodoFilter=nf;renderAllTodos()}else{monthTodoFilter=nf;renderAllTodos()}
  }});
}

function renderTodoList(listId,todos,filter){
  var el=document.getElementById(listId);if(!el)return'';
  var flat=tFlatten(todos,0,filter);
  var h='';flat.forEach(function(t){
    h+='<div class=\"todo-item lv-'+t.level+' lv-'+t.priority+'\" data-tid=\"'+t.id+'\" data-tl=\"'+t.level+'\">';
    h+='<span class=\"grip\" draggable=\"true\">⠿</span>';
    if(t.hasChildren) h+='<button class=\"fold-tgl\" data-action=\"fold\" data-tid=\"'+t.id+'\">'+(t.collapsed?'▶':'▼')+'</button>';
    else h+='<span class=\"fold-spacer\"></span>';
    var lvLabel=t.priority==='urgent'?'🔴':(t.priority==='important'?'🟡':'🟢');
    h+='<button class=\"lv-btn '+t.priority+'\" data-action=\"prio\" data-tid=\"'+t.id+'\">'+lvLabel+'</button>';
    h+='<div class=\"todo-text\" contenteditable=\"true\" data-action=\"edit\" data-tid=\"'+t.id+'\">'+eText(t.text)+'</div>';
    if(t.childCount) h+='<span class=\"child-count\">'+t.childCount+'子</span>';
    h+='<button class=\"sub-btn\" data-action=\"child\" data-tid=\"'+t.id+'\">+子</button>';
    h+='<button class=\"del-btn\" data-action=\"del\" data-tid=\"'+t.id+'\">✕</button>';
    h+='</div>';
  });
  el.innerHTML=h||'<div style=\"text-align:center;color:#6b7280;padding:12px\">暂无待办，点击下方添加</div>';
}

function eText(t){return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function dText(t){var d=document.createElement('div');d.innerHTML=t;return d.textContent}

function attachTodoEvents(listId,todosRef,storageKey){
  var list=document.getElementById(listId);if(!list)return;

  // Click handlers
  list.addEventListener('click',function(e){
    var tgt=e.target,act=tgt.dataset.action;
    if(!act) return;
    var id=parseInt(tgt.dataset.tid);
    if(act==='fold'){
      var f=tFind(todosRef,id);if(f){f.item.collapsed=!f.item.collapsed;tSave(storageKey,todosRef);renderAllTodos()}
    } else if(act==='prio'){
      var f=tFind(todosRef,id);if(f){var p=f.item.priority;f.item.priority=p==='urgent'?'important':(p==='important'?'normal':'urgent');tSave(storageKey,todosRef);renderAllTodos()}
    } else if(act==='del'){
      var f=tFind(todosRef,id);if(f){f.parent.splice(f.index,1);tSave(storageKey,todosRef);renderAllTodos()}
    } else if(act==='child'){
      var f=tFind(todosRef,id);if(f){if(!f.item.children)f.item.children=[];var nid=tMaxId(todosRef)+1;f.item.children.push({id:nid,text:'',priority:f.item.priority,children:[],collapsed:false});f.item.collapsed=false;tSave(storageKey,todosRef);renderAllTodos();setTimeout(function(){var it=document.querySelector('#'+listId+' .todo-text[data-tid=\"'+nid+'\"]');if(it)it.focus()},50)}
    }
  });

  // Text edit (blur save)
  list.addEventListener('blur',function(e){
    if(e.target.classList.contains('todo-text')){
      var id=parseInt(e.target.dataset.tid);
      var f=tFind(todosRef,id);
      if(f){f.item.text=dText(e.target.innerText)||f.item.text;tSave(storageKey,todosRef)}
    }
  },true);

  // Keyboard: Enter=new sibling below, Backspace on empty=outdent/delete
  list.addEventListener('keydown',function(e){
    if(!e.target.classList.contains('todo-text'))return;
    var id=parseInt(e.target.dataset.tid);
    var f=tFind(todosRef,id);
    if(!f)return;
    var txt=e.target.innerText.trim();
    if(e.key==='Enter'){
      e.preventDefault();
      var nid=tMaxId(todosRef)+1;
      f.parent.splice(f.index+1,0,{id:nid,text:'',priority:f.item.priority,children:[],collapsed:false});
      tSave(storageKey,todosRef);renderAllTodos();
      setTimeout(function(){var it=document.querySelector('#'+listId+' .todo-text[data-tid=\"'+nid+'\"]');if(it)it.focus()},50);
    } else if(e.key==='Tab'&&!e.shiftKey){
      e.preventDefault();
      var prev=null;
      var flatEls=list.querySelectorAll('.todo-item');
      var ci=-1;for(var i=0;i<flatEls.length;i++){if(parseInt(flatEls[i].dataset.tid)===id){ci=i;break}}
      if(ci>0){var pid=parseInt(flatEls[ci-1].dataset.tid);var pf=tFind(todosRef,pid);if(pf){f.parent.splice(f.index,1);if(!pf.item.children)pf.item.children=[];pf.item.children.push(f.item);tSave(storageKey,todosRef);renderAllTodos()}}
    } else if(e.key==='Backspace'&&!txt){
      e.preventDefault();
      var li=tFind(todosRef,id);
      if(!li || (f.item.children&&f.item.children.length>0)) return;
      li.parent.splice(li.index,1);tSave(storageKey,todosRef);renderAllTodos();
    }
  });

  // Drag & drop
  list.addEventListener('dragstart',function(e){
    var grip=e.target.closest('.grip');if(!grip)return;
    var item=grip.closest('.todo-item');if(!item)return;
    e.dataTransfer.setData('text/plain',item.dataset.tid);
    item.classList.add('drag-ghost');
  });
  list.addEventListener('dragend',function(e){
    var items=list.querySelectorAll('.todo-item');items.forEach(function(it){it.classList.remove('drag-ghost','drag-above','drag-below')});
  });
  list.addEventListener('dragover',function(e){e.preventDefault();
    var tgt=e.target.closest('.todo-item');if(!tgt||tgt.classList.contains('drag-ghost'))return;
    var rect=tgt.getBoundingClientRect(),mid=rect.top+rect.height/2;
    list.querySelectorAll('.todo-item').forEach(function(it){it.classList.remove('drag-above','drag-below')});
    tgt.classList.add(e.clientY<mid?'drag-above':'drag-below');
  });
  list.addEventListener('drop',function(e){
    e.preventDefault();
    var srcId=parseInt(e.dataTransfer.getData('text/plain'));
    var tgt=e.target.closest('.todo-item');if(!tgt||tgt.classList.contains('drag-ghost'))return;
    var dstId=parseInt(tgt.dataset.tid);
    if(srcId===dstId||tDescendant(todosRef,srcId,dstId))return;
    var src=tFind(todosRef,srcId),dst=tFind(todosRef,dstId);
    if(!src||!dst)return;
    src.parent.splice(src.index,1);
    var fi=dst.index;if(tgt.classList.contains('drag-below'))fi++;
    dst.parent.splice(fi,0,src.item);
    tSave(storageKey,todosRef);renderAllTodos();
  });
}

function setupAddButton(btnId,todosRef,storageKey,isMonth){
  var btn=document.getElementById(btnId);if(!btn)return;
  btn.onclick=function(){
    var nid=tMaxId(todosRef)+1;
    todosRef.push({id:nid,text:'',priority:'normal',children:[],collapsed:false});
    tSave(storageKey,todosRef);renderAllTodos();
    var listId=isMonth?'monthTodoList':'weekTodoList';
    setTimeout(function(){var it=document.querySelector('#'+listId+' .todo-text[data-tid=\"'+nid+'\"]');if(it)it.focus()},50);
  };
}

function initTodos(){
  weekTodos=tLoad('bht_week_todos_v2');monthTodos=tLoad('bht_month_todos_v2');
  // Generate defaults if empty
  if(!weekTodos.length&&window._lastWd){
    weekTodos=genDefaults(false,window._lastWd);tSave('bht_week_todos_v2',weekTodos);
  }
  if(!monthTodos.length){
    // Use latest month data for defaults
    var mk=Object.keys(MONTHS_DATA).sort().pop();
    var md=mk?MONTHS_DATA[mk]:null;
    if(md) monthTodos=genDefaults(true,{skus:md.skus,total:md.total});else monthTodos=[{id:2001,text:'月度 核验7月利润率是否达到8%目标',priority:'urgent',children:[],collapsed:false},{id:2002,text:'月度 8月广告预算规划',priority:'important',children:[]},{id:2003,text:'月度 供应商比价谈判(降低采购成本)',priority:'normal',children:[]}];
    tSave('bht_month_todos_v2',monthTodos);
  }
  renderAllTodos();
}

function renderAllTodos(){
  renderTodoFilters('weekTodoFilters',weekTodoFilter,'bht_week_todos_v2',weekTodos);
  renderTodoFilters('monthTodoFilters',monthTodoFilter,'bht_month_todos_v2',monthTodos);
  renderTodoList('weekTodoList',weekTodos,weekTodoFilter);
  renderTodoList('monthTodoList',monthTodos,monthTodoFilter);
}

// Attach event handlers after DOM ready
document.addEventListener('DOMContentLoaded',function(){
  initTodos();
  setupAddButton('btn-add-week-todo',weekTodos,'bht_week_todos_v2',false);
  setupAddButton('btn-add-month-todo',monthTodos,'bht_month_todos_v2',true);
  attachTodoEvents('weekTodoList',weekTodos,'bht_week_todos_v2');
  attachTodoEvents('monthTodoList',monthTodos,'bht_month_todos_v2');
});

// ===== SECTION TOGGLE & DRAG =====
var SECTION_IDS = ['kpi','charts','alerts','todos','hxplan','skutable'];
function collapseAll(){
  SECTION_IDS.forEach(function(id){
    var body=document.getElementById(id+'Body'), btn=document.getElementById(id+'Toggle');
    if(body){body.classList.add('collapsed')}
    if(btn){btn.classList.add('collapsed')}
    sectionState[id]=true;
  });
  localStorage.setItem('bht_sections',JSON.stringify(sectionState));
}
function expandAll(){
  SECTION_IDS.forEach(function(id){
    var body=document.getElementById(id+'Body'), btn=document.getElementById(id+'Toggle');
    if(body){body.classList.remove('collapsed')}
    if(btn){btn.classList.remove('collapsed')}
    sectionState[id]=false;
  });
  localStorage.setItem('bht_sections',JSON.stringify(sectionState));
}
function toggleSection(id){
  var body=document.getElementById(id+'Body');
  var btn=document.getElementById(id+'Toggle');
  if(!body||!btn) return;
  var collapsed=!body.classList.contains('collapsed');
  if(collapsed){body.classList.add('collapsed');btn.classList.add('collapsed')}
  else{body.classList.remove('collapsed');btn.classList.remove('collapsed')}
  sectionState[id]=collapsed;
  localStorage.setItem('bht_sections',JSON.stringify(sectionState));
}
var sectionState = JSON.parse(localStorage.getItem('bht_sections')||'{}');
(function(){
  for(var id in sectionState){
    if(sectionState[id]){
      var body=document.getElementById(id+'Body'), btn=document.getElementById(id+'Toggle');
      if(body){body.classList.add('collapsed')}
      if(btn){btn.classList.add('collapsed')}
    }
  }
})();
// Drag reorder
function initDragDrop(){
  var container=document.getElementById('sectionContainer');
  if(!container) return;
  var dragged=null;
  container.addEventListener('dragstart',function(e){
    var wrap=e.target.closest('.section-wrap');
    if(!wrap) return;
    dragged=wrap;wrap.classList.add('dragging');
    e.dataTransfer.effectAllowed='move';
    e.dataTransfer.setData('text/plain','');
  });
  container.addEventListener('dragover',function(e){
    e.preventDefault();
    e.dataTransfer.dropEffect='move';
    var wrap=e.target.closest('.section-wrap');
    if(wrap&&wrap!==dragged) wrap.classList.add('drag-over');
  });
  container.addEventListener('dragleave',function(e){
    var wrap=e.target.closest('.section-wrap');
    // Only remove highlight when truly leaving the section, not when entering a child
    if(wrap&&!wrap.contains(e.relatedTarget)) wrap.classList.remove('drag-over');
  });
  container.addEventListener('drop',function(e){
    e.preventDefault();
    var wrap=e.target.closest('.section-wrap');
    if(wrap&&dragged&&wrap!==dragged){
      wrap.classList.remove('drag-over');
      var rect=wrap.getBoundingClientRect();
      if(e.clientY<rect.top+rect.height/2) container.insertBefore(dragged,wrap);
      else container.insertBefore(dragged,wrap.nextSibling);
      saveSectionOrder();
    }
  });
  container.addEventListener('dragend',function(){
    if(dragged){dragged.classList.remove('dragging');dragged=null}
    container.querySelectorAll('.section-wrap').forEach(function(x){x.classList.remove('drag-over')});
  });
}
function saveSectionOrder(){
  var order=[];
  document.querySelectorAll('#sectionContainer .section-wrap').forEach(function(w){
    order.push(w.dataset.section);
  });
  localStorage.setItem('bht_section_order',JSON.stringify(order));
}
function loadSectionOrder(){
  var order=JSON.parse(localStorage.getItem('bht_section_order')||'[]');
  if(!order.length) return;
  var container=document.getElementById('sectionContainer');
  if(!container) return;
  order.forEach(function(id){
    var el=container.querySelector('[data-section="'+id+'"]');
    if(el) container.appendChild(el);
  });
}

// ===== GET DATA FOR TAB =====
function getMonthData(mk){
  return MONTHS_DATA[mk] || null;
}

function getWeekData(wk){
  if(wk.id.indexOf('month_')===0){
    var mk = wk.monthKey;
    var md = getMonthData(mk);
    if(!md) return null;
    return {total:md.total, parents:md.parents, skus:md.skus, alerts:md.alerts||[], cost:md.cost||null};
  }

  // Try real weekly data
  if(wk.wkKey && WEEKLY_DATA.weeks && WEEKLY_DATA.weeks[wk.wkKey]){
    var wd = WEEKLY_DATA.weeks[wk.wkKey];
    var alerts=[];
    (wd.skus||[]).forEach(function(s){
      var mv=0; try{mv=parseFloat(s.margin)}catch(e){}
      if(s.o>120&&mv<0) alerts.push({l:'red',t:s.sku+'('+s.name+') - 周销量大但亏损',d:'周销'+s.o.toLocaleString()+'单 $'+s.s.toLocaleString()+' 广告$'+s.ad.toLocaleString()+' 毛利率'+s.margin});
      else if(s.o<=2&&s.ad>15) alerts.push({l:'red',t:s.sku+'('+s.name+') - 几乎无单广告烧钱',d:'周销'+s.o+'单 广告$'+s.ad.toLocaleString()+' 建议暂停广告排查'});
    });
    var mk = wd.year ? (wd.year+('0'+wd.month).slice(-2)) : null;
    return {total:wd.total, parents:wd.parents, skus:wd.skus, alerts:alerts, cost:wd.settlementCost||wd.cost||null, orderCost:wd.cost||null, monthKey:mk};
  }

  return null;
}

// ===== RENDER =====
function renderKPI(t, wk){
  if(!t){document.getElementById('kpiRow').innerHTML='<div class="kpi-card" style="grid-column:1/-1;text-align:center;padding:30px"><div class="val" style="color:#8b90a0;font-size:14px">暂无该周数据</div><div class="sub n">从领星导出该周报表后运行 bht_data/run_pipeline.py 更新</div></div>';return}
  var isMonth = wk&&wk.id.indexOf('month_')===0;

  // 结算利润 (settlement profit report)
  var sm = t.settlementMargin;        // null for weeks, a number for months
  var sp = t.settlementProfit;        // null for weeks, a number for months
  var smDisplay = (sm!=null) ? sm.toFixed(2)+'%' : 'N/A';
  var spDisplay = (sp!=null) ? '$'+(sp/1000).toFixed(0)+'k' : '(无周度结算数据)';
  var smColor = (sm!=null) ? (sm>=t.target?'dg':sm>=t.target-0.3?'dy':'dr') : 'dn';
  var smSub = (sm!=null) ? ('目标'+t.target+'% '+(sm>=t.target?'已达标':'差'+(t.target-sm).toFixed(2)+'pp')) : '月度结算利润报表';

  // 订单利润 (order profit report)
  var om = t.orderMargin||t.margin||0;
  var op = t.orderProfit||t.profit||0;
  var omColor = om>=t.target?'dg':om>=t.target-0.3?'dy':'dr';
  var opColor = op>=0?'dg':'dr';

  // 产品表现 (product performance - matches SKU table)
  var pm = t.margin||0;
  var pp = t.profit||0;

  var note='';
  if(wk&&wk.est) note='<span style="font-size:10px;color:#f59e0b;margin-left:4px">(估算)</span>';
  else if(wk&&wk.partial) note='<span style="font-size:10px;color:#3b82f6;margin-left:4px">(真实-部分)</span>';
  else if(wk&&!wk.est&&!isMonth) note='<span style="font-size:10px;color:#22c55e;margin-left:4px">(真实)</span>';

  var days = isMonth ? 30 : 7;
  var cvr = t.cvr||0;
  var hasSettlement = (sm!=null);
  document.getElementById('kpiRow').innerHTML=
    // Row 1 - Margins & Profit by data source
    '<div class="kpi-card"><div class="dot '+smColor+'"></div><div class="lbl">结算利润率'+note+'</div><div class="val">'+smDisplay+'</div><div class="sub '+(hasSettlement?(sm>=t.target?'g':sm>=t.target-0.3?'y':'r'):'n')+'">'+smSub+'</div></div>'+
    '<div class="kpi-card"><div class="dot '+omColor+'"></div><div class="lbl">订单利润率'+note+'</div><div class="val">'+om.toFixed(2)+'%</div><div class="sub n">订单利润报表 | 净利'+'$'+(op/1000).toFixed(0)+'k</div></div>'+
    '<div class="kpi-card"><div class="dot dg"></div><div class="lbl">销售额'+note+'</div><div class="val">$'+(t.sales/1000).toFixed(0)+'k</div><div class="sub n">'+t.orders.toLocaleString()+'单 22SKU</div></div>'+
    '<div class="kpi-card"><div class="dot '+(pp>=0?'dg':'dr')+'"></div><div class="lbl">净利润(产品表现)'+note+'</div><div class="val">$'+(pp/1000).toFixed(0)+'k</div><div class="sub '+(pp>=0?'g':'r')+'">产品表现口径 | 利润率'+pm.toFixed(1)+'%</div></div>'+
    // Row 2 - Traffic & Conversion
    '<div class="kpi-card"><div class="dot '+(t.tacos>14?'dr':'dg')+'"></div><div class="lbl">广告花费'+note+'</div><div class="val">$'+(t.ad/1000).toFixed(0)+'k</div><div class="sub '+(t.tacos>14?'r':'g')+'">TACoS '+t.tacos.toFixed(1)+'%</div></div>'+
    '<div class="kpi-card"><div class="dot dg"></div><div class="lbl">订单总量'+note+'</div><div class="val">'+t.orders.toLocaleString()+'单</div><div class="sub n">日均'+Math.round(t.orders/days)+'单 | 22SKU</div></div>'+
    '<div class="kpi-card"><div class="dot dg"></div><div class="lbl">访客数'+note+'</div><div class="val">'+((t.sessions||0)/1000).toFixed(1)+'k</div><div class="sub n">Sessions | 日均'+Math.round((t.sessions||0)/days).toLocaleString()+'</div></div>'+
    '<div class="kpi-card"><div class="dot '+(cvr>=20?'dg':cvr>=12?'dy':'dr')+'"></div><div class="lbl">转化率 CVR'+note+'</div><div class="val">'+cvr.toFixed(2)+'%</div><div class="sub '+(cvr>=20?'g':cvr>=12?'y':'r')+'">订单/访客 | 基准约15%</div></div>';
}

var charts={};
var costView='auto';
var _costMonth=null,_costWeek=null,_costDay=null;

function switchCostView(view,btn){
  costView=view;
  var btns=document.querySelectorAll('.cost-tab-btn');
  for(var i=0;i<btns.length;i++) btns[i].classList.remove('active');
  if(btn) btn.classList.add('active');
  else {var b=document.querySelector('.cost-tab-btn[data-cost=\x27'+view+'\x27]');if(b)b.classList.add('active')}
  if(window._lastWd) renderCostPanel(window._lastWd);
}

function renderCostTable(costData,totalSales){
  var el=document.getElementById('costTable');
  if(!el) return;
  if(!costData||(!costData.groups&&!costData.labels)){
    el.innerHTML='<div class="cost-empty">暂无成本拆解数据</div>';return;
  }
  var groups=costData.groups;
  // Fallback to flat format if no groups
  if(!groups||!groups.length){
    if(costData.labels&&costData.labels.length){
      var flatHtml='<table class="cost-table"><thead><tr><th>成本项</th><th style="text-align:right">金额($)</th><th style="text-align:right">占比</th><th></th></tr></thead><tbody>';
      for(var i=0;i<costData.labels.length;i++){
        var lv=costData.labels[i], vv=costData.values[i];
        var pp=totalSales>0?(vv/totalSales*100):0;
        flatHtml+='<tr><td>'+lv+'</td><td style="text-align:right;font-weight:600">$'+vv.toLocaleString('en-US')+'</td><td style="text-align:right">'+pp.toFixed(1)+'%</td><td><div class="cost-bar-outer"><div class="cost-bar-inner" style="width:'+Math.min(Math.abs(pp),100)+'%;background:#6366f1"></div></div></td></tr>';
      }
      flatHtml+='</tbody></table>';el.innerHTML=flatHtml;
    }
    return;
  }
  var colors={'商品成本':'#f59e0b','平台交易费':'#3b82f6','营销费用':'#ef4444','库存费用':'#06b6d4','其他费用':'#8b5cf6','净利润':'#22c55e'};
  var html='<table class="cost-table"><thead><tr><th>成本类别</th><th style="text-align:right">金额($)</th><th style="text-align:right">占比</th><th></th></tr></thead><tbody>';
  for(var i=0;i<groups.length;i++){
    var g=groups[i], isProfit=g.isProfit;
    var gpct=totalSales>0?(g.value/totalSales*100):0;
    var barColor=colors[g.label]||(isProfit?(g.value>=0?'#22c55e':'#ef4444'):'#6366f1');
    html+='<tr class="cost-group-row" style="font-weight:700;background:#1a1b2e"><td>'+g.label+'</td><td style="text-align:right">$'+Math.abs(g.value).toLocaleString('en-US')+'</td><td style="text-align:right;color:'+(isProfit?(g.value>=0?'#22c55e':'#ef4444'):'#f1f5f9')+'">'+gpct.toFixed(1)+'%</td><td><div class="cost-bar-outer"><div class="cost-bar-inner" style="width:'+Math.min(Math.abs(gpct),100)+'%;background:'+barColor+'"></div></div></td></tr>';
    if(g.items) for(var j=0;j<g.items.length;j++){
      var it=g.items[j], ipct=totalSales>0?(it.value/totalSales*100):0;
      html+='<tr><td style="padding-left:24px;font-size:12px;color:#8b90a0">  '+it.label+'</td><td style="text-align:right;font-size:12px;color:#8b90a0">$'+it.value.toLocaleString('en-US')+'</td><td style="text-align:right;font-size:12px;color:#6b7280">'+ipct.toFixed(1)+'%</td><td></td></tr>';
    }
  }
  html+='</tbody></table>';
  el.innerHTML=html;
}

function resolveCostData(wd){
  if(costView==='auto'){
    var c=wd.cost;
    if(!c) return null;
    var hasGroups=c.groups&&c.groups.length;
    var hasFlat=c.labels&&c.values&&c.values.length;
    if(hasGroups||hasFlat) return {cost:c, sales: c.sales||wd.total.sales};
    return null;
  }
  if(costView==='month') return _costMonth;
  if(costView==='week') return _costWeek;
  if(costView==='day') return _costDay;
  return null;
}

function renderCostPanel(wd){
  var cd=resolveCostData(wd);
  var costCtx=document.getElementById('chartCost');
  if(!costCtx) return;
  var ctx=costCtx.getContext('2d');
  if(charts.cost){charts.cost.destroy();charts.cost=null}
  var groups=cd&&cd.cost?cd.cost.groups:null;
  if(groups&&groups.length){
    var glabels=groups.map(function(g){return g.label});
    var gvalues=groups.map(function(g){return Math.abs(g.value)});
    var gcolors=['#f59e0b','#3b82f6','#ef4444','#06b6d4','#8b5cf6','#22c55e'];
    charts.cost=new Chart(costCtx,{type:'doughnut',data:{labels:glabels,datasets:[{data:gvalues,backgroundColor:gcolors.slice(0,glabels.length),borderColor:'#161822',borderWidth:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}}});
    renderCostTable(cd.cost,cd.sales);
  } else if(cd&&cd.cost&&cd.cost.labels&&cd.cost.values&&cd.cost.values.some(function(v){return v!==0})){
    // Fallback flat format
    charts.cost=new Chart(costCtx,{type:'doughnut',data:{labels:cd.cost.labels,datasets:[{data:cd.cost.values,backgroundColor:['#6366f1','#8b5cf6','#ef4444','#f59e0b','#3b82f6','#06b6d4','#6b7280','#ec4899','#22c55e'],borderColor:'#161822',borderWidth:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}}});
    renderCostTable(cd.cost,cd.sales);
  } else {
    ctx.clearRect(0,0,costCtx.width,costCtx.height);
    ctx.font='13px "Microsoft YaHei","PingFang SC",sans-serif';
    ctx.fillStyle='#8b90a0';ctx.textAlign='center';
    var msg=costView==='day'?'(暂无日维度成本数据，需从领星导出按天结算利润)':'(暂无成本拆解数据)';
    ctx.fillText(msg,costCtx.width/2,costCtx.height/2);
    document.getElementById('costTable').innerHTML='<div class="cost-empty">'+msg+'</div>';
  }
}

function destroyCharts(){for(var k in charts){if(charts[k])charts[k].destroy()}charts={}}
function renderCharts(wd){
  destroyCharts();
  if(!wd) return;
  Chart.defaults.color='#8b90a0';Chart.defaults.borderColor='#232638';
  var pids=['B09N9815DF','B0C3QMWY9K','B09G9RL5D3','B0FN7BFHQY'];
  var pNames=pids.map(function(id){return wd.parents[id]?wd.parents[id].name:id});
  var pMargins=pids.map(function(id){return wd.parents[id]?wd.parents[id].margin:0});
  var pSales=pids.map(function(id){return wd.parents[id]?wd.parents[id].s:0});
  var pAd=pids.map(function(id){return wd.parents[id]?wd.parents[id].ad:0});
  var sLabels=wd.skus.map(function(s){return s.name&&s.name.length>14?s.name.substr(0,13)+'...':(s.name||s.sku)});
  var sMargins=wd.skus.map(function(s){try{return parseFloat(s.margin)}catch(e){return 0}});
  var sColors=sMargins.map(function(v){return isNaN(v)?'#6b7280':v<0?'#ef4444':v<8?'#f59e0b':v<15?'#3b82f6':'#22c55e'});

  charts.margin=new Chart(document.getElementById('chartMargin'),{type:'bar',data:{labels:pNames,datasets:[{data:pMargins,backgroundColor:pMargins.map(function(v){return v<0?'#ef444488':v<8?'#f59e0b88':'#22c55e88'}),borderColor:pMargins.map(function(v){return v<0?'#ef4444':v<8?'#f59e0b':'#22c55e'}),borderWidth:1.5,borderRadius:6}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{ticks:{callback:function(v){return v+'%'}},grid:{color:'#1e2030'}},x:{grid:{display:false}}}}});

  renderCostPanel(wd);

  charts.sku=new Chart(document.getElementById('chartSKU'),{type:'bar',data:{labels:sLabels,datasets:[{data:sMargins,backgroundColor:sColors.map(function(c){return c+'88'}),borderColor:sColors,borderWidth:1,borderRadius:4}]},options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false}},scales:{x:{ticks:{callback:function(v){return v+'%'}},grid:{color:'#1e2030'}},y:{ticks:{font:{size:10}},grid:{display:false}}}}});

  charts.salesAd=new Chart(document.getElementById('chartSalesAd'),{type:'bar',data:{labels:pNames,datasets:[{label:'销售额($)',data:pSales,backgroundColor:'#6366f188',borderColor:'#6366f1',borderWidth:1,borderRadius:6},{label:'广告费($)',data:pAd,backgroundColor:'#ef444488',borderColor:'#ef4444',borderWidth:1,borderRadius:6}]},options:{responsive:true,plugins:{legend:{position:'top',labels:{usePointStyle:true,padding:12}}},scales:{y:{ticks:{callback:function(v){return '$'+(v/1000).toFixed(0)+'k'}},grid:{color:'#1e2030'}},x:{grid:{display:false}}}}});
}

function renderTable(wd){
  if(!wd){document.getElementById('skuTbody').innerHTML='';return}
  var PD={'B09N9815DF':'330BHT(盒装)','B0C3QMWY9K':'瓶装BHT','B09G9RL5D3':'袋装BHT','B0FN7BFHQY':'蓝黄BHT'};
  var html='',cp='';
  wd.skus.forEach(function(s){
    if(s.p!==cp){
      cp=s.p;
      var sb=wd.skus.filter(function(r){return r.p===cp});
      var to=sb.reduce(function(a,r){return a+r.o},0),ts=sb.reduce(function(a,r){return a+r.s},0),ta=sb.reduce(function(a,r){return a+r.ad},0);
      html+='<tr class="subtot"><td colspan="3"><b>'+cp+'</b> '+PD[cp]+'</td><td style="color:#8b90a0">'+sb.length+'SKU</td><td><b>'+to.toLocaleString()+'</b></td><td><b>$'+ts.toLocaleString()+'</b></td><td><b>$'+ta.toLocaleString()+'</b></td><td colspan="2">TACoS '+(ts>0?(ta/ts*100).toFixed(1):0)+'%</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>';
    }
    var mv=0;try{mv=parseFloat(s.margin.replace('%',''))}catch(e){}
    var tg=isNaN(mv)?'tgy':mv<0?'tgr':mv<8?'tgy':'tgg';
    var ic=isNaN(mv)?'?':mv<0?'!!':'~';
    html+='<tr><td style="color:#8b90a0;font-size:10px">'+s.p+'</td><td><b>'+s.sku+'</b></td><td style="font-size:10px;color:#8b90a0">'+(s.asin||'')+'</td><td>'+s.name+'</td><td>'+s.o.toLocaleString()+'</td><td>$'+s.s.toLocaleString()+'</td><td>$'+s.ad.toLocaleString()+'</td><td>'+(s.acos||'N/A')+'</td><td>'+(s.tacos||'N/A')+'</td><td>'+(s.cvr||'N/A')+'</td><td>'+(s.ad_cvr||'N/A')+'</td><td>'+(s.nat_cvr||'N/A')+'</td><td><span class="tag '+tg+'">'+s.margin+'</span></td><td>'+(s.bsr||'N/A')+'</td><td style="color:'+(isNaN(mv)?'#8b90a0':mv<0?'#ef4444':mv<8?'#f59e0b':'#22c55e')+'">'+ic+'</td></tr>';
  });
  document.getElementById('skuTbody').innerHTML=html;
}

function renderAlerts(wd){
  if(!wd||!wd.alerts||!wd.alerts.length){document.getElementById('alertsSection').innerHTML='';return}
  var html='<div class="section-title">重点关注</div>';
  wd.alerts.forEach(function(a){html+='<div class="alert-item'+(a.l==='warn'?' warn':'')+'"><div class="ai">'+(a.l==='red'?'!!':'*')+'</div><div class="alert-body"><div class="at">'+a.t+'</div><div class="ad">'+a.d+'</div></div></div>'});
  document.getElementById('alertsSection').innerHTML=html;
}

function renderHXPlan(wd){
  var el=document.getElementById('hxPlan');
  if(!el) return;
  // Find HX1045 in current data
  var hx=null;
  if(wd&&wd.skus){
    for(var i=0;i<wd.skus.length;i++){
      if(wd.skus[i].sku==='HX1045'){hx=wd.skus[i];break;}
    }
  }
  if(!hx){
    el.innerHTML='<h3>HX1045 专项优化</h3><div style=\'color:#8b90a0;font-size:12px;padding:12px;text-align:center\'>暂未加载HX1045数据</div>';
    return;
  }
  // Parse current metrics
  var margin=parseFloat(hx.margin)||0;
  var acos=parseFloat(hx.acos)||0;
  var tacos=parseFloat(hx.tacos)||0;
  var orders=hx.o||0;
  var sales=hx.s||0;
  var ad=hx.ad||0;
  var sessions=hx.sessions||0;
  var cvr=sessions>0?orders/sessions*100:0;
  var bsr=hx.bsr||'N/A';

  // Monthly estimates (x4.33 weeks)
  var moOrders=Math.round(orders*4.33);
  var moSales=Math.round(sales*4.33);
  var moAd=Math.round(ad*4.33);

  // Price increase estimate: $1 increase at current order volume
  var priceGain=Math.round(orders*1.0*4.33); // monthly gain from $1 price increase
  // Ad efficiency: assuming ACOS improvement of 3-5pp (redirect from high to low ACOS keywords)
  var adEfficiencyGain=Math.round(ad*0.15*4.33); // 15% of current ad spend recovered
  // TOS bid optimization: ~8% savings on ad spend
  var tosGain=Math.round(ad*0.08*4.33);
  // Cross-variant traffic: estimate 5% of HX1045 orders shift to higher-margin variants
  var crossGain=Math.round(sales*0.03*4.33); // 3% margin improvement on shifted sales
  // COGS reduction 3%: estimate from current cost
  var cogsEst=Math.round(sales*0.43); // COGS ~43% of sales
  var cogsGain=Math.round(cogsEst*0.03*4.33);
  // Listing CVR improvement
  var cvrGain=Math.round(sales*0.02*4.33);

  var totalGain=priceGain+adEfficiencyGain+tosGain+crossGain+cogsGain+cvrGain;
  var targetMargin=(margin+totalGain/moSales*100).toFixed(1);

  var html='<h3>HX1045 专项优化 — 数据驱动 | 最新: 周销'+orders+'单 $'+sales.toLocaleString()+' | 利润率'+margin.toFixed(2)+'% | BSR '+bsr+'</h3>';
  html+='<div class=\'plan-grid\'>';

  // P0 items
  html+='<div class=\'plan-item\'><div class=\'pp\' style=\'color:#ef4444\'>P0</div>';
  html+='<div class=\'pt\'>涨$1.0 (≈$26→$27)</div>';
  html+='<div class=\'pi\'>+$'+priceGain.toLocaleString()+'/月</div>';
  html+='<div class=\'pd\'>BSR '+bsr+'有定价权 | 周销'+orders+'单×$1×4.33周 | 观察CVR是否下降</div></div>';

  html+='<div class=\'plan-item\'><div class=\'pp\' style=\'color:#ef4444\'>P0</div>';
  html+='<div class=\'pt\'>广告提效（总额不变）</div>';
  html+='<div class=\'pi\'>+$'+adEfficiencyGain.toLocaleString()+'/月</div>';
  html+='<div class=\'pd\'>当前ACoS '+acos.toFixed(1)+'% | 周广告$'+ad.toLocaleString()+' | ACoS>'+Math.round(acos*1.2)+'%词降bid→转给ACoS<'+Math.round(acos*0.7)+'%词</div></div>';

  html+='<div class=\'plan-item\'><div class=\'pp\' style=\'color:#ef4444\'>P0</div>';
  html+='<div class=\'pt\'>TOS竞价系数调整</div>';
  html+='<div class=\'pi\'>+$'+tosGain.toLocaleString()+'/月</div>';
  html+='<div class=\'pd\'>搜索顶部+20%bid | 产品页-50%bid | 当前周广告$'+ad.toLocaleString()+' | 预计节省8%</div></div>';

  // P1 items
  html+='<div class=\'plan-item\'><div class=\'pp\' style=\'color:#f59e0b\'>P1</div>';
  html+='<div class=\'pt\'>变体间流量引导</div>';
  html+='<div class=\'pi\'>+$'+crossGain.toLocaleString()+'/月</div>';
  html+='<div class=\'pd\'>A+推荐HX1822(420pcs高利润)/HX1821 | 当前HX1045月销'+moOrders+'单 | 引导5%至高利润变体</div></div>';

  html+='<div class=\'plan-item\'><div class=\'pp\' style=\'color:#f59e0b\'>P1</div>';
  html+='<div class=\'pt\'>采购价降3%（比价）</div>';
  html+='<div class=\'pi\'>+$'+cogsGain.toLocaleString()+'/月</div>';
  html+='<div class=\'pd\'>当前COGS约占销售额43% | 月销'+moOrders+'件 | 备3家供应商比价谈判</div></div>';

  // P2 items
  html+='<div class=\'plan-item\'><div class=\'pp\' style=\'color:#22c55e\'>P2</div>';
  html+='<div class=\'pt\'>Listing优化提自然CVR</div>';
  html+='<div class=\'pi\'>+$'+cvrGain.toLocaleString()+'/月</div>';
  html+='<div class=\'pd\'>当前总CVR '+cvr.toFixed(1)+'% | Sessions '+sessions.toLocaleString()+'/周 | 自然CVR约'+Math.round(cvr*0.6)+'%远低广告CVR约'+Math.round(cvr*1.3)+'%</div></div>';

  html+='</div>';

  // Summary bar
  var barColor=margin<0?'#ef4444':margin<5?'#f59e0b':'#22c55e';
  html+='<div style=\'margin-top:10px;padding:10px;background:'+barColor+'15;border-radius:8px;text-align:center\'>';
  html+='<span style=\'font-weight:700;color:'+barColor+'\'>保守月增$'+totalGain.toLocaleString()+' | 当前利润率'+margin.toFixed(2)+'% → 目标'+targetMargin+'%+ | BSR '+bsr+'排名不受影响</span>';
  html+='</div>';

  el.innerHTML=html;
}

// Todos are now managed by the BHTZ-style system (see genDefaults, renderTodoFilters, renderTodoList, etc. above)

function switchTab(wkId){
  curTab=wkId;
  var btns=document.querySelectorAll('.tab-btn');
  btns.forEach(function(b){b.classList.toggle('active',b.dataset.tab===wkId)});
  var wk=WEEKS.find(function(w){return w.id===wkId});
  if(!wk) return;
  var badge=document.getElementById('dateBadge');
  var wd=getWeekData(wk);
  window._lastWd=wd;
  // Find previous week's data for todo generation (weekly tabs only)
  window._prevWd=null;
  window._prevWeekLabel='';
  if(wkId.indexOf('month_')!==0){
    var wkIdx=-1;
    for(var i=0;i<WEEKS.length;i++){if(WEEKS[i].id===wkId){wkIdx=i;break;}}
    if(wkIdx>0){
      for(var i=wkIdx-1;i>=0;i--){
        var pw=WEEKS[i];
        if(pw.id.indexOf('month_')===0) continue;
        var pwd=getWeekData(pw);
        if(pwd&&pwd.skus&&pwd.skus.length){window._prevWd=pwd;window._prevWeekLabel=pw.label+'('+pw.sub+')';break;}
      }
    }
  }
  // Store cost data sources
  _costMonth=null;_costWeek=null;_costDay=null;
  if(wd){
    // Monthly cost lookup
    var mk=wk.monthKey||(wd.monthKey);
    if(mk){
      var md=getMonthData(mk);
      if(md&&md.cost&&md.cost.labels&&md.cost.values.some(function(v){return v!==0})){
        _costMonth={cost:md.cost,sales:md.total.sales};
      }
    }
    // If on month tab and no MONTH_DATA entry, use wd.cost directly
    if(!_costMonth&&wd.cost&&wd.cost.labels&&wd.cost.values.some(function(v){return v!==0})){
      _costMonth={cost:wd.cost,sales:wd.total.sales};
    }
    // Weekly cost: from current data if available
    if(wd.cost&&wd.cost.labels&&wd.cost.values&&wd.cost.values.some(function(v){return v!==0})){
      _costWeek={cost:wd.cost,sales:wd.total.sales};
    }
  }
  // Update cost tab button states to reflect available data
  var ctabs=document.querySelectorAll('.cost-tab-btn');
  ctabs.forEach(function(b){
    var v=b.getAttribute('data-cost');
    if(v==='day'){b.style.opacity='0.4';b.title='日维度需导出按天结算利润'}
    else{b.style.opacity='1';b.title=''}
  });
  if(wd && !wk.est && wk.id.indexOf('month_')!==0){
    if(wk.partial) {
      badge.textContent='[真实-部分] '+wk.label+' ('+wk.sub+')';
      badge.style.borderColor='#3b82f6';
    } else {
      badge.textContent='[真实] '+wk.label+' ('+wk.sub+')';
      badge.style.borderColor='#22c55e';
    }
  } else if(wk.est){
    badge.textContent='[估算] '+wk.label+' ('+wk.sub+')';
    badge.style.borderColor='#f59e0b';
  } else if(wk.id.indexOf('month_')===0){
    var md = getMonthData(wk.monthKey);
    badge.textContent = md ? md.date : wk.sub;
    badge.style.borderColor='#2a2d3e';
  } else {
    badge.textContent=wk.label+' ('+wk.sub+') - 暂无数据';
    badge.style.borderColor='#ef4444';
  }
  renderKPI(wd?wd.total:null, wk);
  renderCharts(wd);
  renderTable(wd);
  renderAlerts(wd);
  renderHXPlan(wd);
  renderAllTodos();
  // Reset cost view to auto on tab switch
  costView='auto';
  var ctb=document.querySelectorAll('.cost-tab-btn');
  ctb.forEach(function(b){b.classList.remove('active')});
  var autoBtn=document.querySelector('.cost-tab-btn[data-cost=\x27auto\x27]');
  if(autoBtn) autoBtn.classList.add('active');
}

// Build tabs - week tabs row, month tabs row
(function(){
  var weekHtml='', monthHtml='';
  var moSeen={};
  WEEKS.forEach(function(w, i){
    if(w.id.indexOf('month_')===0){
      monthHtml+='<button class="tab-btn'+(w.id===DEFAULT_TAB?' active':'')+'" data-tab="'+w.id+'">'+w.label+'<br><small>'+w.sub+'</small></button>';
    } else {
      if(MONTH_BOUNDARIES.indexOf(i)>=0){
        weekHtml+='<span class="tab-sep"></span>';
      }
      var subText=w.sub;
      if(w.est) subText='~'+subText;
      else if(w.hasReal) subText='*'+subText;
      weekHtml+='<button class="tab-btn" data-tab="'+w.id+'">'+w.label+'<br><small>'+subText+'</small></button>';
    }
  });
  document.getElementById('tabWeek').innerHTML=weekHtml;
  document.getElementById('tabMonth').innerHTML=monthHtml;
  var btns=document.querySelectorAll('.tab-btn');
  btns.forEach(function(b){b.addEventListener('click',function(){switchTab(b.dataset.tab)})});
})();

document.getElementById('dateBadge').textContent = 'Loading...';
switchTab(DEFAULT_TAB);
loadSectionOrder();
initDragDrop();
'''

# ===== Assemble final HTML =====
html_parts = []
html_parts.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BHT产品线 - 运营数据看板</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect rx='20' width='100' height='100' fill='%23fef3c7' stroke='%23f59e0b' stroke-width='3'/><text x='50' y='68' text-anchor='middle' fill='%2392410e' font-size='36' font-weight='bold' font-family='sans-serif'>BHT</text></svg>">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script>
if(typeof Chart==='undefined'){
  var s=document.createElement('script');
  s.src='https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.7/chart.umd.min.js';
  document.head.appendChild(s);
}
</script>
<style>''')
html_parts.append(CSS)
html_parts.append('''</style>
</head>
<body>
<div class="hdr">
  <div><h1>BHT产品线 - 运营数据看板</h1><span style="color:#8b90a0;font-size:12px">haisstronica-US | Butt Terminals | 张璐</span></div>
  <div style="display:flex;align-items:center;gap:8px">
    <button class="collapse-all-btn" onclick="collapseAll()">📂 全部折叠</button>
    <button class="collapse-all-btn" onclick="expandAll()">📋 全部展开</button>
    <div class="badge" id="dateBadge">Loading...</div>
  </div>
</div>
<div class="tab-nav" id="tabWeek" style="margin-bottom:4px"></div>
<div class="tab-nav" id="tabMonth" style="margin-bottom:14px"></div>
<div id="sectionContainer">
  <!-- 1. 核心KPI -->
  <div class="section-wrap" data-section="kpi">
    <div class="section-header">
      <span class="drag-handle" draggable="true">⠿</span>
      <button class="section-toggle" id="kpiToggle" onclick="toggleSection(\x27kpi\x27)">▼</button>
      <span class="section-title">核心KPI</span>
    </div>
    <div class="section-body" id="kpiBody">
      <div style="padding:12px 14px"><div class="kpi-row" id="kpiRow"></div></div>
    </div>
  </div>
  <!-- 2. 图表分析 -->
  <div class="section-wrap" data-section="charts">
    <div class="section-header">
      <span class="drag-handle" draggable="true">⠿</span>
      <button class="section-toggle" id="chartsToggle" onclick="toggleSection(\x27charts\x27)">▼</button>
      <span class="section-title">图表分析</span>
    </div>
    <div class="section-body" id="chartsBody">
      <div style="padding:12px 14px">
        <div class="charts-row">
          <div class="chart-panel"><h3>各父ASIN毛利率对比</h3><canvas id="chartMargin"></canvas></div>
          <div class="chart-panel">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:4px">
              <h3 style="margin:0">成本结构拆解</h3>
              <div class="cost-tabs">
                <button class="cost-tab-btn active" data-cost="auto" onclick="switchCostView(\x27auto\x27,this)">自动</button>
                <button class="cost-tab-btn" data-cost="month" onclick="switchCostView(\x27month\x27,this)">月</button>
                <button class="cost-tab-btn" data-cost="week" onclick="switchCostView(\x27week\x27,this)">周</button>
                <button class="cost-tab-btn" data-cost="day" onclick="switchCostView(\x27day\x27,this)">日</button>
              </div>
            </div>
            <div class="cost-chart-wrap"><canvas id="chartCost"></canvas></div>
            <div id="costTable" class="cost-table-wrap"></div>
          </div>
        </div>
        <div class="charts-row">
          <div class="chart-panel"><h3>22个SKU毛利率排名</h3><canvas id="chartSKU"></canvas></div>
          <div class="chart-panel"><h3>销售额 vs 广告费对比</h3><canvas id="chartSalesAd"></canvas></div>
        </div>
      </div>
    </div>
  </div>
  <!-- 3. 重点关注 -->
  <div class="section-wrap" data-section="alerts">
    <div class="section-header">
      <span class="drag-handle" draggable="true">⠿</span>
      <button class="section-toggle" id="alertsToggle" onclick="toggleSection(\x27alerts\x27)">▼</button>
      <span class="section-title">重点关注</span>
    </div>
    <div class="section-body" id="alertsBody">
      <div style="padding:4px 14px 12px"><div id="alertsSection"></div></div>
    </div>
  </div>
  <!-- 4. 待办事项 -->
  <div class="section-wrap" data-section="todos">
    <div class="section-header">
      <span class="drag-handle" draggable="true">⠿</span>
      <button class="section-toggle" id="todosToggle" onclick="toggleSection(\x27todos\x27)">▼</button>
      <span class="section-title">待办事项</span>
    </div>
    <div class="section-body" id="todosBody">
      <div style="padding:4px 14px 12px">
        <div class="todo-wrap"><div class="todo-hdr"><h4>📅 周度待办 (基于上周数据分析)</h4><div><button class="todo-fold-btn" onclick="toggleTodoFold('week',false)">📂 全部折叠</button><button class="todo-fold-btn" onclick="toggleTodoFold('week',true)" style="margin-left:4px">📋 全部展开</button></div></div><div id="weekTodoFilters" class="todo-filters"></div><div id="weekTodoList" class="todo-list"></div><div class="todo-add-wrap"><button id="btn-add-week-todo">+ 添加周度待办</button></div>
        </div>
        <div class="todo-wrap" style="margin-top:18px"><div class="todo-hdr"><h4>📊 月度待办 (基于月度数据分析8月规划)</h4><div><button class="todo-fold-btn" onclick="toggleTodoFold('month',false)">📂 全部折叠</button><button class="todo-fold-btn" onclick="toggleTodoFold('month',true)" style="margin-left:4px">📋 全部展开</button></div></div><div id="monthTodoFilters" class="todo-filters"></div><div id="monthTodoList" class="todo-list"></div><div class="todo-add-wrap"><button id="btn-add-month-todo">+ 添加月度待办</button></div></div>
        </div>
      </div>
    </div>
  </div>
  <!-- 5. HX1045专项优化 -->
  <div class="section-wrap" data-section="hxplan">
    <div class="section-header">
      <span class="drag-handle" draggable="true">⠿</span>
      <button class="section-toggle" id="hxplanToggle" onclick="toggleSection(\x27hxplan\x27)">▼</button>
      <span class="section-title">HX1045专项优化</span>
    </div>
    <div class="section-body" id="hxplanBody">
      <div style="padding:4px 14px 12px">
        <div class="hx-section" id="hxPlan"></div>
      </div>
    </div>
  </div>
  <!-- 6. SKU明细表 -->
  <div class="section-wrap" data-section="skutable">
    <div class="section-header">
      <span class="drag-handle" draggable="true">⠿</span>
      <button class="section-toggle" id="skutableToggle" onclick="toggleSection(\x27skutable\x27)">▼</button>
      <span class="section-title">SKU明细表</span>
    </div>
    <div class="section-body" id="skutableBody">
      <div style="padding:4px 14px 12px">
        <div class="table-wrap">
          <div style="padding:12px 16px;display:flex;justify-content:space-between;align-items:center"><span style="font-size:14px;font-weight:700;color:#fff;margin:0">22个SKU明细</span><span style="font-size:10px;color:#8b90a0">绿>=15% 黄0~15% 红<0%</span></div>
          <div class="table-scroll"><table><thead><tr><th>父ASIN</th><th>SKU</th><th>ASIN</th><th>品名</th><th>销量</th><th>销售额</th><th>广告费</th><th>ACoS</th><th>TACoS</th><th>CVR</th><th>广告CVR</th><th>自然CVR</th><th>毛利率</th><th>BSR</th><th>状态</th></tr></thead><tbody id="skuTbody"></tbody></table></div>
        </div>
      </div>
    </div>
  </div>
</div><!-- end sectionContainer -->
<div class="foot">更新流程: 领星导出3报表到桌面 -> 运行 bht_data/run_pipeline.py -> 刷新本页<br>数据文件夹: C:/Users/haishan10/bht_data/ | 更新: 每周四下午</div>

<script>
''')

# Inject data + JS template with replacements
js = JS_TEMPLATE
js = js.replace('__MONTHS_DATA__', months_json)
js = js.replace('__WEEKLY_DATA__', weekly_json)
js = js.replace('__WEEKS__', weeks_json)
js = js.replace('__DEFAULT_TAB__', default_tab)
js = js.replace('__MONTH_BOUNDARIES__', json.dumps(month_boundaries))

html_parts.append(js)
html_parts.append('''
</script>
</body>
</html>''')

html = '\n'.join(html_parts)

output_path = os.path.join(DESKTOP, 'Weekly_Dashboard.html')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'[OK] Dashboard written: {output_path}')
print(f'Size: {len(html):,} bytes')
n_weeks = len([w for w in WEEKS if not w['id'].startswith('month_')])
n_months = len([w for w in WEEKS if w['id'].startswith('month_')])
print(f'Weeks: {n_weeks} | Months: {n_months} | Default tab: {default_tab}')
