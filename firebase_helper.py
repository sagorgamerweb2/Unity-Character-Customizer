"""Firebase Firestore ডাটাবেস (সম্পূর্ণ ফ্রি Spark প্ল্যানে চলে — Storage লাগে না)।
বড় ফাইল zlib দিয়ে ছোট করে ৮০০KB-এর টুকরো করে Firestore-এ রাখা হয়।
"""
import io
import json
import time
import uuid
import zlib

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore
from PIL import Image

COL_FILES, COL_CHARS, COL_ITEMS = "ucc_files", "ucc_characters", "ucc_items"
CHUNK = 800_000
BATCH_CHUNKS = 6


def _credentials_info():
    try:
        if "FIREBASE_JSON" in st.secrets:
            raw = st.secrets["FIREBASE_JSON"]
            info = json.loads(raw, strict=False) if isinstance(raw, str) else dict(raw)
        elif "firebase" in st.secrets:
            info = dict(st.secrets["firebase"])
        else:
            raise RuntimeError("Secrets-এ FIREBASE_JSON পাওয়া যায়নি।")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"FIREBASE_JSON ঠিকমতো পেস্ট হয়নি: {e}") from e
    pk = info.get("private_key", "")
    if "\\n" in pk:
        info["private_key"] = pk.replace("\\n", "\n")
    return info


@st.cache_resource(show_spinner=False)
def get_db():
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(_credentials_info()))
    return firestore.client()


# ------------------------------------------------------------------ files
def save_file(data: bytes, name: str = "file") -> str:
    db = get_db()
    fid = uuid.uuid4().hex
    comp = zlib.compress(data, 6)
    parts = [comp[i:i + CHUNK] for i in range(0, len(comp), CHUNK)] or [b""]
    ref = db.collection(COL_FILES).document(fid)
    try:
        for s in range(0, len(parts), BATCH_CHUNKS):
            b = db.batch()
            for i in range(s, min(s + BATCH_CHUNKS, len(parts))):
                b.set(ref.collection("chunks").document(f"{i:05d}"), {"i": i, "data": parts[i]})
            b.commit()
        ref.set({"name": name, "size": len(data), "chunks": len(parts), "created": time.time()})
    except Exception:
        _delete_chunks(ref)
        raise
    return fid


@st.cache_data(max_entries=40, show_spinner=False)
def load_file(file_id):
    if not file_id:
        return None
    ref = get_db().collection(COL_FILES).document(file_id)
    snap = ref.get()
    if not snap.exists:
        return None
    info = snap.to_dict()
    docs = sorted((d.to_dict() for d in ref.collection("chunks").stream()), key=lambda d: d["i"])
    if len(docs) != info["chunks"]:
        raise RuntimeError(f"ফাইল অসম্পূর্ণ ({len(docs)}/{info['chunks']} টুকরো)")
    return zlib.decompress(b"".join(d["data"] for d in docs))


def _delete_chunks(ref):
    batch, n = get_db().batch(), 0
    for d in ref.collection("chunks").stream():
        batch.delete(d.reference)
        n += 1
        if n % 400 == 0:
            batch.commit()
            batch = get_db().batch()
    batch.commit()


def delete_file(file_id):
    if not file_id:
        return
    try:
        ref = get_db().collection(COL_FILES).document(file_id)
        _delete_chunks(ref)
        ref.delete()
        load_file.clear()
    except Exception:
        pass


def make_thumb(img_bytes, size=160):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        img.load()
        img = img.convert("RGB")
        img.thumbnail((size, size))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=80)
        return out.getvalue()
    except Exception:
        return None


# ------------------------------------------------------------------ characters
@st.cache_data(ttl=300, show_spinner=False)
def list_characters():
    out = []
    for d in get_db().collection(COL_CHARS).stream():
        x = d.to_dict() or {}
        x["id"] = d.id
        out.append(x)
    out.sort(key=lambda c: (c.get("name") or "").lower())
    return out


def add_character(name, desc, file_id, ids):
    get_db().collection(COL_CHARS).add(
        {"name": name, "desc": desc, "file_id": file_id, "ids": ids, "created": time.time()}
    )
    list_characters.clear()


def update_character(cid, name, desc, ids, new_file_id=None):
    ref = get_db().collection(COL_CHARS).document(cid)
    data = {"name": name, "desc": desc, "ids": ids}
    old_file = None
    if new_file_id:
        old_file = (ref.get().to_dict() or {}).get("file_id")
        data["file_id"] = new_file_id
    ref.update(data)
    if old_file:
        delete_file(old_file)
    list_characters.clear()


def delete_character(cid):
    ref = get_db().collection(COL_CHARS).document(cid)
    old = ref.get().to_dict() or {}
    ref.delete()
    delete_file(old.get("file_id"))
    list_characters.clear()


# ------------------------------------------------------------------ items
FILE_KEYS = ("mesh_file", "d_file", "n_file", "s_file")


@st.cache_data(ttl=300, show_spinner=False)
def list_items():
    out = []
    for d in get_db().collection(COL_ITEMS).stream():
        x = d.to_dict() or {}
        x["id"] = d.id
        out.append(x)
    out.sort(key=lambda c: (c.get("name") or "").lower())
    return out


def add_item(name, category, files: dict, thumb):
    data = {"name": name, "category": category, "thumb": thumb, "created": time.time()}
    for k in FILE_KEYS:
        data[k] = files.get(k)
    get_db().collection(COL_ITEMS).add(data)
    list_items.clear()


def update_item(iid, name, category, new_files: dict, new_thumb=None):
    ref = get_db().collection(COL_ITEMS).document(iid)
    old = ref.get().to_dict() or {}
    data = {"name": name, "category": category}
    for k, v in new_files.items():
        if v:
            data[k] = v
    if new_thumb:
        data["thumb"] = new_thumb
    ref.update(data)
    for k, v in new_files.items():
        if v and old.get(k):
            delete_file(old[k])
    list_items.clear()


def delete_item(iid):
    ref = get_db().collection(COL_ITEMS).document(iid)
    old = ref.get().to_dict() or {}
    ref.delete()
    for k in FILE_KEYS:
        delete_file(old.get(k))
    list_items.clear()
