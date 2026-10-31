#!/usr/bin/env python3
"""Local OCR helper for Guatemalan DPI photos. Originals are never modified."""
from __future__ import annotations
import argparse, csv, difflib, json, re, shutil, sys, unicodedata, zipfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageOps
    import pytesseract
except ImportError as e:
    print(f"Falta dependencia: {e}. Ejecute instalar.bat o pip install -r requirements.txt", file=sys.stderr); raise SystemExit(2)

EXTS={'.jpg','.jpeg','.png','.tif','.tiff','.bmp'}
# Al elegir una carpeta de resultados anterior se vuelven a leer sus elementos
# en Revisar; Procesadas se omite para no duplicar el lote completo.
IGNORE={'procesadas','cache','caché','__pycache__'}
CUI_RE=re.compile(r'(?<!\d)(\d{4})\D{0,3}(\d{5})\D{0,3}(\d{4})(?!\d)')

def clean(s):
    s=unicodedata.normalize('NFKD',str(s or ''))
    s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+',' ',s).strip()

def norm_key(s):
    return re.sub(r'[^A-Z0-9]+','',clean(s).upper())

def digits_only(value):
    if isinstance(value,float) and value.is_integer(): value=int(value)
    raw=str(value or '').strip()
    if re.fullmatch(r'\d+\.0+',raw): raw=raw.split('.',1)[0]
    return re.sub(r'\D','',raw)

def parse_date(raw):
    if isinstance(raw,datetime): return raw.date().isoformat()
    if isinstance(raw,date): return raw.isoformat()
    value=clean(raw).upper()
    m=re.search(r'(?<!\d)([0-9O]{1,2})[./\-]([0-9O]{1,2})[./\-]([0-9O]{2,4})(?!\d)',value)
    if m:
        d,month,year=(int(x.replace('O','0')) for x in m.groups())
    else:
        m=re.search(r'(?<!\d)([0-9O]{1,2})\s*([A-Z]{3,9})\s*([0-9O]{4})(?!\d)',value)
        if not m: return None
        d,mon,year=m.groups(); d=int(d.replace('O','0')); year=int(year.replace('O','0'))
        month={'ENE':1,'JAN':1,'FEB':2,'MAR':3,'ABR':4,'APR':4,'MAY':5,'JUN':6,'JUL':7,'AGO':8,'AUG':8,'SEP':9,'SET':9,'OCT':10,'NOV':11,'DIC':12,'DEC':12}.get(mon[:3])
        if not month: return None
    year+=2000 if year<100 else 0
    try: return date(year,month,d).isoformat() if 1900<=year<=2050 else None
    except ValueError: return None

def pil_to_cv(im):
    im=ImageOps.exif_transpose(im).convert('RGB')
    return cv2.cvtColor(np.array(im),cv2.COLOR_RGB2BGR)

def prep(path):
    with Image.open(path) as im:
        im.seek(0)
        return pil_to_cv(im.copy())

def versions(img):
    # Orientation trials; grayscale plus contrast/binary variants improve OCR without changing source.
    for k in (0,1,2,3):
        rot=np.rot90(img,k).copy() if k else img
        gray=cv2.cvtColor(rot,cv2.COLOR_BGR2GRAY)
        h,w=gray.shape
        if max(h,w)<1400:
            scale=min(3.0,1400/max(h,w))
            if scale>1: gray=cv2.resize(gray,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
        yield k, gray
        clahe=cv2.createCLAHE(clipLimit=2.2,tileGridSize=(8,8)).apply(gray)
        yield k, clahe
        yield k, cv2.threshold(clahe,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]

def ocr(img,lang,psm,tessdata):
    cfg=f'--oem 1 --psm {psm}'
    if tessdata: cfg+=f' --tessdata-dir "{tessdata}"'
    return pytesseract.image_to_string(img,lang=lang,config=cfg)

def score(text):
    u=clean(text).upper()
    mrz=18 if any(x in u for x in ('IDGTM','IDETM')) else 0
    return (mrz + u.count('<<')*4 + len(CUI_RE.findall(u))*12 +
            sum(u.count(x)*3 for x in ('NOMBRE','APELLIDO','VECINDAD','VENCIMIENTO','LUGAR DE NACIMIENTO','ESTADO CIVIL','REPUBLICA','GUATEMALA')))

def extract_name_fields(text):
    lines=[clean(re.sub(r'[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]',' ',x)).upper() for x in text.splitlines()]
    stop_words=('APELLIDOS?','NOMBRES?','NACIONALIDAD','PAIS','SEXO','FECHA','CUI','DPI','VECINDAD','FIRMA','CODIGO','IDENTIFICACION')
    translations={'GIVEN NAMES','GIVEN NAME','FIRST NAME','FIRST NAMES','SURNAME','LAST NAME','FAMILY NAME'}
    def field(label,stop_pattern,max_lines):
        for i,line in enumerate(lines):
            m=re.search(r'\b'+label+r'\b\s*(.*)',line)
            if not m: continue
            values=[]
            for nxt in lines[i+1:i+1+max_lines]:
                if not nxt: continue
                if nxt in translations: continue
                if re.search(r'\b(?:'+stop_pattern+r')\b',nxt): break
                if any(re.search(r'\b'+w+r'\b',nxt) for w in stop_words): break
                values.append(nxt)
            value=clean(' '.join(values).title())
            if value and len(norm_key(value))>=4: return value
        return None
    nombres=field(r'NOMBRES?',r'APELLIDOS?|NACIONALIDAD|PAIS|SEXO|FECHA|CUI|DPI',4)
    apellidos=field(r'APELLIDOS?',r'NOMBRES?|NACIONALIDAD|PAIS|SEXO|FECHA|CUI|DPI',5)
    combined=clean(' '.join(x for x in (nombres,apellidos) if x)).title() or None
    # A one-letter or label-like OCR fragment is not a usable identity.
    bad={'CODIGO','UNICO','IDENTIFICACION','REPUBLICA','GUATEMALA','NOMBRE','APELLIDOS','CUI','DPI'}
    if combined and (len(norm_key(combined))<6 or len(combined.split())<2 or bad.intersection(re.findall(r'[A-Z]+',clean(combined).upper()))):
        return None,None,None
    return nombres,apellidos,combined

def ocr_name_region(img,lang,tessdata):
    """Read the printed name/surname block on the front of the card, away from the CUI."""
    h,w=img.shape[:2]
    # Covers both the older card layout and the newer bilingual layout, whose
    # name block starts farther left than the CUI field.
    x1,x2=int(w*.28),int(w*.66); y1,y2=int(h*.18),int(h*.62)
    roi=img[y1:y2,x1:x2]
    if roi.size==0: return ''
    gray=cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY)
    gray=cv2.resize(gray,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
    variants=[gray,cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(gray)]
    best=''; best_score=-1
    for v in variants:
        for psm in (4,6,11):
            text=ocr(v,lang,psm,tessdata)
            score=4*('NOMBRE' in clean(text).upper())+4*('APELLIDO' in clean(text).upper())+min(len(text),100)/100
            if score>best_score: best,best_score=text,score
    return best

def ocr_cui_region(img,lang,tessdata):
    """Try the CUI locations used by both older and current DPI layouts."""
    h,w=img.shape[:2]
    boxes=((.15,.45,.25,.42),(.28,.58,.36,.55))
    candidates=[]
    for xa,xb,ya,yb in boxes:
        roi=img[int(h*ya):int(h*yb),int(w*xa):int(w*xb)]
        if roi.size==0: continue
        gray=cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY)
        gray=cv2.resize(gray,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
        enhanced=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(gray)
        for variant in (gray,enhanced):
            for psm in (6,7,11):
                text=ocr(variant,lang,psm,tessdata)
                strength=12*len(CUI_RE.findall(text))+min(len(re.findall(r'\d',text)),20)/20
                candidates.append((strength,text))
    return max(candidates,key=lambda x:x[0])[1] if candidates else ''

def extract(text,name_text=''):
    up=clean(text).upper()
    compact=re.sub(r'\s+','',up)
    marker=re.search(r'I[D0][OGQE6]TM',compact)
    cui_candidates=[]
    cui_repaired_candidates=[]
    mrz_digit_run=None
    if marker:
        tail=compact[marker.end():]
        tail=re.sub(r'^[^0-9OQIL|]*','',tail)
        run=re.match(r'[0-9OQIL|]{13,}',tail)
        if run:
            mrz_digit_run=run.group(0)
            digits=run.group(0).translate(str.maketrans({'O':'0','Q':'0','I':'1','L':'1','|':'1'}))
            digits=re.sub(r'\D','',digits)
            cui_candidates=list(dict.fromkeys(digits[i:i+13] for i in range(max(0,len(digits)-12))))
            if len(digits)==14:
                cui_repaired_candidates=list(dict.fromkeys(digits[:i]+digits[i+1:] for i in range(len(digits))))
        cui=None
    else:
        cui=''.join(CUI_RE.findall(up)[0]) if CUI_RE.findall(up) else None
    # Also normalize common OCR substitutions only inside a long digit-like run.
    if not cui and not marker:
        for run in re.findall(r'[0-9OQIL| ]{13,22}',up):
            digits=re.sub(r'\D','',run.translate(str.maketrans({'O':'0','Q':'0','I':'1','L':'1','|':'1'})))
            if len(digits)==13: cui=digits; break
    lines=[re.sub(r'\s+','',x.upper()) for x in text.splitlines()]
    has_mrz_marker=bool(marker)
    mrz=[x for x in lines if '<' in x and len(x)>=20 and (has_mrz_marker or x.count('<')>=5)]
    nombres,apellidos,name=extract_name_fields(name_text) if name_text else (None,None,None)
    if not name: nombres,apellidos,name=extract_name_fields(text)
    mrz_name=None
    for line in reversed(mrz):
        if not re.search(r'[A-Z]{2,}<<[A-Z]{2,}',line) or (not has_mrz_marker and line.count('<')<5): continue
        surname_part,given_part=line.split('<<',1)
        surnames=re.findall(r'[A-Z]+',surname_part)
        given=re.findall(r'[A-Z]+',given_part)
        surnames=[x for x in surnames if len(x)>1 and x not in {'GTM','IDGTM'}]
        given=[x for x in given if len(x)>1 and x not in {'GTM','IDGTM'}]
        if surnames and given:
            # ICAO MRZ order is surname first, then given names. Use one of each
            # for reverse-face filenames and registry fallback.
            mrz_name=f'{given[0].title()} {surnames[0].title()}'
            break
    if mrz_name:
        nombres,apellidos=mrz_name.split(' ',1); name=mrz_name
    birth=expiry=None
    date_token=r'(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}|\d{1,2}\s*[A-Z]{3,9}\s*\d{4})'
    m=re.search(r'(?:FECHA\s+DE\s+)?NACIMIENTO[^\d]{0,40}'+date_token,up)
    if m: birth=parse_date(m.group(1))
    m=re.search(r'(?:VENCIMIENTO|EXPIRACION|VALIDO\s+HASTA)[^\d]{0,40}'+date_token,up)
    if m: expiry=parse_date(m.group(1))
    return {'cui':cui,'cui_candidates':cui_candidates,'cui_repaired_candidates':cui_repaired_candidates,'mrz_digit_run':mrz_digit_run,'nombre':name,'nombres':nombres,'apellidos':apellidos,'fecha_nacimiento':birth,'fecha_vencimiento':expiry,'mrz':mrz,'mrz_name':mrz_name}

def load_cader_csv(path):
    # L_TODOS.csv: three header rows, semicolon delimiter, Latin-1, data starts at row 4.
    records=[]
    with Path(path).open('r',encoding='latin-1',newline='') as f:
        rows=list(csv.reader(f,delimiter=';'))
    for row in rows[3:]:
        if len(row)<10: continue
        digits=digits_only(row[9])
        if len(digits)!=13: continue
        names=[clean(x) for x in row[3:6] if clean(x)]
        surnames=[clean(x) for x in row[6:9] if clean(x)]
        records.append({'cui':digits,'nombres':' '.join(names).title() or None,'apellidos':' '.join(surnames).title() or None,
                        'nombre':clean(' '.join(names+surnames)).title() or None,'codigo_comunidad':clean(row[0]) or None,
                        'comunidad':clean(row[1]).title() or None})
    if not records: raise RuntimeError('No encontré filas con CUI de 13 dígitos en L_TODOS.csv. Se espera separador ;, Latin-1 y CUI en la columna 10.')
    return records

def load_registry(path):
    path=Path(path)
    if path.suffix.lower()=='.csv': return load_cader_csv(path)
    try: from openpyxl import load_workbook
    except ImportError: raise RuntimeError('Para leer Excel, ejecute instalar.bat para instalar openpyxl.')
    wb=load_workbook(path,read_only=True,data_only=True); ws=wb.active
    header=None; header_row=None
    for rn,row in enumerate(ws.iter_rows(min_row=1,max_row=min(ws.max_row,15),values_only=True),1):
        keys=[norm_key(v) for v in row]
        if any(k in {'CUI','DPI','NUMERODEDPI','NUMERODEIDENTIFICACION'} for k in keys) and any('NOMBRE' in k for k in keys):
            header=keys; header_row=rn; break
    if header is None: raise RuntimeError('Use encabezados como CUI, Nombres, Apellidos, Fecha nacimiento y Fecha vencimiento.')
    def col(aliases): return next((i for i,k in enumerate(header) if k in aliases),None)
    ci=col({'CUI','DPI','NUMERODEDPI','NUMERODEIDENTIFICACION'})
    ni=col({'NOMBRES','PRENOMBRES','NOMBRE','NOMBRECOMPLETO'})
    ai=col({'APELLIDOS','APELLIDO'})
    bi=col({'FECHANACIMIENTO','FECHADENACIMIENTO','NACIMIENTO'})
    ei=col({'FECHAVENCIMIENTO','VENCIMIENTO','FECHADEVENCIMIENTO'})
    rows=[]
    for row in ws.iter_rows(min_row=header_row+1,values_only=True):
        get=lambda i: row[i] if i is not None and i<len(row) else None
        cui=digits_only(get(ci)) or None
        nombres=clean(get(ni)).title() or None; apellidos=clean(get(ai)).title() or None
        if not cui and not nombres: continue
        rows.append({'cui':cui,'nombres':nombres,'apellidos':apellidos,'nombre':clean(' '.join(x for x in (nombres,apellidos) if x)) or None,'fecha_nacimiento':parse_date(get(bi)),'fecha_vencimiento':parse_date(get(ei)),'comunidad':None})
    wb.close(); return rows

def name_similarity(a,b):
    aa=clean(a).upper(); bb=clean(b).upper()
    if not aa or not bb: return 0.0
    sequence=difflib.SequenceMatcher(None,norm_key(aa),norm_key(bb)).ratio()
    at=set(re.findall(r'[A-Z0-9]+',aa)); bt=set(re.findall(r'[A-Z0-9]+',bb))
    coverage=len(at & bt)/len(at) if at else 0.0
    return max(sequence,coverage*.90)

def official_name_contained(ocr_name,official_name):
    """Match the complete roster name in OCR order, allowing extra card surnames."""
    query=re.findall(r'[A-Z0-9]+',clean(ocr_name).upper())
    official=re.findall(r'[A-Z0-9]+',clean(official_name).upper())
    if len(official)<3 or len(query)<len(official) or query[0]!=official[0]: return False
    pos=0
    for token in official:
        try: pos=query.index(token,pos)+1
        except ValueError: return False
    return True

def match_registry(fields,registry):
    if not registry: return None,'sin registro'
    token_count=len(re.findall(r'[A-Z0-9]+',clean(fields.get('nombre','')).upper()))
    mrz_tokens=set(re.findall(r'[A-Z0-9]+',clean(fields.get('mrz_name','')).upper()))
    mrz_candidates=set(fields.get('cui_candidates') or [])
    if mrz_candidates:
        hits=[r for r in registry if r.get('cui') in mrz_candidates]
        if hits:
            if len({r.get('cui') for r in hits})==1:
                if len(hits)==1: return hits[0],'CUI exacto en MRZ'
                by_mrz=[r for r in hits if mrz_tokens and mrz_tokens.issubset(set(re.findall(r'[A-Z0-9]+',clean(r.get('nombre','')).upper())))]
                if len(by_mrz)==1: return by_mrz[0],'CUI exacto en MRZ; nombre resuelve duplicado'
                if len({(r.get('nombre'),r.get('comunidad')) for r in hits})==1: return hits[0],'CUI exacto en MRZ'
                return None,'CUI duplicado en registro; MRZ no distingue'
            by_mrz=[r for r in hits if mrz_tokens and mrz_tokens.issubset(set(re.findall(r'[A-Z0-9]+',clean(r.get('nombre','')).upper())))]
            if len(by_mrz)==1: return by_mrz[0],'MRZ y nombre coinciden con un registro'
            return None,'MRZ produce varios CUI posibles; revisar'
    repaired_candidates=set(fields.get('cui_repaired_candidates') or [])
    if repaired_candidates:
        hits=[r for r in registry if r.get('cui') in repaired_candidates]
        if hits:
            if len({r.get('cui') for r in hits})==1:
                if len(hits)==1: return hits[0],'CUI MRZ con dígito OCR sobrante; confirmado en registro'
                by_mrz=[r for r in hits if mrz_tokens and mrz_tokens.issubset(set(re.findall(r'[A-Z0-9]+',clean(r.get('nombre','')).upper())))]
                if len(by_mrz)==1: return by_mrz[0],'CUI MRZ reparado; nombre resuelve duplicado'
                if len({(r.get('nombre'),r.get('comunidad')) for r in hits})==1: return hits[0],'CUI MRZ reparado; confirmado en registro'
                return None,'CUI MRZ reparado pero duplicado en registro; revisar'
            by_mrz=[r for r in hits if mrz_tokens and mrz_tokens.issubset(set(re.findall(r'[A-Z0-9]+',clean(r.get('nombre','')).upper())))]
            if len(by_mrz)==1: return by_mrz[0],'CUI MRZ reparado y nombre coincide'
            return None,'CUI MRZ reparado produce varios registros; revisar'
    if mrz_tokens:
        by_mrz=[r for r in registry if mrz_tokens.issubset(set(re.findall(r'[A-Z0-9]+',clean(r.get('nombre','')).upper())))]
        if len(by_mrz)==1: return by_mrz[0],'nombre MRZ coincide de forma única'
        if len(by_mrz)>1: return None,'nombre MRZ aparece en varios registros; revisar'
    if fields.get('cui'):
        hits=[r for r in registry if r.get('cui')==fields['cui']]
        if len(hits)==1: return hits[0],'CUI exacto'
        if hits:
            q=norm_key(fields.get('nombre',''))
            ranked=sorted(((name_similarity(fields.get('nombre'),r.get('nombre')),r) for r in hits),key=lambda x:x[0],reverse=True) if len(q)>=6 else []
            if ranked and ranked[0][0]>=.94 and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=.08):
                return ranked[0][1],'CUI duplicado; nombre OCR distingue registro'
            return None,'CUI duplicado en registro; nombre no distingue'
        query=norm_key(fields.get('nombre',''))
        ranked=sorted(((name_similarity(fields.get('nombre'),r.get('nombre')),r) for r in registry),key=lambda x:x[0],reverse=True) if len(query)>=8 and token_count>=3 else []
        if ranked and ranked[0][0]>=.96 and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=.10):
            return ranked[0][1],f"nombre muy similar {ranked[0][0]:.0%}; CUI OCR no coincide"
        return None,'CUI no está en registro' if not ranked or ranked[0][0]<.80 else 'CUI no coincide y nombre ambiguo'
    query=norm_key(fields.get('nombre',''))
    # Si faltó leer el CUI, admite una coincidencia exacta de todos los tokens
    # oficiales en orden. Así se tolera que el DPI incluya apellidos adicionales
    # que no aparecen en el padrón, siempre que la identidad sea única.
    contained=[r for r in registry if official_name_contained(fields.get('nombre'),r.get('nombre'))]
    identities={(r.get('cui'),r.get('comunidad')) for r in contained}
    if len(identities)==1 and contained:
        return contained[0],'nombre OCR contiene todos los nombres oficiales; coincidencia única en registro'
    if len(identities)>1:
        return None,'nombre OCR coincide con varios registros; revisar Excel'
    ranked=sorted(((name_similarity(fields.get('nombre'),r.get('nombre')),r) for r in registry),key=lambda x:x[0],reverse=True) if len(query)>=6 and token_count>=3 else []
    if ranked and ranked[0][0]>=.90 and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=.08): return ranked[0][1],f"nombre aproximado {ranked[0][0]:.0%}"
    if ranked and ranked[0][0]>=.80: return None,'coincidencia de nombre ambigua; revisar Excel'
    return None,'sin coincidencia en Excel'

def side(text):
    u=clean(text).upper()
    compact=re.sub(r'\s+','',u)
    mrz_name=bool(re.search(r'[A-Z]{2,}<<[A-Z]{2,}',compact) and compact.count('<')>=5)
    has_mrz=bool(re.search(r'I[D0][OGQE6]TM',compact))
    if has_mrz or mrz_name or any(x in u for x in ('VECINDAD','NEIGHBORHOOD','LUGAR DE NACIMIENTO','ESTADO CIVIL','NUMERO DE SERIE','NÚMERO DE SERIE','VENCIMIENTO','FECHA DE VENCIMIENTO')): return 'Reverso'
    if CUI_RE.search(u) or 'NOMBRE' in u or 'APELLIDO' in u or 'NACIMIENTO' in u: return 'Adverso'
    return 'No determinado'

def safe_name(s):
    s=clean(s)
    s=re.sub(r'[<>:"/\\|?*\x00-\x1f]','',s).strip(' .-_—–')
    return (s[:100] or 'Sin identificar')

def short_official_name(record):
    given=clean(record.get('nombres','')).split()
    surnames=clean(record.get('apellidos','')).split()
    if not given or not surnames: return record.get('nombre')
    surname=surnames[0]
    if surname.upper() in {'DE','DEL','LA','LAS','LOS'} and len(surnames)>1:
        surname+=' '+surnames[1]
    return f'{given[0]} {surname}'

def unique_path(p):
    if not p.exists(): return p
    for n in range(2,10000):
        q=p.with_name(f'{p.stem} ({n}){p.suffix}')
        if not q.exists(): return q
    raise RuntimeError('No se pudo generar nombre único')

def main():
    ap=argparse.ArgumentParser(description='OCR local de fotografías de DPI; conserva originales.')
    ap.add_argument('carpeta',nargs='?',help='Carpeta con imágenes; si se omite abre selector')
    ap.add_argument('-o','--salida',help='Carpeta de salida (por defecto: <entrada>_resultado)')
    ap.add_argument('--tesseract',help='Ruta a tesseract.exe si no está en PATH')
    ap.add_argument('--tessdata',help='Carpeta con traineddata, por ejemplo .../tessdata')
    ap.add_argument('--lang',default='spa+eng',help='Idiomas instalados en Tesseract (por defecto spa+eng)')
    ap.add_argument('--registro',help='Registro opcional CSV/Excel para validar CUI y nombre')
    ap.add_argument('--sin-zip',action='store_true',help='No crear ZIP del resultado')
    args=ap.parse_args()
    registry=[]
    if args.registro:
        try: registry=load_registry(Path(args.registro).expanduser())
        except Exception as e: print(f'No se pudo leer el registro: {e}',file=sys.stderr); return 2
    src=Path(args.carpeta).expanduser() if args.carpeta else None
    if src is None:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk(); root.withdraw(); chosen=filedialog.askdirectory(title='Elige la carpeta con las fotografías')
        if not chosen: root.destroy(); print('No se eligió carpeta.'); return 1
        if not args.registro:
            args.registro=filedialog.askopenfilename(title='Listado CADER Excel/CSV (opcional; Cancelar para omitir)',filetypes=[('Excel o CSV','*.xlsx *.xlsm *.csv'),('Todos','*.*')])
            if args.registro:
                try: registry=load_registry(Path(args.registro))
                except Exception as e: root.destroy(); print(f'No se pudo leer el registro: {e}',file=sys.stderr); return 2
        root.destroy()
        src=Path(chosen)
    src=src.resolve()
    if not src.is_dir(): print(f'No existe la carpeta: {src}',file=sys.stderr); return 2
    out=Path(args.salida).expanduser().resolve() if args.salida else src.parent/(src.name+'_resultado')
    if out==src or src in out.parents: print('La salida debe estar fuera de la carpeta de entrada.',file=sys.stderr); return 2
    if args.tesseract:
        pytesseract.pytesseract.tesseract_cmd=args.tesseract
    else:
        candidates=[Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe")]
        for candidate in candidates:
            if candidate.is_file():
                pytesseract.pytesseract.tesseract_cmd=str(candidate)
                break
    try: pytesseract.get_tesseract_version()
    except Exception as e: print(f'No se encuentra Tesseract. Instálelo y/o indique --tesseract. Detalle: {e}',file=sys.stderr); return 2
    files=sorted(p for p in src.rglob('*') if p.is_file() and p.suffix.lower() in EXTS and not any(x.lower() in IGNORE for x in p.relative_to(src).parts[:-1]))
    if not files: print('No se encontraron imágenes compatibles.'); return 0
    processed=out/'Procesadas'; review=out/'Revisar'; processed.mkdir(parents=True,exist_ok=True); review.mkdir(parents=True,exist_ok=True)
    report=[]
    for idx,path in enumerate(files,1):
        print(f'[{idx}/{len(files)}] {path.name}')
        best=(-1,'',0)
        try:
            img=prep(path)
            for k,v in versions(img):
                txt=ocr(v,args.lang,6,args.tessdata)
                sc=score(txt)
                if sc>best[0]: best=(sc,txt,k)
            # A second mode can recover sparse/MRZ layouts.
            txt2=ocr(img,args.lang,11,args.tessdata)
            if score(txt2)>best[0]: best=(score(txt2),txt2,0)
            text=best[1]
            oriented=np.rot90(img,best[2]).copy() if best[2] else img
            name_text=ocr_name_region(oriented,args.lang,args.tessdata)
            cui_text=ocr_cui_region(oriented,args.lang,args.tessdata)
            fields=extract(cui_text+'\n'+text,name_text); face=side(text)
            cui_ocr=fields['cui']; cui=cui_ocr; cui_registro=None
            nombre_ocr=fields['nombre']; name=nombre_ocr
            expiry_ocr=fields['fecha_vencimiento']; expiry=expiry_ocr; birth=fields['fecha_nacimiento']
            matched,validation=match_registry(fields,registry)
            name_similarity_score=None; expiry_registry=None
            if matched:
                cui_registro=matched.get('cui'); cui=cui_registro or cui
                name_similarity_score=name_similarity(nombre_ocr,matched.get('nombre')) if nombre_ocr else None
                if validation.startswith('nombre OCR contiene todos los nombres oficiales'):
                    # Preserve extra surname tokens read from the card; the
                    # register is used to confirm the match and provide CUI/community.
                    alerts.append('Coincidencia única por nombre con el padrón; se conservó el nombre completo leído en la tarjeta.')
                else:
                    fields['nombres']=matched.get('nombres') or fields['nombres']
                    fields['apellidos']=matched.get('apellidos') or fields['apellidos']
                    name=matched.get('nombre') or name
                birth=birth or matched.get('fecha_nacimiento')
                expiry_registry=matched.get('fecha_vencimiento')
                expiry=expiry or expiry_registry
            reason=[]
            alerts=[]
            if not cui: reason.append('CUI no detectado')
            if not name: reason.append('Nombre no detectado')
            if face=='No determinado': reason.append('Cara no determinada')
            if registry and not matched: reason.append(validation)
            if matched and cui_ocr and cui_registro and cui_ocr!=cui_registro: reason.append('CUI OCR distinto al registro; revisar')
            if matched and cui_ocr==cui_registro and nombre_ocr and name_similarity_score is not None and name_similarity_score<.70:
                alerts.append('El OCR del nombre fue débil; se usó el nombre oficial porque el CUI coincide exactamente.')
            if expiry_ocr and expiry_registry and expiry_ocr!=expiry_registry:
                reason.append('Fecha de vencimiento OCR distinta al registro; revisar')
            state='No determinado'
            if expiry:
                state='Vigente' if date.fromisoformat(expiry)>=date.today() else 'Vencido'
                if state=='Vencido': reason.append('DPI vencido')
            confidence=round(min(0.98,0.25+(0.22 if cui else 0)+(0.2 if name else 0)+(0.16 if face!='No determinado' else 0)+(0.12 if expiry else 0)+(0.05 if best[0]>=10 else 0)+(0.1 if matched else 0)),2)
            destdir=review if reason else processed
            face_label={'Adverso':'1. Adverso','Reverso':'2. Reverso'}.get(face,'Revisar')
            filename_name=fields.get('mrz_name') if face=='Reverso' and fields.get('mrz_name') else name
            if face=='Reverso' and matched and name_similarity_score is not None and name_similarity_score<.70:
                filename_name=short_official_name(matched)
            filename_name=filename_name or name or cui or path.stem
            dest=unique_path(destdir/f'{safe_name(filename_name)} - {face_label}{path.suffix.lower()}')
            shutil.copy2(path,dest)
            report.append({'archivo_original':str(path),'archivo_nuevo':str(dest),'nombre':name,'nombre_archivo':filename_name,'nombre_ocr':nombre_ocr,'similitud_nombre_registro':round(name_similarity_score,3) if name_similarity_score is not None else None,'nombres':fields['nombres'],'apellidos':fields['apellidos'],'cui':cui,'cui_ocr':cui_ocr,'cui_mrz_original':fields['mrz_digit_run'],'cui_candidatos_mrz':fields['cui_candidates'],'cui_reparados_mrz':fields['cui_repaired_candidates'],'cui_registro':cui_registro,'codigo_comunidad_cader':matched.get('codigo_comunidad') if matched else None,'comunidad':matched.get('comunidad') if matched else None,'comunidad_cader':matched.get('comunidad') if matched else None,'fecha_nacimiento':birth,'fecha_vencimiento':expiry,'fecha_vencimiento_ocr':expiry_ocr,'fecha_vencimiento_registro':expiry_registry,'estado':state,'cara':face,'confianza':confidence,'validacion_registro':validation,'alertas':alerts,'motivo_revision':reason,'mrz_detectada':bool(fields['mrz']),'nombre_mrz':fields['mrz_name'],'rotacion_grados':best[2]*90,'texto_ocr':text[:1200],'texto_ocr_nombre':name_text[:500],'texto_ocr_cui':cui_text[:500]})
        except Exception as e:
            dest=unique_path(review/f'{safe_name(path.stem)} - Error{path.suffix.lower()}')
            try: shutil.copy2(path,dest)
            except Exception: dest=None
            report.append({'archivo_original':str(path),'archivo_nuevo':str(dest) if dest else None,'nombre':None,'nombre_archivo':None,'nombre_ocr':None,'nombres':None,'apellidos':None,'cui':None,'cui_ocr':None,'cui_candidatos_mrz':[],'cui_reparados_mrz':[],'cui_registro':None,'codigo_comunidad_cader':None,'comunidad':None,'comunidad_cader':None,'fecha_nacimiento':None,'fecha_vencimiento':None,'estado':'No determinado','cara':'No determinado','confianza':0,'validacion_registro':'error','alertas':[],'motivo_revision':[f'Error: {e}'],'texto_ocr':''})
    jsonpath=out/'reporte.json'
    jsonpath.write_text(json.dumps({'herramienta':'Tesseract OCR','idiomas':args.lang,'fecha_proceso':date.today().isoformat(),'registro_usado':bool(registry),'cantidad':len(report),'registros':report},ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.sin_zip:
        zip_path=out.with_suffix('.zip')
        with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
            for p in out.rglob('*'):
                if p.is_file(): z.write(p,p.relative_to(out.parent))
        print(f'ZIP: {zip_path}')
    print(f'Reporte: {jsonpath}\nProcesadas: {len(files)}. Revisar: {sum(bool(x.get("motivo_revision")) for x in report)}')
    return 0

if __name__=='__main__': raise SystemExit(main())

