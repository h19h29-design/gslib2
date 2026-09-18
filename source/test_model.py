import json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
def test_model():
 d=json.loads((ROOT/'model.json').read_text()); assert d['version']=='2.0-video'
 assert len(d['rooms'])>=66
 assert len(d['observations'])>=6
 assert all(o['source'].endswith('.MP4') and o['time_range'] for o in d['observations'])
 assert any(m['level']==0 and m['layer']=='videoBuilt' for m in d['meshes'])
 assert any(m['level']==0 and m['layer']=='videoFurniture' for m in d['meshes'])
 for l in ['power','comm','fire','plumbing','hvacpipe']:
  assert any(m['layer']==l for m in d['meshes'])
 for floor in [-1,0,1,2,3,4,9]: assert any(m['level']==floor for m in d['meshes'])
 assert (ROOT/'Gayang_Library_Video.glb').read_bytes()[:4]==b'glTF'
 assert len(d['landmarks'])>=5
 print('PASS new scene data requirements')
if __name__=='__main__':test_model()
