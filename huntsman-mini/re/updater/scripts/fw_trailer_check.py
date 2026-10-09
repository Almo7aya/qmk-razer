import zlib, struct
p = r"Z:\projects\github\qmk-razer\huntsman-mini\stock\firmware\HuntsmanMini_dev1_v1.12.00.bin"
b = open(p, "rb").read()
print("len", len(b), hex(len(b)), "end", hex(0x08004000+len(b)))
print("vec SP=%08x reset=%08x" % struct.unpack_from("<II", b, 0))
print("tail", b[-48:].hex())
crc = zlib.crc32(b) & 0xffffffff
print("crc32 whole", hex(crc))
crc_wo = zlib.crc32(b[:-4]) & 0xffffffff
print("crc32 w/o last4", hex(crc_wo), "last4 le", hex(struct.unpack_from("<I", b, len(b)-4)[0]))
s = sum(b) & 0xffff
print("sum16", hex(s), "sum32", hex(sum(b) & 0xffffffff))
x = 0
for c in b: x ^= c
print("xor8", hex(x))
for name, val in [("len", len(b)), ("end", 0x08004000+len(b)), ("crc", crc)]:
    for fmt in ("<I", ">I"):
        pat = struct.pack(fmt, val)
        i = b.find(pat)
        if i >= 0: print("found", name, fmt, "at", hex(0x08004000+i))
# look for words in first 0x200 after vectors that look like magic
for off in range(0, 0x200, 4):
    w = struct.unpack_from("<I", b, off)[0]
    if not (0x08004000 <= w < 0x08040000) and w not in (0,) and not (0x20000000 <= w < 0x20008000):
        print("non-ptr word in vector area at", hex(0x08004000+off), hex(w))
