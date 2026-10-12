"""🛠️ কাস্টম এডিট: যেকোনো asset bundle দিয়ে যেকোনো Path ID-তে ফাইল/ছবি বসানো"""
import streamlit as st

import finish
import processing as proc


def render():
    st.title("🛠️ কাস্টম এডিট")
    st.caption("নিজের asset bundle দিন, যে Path ID বদলাতে চান সেটা লিখুন, আর তার ফাইল (ডাম্প) অথবা ছবি দিন। "
               "একটা, দুইটা বা যত খুশি Path ID একসাথে বদলানো যায়।")

    bf = st.file_uploader("এডিট করার asset bundle (আনকম্প্রেসড)", key="custom_bundle")
    if not bf:
        st.info("আগে asset bundle আপলোড করুন।")
        return
    data = bf.getvalue()
    key = (bf.name, bf.size)
    cache = st.session_state.get("custom_types")
    if not cache or cache["key"] != key:
        try:
            with st.spinner("বান্ডেল পড়া হচ্ছে…"):
                types = proc.object_types(data)
        except Exception as e:
            st.error(str(e))
            return
        st.session_state.custom_types = cache = {"key": key, "types": types}
    types = cache["types"]
    st.success(f"✅ বান্ডেল লোড হয়েছে — মোট {len(types)} টি অবজেক্ট")

    n = st.session_state.setdefault("custom_n", 1)
    edits, seen = [], set()
    for i in range(n):
        with st.container(border=True):
            st.markdown(f"**পরিবর্তন #{i + 1}**")
            pid_in = st.text_input("Path ID", key=f"cpid_{i}")
            f = st.file_uploader("ফাইল (ডাম্প .dat) অথবা ছবি (PNG/JPG)", key=f"cfile_{i}")
            pid, ok = "", False
            try:
                pid = proc.clean_id(pid_in)
            except proc.ProcessingError as e:
                st.error(str(e))
            if pid:
                t = types.get(pid)
                if t is None:
                    st.error("❌ এই Path ID বান্ডেলে নেই")
                elif pid in seen:
                    st.error("❌ এই Path ID আগেই দেওয়া হয়েছে")
                elif t == "Texture2D":
                    st.caption("🖼️ Texture2D — ছবি দিন")
                    ok = True
                elif t in proc.MESH_TYPES:
                    st.caption(f"🧩 {t} — ডাম্প ফাইল দিন")
                    ok = True
                else:
                    st.warning(f"এর টাইপ {t} — এটি সাপোর্ট করা হয় না")
                seen.add(pid)
            if ok and f:
                edits.append((pid, f.getvalue(), f.name, f.size))

    c1, c2 = st.columns(2)
    if c1.button("➕ আরেকটা Path ID", use_container_width=True):
        st.session_state.custom_n = n + 1
        st.rerun()
    if c2.button("➖ শেষটা বাদ দিন", disabled=n <= 1, use_container_width=True):
        st.session_state.custom_n = n - 1
        st.rerun()

    keep = st.checkbox("ছবি আসল Texture-এর সাইজে রিসাইজ হবে (প্রস্তাবিত)", value=True)
    sig = (key, keep) + tuple((p, nm, sz) for p, _, nm, sz in edits)
    st.markdown("---")
    if st.button("📦 ধাপ ১+২: বান্ডেল তৈরি করুন", type="primary", disabled=not edits, use_container_width=True):
        run(data, edits, keep, sig)

    b = st.session_state.get("build")
    if b and b["char"] == "custom" and b["sig"] == sig:
        finish.step3("custom", sig, b)


def run(data, edits, keep, sig):
    st.session_state.pop("final", None)
    st.session_state.pop("build", None)
    pairs = [(p, blob) for p, blob, _, _ in edits]
    with st.status("প্রসেসিং চলছে…", expanded=True) as status:
        try:
            st.write("**ধাপ ১: 3D মডেল/ডাম্প ইমপোর্ট**")
            s1, done = proc.custom_stage1(data, pairs, st.write)
            st.write("**ধাপ ২: ছবি (Texture) ইমপোর্ট**")
            s2 = proc.custom_stage2(s1, pairs, done, keep, st.write)
            st.session_state.build = {"char": "custom", "sig": sig, "bytes": s2}
            status.update(label="✅ ধাপ ১+২ সম্পন্ন", state="complete")
        except Exception as e:
            status.update(label="❌ ব্যর্থ", state="error")
            st.error(str(e))
