"""Artifact acceptance checks. Run after build_model.py."""
import json, pathlib, struct
root=pathlib.Path(__file__).resolve().parent.parent
p=root/'model.json'
assert p.exists(), 'Actual 3D geometry has not been generated'
d=json.loads(p.read_text())
assert set(m['level'] for m in d['meshes']) >= {-1,0,1,2,3,4,9}
assert len(d['rooms']) >= 40
assert len(d['sources'])==4
assert all(m['count']%3==0 and m['count']>0 for m in d['meshes'])
assert any(m['layer']=='interior' for m in d['meshes'])
assert any(m['layer']=='mep' for m in d['meshes'])
assert d['voids']['1'], '2F atrium opening must not be filled'
g=root/'Gayang_Library.glb'
assert g.exists() and g.stat().st_size>100000
magic,ver,length=struct.unpack('<4sII',g.read_bytes()[:12]); assert magic==b'glTF' and ver==2 and length==g.stat().st_size
print('PASS: levels, room metadata, four source sets, mesh triangles, interiors, MEP, atrium, GLB header')
