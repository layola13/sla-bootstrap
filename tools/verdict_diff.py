#!/usr/bin/env python3
"""阶段出口门：verdict 名集对拍。

用法: tools/verdict_diff.py <baseline.txt> <current.txt>
比较两份 verdict 名集（逐文件 PASS/FAIL:<trap>/SKIP:<reason>）是否逐项相等。
阶段门纪律（EXECUTION_PLAN §3）：只看计数不算过，必须逐名相等。
"""
import sys

def load(path):
    d={}
    for line in open(path,encoding='utf-8'):
        line=line.strip()
        if not line or line.startswith('#'): continue
        parts=line.split(' ',1)
        if len(parts)!=2: continue
        d[parts[0]]=parts[1]
    return d

a=load(sys.argv[1]); b=load(sys.argv[2])
only_a=sorted(set(a)-set(b)); only_b=sorted(set(b)-set(a))
diff=sorted(k for k in set(a)&set(b) if a[k]!=b[k])
ok=not(only_a or only_b or diff)
print(f"[{'PASS' if ok else 'FAIL'}] verdict name-set: baseline={len(a)} current={len(b)}")
if only_a: print("  only in baseline:",only_a)
if only_b: print("  only in current:",only_b)
if diff:
    for k in diff: print(f"  {k}: baseline={a[k]} current={b[k]}")
sys.exit(0 if ok else 1)
