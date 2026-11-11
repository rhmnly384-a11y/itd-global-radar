#!/usr/bin/env python3
"""ITD Offline Intelligence — rerank discovery candidates; NEVER approve execution."""
from __future__ import annotations
import json,math,re,datetime as dt,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
TAGS={
 "3d-cinematic":("three","webgl","3d","render","animation","blender","gsap","glb"),
 "ui-web":("frontend","ui","react","design system","tailwind","website"),
 "coding-agents":("coding-agent","code assistant","agent","codex","devtool"),
 "automation":("workflow","automation","playwright","browser","robot"),
 "research-crawling":("research","search","crawler","scraping","retrieval"),
 "data-excel":("spreadsheet","excel","etl","analytics","dataframe","inventory"),
 "documents-pdf":("pdf","document","ocr","office"),
 "databases":("postgres","database","sql","sqlite","storage"),
 "ai-ml":("ai","llm","transformer","inference","ml","rag"),
 "security":("security","vulnerability","privacy","audit"),
 "devops":("docker","devops","deployment","kubernetes","self-host"),
 "mcp":("mcp","model context protocol","integration","connector")
}
NAME=re.compile(r'^[a-zA-Z0-9_.-]{1,100}/[a-zA-Z0-9_.-]{1,100}$')
def moment(s):
 try:return dt.datetime.fromisoformat(str(s).replace('Z','+00:00')).astimezone(dt.timezone.utc)
 except (ValueError,TypeError):return None
def classify(x):
 text=" ".join([str(x.get('repo','')),str(x.get('description',''))]+[str(t) for t in x.get('topics',[])[:30]]).lower()
 return [k for k,words in TAGS.items() if any(w in text for w in words)][:4] or ['general']
def build(snapshot,history):
 now=moment(snapshot.get('generated_at_utc'))
 if not now or snapshot.get('allow_paid') is not False or snapshot.get('status')!='READ_ONLY_CANDIDATES_NOT_INSTALLED':raise ValueError('Invalid/unsafe discovery snapshot')
 if not isinstance(snapshot.get('candidates'),list):raise ValueError('No candidates list')
 old=history.get('repositories',{}) if isinstance(history.get('repositories',{}),dict) else {}
 rows=[];new={};seen=set()
 for x in snapshot['candidates'][:250]:
  if not isinstance(x,dict):continue
  name=x.get('repo','');stars=x.get('stars')
  if not isinstance(name,str) or not NAME.fullmatch(name) or '..' in name:continue
  if not isinstance(stars,int) or isinstance(stars,bool) or stars<0:continue
  if str(x.get('url','')).lower().rstrip('/')!='https://github.com/'+name.lower():continue
  key=name.lower()
  if key in seen:continue
  seen.add(key)
  before=old.get(key,{}) if isinstance(old.get(key,{}),dict) else {}
  samples=[s for s in before.get('samples',[]) if isinstance(s,dict) and isinstance(s.get('stars'),int) and moment(s.get('date')) and moment(s['date'])<=now and moment(s['date']).date()!=now.date()]
  samples.sort(key=lambda o:o['date'])
  last=samples[-1] if samples else None
  days=max(1,(now-moment(last['date'])).days) if last else None
  delta=stars-last['stars'] if last else None
  velocity=round(max(0,delta)/days,2) if delta is not None else None
  pushed=moment(x.get('last_push'));created=moment(x.get('created_at'))
  days_since_push=(now-pushed).days if pushed else None
  days_since_birth=(now-created).days if created else None
  archived=bool(x.get('archived') or x.get('disabled'))
  license=x.get('license') or 'UNKNOWN'
  flags=[]
  if archived:flags.append('ARCHIVED')
  if license in ('UNKNOWN','NOASSERTION','NONE'):flags.append('LICENSE_NOT_VERIFIED')
  if days_since_push is None or days_since_push>365:flags.append('MAINTENANCE_UNVERIFIED_OR_STALE')
  if delta is not None and delta<0:flags.append('STAR_COUNT_DECREASED')
  novelty=18 if days_since_birth is not None and 0<=days_since_birth<=21 else 8 if days_since_birth is not None and days_since_birth<=60 else 0
  activity=12 if days_since_push is not None and days_since_push<=30 else 5 if days_since_push is not None and days_since_push<=120 else 0
  momentum=min(25,6*math.log1p(velocity)) if velocity is not None else 0
  size=min(20,3*math.log1p(stars))
  score=round(novelty+activity+momentum+size+(4 if license not in ('UNKNOWN','NOASSERTION','NONE') else -6)-(35 if archived else 0),2)
  lane=('watchlist' if archived or 'MAINTENANCE_UNVERIFIED_OR_STALE' in flags else
        'emerging' if days_since_birth is not None and days_since_birth<=45 else
        'rising' if velocity is not None and velocity>=5 else 'established')
  rows.append(dict(repo=name,url='https://github.com/'+name,stars=stars,
     license=license,category=classify(x),lane=lane,score=score,stars_delta=delta,
     observed_days=days,stars_per_day=velocity,risks=flags,
     cost='NOT_VERIFIED',runtime='NOT_VERIFIED',security='NOT_VERIFIED',
     execution='DISCOVERY_ONLY_NOT_INSTALLED',source=x.get('source','github-search')))
  new[key]=dict(last_seen=now.isoformat(),samples=(samples+[dict(date=now.isoformat(),stars=stars)])[-32:])
 if not rows:raise ValueError('No valid candidates; preserve previous report')
 for key in sorted(old,key=lambda k:old[k].get('last_seen','') if isinstance(old[k],dict) else '',reverse=True):
  if len(new)>=1000:break
  if key not in new and NAME.fullmatch(key):
   t=moment(old[key].get('last_seen')) if isinstance(old[key],dict) else None
   if t and now-t<=dt.timedelta(days=60):new[key]=old[key]
 rows.sort(key=lambda r:(-r['score'],r['repo'].lower()))
 lanes={k:[r for r in rows if r['lane']==k][:20] for k in ('emerging','rising','established','watchlist')}
 domains={k:[r for r in rows if k in r['category'] and r['lane']!='watchlist'][:10] for k in (*TAGS,'general')}
 obj={'schema_version':2,'generated_at_utc':now.isoformat(),'source_count':len(rows),
  'read_only':True,'no_paid_actions':True,'eligible_for_execution':False,
  'WARNING':'Discovery only. Never infer zero-cost, license suitability, availability, security or permission from this catalog.',
  'source_errors':snapshot.get('errors',[])[:12],'lanes':lanes,'domains':domains,'top':rows[:100]}
 return obj,{'schema_version':1,'repositories':new}
def report(x):
 lines=['# ITD Tool Discovery Intelligence',f"Last scan: {x['generated_at_utc']}",
  '','**Candidates only. None are verified free, safe, installed, or compatible.**','']
 for lane,items in x['lanes'].items():
  lines+=['## '+lane,'','| Repo | Stars | Measured growth/day | Domains | Risk flags |','|---|---:|---:|---|---|']
  for r in items[:8]:
   risk=', '.join(r['risks']).replace('|','/') or 'not audited'
   growth='unknown' if r['stars_per_day'] is None else str(r['stars_per_day'])
   lines.append(f"| [{r['repo']}]({r['url']}) | {r['stars']} | {growth} | {', '.join(r['category'])} | {risk} |")
  lines+=['']
 return '\n'.join(lines)
def main():
 data=ROOT/'data'
 s=json.loads((data/'latest.json').read_text(encoding='utf-8'))
 hist_path=data/'observations.json'
 h=json.loads(hist_path.read_text(encoding='utf-8')) if hist_path.exists() else {}
 info,history=build(s,h)
 (data/'intelligence.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (data/'intelligence.md').write_text(report(info)+'\n',encoding='utf-8')
 hist_path.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('ITD_INTELLIGENCE_OK',info['source_count'],'untrusted candidates')
if __name__=='__main__':main()
