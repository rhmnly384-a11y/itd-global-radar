import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).parent/'scripts'/'intelligence.py'
s=importlib.util.spec_from_file_location('intelligence',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
NOW='2026-11-11T03:47:45+00:00'
def tool(name='sample/three-tool',stars=100,push='2026-11-10T01:00:00Z',birth='2026-11-08T01:00:00Z',license='MIT'):
 return dict(repo=name,url='https://github.com/'+name,stars=stars,created_at=birth,last_push=push,license=license,description='threejs 3d animation')
def snapshot(c):return dict(generated_at_utc=NOW,status='READ_ONLY_CANDIDATES_NOT_INSTALLED',allow_paid=False,candidates=c,errors=[])
class Tests(unittest.TestCase):
 def test_paid_snapshot_refused(self):
  s=snapshot([tool()]);s['allow_paid']=True
  with self.assertRaises(ValueError):m.build(s,{})
 def test_injected_url_refused(self):
  x=tool();x['url']='https://example.com/malicious'
  with self.assertRaises(ValueError):m.build(snapshot([x]),{})
 def test_deduplicate(self):self.assertEqual(m.build(snapshot([tool(),tool()]),{})[0]['source_count'],1)
 def test_new_tools_detected(self):self.assertEqual(m.build(snapshot([tool()]),{})[0]['lanes']['emerging'][0]['repo'],'sample/three-tool')
 def test_previous_observation_growth(self):
  history={'repositories':{'sample/three-tool':{'last_seen':'2026-11-10T03:47:45+00:00','samples':[dict(date='2026-11-10T03:47:45+00:00',stars=80)]}}}
  r,_=m.build(snapshot([tool(stars=100)]),history)
  self.assertEqual(r['top'][0]['stars_delta'],20)
 def test_no_auto_execute(self):
  r,_=m.build(snapshot([tool()]),{})
  self.assertFalse(r['eligible_for_execution'])
  self.assertEqual(r['top'][0]['cost'],'NOT_VERIFIED')
 def test_old_archived_watchlist(self):
  x=tool();x['archived']=True
  self.assertEqual(m.build(snapshot([x]),{})[0]['lanes']['watchlist'][0]['repo'],x['repo'])
 def test_license_flag(self):
  r,_=m.build(snapshot([tool(license='NOASSERTION')]),{})
  self.assertIn('LICENSE_NOT_VERIFIED',r['top'][0]['risks'])
 def test_recent_beats_stale(self):
  a=tool(name='big/legacy',stars=1000000,push='2022-01-01T01:00:00Z',birth='2018-01-01T01:00:00Z')
  b=tool(name='little/new',stars=150)
  self.assertEqual(m.build(snapshot([a,b]),{})[0]['top'][0]['repo'],'little/new')
 def test_same_day_idempotent(self):
  x=tool();_,h=m.build(snapshot([x]),{})
  _,hh=m.build(snapshot([x]),h)
  self.assertEqual(len(hh['repositories']['sample/three-tool']['samples']),1)
 def test_categories(self):
  r,_=m.build(snapshot([tool()]),{})
  self.assertIn('3d-cinematic',r['top'][0]['category'])
if __name__=='__main__':unittest.main()
