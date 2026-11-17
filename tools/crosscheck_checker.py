#!/usr/bin/env python3
"""checker 仿射状态机 ↔ sci capability.zig 能力位/转移表对拍。"""
import sys
import re
CAP="/content/sa_all/sci/src/common/capability.zig"
CK='crates/sla-checker/src/checker.sla'
# sci 能力位
sci=open(CAP,encoding='utf-8').read()
cap={}
for m in re.finditer(r'(\w+) = 0x([0-9A-Fa-f]+),',sci):
    cap[m.group(1)]=int(m.group(2),16)
sla=open(CK,encoding='utf-8').read()
sla_caps={}
for m in re.finditer(r'const ST_(\w+): u16 = (\d+);',sla):
    sla_caps[m.group(1)]=int(m.group(2))
# 映射：UNAINIT->uninitialized, ACTIVE->active, LOCKED_READ->locked_read,
# LOCKED_MUT->locked_mut, CONSUMED->consumed
mp={'UNAINIT':'uninitialized','ACTIVE':'active','LOCKED_READ':'locked_read','LOCKED_MUT':'locked_mut','CONSUMED':'consumed'}
ok=True
for k,v in mp.items():
    sci_v=cap.get(v)
    sla_v=sla_caps.get(k)
    if sci_v!=sla_v:
        print(f"FAIL {k}: sci {v}={sci_v} sla={sla_v}"); ok=False
print(f"[{'PASS' if ok else 'FAIL'}] capability bits: sci={len(cap)} sla={len(sla_caps)}")
print(f"  bits: { {k:sla_caps.get(k) for k in mp} }")
sys.exit(0 if ok else 1)
