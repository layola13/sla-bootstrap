#!/usr/bin/env python3
"""阶段出口门对拍（tag 名集/序）：Zig lexer/ast ↔ SLA 移植版。

不依赖编译运行：静态解析三者 tag 名列表，逐项比对名字与序号。
这是发射逐字节对拍的前置——tag 名集/序不一致则后续对拍无意义。
"""
import re, sys

def zig_lexer_tags(path):
    src=open(path,encoding='utf-8').read().split('\n')
    tags=[]; inside=False
    for l in src:
        if l.strip()=='pub const Tag = enum {': inside=True; continue
        if inside and l.strip()=='};': break
        if inside:
            m=re.match(r'\s*(\w+),',l)
            if m: tags.append(m.group(1))
    return tags

def zig_ast_node_tags(path):
    src=open(path,encoding='utf-8').read().split('\n')
    tags=[]; inside=False
    for l in src:
        if l.startswith('pub const Node = union(enum) {'): inside=True; continue
        if inside and l.strip()=='};': break
        if inside:
            m=re.match(r'^    (\w+):',l)
            if m: tags.append(m.group(1))
    return tags

def sla_tags(path, prefix):
    tags={}
    for l in open(path,encoding='utf-8'):
        m=re.match(r'const ('+prefix+r'[A-Z0-9_]+): i32 = (\d+);',l)
        if m: tags[int(m.group(2))]=m.group(1)
    return [tags[i] for i in sorted(tags)]

def norm_lexer(t): return t.upper().replace('TAG_','',1)
def norm_ast(t): return t.upper().replace('NODE_','',1)

PLUG='/content/sa_all/sa_plugin_sla/src'
BASE='/content/sa_all/sla-bootstrap/crates'

def compare(name, a, b, norm):
    na=[norm(x) for x in a]; nb=[norm(x) for x in b]
    ok = na==nb
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: zig={len(a)} sla={len(b)}")
    if not ok:
        for i,(x,y) in enumerate(zip(na,nb)):
            if x!=y: print(f"  idx {i}: zig={x} sla={y}")
        if len(na)!=len(nb): print(f"  length mismatch at {min(len(na),len(nb))}")
    return ok

r1=compare('lexer.Tag', zig_lexer_tags(PLUG+'/lexer.zig'), sla_tags(BASE+'/sla-lexer/src/token.sla','TAG_'), norm_lexer)
r2=compare('ast.Node', zig_ast_node_tags(PLUG+'/ast.zig'), sla_tags(BASE+'/sla-ast/src/ast.sla','NODE_'), norm_ast)

# 关键字表 1:1（Zig checkKeyword ↔ SLA KW_* 常量）
def zig_keywords(path):
    s=open(path,encoding='utf-8').read()
    return set(m.group(1) for m in re.finditer(r'eql\(u8, str, "([a-z_]+)"\)\)',s))
def sla_keywords(path):
    s=open(path,encoding='utf-8').read()
    words=set()
    for m in re.finditer(r'const KW_[A-Z_]+: u64 = (\d+);',s):
        v=int(m.group(1))
        words.add(bytes((v>>(8*i))&0xff for i in range(8)).rstrip(b'\x00').decode())
    return words
zk=zig_keywords(PLUG+'/lexer.zig'); sk=sla_keywords(BASE+'/sla-lexer/src/lexer.sla')
r3 = zk==sk
print(f"[{'PASS' if r3 else 'FAIL'}] lexer keywords: zig={len(zk)} sla={len(sk)}")
if not r3:
    print("  missing:",sorted(zk-sk),"extra:",sorted(sk-zk))
sys.exit(0 if (r1 and r2 and r3) else 1)
