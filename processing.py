"""Unity AssetBundle প্রসেসিং: Mesh ইমপোর্ট → Texture ইমপোর্ট → সাইজ ম্যাচ"""
import io
import re
import struct

from PIL import Image

from mesh_dump import deep_merge, looks_like_text_dump, parse_uabe_dump

EXPECT = {"mesh": "Mesh", "d": "Texture2D", "n": "Texture2D", "s": "Texture2D"}


class ProcessingError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def clean_id(v) -> str:
    s = str(v if v is not None else "").strip()
    if s in ("", "0"):
        return ""
    if not re.fullmatch(r"-?\d+", s):
        raise ProcessingError(f"Path ID অবশ্যই সংখ্যা হতে হবে (যেমন -6210741933801247858): '{s}'")
    return s


def _load(data):
    import UnityPy

    try:
        return UnityPy.load(bytes(data))
    except Exception as e:
        raise ProcessingError(f"Unity ফাইল লোড করা যায়নি: {e}") from e


def _index(env):
    return {str(o.path_id): o for o in env.objects}


def _save(env, packer="none"):
    f = getattr(env, "file", None)
    if f is None:
        f = next(iter(env.files.values()))
    try:
        return bytes(f.save(packer=packer))
    except TypeError:
        return bytes(f.save())


def bundle_header(data: bytes):
    """UnityFS হেডার থেকে কম্প্রেশন টাইপ পড়ে (none/lzma/lz4)।"""
    try:
        if data[:7] != b"UnityFS":
            return None
        pos = 8
        version = struct.unpack(">I", data[pos:pos + 4])[0]
        pos += 4
        for _ in range(2):
            pos = data.index(b"\x00", pos) + 1
        size, _c, _u, flags = struct.unpack(">qIII", data[pos:pos + 20])
        comp = {0: "none", 1: "lzma", 2: "lz4", 3: "lz4"}.get(flags & 0x3F)
        return {"version": version, "size": size, "compression": comp}
    except Exception:
        return None


# ---------------------------------------------------------------- admin tools
def inspect_bundle(data):
    env = _load(data)
    rows = []
    for o in env.objects:
        t = o.type.name
        if t not in ("Mesh", "Texture2D"):
            continue
        name, info = "", ""
        try:
            d = o.read()
            name = getattr(d, "m_Name", "") or ""
            if t == "Texture2D":
                fmt = getattr(d.m_TextureFormat, "name", d.m_TextureFormat)
                info = f"{d.m_Width}x{d.m_Height} {fmt}"
        except Exception as e:
            info = f"(পড়া যায়নি: {e})"
        rows.append({"Path ID": str(o.path_id), "Type": t, "Name": name, "Info": info})
    rows.sort(key=lambda r: (r["Type"], r["Name"].lower()))
    return rows


def validate_ids(data, ids):
    """দেওয়া Path ID গুলো বান্ডেলে আছে কিনা এবং টাইপ ঠিক কিনা যাচাই করে।"""
    idx = _index(_load(data))
    problems = []
    for cat, slots in ids.items():
        for slot, val in slots.items():
            pid = clean_id(val)
            if not pid:
                continue
            o = idx.get(pid)
            if o is None:
                problems.append(f"{cat}/{slot}: Path ID {pid} বান্ডেলে নেই")
            elif o.type.name != EXPECT[slot]:
                problems.append(f"{cat}/{slot}: ID {pid} হলো {o.type.name}, কিন্তু {EXPECT[slot]} দরকার")
    return problems


# ---------------------------------------------------------------- mesh
def _sniff(blob):
    if blob[:7] == b"UnityFS" or blob[:8] in (b"UnityRaw", b"UnityWeb"):
        return "bundle"
    if looks_like_text_dump(blob):
        return "text"
    return "raw"


def import_mesh(dst, blob, log):
    kind = _sniff(blob)
    if kind == "bundle":
        src_env = _load(blob)
        src = next((o for o in src_env.objects if o.type.name == "Mesh"), None)
        if src is None:
            raise ProcessingError("আপলোড করা বান্ডেলে কোনো Mesh নেই")
        tree = src.read_typetree()
        sd = tree.get("m_StreamData")
        if isinstance(sd, dict) and sd.get("size"):
            raise ProcessingError("এই Mesh-এর ডাটা বাইরের .resS ফাইলে আছে — Raw (.dat) ডাম্প ব্যবহার করুন")
        dst.save_typetree(tree)
    elif kind == "text":
        try:
            new = parse_uabe_dump(blob.decode("utf-8-sig", errors="replace"))
            cur = dst.read_typetree()
            dst.save_typetree(deep_merge(cur, new))
        except Exception as e:
            raise ProcessingError(
                f"টেক্সট ডাম্প (.txt) পড়া যায়নি ({e}). অনুগ্রহ করে UABE থেকে 'Export Raw' (.dat) দিয়ে আবার চেষ্টা করুন।"
            ) from e
    else:
        if len(blob) < 16:
            raise ProcessingError("Mesh ফাইল খুব ছোট — ভুল ফাইল?")
        n = struct.unpack("<I", blob[:4])[0]
        if n > 512 or 4 + n > len(blob):
            raise ProcessingError("Raw ফাইলটি সঠিক Mesh ডাম্প মনে হচ্ছে না")
        dst.set_raw_data(blob)
    log(f"   • Mesh ইমপোর্ট ({kind})")


# ---------------------------------------------------------------- texture
def import_texture(obj, img_bytes, keep_size, log):
    tex = obj.read()
    img = Image.open(io.BytesIO(img_bytes))
    img.load()
    img = img.convert("RGBA")
    if keep_size:
        w, h = int(tex.m_Width), int(tex.m_Height)
        if img.size != (w, h):
            img = img.resize((w, h), Image.LANCZOS)
            log(f"   • ছবি রিসাইজ হয়ে {w}x{h} হয়েছে")
    mips = max(1, int(getattr(tex, "m_MipCount", 1) or 1))
    try:
        try:
            tex.set_image(img, mipmap_count=mips)
        except (TypeError, AttributeError):
            tex.image = img
        tex.save()
    except Exception as e:
        # ফরম্যাট এনকোড না হলে RGBA32 ব্যবহার (ফাইল বড় হবে)
        try:
            from UnityPy.enums import TextureFormat

            tex = obj.read()
            tex.set_image(img, target_format=TextureFormat.RGBA32)
            tex.save()
            log(f"   ⚠️ আসল ফরম্যাটে এনকোড হয়নি ({e}); RGBA32 ব্যবহার হয়েছে (ফাইল বড় হবে)")
        except Exception as e2:
            raise ProcessingError(f"Texture ইমপোর্ট ব্যর্থ: {e2}") from e2


# ---------------------------------------------------------------- stages
def stage1_meshes(base_bytes, char_ids, picks, mesh_blobs, log):
    """ধাপ ১: 3D Mesh ইমপোর্ট। (bytes, [(cat, path_id)]) ফেরত দেয়।"""
    env = _load(base_bytes)
    idx = _index(env)
    done = []
    for cat in picks:
        blob = mesh_blobs.get(cat)
        if not blob:
            log(f"[{cat}] এই আইটেমে Mesh ফাইল নেই — বাদ")
            continue
        pid = clean_id(char_ids.get(cat, {}).get("mesh"))
        if not pid:
            log(f"[{cat}] ক্যারেক্টারে Mesh Path ID দেওয়া নেই — বাদ")
            continue
        obj = idx.get(pid)
        if obj is None or obj.type.name != "Mesh":
            raise ProcessingError(f"[{cat}] Path ID {pid} বেস ফাইলে Mesh হিসেবে পাওয়া যায়নি")
        log(f"[{cat}] Mesh → {pid}")
        import_mesh(obj, blob, log)
        done.append((cat, pid))
    return _save(env, "none"), done


def stage2_textures(stage1_bytes, char_ids, picks, tex_blobs, mesh_done, keep_size, log):
    """ধাপ ২: ধাপ ১-এর ফাইল আবার লোড করে Texture ইমপোর্ট।"""
    env = _load(stage1_bytes)
    idx = _index(env)
    for cat, pid in mesh_done:  # ধাপ ১-এর Mesh ঠিকমতো পড়া যায় কিনা যাচাই
        try:
            idx[pid].read()
        except Exception as e:
            raise ProcessingError(f"[{cat}] ইমপোর্ট করা Mesh পড়া যাচ্ছে না — ডাম্প ফাইলটি সম্ভবত ভুল: {e}") from e
    for cat in picks:
        for slot in ("d", "n", "s"):
            blob = tex_blobs.get(cat, {}).get(slot)
            if not blob:
                continue
            pid = clean_id(char_ids.get(cat, {}).get(slot))
            if not pid:
                log(f"[{cat}] Texture {slot.upper()}: ক্যারেক্টারে ID নেই — বাদ")
                continue
            obj = idx.get(pid)
            if obj is None or obj.type.name != "Texture2D":
                raise ProcessingError(f"[{cat}] Path ID {pid} বেস ফাইলে Texture2D হিসেবে পাওয়া যায়নি")
            log(f"[{cat}] Texture {slot.upper()} → {pid}")
            import_texture(obj, blob, keep_size, log)
    return _save(env, "none")


def fit_to_size(cands, order, target):
    """(packer, data, status) — status: padded | exact | trimmed | over"""
    fit = [p for p in order if p in cands and len(cands[p]) <= target]
    if fit:
        p = fit[0]
        d = cands[p]
        pad = target - len(d)
        return p, d + b"\x00" * pad, ("exact" if pad == 0 else "padded")
    p = min(cands, key=lambda k: len(cands[k]))
    d = cands[p]
    over = len(d) - target
    zeros = len(d) - len(d.rstrip(b"\x00"))
    if zeros >= over:
        return p, d[:target], "trimmed"
    return p, d, "over"


def build_final(bundle_bytes, original_bytes, log):
    """ধাপ ৩: কম্প্রেস করে অরিজিনাল ফাইলের সাইজের সমান করা।"""
    target = len(original_bytes)
    hdr = bundle_header(original_bytes)
    pref = (hdr or {}).get("compression") or "lz4"
    log(f"অরিজিনাল সাইজ: {target:,} বাইট | কম্প্রেশন: {pref}")
    order = [pref] + [p for p in ("lz4", "lzma", "none") if p != pref]
    env = _load(bundle_bytes)
    cands = {}
    for p in order:
        try:
            cands[p] = _save(env, p)
            log(f"   {p}: {len(cands[p]):,} বাইট")
        except Exception as e:
            log(f"   {p}: ব্যর্থ ({e})")
    if not cands:
        raise ProcessingError("কোনো কম্প্রেশনেই ফাইল সেভ করা যায়নি")
    packer, data, status = fit_to_size(cands, order, target)
    return data, {"packer": packer, "status": status, "size": len(data), "target": target}
