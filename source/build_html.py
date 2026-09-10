"""Build an offline single-file 3D viewer; PDFs are only read, never modified."""
from pathlib import Path
import json, base64, io
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'source'
ASSET_PATH=ROOT/'assets'/'drawings.json'
if not ASSET_PATH.exists():
    import fitz
    sources=[
      ('-1','B1 · 지하 평면 수정후','01 설계변경도면_건축.pdf',37,'지하층 실 구획과 기계실·물탱크실. 건축 PDF 37쪽.'),
      ('0','1F · 1층 평면 수정후','01 설계변경도면_건축.pdf',40,'로비, 책누리터, 북카페와 다목적실. 건축 PDF 40쪽.'),
      ('1','2F · 2층 평면 수정후','01 설계변경도면_건축.pdf',43,'자료실, 열린 책누리터, 서고와 강의공간. 건축 PDF 43쪽.'),
      ('2','3F · 3층 평면 수정후','01 설계변경도면_건축.pdf',46,'청소년자료실, 마을공방, 사무공간 및 데크. 건축 PDF 46쪽.'),
      ('3','4F · 4층 평면 수정후','01 설계변경도면_건축.pdf',49,'서진홀, 그룹회의실, 강의실 및 데크. 건축 PDF 49쪽.'),
      ('4','RF · 옥상 평면 수정후','01 설계변경도면_건축.pdf',52,'옥상 정원, 열린 공간과 설비 위치. 건축 PDF 52쪽.'),
      ('elevation','외관 · 남측면 수정후','01 설계변경도면_건축.pdf',56,'아치·외피·창호의 반복과 신축/리모델링부 관계. 건축 PDF 56쪽.'),
      ('section','높이 · 종단면 수정후','01 설계변경도면_건축.pdf',67,'층간 높이와 공간 관계를 확인하는 참고 단면. 건축 PDF 67쪽.'),
      ('civil','토목 · 포장계획 수정후','02 설계변경도면_토목.pdf',16,'부지·포장 구역의 위치를 참고했습니다. 지반 상세와 매설 배관은 전체 복원하지 않았습니다. 토목 PDF 16쪽.'),
      ('landscape','조경 · 식재계획 변경','03 설계변경도면_조경.pdf',9,'식재 구역·나무 위치를 참고했습니다. 나무의 개별 수형·규격은 단순화한 표현입니다. 조경 PDF 9쪽.'),
      ('terrace','조경 · 층별시설물 계획','03 설계변경도면_조경.pdf',10,'테라스·옥상 화분, 플랜터와 연식의자 계획. 조경 PDF 10쪽.'),
      ('mep','기계설비 · 지하 기계실','04 설계변경도면_기계설비.pdf',9,'저수조와 펌프 등 주요 장비의 형태·위치를 참고했습니다. 전체 배관망을 복원한 모델은 아닙니다. 기계설비 PDF 9쪽.'),
      ('mep-roof','기계설비 · 옥탑 냉난방','04 설계변경도면_기계설비.pdf',16,'옥상 주요 냉난방 실외기의 위치를 단순화해 표현했습니다. 기계설비 PDF 16쪽.'),
    ]
    assets={};docs={}
    for key,title,fn,page,caption in sources:
        if fn not in docs:docs[fn]=fitz.open('/mnt/data/'+fn)
        p=docs[fn][page-1];pix=p.get_pixmap(matrix=fitz.Matrix(1.65,1.65),alpha=False)
        im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        im.thumbnail((2050,1600));bio=io.BytesIO();im.save(bio,format='JPEG',quality=85,optimize=True)
        assets[key]={'title':title,'data':'data:image/jpeg;base64,'+base64.b64encode(bio.getvalue()).decode(),'caption':caption}
    ASSET_PATH.write_text(json.dumps(assets,ensure_ascii=False,separators=(',',':')))
else:assets=json.loads(ASSET_PATH.read_text())
template=(SRC/'template.html').read_text()
subs={'STYLE':(SRC/'style.css').read_text(),'MODEL':(ROOT/'model.json').read_text(),'ASSETS':json.dumps(assets,ensure_ascii=False,separators=(',',':')),'GLB':base64.b64encode((ROOT/'Gayang_Library.glb').read_bytes()).decode(),'VIEWER':(SRC/'viewer.js').read_text()}
for key,value in subs.items():template=template.replace('/*__'+key+'__*/',value)
out=ROOT/'Gayang_Library_3D.html';out.write_text(template,encoding='utf-8')
print(out,out.stat().st_size,'bytes')
