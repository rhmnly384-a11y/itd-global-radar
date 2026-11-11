import importlib.util, pathlib, unittest
p=pathlib.Path(__file__).parent/'scripts'/'discover_github.py'
spec=importlib.util.spec_from_file_location('radar',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RadarTests(unittest.TestCase):
 def test_path_restriction(self):
  self.assertIsNone(m.normalize('test/../evil'))
 def test_repo_normalization(self):
  self.assertEqual(m.normalize('sindresorhus/awesome'),'sindresorhus/awesome')
 def test_non_repo_links_filtered(self):
  self.assertFalse(m.links_from_readme('https://github.com/topics/javascript'))
 def test_extract_links(self):
  a=m.links_from_readme('hello https://github.com/mrdoob/three.js world https://github.com/mrdoob/three.js')
  self.assertEqual(a,['mrdoob/three.js'])
 def test_read_only_cost_unknown(self):
  x=m.candidate('a/b',{'full_name':'a/b','stargazers_count':300,'html_url':'https://github.com/a/b'},'test')
  self.assertEqual(x['cost_status'],'NOT_VERIFIED_FOR_ACTUAL_TASK')
  self.assertEqual(x['execution_status'],'DISCOVERY_ONLY_NOT_INSTALLED')
 def test_archived_score_lower(self):
  o={'stars':1000,'last_push':'2026-11-10','license':'MIT','archived':False}
  a=m.score(o)[0];o['archived']=True
  self.assertLess(m.score(o)[0],a)
 def test_only_github_api(self):
  self.assertEqual(m.BASE,'https://api.github.com/')
if __name__=='__main__':unittest.main()
