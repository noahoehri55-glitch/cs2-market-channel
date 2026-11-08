"""Turn the price repo's data-branch git history into a daily long-format CSV."""
import json, subprocess, sys, csv, re, os
repo, out = sys.argv[1], sys.argv[2]
def num(s):
    if s is None: return None
    s=re.sub(r'[^\d,\.]','',str(s))
    if not s: return None
    # European: 1.234,56
    return float(s.replace('.','').replace(',','.'))
ep=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'episode.json')
cut=json.load(open(ep)).get('data_cutoff') if os.path.exists(ep) else None  # freeze the exact snapshot the script was written from
commits=subprocess.check_output(['git','-C',repo,'log','data','--reverse','--format=%H %cs']+([f'--before={cut}'] if cut else [])).decode().split('\n')
rows={}
for line in commits:
    if not line.strip(): continue
    h,day=line.split()
    try:
        d=json.loads(subprocess.check_output(['git','-C',repo,'show',f'{h}:prices.json'],stderr=subprocess.DEVNULL))
    except Exception: continue
    for p in d.get('prices',[]):
        v=p.get('volume'); 
        rows[(day,p['name'])]=(num(p.get('median_price')),num(p.get('lowest_price')),int(re.sub(r'\D','',str(v))) if v not in (None,'') else None,p.get('updated_at'))
with open(out,'w',newline='') as f:
    w=csv.writer(f); w.writerow(['day','name','median','lowest','volume','updated_at'])
    for (day,name),r in sorted(rows.items()): w.writerow([day,name,*r])
print(len(rows),'rows')
