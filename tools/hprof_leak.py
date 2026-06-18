#!/usr/bin/env python3
"""Minimal HPROF (JAVA PROFILE 1.0.2) analyzer for leak hunting.
Pass 1: class histogram (instance count + bytes) + collect target-class instance ids
        + class instance-field layouts + superclass chain.
Pass 2: scan every instance & object-array for references TO the target ids ->
        tally which classes (and which fields) hold them = the retainer.
Usage: hprof_leak.py <file.hprof> [target_substr=ServerPlayer]
"""
import sys, struct, mmap
from collections import defaultdict, Counter

PATH = sys.argv[1]
TARGET = sys.argv[2] if len(sys.argv) > 2 else "ServerPlayer"

# basic-type sizes (id size resolved at runtime)
BT = {4: 1, 5: 2, 6: 4, 7: 8, 8: 1, 9: 2, 10: 4, 11: 8}  # bool,char,float,double,byte,short,int,long


def run():
    f = open(PATH, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    # header
    p = mm.find(b"\0") + 1
    idsize = struct.unpack_from(">I", mm, p)[0]; p += 4
    p += 8  # timestamp
    assert idsize == 8, f"unexpected id size {idsize}"
    BT[2] = idsize
    n = len(mm)

    strings = {}      # id -> str
    classname = {}    # class_obj_id -> name (dotted)
    load_name = {}    # class_obj_id -> name_string_id
    layout = {}       # class_obj_id -> (super_id, [(field_name_id, type), ...])
    hist_cnt = Counter()
    hist_bytes = Counter()
    target_ids = set()
    target_class_ids = set()

    def rd(fmt, off):
        return struct.unpack_from(fmt, mm, off)

    # ---------- PASS 1 ----------
    p0 = p
    while p < n:
        tag = mm[p]; rec_len = rd(">I", p + 5)[0]; body = p + 9; p = body + rec_len
        if tag == 0x01:  # STRING
            sid = rd(">Q", body)[0]
            strings[sid] = mm[body + 8: body + rec_len].decode("utf-8", "replace")
        elif tag == 0x02:  # LOAD_CLASS
            cid = rd(">Q", body + 4)[0]; nid = rd(">Q", body + 16)[0]
            load_name[cid] = nid
        elif tag in (0x0C, 0x1C):  # HEAP_DUMP / SEGMENT
            q = body; end = body + rec_len
            while q < end:
                st = mm[q]; q += 1
                if st == 0x20:  # CLASS_DUMP
                    cid = rd(">Q", q)[0]
                    sup = rd(">Q", q + 8 + 4)[0]
                    q2 = q + 8 + 4 + 8 + 8 + 8 + 8 + 8 + 8 + 4  # ->constant pool count
                    cpn = rd(">H", q2)[0]; q2 += 2
                    for _ in range(cpn):
                        t = mm[q2 + 2]; q2 += 3 + BT[t]
                    sfn = rd(">H", q2)[0]; q2 += 2
                    for _ in range(sfn):
                        t = mm[q2 + idsize]; q2 += idsize + 1 + BT[t]
                    ifn = rd(">H", q2)[0]; q2 += 2
                    fields = []
                    for _ in range(ifn):
                        fnid = rd(">Q", q2)[0]; t = mm[q2 + idsize]; q2 += idsize + 1
                        fields.append((fnid, t))
                    layout[cid] = (sup, fields)
                    q = q2
                elif st == 0x21:  # INSTANCE_DUMP
                    oid = rd(">Q", q)[0]; cid = rd(">Q", q + 8 + 4)[0]
                    nb = rd(">I", q + 8 + 4 + 8)[0]
                    hist_cnt[cid] += 1; hist_bytes[cid] += nb
                    if cid in target_class_ids:
                        target_ids.add(oid)
                    q += 8 + 4 + 8 + 4 + nb
                elif st == 0x22:  # OBJECT_ARRAY_DUMP
                    ne = rd(">I", q + 8 + 4)[0]
                    q += 8 + 4 + 4 + idsize + ne * idsize
                elif st == 0x23:  # PRIMITIVE_ARRAY_DUMP
                    ne = rd(">I", q + 8 + 4)[0]; t = mm[q + 8 + 4 + 4]
                    q += 8 + 4 + 4 + 1 + ne * BT[t]
                elif st in (0xFF, 0x05, 0x07):  # roots: id
                    q += idsize
                elif st == 0x01:  # ROOT_JNI_GLOBAL id+id
                    q += idsize * 2
                elif st in (0x02, 0x03):  # id+u4+u4
                    q += idsize + 8
                elif st in (0x04, 0x06, 0x08):  # id+u4 (0x08 id+u4+u4)
                    q += idsize + (8 if st == 0x08 else 4)
                else:
                    raise RuntimeError(f"unknown subrec 0x{st:02x} at {q-1}")
        # resolve target class ids as soon as load_name known (cheap re-check)
        if tag == 0x02:
            nm = strings.get(load_name[cid])
            if nm and TARGET.lower() in nm.replace("/", ".").lower():
                target_class_ids.add(cid)

    for cid, nid in load_name.items():
        classname[cid] = (strings.get(nid, "?")).replace("/", ".")

    # report histogram
    print(f"== top classes by instance count ==")
    for cid, c in hist_cnt.most_common(18):
        print(f"  {c:8d}  {hist_bytes[cid]//1024:8d}KB  {classname.get(cid,'?')}")
    print(f"\n== target '{TARGET}' classes ==")
    for cid in target_class_ids:
        print(f"  {hist_cnt.get(cid,0)} instances  {classname.get(cid,'?')}  (ids collected: {len(target_ids)})")

    if not target_ids:
        print("no target instances found"); return

    # ---------- PASS 2: who references the target ids ----------
    # precompute full field chain (obj fields only) per class
    chain = {}
    def get_chain(cid):
        if cid in chain: return chain[cid]
        out = []
        c = cid
        seen = set()
        while c and c in layout and c not in seen:
            seen.add(c)
            sup, fields = layout[c]
            for fnid, t in fields:
                out.append((fnid, t))
            c = sup
        chain[cid] = out
        return out

    referrers = Counter()      # referrer class -> count
    referrer_field = Counter()  # (referrer class, field name) -> count
    p = p0
    while p < n:
        tag = mm[p]; rec_len = rd(">I", p + 5)[0]; body = p + 9; p = body + rec_len
        if tag in (0x0C, 0x1C):
            q = body; end = body + rec_len
            while q < end:
                st = mm[q]; q += 1
                if st == 0x20:  # CLASS_DUMP (skip, sized as pass1)
                    q2 = q + 8 + 4 + 8 + 8 + 8 + 8 + 8 + 8 + 4
                    cpn = rd(">H", q2)[0]; q2 += 2
                    for _ in range(cpn):
                        t = mm[q2 + 2]; q2 += 3 + BT[t]
                    sfn = rd(">H", q2)[0]; q2 += 2
                    for _ in range(sfn):
                        t = mm[q2 + idsize]; q2 += idsize + 1 + BT[t]
                    ifn = rd(">H", q2)[0]; q2 += 2 + ifn * (idsize + 1)
                    q = q2
                elif st == 0x21:  # INSTANCE_DUMP -> check ref fields
                    oid = rd(">Q", q)[0]; cid = rd(">Q", q + 12)[0]; nb = rd(">I", q + 20)[0]
                    fbase = q + 24
                    off = fbase
                    for fnid, t in get_chain(cid):
                        sz = BT[t]
                        if t == 2:  # object ref
                            ref = rd(">Q", off)[0]
                            if ref in target_ids:
                                cn = classname.get(cid, "?")
                                referrers[cn] += 1
                                referrer_field[(cn, strings.get(fnid, "?"))] += 1
                        off += sz
                    q = fbase + nb
                elif st == 0x22:  # OBJECT_ARRAY_DUMP -> check elements
                    ne = rd(">I", q + 12)[0]; acid = rd(">Q", q + 16)[0]
                    ebase = q + 16 + idsize
                    hit = False
                    for i in range(ne):
                        if rd(">Q", ebase + i * idsize)[0] in target_ids:
                            hit = True
                    if hit:
                        referrers["[array] " + classname.get(acid, "?")] += 1
                    q = ebase + ne * idsize
                elif st == 0x23:
                    ne = rd(">I", q + 12)[0]; t = mm[q + 16]; q += 17 + ne * BT[t]
                elif st in (0xFF, 0x05, 0x07):
                    q += idsize
                elif st == 0x01:
                    q += idsize * 2
                elif st in (0x02, 0x03):
                    q += idsize + 8
                elif st in (0x04, 0x06, 0x08):
                    q += idsize + (8 if st == 0x08 else 4)
                else:
                    raise RuntimeError(f"p2 unknown 0x{st:02x}")

    print(f"\n== DIRECT HOLDERS of {TARGET} (referrer class -> how many refs) ==")
    for cn, c in referrers.most_common(20):
        print(f"  {c:5d}  {cn}")
    print(f"\n== holder field detail ==")
    for (cn, fn), c in referrer_field.most_common(20):
        print(f"  {c:5d}  {cn} . {fn}")


run()
