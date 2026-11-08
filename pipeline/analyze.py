"""Compute every number used in the video from data/history.csv -> build/facts.json"""
import pandas as pd, numpy as np, json, os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d=pd.read_csv(f'{ROOT}/data/history.csv',parse_dates=['day'])
EP=json.load(open(f'{ROOT}/episode.json')) if os.path.exists(f'{ROOT}/episode.json') else {}
if EP.get('data_end'): d=d[d.day<=EP['data_end']]  # pin data so narration and graphics match
early=d[d.day<'2026-03-20'].groupby('name').size()
all_cases=[n for n in early.index if 'Case' in n]
ACTIVE={'Dreams & Nightmares Case','Fracture Case'}  # excluded: still (or recently) in the regular pool
cases=[c for c in all_cases if c not in ACTIVE]
p=d[d.name.isin(cases)].pivot_table(index='day',columns='name',values='median').sort_index()
p=p.asfreq('D').interpolate(limit=3)
sm=p.rolling(7,min_periods=4).median()                       # trailing 7-day median: robust to outliers, ends on 'now'
base=p.loc['2026-03-15':'2026-03-21'].median()               # baseline = median of first full week
idx=sm/base*100
med=idx.median(axis=1)
med=med.dropna()
peak_day=med.idxmax()
last_week=p.iloc[-7:].median()
s=pd.DataFrame({'base':base,'now':last_week}); s['chg']=(s.now/s.base-1)*100; s=s.sort_values('chg')
v=d[d.name.isin(cases)].pivot_table(index='day',columns='name',values='volume').sort_index()
vm=(v.resample('MS').sum().sum(axis=1)/v.resample('MS').count().sum(axis=1))
wk=med.pct_change(7)*100
equal100=(last_week/base).mean()*100
def at(day): return float(med.loc[day])
facts={
 'n_cases':len(cases),'first_day':str(d.day.min().date()),'last_day':str(d.day.max().date()),
 'index_peak':round(float(med.max()),1),'peak_day':str(peak_day.date()),
 'index_now':round(float((last_week/base).median()*100),1),
 'chg_since_march':round(float((last_week/base).median()*100-100),1),
 'chg_from_peak':round(float((last_week/base).median()*100/med.max()*100-100),1),
 'index_aug17':round(at('2026-08-17'),1),
 'jun20':round(at('2026-06-20'),1),'jul1':round(at('2026-07-01'),1),
 'oct1':round(at('2026-10-01'),1),'oct15':round(at('2026-10-15'),1),
 'worst_weeks':{str(k.date()):round(float(x),1) for k,x in wk.nsmallest(40).groupby(lambda t:t.strftime('%Y-%m')).head(1).items()},
 'worst_day':str(wk.idxmin().date()),'worst_chg':round(float(wk.min()),1),
 'june_day':str(wk.loc['2026-06-01':'2026-07-15'].idxmin().date()),'june_chg':round(float(wk.loc['2026-06-01':'2026-07-15'].min()),1),
 'series_last':round(float(med.iloc[-1]),1),
 'n_down':int((s.chg<0).sum()),'n_up':int((s.chg>=0).sum()),
 'equal_100':round(float(equal100),2),
 'worst':[[k,round(float(r.base),2),round(float(r.now),2),round(float(r.chg),1)] for k,r in s.head(5).iterrows()],
 'best':[[k,round(float(r.base),2),round(float(r.now),2),round(float(r.chg),1)] for k,r in s.tail(5).iloc[::-1].iterrows()],
 'vol_by_month':{k.strftime('%Y-%m'):round(float(x)) for k,x in vm.items()},
 'vol_chg_mar_oct':round(float(vm['2026-10-01']/vm['2026-03-01']*100-100),1),
 'series':[[str(k.date()),round(float(x),2)] for k,x in med.dropna().items()],
}
# active-case comparison (tracked from mid-July only)
a=d[d.name.isin(['Kilowatt Case','Revolution Case'])].pivot_table(index='day',columns='name',values='median').sort_index()
facts['active']={c:[round(float(a[c].dropna().iloc[:7].median()),2),round(float(a[c].dropna().iloc[-7:].median()),2),str(a[c].dropna().index[0].date())] for c in a}
os.makedirs(f'{ROOT}/build',exist_ok=True); json.dump(facts,open(f'{ROOT}/build/facts.json','w'),indent=1)
print(json.dumps({k:v for k,v in facts.items() if k!='series'},indent=1)); print(len(facts['series']))
