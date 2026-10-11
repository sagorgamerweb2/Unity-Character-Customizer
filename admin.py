"""অ্যাডমিন প্যানেল"""
import hmac
import time

import streamlit as st

import firebase_helper as fb
import processing as proc
from config import CAT_LABEL, CATEGORIES, SLOTS

IMG_TYPES = ["png", "jpg", "jpeg", "webp"]


def _admin_password():
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except Exception:
        return None


def login_gate() -> bool:
    if st.session_state.get("is_admin"):
        return True
    expected = _admin_password()
    if not expected:
        st.error("Streamlit Secrets-এ ADMIN_PASSWORD সেট করা নেই। README-এর ধাপ দেখুন।")
        return False
    st.subheader("🔐 অ্যাডমিন লগইন")
    if st.session_state.get("fails", 0) >= 5:
        st.error("অনেকবার ভুল পাসওয়ার্ড। পেজ রিফ্রেশ করে আবার চেষ্টা করুন।")
        return False
    with st.form("login"):
        pw = st.text_input("পাসওয়ার্ড", type="password")
        if st.form_submit_button("লগইন", use_container_width=True):
            if hmac.compare_digest(pw.encode(), str(expected).encode()):
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.session_state.fails = st.session_state.get("fails", 0) + 1
                time.sleep(1.2)
                st.error("পাসওয়ার্ড ভুল")
    return False


def ids_inputs(prefix, current=None):
    current = current or {}
    out = {}
    for key, label in CATEGORIES:
        cur = current.get(key, {})
        with st.expander(label):
            vals = {}
            for row in (SLOTS[:2], SLOTS[2:]):
                cols = st.columns(2)
                for col, (slot, slabel) in zip(cols, row):
                    vals[slot] = col.text_input(slabel, value=cur.get(slot, ""), key=f"{prefix}_{key}_{slot}")
            out[key] = vals
    return out


def check_ids(ids):
    clean, errs = {}, []
    for cat, slots in ids.items():
        clean[cat] = {}
        for slot, v in slots.items():
            try:
                clean[cat][slot] = proc.clean_id(v)
            except proc.ProcessingError as e:
                errs.append(f"{CAT_LABEL[cat]} / {slot}: {e}")
    return clean, errs


# ---------------------------------------------------------------- characters
def tab_characters():
    chars_now = fb.list_characters()
    with st.expander("➕ নতুন ক্যারেক্টার যোগ করুন", expanded=not chars_now):
        with st.form("add_char"):
            name = st.text_input("ক্যারেক্টারের নাম")
            desc = st.text_input("বর্ণনা (ঐচ্ছিক)")
            f = st.file_uploader("Base asset bundle (আনকম্প্রেসড ফাইল)", key="add_char_file")
            st.caption("প্রতিটি ক্যাটাগরির Path ID দিন (যেটা নেই সেটা ফাঁকা রাখুন):")
            ids = ids_inputs("addc")
            force = st.checkbox("ID-তে সমস্যা থাকলেও সেভ করুন")
            go = st.form_submit_button("💾 সেভ করুন", use_container_width=True)
        if go:
            clean, errs = check_ids(ids)
            if not name.strip():
                st.error("নাম দিন")
            elif not f:
                st.error("বান্ডেল ফাইল আপলোড করুন")
            elif errs:
                st.error("\n\n".join(errs))
            else:
                data = f.getvalue()
                try:
                    with st.spinner("Path ID যাচাই হচ্ছে…"):
                        problems = proc.validate_ids(data, clean)
                except proc.ProcessingError as e:
                    st.error(str(e))
                    problems = None
                if problems is not None:
                    if problems and not force:
                        st.error("এই সমস্যাগুলো পাওয়া গেছে:")
                        for p in problems:
                            st.write("• " + p)
                    else:
                        with st.spinner("Firebase-এ সেভ হচ্ছে…"):
                            fid = fb.save_file(data, f.name)
                            fb.add_character(name.strip(), desc.strip(), fid, clean)
                        st.success("✅ ক্যারেক্টার যোগ হয়েছে")

    st.markdown("### ক্যারেক্টার তালিকা")
    for ch in fb.list_characters():
        cid = ch["id"]
        with st.expander(f"👤 {ch.get('name', '?')}"):
            with st.form(f"edit_{cid}"):
                n = st.text_input("নাম", value=ch.get("name", ""))
                d = st.text_input("বর্ণনা", value=ch.get("desc", ""))
                nf = st.file_uploader("বান্ডেল বদলাতে চাইলে নতুন ফাইল দিন (ঐচ্ছিক)", key=f"ef_{cid}")
                ids = ids_inputs(f"ec_{cid}", ch.get("ids"))
                sv = st.form_submit_button("💾 পরিবর্তন সেভ করুন", use_container_width=True)
            if sv:
                clean, errs = check_ids(ids)
                if errs:
                    st.error("\n\n".join(errs))
                else:
                    try:
                        data = nf.getvalue() if nf else fb.load_file(ch.get("file_id"))
                        problems = proc.validate_ids(data, clean) if data else ["বেস ফাইল পাওয়া যায়নি"]
                    except Exception as e:
                        problems = [str(e)]
                    if problems:
                        st.warning("সমস্যা: " + " | ".join(problems) + " — তবুও সেভ হচ্ছে।")
                    new_fid = fb.save_file(nf.getvalue(), nf.name) if nf else None
                    fb.update_character(cid, n.strip(), d.strip(), clean, new_fid)
                    st.success("✅ সেভ হয়েছে (পেজ রিফ্রেশ করলে নতুন তথ্য দেখাবে)")
            if st.checkbox("মুছে ফেলার জন্য নিশ্চিত", key=f"dc_{cid}"):
                if st.button("🗑️ ডিলিট করুন", key=f"dcb_{cid}"):
                    fb.delete_character(cid)
                    st.rerun()


# ---------------------------------------------------------------- items
def tab_items():
    with st.expander("➕ নতুন আইটেম যোগ করুন", expanded=not fb.list_items()):
        with st.form("add_item"):
            name = st.text_input("আইটেমের নাম")
            cat = st.selectbox("ক্যাটাগরি", [k for k, _ in CATEGORIES], format_func=lambda k: CAT_LABEL[k])
            mesh = st.file_uploader("3D মডেল ডাম্প ফাইল (UABE Export Raw .dat সবচেয়ে নিরাপদ)", key="ai_mesh")
            d = st.file_uploader("Texture D (ছবি)", type=IMG_TYPES, key="ai_d")
            n = st.file_uploader("Texture N (ছবি)", type=IMG_TYPES, key="ai_n")
            s = st.file_uploader("Texture S (ছবি)", type=IMG_TYPES, key="ai_s")
            go = st.form_submit_button("💾 আইটেম সেভ করুন", use_container_width=True)
        if go:
            if not name.strip():
                st.error("নাম দিন")
            elif not (mesh or d or n or s):
                st.error("অন্তত একটি ফাইল দিন")
            else:
                with st.spinner("Firebase-এ আপলোড হচ্ছে…"):
                    files = {
                        k: (fb.save_file(u.getvalue(), u.name) if u else None)
                        for k, u in (("mesh_file", mesh), ("d_file", d), ("n_file", n), ("s_file", s))
                    }
                    src = d or n or s
                    thumb = fb.make_thumb(src.getvalue()) if src else None
                    fb.add_item(name.strip(), cat, files, thumb)
                st.success("✅ আইটেম যোগ হয়েছে")

    st.markdown("### আইটেম তালিকা")
    flt = st.selectbox("ক্যাটাগরি ফিল্টার", ["all"] + [k for k, _ in CATEGORIES],
                       format_func=lambda k: "সব" if k == "all" else CAT_LABEL[k])
    for it in fb.list_items():
        if flt != "all" and it.get("category") != flt:
            continue
        iid = it["id"]
        with st.expander(f"📦 {it.get('name', '?')}  ·  {CAT_LABEL.get(it.get('category'), '')}"):
            if it.get("thumb"):
                st.image(it["thumb"], width=110)
            have = [lbl for k, lbl in (("mesh_file", "Mesh"), ("d_file", "D"), ("n_file", "N"), ("s_file", "S")) if it.get(k)]
            st.caption("আছে: " + ", ".join(have))
            with st.form(f"ei_{iid}"):
                nn = st.text_input("নাম", value=it.get("name", ""))
                keys = [k for k, _ in CATEGORIES]
                cc = st.selectbox("ক্যাটাগরি", keys, index=keys.index(it["category"]) if it.get("category") in keys else 0,
                                  format_func=lambda k: CAT_LABEL[k])
                m2 = st.file_uploader("Mesh বদলান (ঐচ্ছিক)", key=f"em_{iid}")
                d2 = st.file_uploader("Texture D বদলান (ঐচ্ছিক)", type=IMG_TYPES, key=f"ed_{iid}")
                n2 = st.file_uploader("Texture N বদলান (ঐচ্ছিক)", type=IMG_TYPES, key=f"en_{iid}")
                s2 = st.file_uploader("Texture S বদলান (ঐচ্ছিক)", type=IMG_TYPES, key=f"es_{iid}")
                sv = st.form_submit_button("💾 সেভ", use_container_width=True)
            if sv:
                new = {k: (fb.save_file(u.getvalue(), u.name) if u else None)
                       for k, u in (("mesh_file", m2), ("d_file", d2), ("n_file", n2), ("s_file", s2))}
                src = d2
                fb.update_item(iid, nn.strip(), cc, new, fb.make_thumb(src.getvalue()) if src else None)
                st.success("✅ সেভ হয়েছে (রিফ্রেশ করলে দেখাবে)")
            if st.checkbox("মুছে ফেলার জন্য নিশ্চিত", key=f"di_{iid}"):
                if st.button("🗑️ ডিলিট করুন", key=f"dib_{iid}"):
                    fb.delete_item(iid)
                    st.rerun()


# ---------------------------------------------------------------- explorer
def tab_explorer():
    st.caption("বান্ডেল আপলোড করলে ভিতরের সব Mesh ও Texture2D-এর নাম ও Path ID দেখাবে।")
    f = st.file_uploader("Asset bundle", key="explore_file")
    if f and st.button("🔍 তালিকা দেখান", use_container_width=True):
        try:
            with st.spinner("পড়া হচ্ছে…"):
                rows = proc.inspect_bundle(f.getvalue())
            st.write(f"মোট {len(rows)} টি")
            st.dataframe(rows, use_container_width=True)
        except Exception as e:
            st.error(str(e))


def render():
    st.title("🔐 অ্যাডমিন প্যানেল")
    if not login_gate():
        return
    if st.button("লগআউট"):
        st.session_state.is_admin = False
        st.rerun()
    t1, t2, t3 = st.tabs(["👤 ক্যারেক্টার", "📦 আইটেম", "🔍 Path ID খুঁজুন"])
    with t1:
        tab_characters()
    with t2:
        tab_items()
    with t3:
        tab_explorer()
