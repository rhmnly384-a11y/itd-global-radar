#!/usr/bin/env python3
"""ITD read-only discovery radar. Public GitHub API only. No paid models, no installs."""
from __future__ import annotations
import argparse, base64, datetime as dt, json, math, os, pathlib, re, sys, urllib.error, urllib.parse, urllib.request

BASE = 'https://api.github.com/'
ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_PATTERN = re.compile(r'https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?=[/\s)\]#?"\'>]|$)',re.I)
EXCLUDED = {'issues','pull','actions','discussions','tree','blob','releases','sponsors','topics','features','settings','orgs','explore','marketplace','login','signup','search','trending','users','gist'}

class API:
    def __init__(self,max_calls=50):
        self.max_calls=max_calls;self.calls=0;self.errors=[]
        self.token=os.environ.get('GITHUB_TOKEN','').strip()
    def fetch(self,path,raw=False):
        if self.calls>=self.max_calls: return None
        if not re.fullmatch(r'[A-Za-z0-9_./?=&%:+,<>!*"-]+',path):
            self.errors.append('Unsafe GitHub path was rejected');return None
        self.calls+=1
        headers={'User-Agent':'ITD-Free-Discovery-Radar/2.1','Accept':'application/vnd.github.raw+json' if raw else 'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
        if self.token:headers['Authorization']='Bearer '+self.token
        try:
            req=urllib.request.Request(BASE+path,headers=headers)
            with urllib.request.urlopen(req,timeout=12) as response:
                data=response.read(2_000_000)
            if raw:
                try:
                    j=json.loads(data)
                    if isinstance(j,dict) and 'content' in j:return base64.b64decode(j['content']).decode('utf-8','replace')
                except (json.JSONDecodeError,ValueError,UnicodeDecodeError):pass
                return data.decode('utf-8','replace')
            return json.loads(data)
        except (urllib.error.URLError,ValueError,TimeoutError,OSError) as e:
            self.errors.append(f'{path[:90]}: {str(e)[:130]}');return None

def iso_day(days_back=0):
    return (dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=days_back)).strftime('%Y-%m-%d')

def normalize(repo):
    parts=repo.strip('/').split('/')
    if len(parts)!=2:return None
    a,b=parts;b=b.rstrip('.,:;')
    if a.lower() in EXCLUDED or b.lower() in EXCLUDED:return None
    if not re.fullmatch('[A-Za-z0-9_.-]{1,100}',a) or not re.fullmatch('[A-Za-z0-9_.-]{1,100}',b):return None
    return a+'/'+b

def links_from_readme(text,limit=20):
    seen=set();out=[]
    for a,b in REPO_PATTERN.findall(text[:600_000]):
        repo=normalize(a+'/'+b)
        if repo and repo.lower() not in seen:
            seen.add(repo.lower());out.append(repo)
            if len(out)>=limit:break
    return out

def candidate(repo,metadata,via):
    if not isinstance(metadata,dict) or not metadata.get('full_name'):return None
    license_data=metadata.get('license') or {}
    return dict(repo=metadata['full_name'],url=metadata.get('html_url') or f'https://github.com/{repo}',name=metadata.get('name',''),description=(metadata.get('description') or '')[:350],stars=int(metadata.get('stargazers_count') or 0),forks=int(metadata.get('forks_count') or 0),last_push=metadata.get('pushed_at'),created_at=metadata.get('created_at'),archived=bool(metadata.get('archived')),disabled=bool(metadata.get('disabled')),license=(license_data.get('spdx_id') or 'UNKNOWN'),topics=metadata.get('topics') or [],source=via,cost_status='NOT_VERIFIED_FOR_ACTUAL_TASK',execution_status='DISCOVERY_ONLY_NOT_INSTALLED',security_status='NOT_AUDITED')

def score(item,previous_stars=None):
    pushed=(item.get('last_push') or '')[:10]
    recent=False
    try:recent=(dt.date.today()-dt.date.fromisoformat(pushed)).days<=90
    except ValueError:pass
    delta=max(0,item.get('stars',0)-previous_stars) if isinstance(previous_stars,int) else 0
    points=math.log1p(item.get('stars',0))*4 + (12 if recent else -12) + min(35,delta/5)
    if item.get('license') in ('UNKNOWN','NOASSERTION','NONE'):points-=20
    if item.get('archived') or item.get('disabled'):points-=100
    return round(points,2), (delta if previous_stars is not None else None)

def search_queries():
    recent=iso_day(50);born=iso_day(21)
    return [
        f'topic:ai-agents stars:>75 pushed:>{recent}',
        f'topic:mcp-server stars:>30 pushed:>{recent}',
        f'topic:threejs stars:>35 pushed:>{recent}',
        f'topic:animation stars:>50 pushed:>{recent}',
        f'topic:browser-automation stars:>35 pushed:>{recent}',
        f'topic:data-engineering stars:>35 pushed:>{recent}',
        f'topic:developer-tools stars:>100 pushed:>{recent}',
        f'created:>{born} stars:>100',
    ]

def load_json(path,default):
    try:return json.loads(path.read_text())
    except (FileNotFoundError,ValueError):return default

def run(max_calls=50,max_directories=6):
    api=API(max_calls);source_file=ROOT/'registry'/'discovery-seeds.json'
    index=load_json(source_file,{})
    if not index.get('sources'):raise SystemExit('Missing source seeds')
    old=load_json(ROOT/'data'/'latest.json',{})
    previous={x['repo'].lower():x.get('stars') for x in old.get('candidates',[]) if 'repo' in x}
    by_repo={}
    def take(item):
        if item and item['repo'].lower() not in by_repo:by_repo[item['repo'].lower()]=item
    # Trending is approximated from public GitHub Search results, not an invented Trending API.
    for term in search_queries():
        if api.calls>=api.max_calls:break
        q=urllib.parse.urlencode({'q':term,'sort':'stars','order':'desc','per_page':10})
        result=api.fetch('search/repositories?'+q)
        for item in ((result or {}).get('items') or []):take(candidate(item.get('full_name',''),item,'github-repository-search'))
    mega=[s for s in index['sources'] if s['kind'] in ('mega-index','skill-collection','api-directory','cost-reference')]
    offset=(dt.datetime.now(dt.timezone.utc).timetuple().tm_yday*max_directories)%len(mega)
    rotating=[mega[(offset+i)%len(mega)] for i in range(min(max_directories,len(mega)))]
    for source in rotating:
        if api.calls>=api.max_calls:break
        repo=source['repo']
        info=api.fetch('repos/'+repo)
        take(candidate(repo,info,'verified-seed'))
        if source['kind'] in ('mega-index','skill-collection','api-directory'):
            readme=api.fetch('repos/'+repo+'/readme',raw=True)
            for linked in links_from_readme(readme or '', limit=5):
                if api.calls>=api.max_calls:break
                meta=api.fetch('repos/'+linked)
                take(candidate(linked,meta,'readme-of:'+repo))
    candidates=[]
    for item in by_repo.values():
        sc,delta=score(item,previous.get(item['repo'].lower()))
        item['discovery_score']=sc;item['stars_gained_since_previous_snapshot']=delta
        candidates.append(item)
    candidates.sort(key=lambda x:x['discovery_score'],reverse=True)
    if not candidates:
        raise SystemExit('No candidates verified; keeping last existing snapshot unchanged. '+str(api.errors[:2]))
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    snapshot={'schema_version':1,'generated_at_utc':now,'status':'READ_ONLY_CANDIDATES_NOT_INSTALLED','allow_paid':False,'api_calls':api.calls,'seed_count':len(index['sources']),'scanned_directory_repos':[s['repo'] for s in rotating],'queries':search_queries(),'errors':api.errors[:12],'candidates':candidates[:120]}
    folder=ROOT/'data';folder.mkdir(exist_ok=True)
    (folder/'latest.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
    lines=['# ITD daily radar — '+now,'','**Discovery only.** A repository appearing here is NOT installed, security-audited, confirmed free for the requested workflow, or authorized to run. No paid services or coins.','',f'- GitHub API requests: {api.calls}/{api.max_calls}',f'- Candidate repositories: {len(candidates)}',f'- Seed directories sampled today: {len(rotating)}/{len(mega)}','', '| Rank | Repository | Stars | Since previous | License | Last push |', '|---:|---|---:|---:|---|---|']
    for n,item in enumerate(candidates[:35],1):
        delta=item['stars_gained_since_previous_snapshot'];delta='unknown' if delta is None else ('+'+str(delta))
        lines.append(f'| {n} | [{item["repo"]}]({item["url"]}) | {item["stars"]} | {delta} | {item["license"]} | {(item["last_push"] or "unknown")[:10]} |')
    if api.errors:lines+=['','## Incomplete checks','']+['- '+x for x in api.errors[:12]]
    (folder/'daily.md').write_text('\n'.join(lines)+'\n')
    print('RADAR_OK',len(candidates),'candidates',api.calls,'calls',len(api.errors),'warnings; no installs and no payments')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--max-api-calls',type=int,default=50);ap.add_argument('--max-directories',type=int,default=6)
    x=ap.parse_args();run(max(1,min(100,x.max_api_calls)),max(1,min(12,x.max_directories)))
if __name__=='__main__':main()
