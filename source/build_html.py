from pathlib import Path
import base64,json
ROOT=Path(__file__).resolve().parent.parent
p=ROOT/'source'
t=(p/'template.html').read_text()
assets=json.loads((ROOT/'assets/drawings.json').read_text())
assets.update(json.loads((ROOT/'assets/video_frames.json').read_text()))
for k,v in {'STYLE':(p/'style.css').read_text(),'MODEL':(ROOT/'model.json').read_text(),'ASSETS':json.dumps(assets,ensure_ascii=False,separators=(',',':')),'GLB':base64.b64encode((ROOT/'Gayang_Library_Video.glb').read_bytes()).decode(),'VIEWER':(p/'viewer.js').read_text()}.items():t=t.replace('/*__'+k+'__*/',v)
(ROOT/'index.html').write_text(t,encoding='utf8')
print('HTML', (ROOT/'index.html').stat().st_size)
