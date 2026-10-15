import re,json
def build(photos_path='photos.json', out='shelfmap.html'):
    s=open('src0.html').read()
    P=json.load(open(photos_path))
    js=json.dumps(P,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    m=re.search(r'(<script type="application/json" id="spinephotos">)(.*?)(</script>)',s,re.S)
    s=s[:m.start(2)]+js+s[m.end(2):]
    reps=[
     ("  // A photo shows only while the item is exactly the set that was photographed (same number of volumes).\n  const photoOf = it => { const p = PHOTOS[it.b]; return p && p.n === it.n ? p : null; };",
      "  // A photo shows only while the item is exactly the set that was photographed (same number of volumes).\n  // A set split over two levels has one photo per level, so prefer the photo taken on this level.\n  // The same set can stand twice on one level, so the item's position decides between them.\n  const photoOf = (it, sid, i) => { const ps = PHOTOS[it.b]; if (!Array.isArray(ps)) return null;\n    return ps.find(p => p.s === sid && p.i === i && p.n === it.n) || ps.find(p => p.s === sid && p.n === it.n) || ps.find(p => p.n === it.n) || null; };"),
     ("      const p = photoOf(it);", "      const p = photoOf(it, s.id, i);"),
    ]
    XB=json.load(open('extra_books.json')) if __import__('os').path.exists('extra_books.json') else {}
    if XB:
        m2=re.search(r'(<script type="application/json" id="books">)(.*?)(</script>)',s,re.S)
        bk=json.loads(m2.group(2)); have={b['id'] for b in bk}
        bk+= [b for k,b in XB.items() if k not in have]
        s=s[:m2.start(2)]+json.dumps(bk,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+s[m2.end(2):]
    for a,b in reps:
        assert s.count(a)==1,(a[:60],s.count(a)); s=s.replace(a,b)
    a="s.items.some(photoOf)"; assert s.count(a)==2; s=s.replace(a,"s.items.some(it => photoOf(it, s.id))")
    assert 'photoOf(it)' not in s
    open(out,'w').write(s); return s
if __name__=='__main__':
    s=build(); print(len(s))
