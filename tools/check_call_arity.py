#!/usr/bin/env python3
"""Mole #5 hunter: expand includes of a shader program, collect function
definitions (incl. function-like macros) and calls, report calls whose
argument count matches no known definition arity."""
import re, sys, os

PACK = sys.argv[1] if len(sys.argv) > 1 else r"shaderpacks/ComplementaryReimagined_r5.8.1 + EuphoriaPatches_1.9.3 + Supplemental Patches/shaders"
ENTRY = sys.argv[2] if len(sys.argv) > 2 else "/program/gbuffers_entities.glsl"

seen_files = []
lines_out = []  # (file, lineno, text)

def expand(path, depth=0):
    if depth > 40:
        return
    full = os.path.join(PACK, path.lstrip("/"))
    if not os.path.isfile(full):
        lines_out.append((path, 0, f"// MISSING INCLUDE {path}"))
        return
    seen_files.append(path)
    base_dir = os.path.dirname(path)
    with open(full, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            m = re.match(r'\s*#include\s+"([^"]+)"', line)
            if m:
                inc = m.group(1)
                if not inc.startswith("/"):
                    inc = base_dir + "/" + inc
                expand(inc, depth + 1)
            else:
                lines_out.append((path, i, line.rstrip("\n")))

expand(ENTRY)
src_join = "\n".join(t for (_, _, t) in lines_out)

BUILTINS = set("""texture texture2D texture2DLod textureLod textureGrad texelFetch textureSize
vec2 vec3 vec4 ivec2 ivec3 ivec4 uvec2 uvec3 uvec4 mat2 mat3 mat4 float int uint bool
abs min max clamp mix smoothstep step floor ceil fract mod pow exp exp2 log log2 sqrt
inversesqrt sin cos tan asin acos atan length distance dot cross normalize reflect refract
dFdx dFdy fwidth transpose inverse sign radians degrees any all not equal notEqual
lessThan lessThanEqual greaterThan greaterThanEqual round trunc isnan isinf
unpackUnorm2x16 packUnorm2x16 floatBitsToInt intBitsToFloat imageLoad imageStore
shadow2D shadow2DLod gl_FragData defined return if for while switch
""".split())

# ---- collect definitions: "type name(params) {" or ";" (prototypes) ----
def count_args(argstr):
    s = argstr.strip()
    if s == "" or s == "void":
        return 0
    depth = 0; n = 1
    for ch in s:
        if ch in "([": depth += 1
        elif ch in ")]": depth -= 1
        elif ch == "," and depth == 0: n += 1
    return n

defs = {}  # name -> set of arities
DEF_RE = re.compile(r'^\s*(?:const\s+)?(?:void|float|int|uint|bool|[iu]?vec[234]|mat[234](?:x[234])?)\s+(\w+)\s*\(([^)]*)\)\s*(?:\{|;)?\s*$')
MACRO_RE = re.compile(r'^\s*#define\s+(\w+)\(([^)]*)\)')
# multi-line defs: join continuation by scanning raw text instead
RAW_DEF_RE = re.compile(r'(?:^|\n)\s*(?:const\s+)?(?:void|float|int|uint|bool|[iu]?vec[234]|mat[234](?:x[234])?)\s+(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)\s*\{', re.S)

for m in RAW_DEF_RE.finditer(src_join):
    name, args = m.group(1), m.group(2)
    defs.setdefault(name, set()).add(count_args(args))
for (f, i, t) in lines_out:
    m = MACRO_RE.match(t)
    if m:
        defs.setdefault(m.group(1), set()).add(count_args(m.group(2)))

# ---- collect calls with file/line, scanning joined text for multi-line calls ----
CALL_RE = re.compile(r'\b(\w+)\s*\(')
mismatches = []
# build a char-offset -> (file,line) map
offsets = []
pos = 0
for (f, i, t) in lines_out:
    offsets.append((pos, f, i))
    pos += len(t) + 1

def locate(off):
    lo, hi = 0, len(offsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offsets[mid][0] <= off: lo = mid
        else: hi = mid - 1
    return offsets[lo][1], offsets[lo][2]

for m in CALL_RE.finditer(src_join):
    name = m.group(1)
    if name in BUILTINS or name not in defs:
        continue
    # skip if this is the definition itself (preceded by a type token)
    pre = src_join[max(0, m.start()-40):m.start()]
    if re.search(r'(?:void|float|int|uint|bool|[iu]?vec[234]|mat[234](?:x[234])?)\s+$', pre):
        continue
    if re.search(r'#define\s+$', pre):
        continue
    # extract arg string to matching close paren
    depth = 1; j = m.end()
    while j < len(src_join) and depth > 0:
        if src_join[j] in "(": depth += 1
        elif src_join[j] == ")": depth -= 1
        j += 1
    args = src_join[m.end():j-1]
    n = count_args(args)
    if n not in defs[name]:
        f, ln = locate(m.start())
        mismatches.append((f, ln, name, n, sorted(defs[name])))

print(f"expanded {len(seen_files)} files, {len(lines_out)} lines")
print(f"definitions: {len(defs)} names")
if not mismatches:
    print("NO ARITY MISMATCHES FOUND")
for (f, ln, name, n, expect) in mismatches:
    print(f"MISMATCH {f}:{ln} call {name}() with {n} args, defined arities {expect}")
