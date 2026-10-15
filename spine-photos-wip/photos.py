import os
U='/root/.claude/uploads/1b0dbdb4-5408-5e23-bb28-311d8f83a541/'
def ordered():
    fs=[(os.stat(U+f).st_mtime_ns, f[:8]) for f in os.listdir(U) if f.endswith('.jpg')]
    return [f for t,f in sorted(fs)]
def path(pid): return U+pid+'-image.jpg'
