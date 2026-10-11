import base64

import streamlit as st
import streamlit.components.v1 as components

import admin
import firebase_helper as fb
import processing as proc
from config import CATEGORIES

IMG_TYPES = ["png", "jpg", "jpeg", "webp"]
UPLOAD = "__upload__"

st.set_page_config(page_title="Character Customizer", page_icon="🎮", layout="centered",
                   initial_sidebar_state="collapsed")
st.markdown("<style>.block-container{padding-top:1.2rem}</style>", unsafe_allow_html=True)

try:
    fb.get_db()
except Exception as e:
    st.error("❌ Firebase সংযোগ হয়নি। Streamlit → Settings → Secrets ঠিক আছে কিনা দেখুন।")
    st.code(str(e))
    st.stop()


def auto_download(data: bytes, filename: str):
    if len(data) > 30 * 1024 * 1024:
        return  # খুব বড় ফাইলে শুধু বাটন
    b64 = base64.b64encode(data).decode()
    components.html(
        f'<a id="d" download="{filename}" href="data:application/octet-stream;base64,{b64}"></a>'
        '<script>document.getElementById("d").click();</script>',
        height=0,
    )


def page_public():
    chars, items = fb.list_characters(), fb.list_items()
    if not chars:
        st.info("এখনো কোনো ক্যারেক্টার যোগ করা হয়নি। অ্যাডমিন প্যানেল থেকে যোগ করুন।")
        return
    char = next((c for c in chars if c["id"] == st.session_state.get("sel_char")), None)
    if char is None:
        st.title("🎮 ক্যারেক্টার বেছে নিন")
        for c in chars:
            with st.container(border=True):
                st.subheader(c.get("name", "?"))
                if c.get("desc"):
                    st.caption(c["desc"])
                if st.button("এই ক্যারেক্টার নিন →", key=f"pick_{c['id']}", use_container_width=True):
                    st.session_state.sel_char = c["id"]
                    st.session_state.pop("build", None)
                    st.session_state.pop("final", None)
                    st.rerun()
        return
    customize(char, items)


def customize(char, items):
    if st.button("← অন্য ক্যারেক্টার"):
        for k in ("sel_char", "build", "final"):
            st.session_state.pop(k, None)
        st.rerun()
    st.title(f"👤 {char.get('name', '')}")
    st.caption("যে অংশ বদলাতে চান সেটা সিলেক্ট করুন। না করলে অরিজিনাল থাকবে।")

    ids_all = char.get("ids", {})
    picks = {}
    for key, label in CATEGORIES:
        ids = ids_all.get(key, {})
        if not any(ids.get(k) for k in ("mesh", "d", "n", "s")):
            continue
        cat_items = {i["id"]: i for i in items if i.get("category") == key}
        choice = st.selectbox(
            label, [None] + list(cat_items) + [UPLOAD],
            format_func=lambda x, ci=cat_items: "— অরিজিনাল —" if x is None
            else "📱 ফোন থেকে সরাসরি আপলোড" if x == UPLOAD else ci[x]["name"],
            key=f"pick_{char['id']}_{key}")
        if choice == UPLOAD:
            kp = f"up_{char['id']}_{key}"
            m = st.file_uploader("3D মডেল ডাম্প ফাইল (.dat)", key=f"{kp}_mesh")
            d = st.file_uploader("Texture D (ছবি)", type=IMG_TYPES, key=f"{kp}_d")
            n = st.file_uploader("Texture N (ছবি)", type=IMG_TYPES, key=f"{kp}_n")
            s_ = st.file_uploader("Texture S (ছবি)", type=IMG_TYPES, key=f"{kp}_s")
            up = {k: u for k, u in (("mesh", m), ("d", d), ("n", n), ("s", s_)) if u}
            if up:
                picks[key] = {
                    "sig": ("up",) + tuple((k, u.name, u.size) for k, u in sorted(up.items())),
                    "up": {k: u.getvalue() for k, u in up.items()},
                    "item": None,
                }
        elif choice:
            it = cat_items[choice]
            picks[key] = {"sig": ("db", choice), "up": None, "item": it}
            if it.get("thumb"):
                st.image(it["thumb"], width=90)

    sig = tuple(sorted((k, v["sig"]) for k, v in picks.items()))
    st.markdown("---")
    if st.button("📦 ধাপ ১+২: বান্ডেল তৈরি করুন", type="primary", disabled=not picks, use_container_width=True):
        run_build(char, picks, sig)

    b = st.session_state.get("build")
    if b and b["char"] == char["id"] and b["sig"] == sig:
        step3(char, sig, b)


def run_build(char, picks, sig):
    st.session_state.pop("final", None)
    st.session_state.pop("build", None)
    with st.status("প্রসেসিং চলছে…", expanded=True) as status:
        def log(m):
            st.write(m)
        try:
            base = fb.load_file(char.get("file_id"))
            if not base:
                raise proc.ProcessingError("বেস ক্যারেক্টার ফাইল পাওয়া যায়নি")
            mesh_blobs, tex_blobs = {}, {}
            log("ফাইল ডাউনলোড হচ্ছে…")
            for cat, pk in picks.items():
                if pk["up"]:  # ফোন থেকে আপলোড করা ফাইল
                    mesh_blobs[cat] = pk["up"].get("mesh")
                    tex_blobs[cat] = {s: pk["up"].get(s) for s in ("d", "n", "s")}
                else:  # Firebase আইটেম
                    it = pk["item"]
                    mesh_blobs[cat] = fb.load_file(it.get("mesh_file"))
                    tex_blobs[cat] = {s: fb.load_file(it.get(f"{s}_file")) for s in ("d", "n", "s")}
            ids = char.get("ids", {})
            log("**ধাপ ১: 3D Mesh ইমপোর্ট**")
            s1, done = proc.stage1_meshes(base, ids, picks, mesh_blobs, log)
            log("**ধাপ ২: Texture ইমপোর্ট**")
            s2 = proc.stage2_textures(s1, ids, picks, tex_blobs, done, True, log)
            st.session_state.build = {"char": char["id"], "sig": sig, "bytes": s2}
            status.update(label="✅ ধাপ ১+২ সম্পন্ন", state="complete")
        except Exception as e:
            status.update(label="❌ ব্যর্থ", state="error")
            st.error(str(e))


def step3(char, sig, b):
    st.success("ধাপ ১+২ সম্পন্ন ✅")
    st.markdown("### ধাপ ৩ — অরিজিনাল ফাইল দিয়ে সাইজ মেলানো")
    orig = st.file_uploader("অরিজিনাল asset bundle আপলোড করুন", key="orig_up")
    if orig and st.button("🚀 ফাইনাল ফাইল বানান ও ডাউনলোড", type="primary", use_container_width=True):
        with st.status("কম্প্রেস ও সাইজ মেলানো হচ্ছে…", expanded=True) as status:
            try:
                data, info = proc.build_final(b["bytes"], orig.getvalue(), st.write)
                st.session_state.final = {"char": char["id"], "sig": sig, "bytes": data, "name": orig.name,
                                          "info": info, "auto": True}
                status.update(label="✅ তৈরি হয়েছে", state="complete")
            except Exception as e:
                status.update(label="❌ ব্যর্থ", state="error")
                st.error(str(e))
    f = st.session_state.get("final")
    if f and f["char"] == char["id"] and f["sig"] == sig:
        info = f["info"]
        msg = {"padded": "শেষে 00 বাইট যোগ করে অরিজিনালের সমান করা হয়েছে ✅",
               "exact": "সাইজ হুবহু মিলেছে ✅",
               "trimmed": "শেষের অতিরিক্ত 00 বাইট ছেঁটে সাইজ মেলানো হয়েছে ✅",
               "over": "⚠️ ফাইল অরিজিনালের চেয়ে বড় হয়ে গেছে — সাইজ মেলানো যায়নি। ছোট/কম রেজোলিউশনের ছবি দিয়ে চেষ্টা করুন।"}[info["status"]]
        (st.warning if info["status"] == "over" else st.success)(
            f"{msg}\n\nফাইনাল: {info['size']:,} বাইট | অরিজিনাল: {info['target']:,} বাইট")
        st.download_button(f"⬇️ {f['name']} ডাউনলোড", f["bytes"], file_name=f["name"],
                           mime="application/octet-stream", use_container_width=True)
        if f.get("auto"):
            f["auto"] = False
            auto_download(f["bytes"], f["name"])


mode = st.radio("মেনু", ["🏠 হোম", "🔐 অ্যাডমিন"], horizontal=True, label_visibility="collapsed")
if mode == "🏠 হোম":
    page_public()
else:
    admin.render()
