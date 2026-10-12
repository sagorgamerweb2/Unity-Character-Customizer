import base64

import streamlit as st
import streamlit.components.v1 as components

import processing as proc


def auto_download(data: bytes, filename: str):
    if len(data) > 30 * 1024 * 1024:
        return  # খুব বড় ফাইলে শুধু বাটন
    b64 = base64.b64encode(data).decode()
    components.html(
        f'<a id="d" download="{filename}" href="data:application/octet-stream;base64,{b64}"></a>'
        '<script>document.getElementById("d").click();</script>',
        height=0,
    )


def step3(scope, sig, b):
    st.success("ধাপ ১+২ সম্পন্ন ✅")
    st.markdown("### ধাপ ৩ — অরিজিনাল ফাইল দিয়ে সাইজ মেলানো")
    orig = st.file_uploader("অরিজিনাল asset bundle আপলোড করুন", key="orig_up")
    if orig and st.button("🚀 ফাইনাল ফাইল বানান ও ডাউনলোড", type="primary", use_container_width=True):
        with st.status("কম্প্রেস ও সাইজ মেলানো হচ্ছে…", expanded=True) as status:
            try:
                data, info = proc.build_final(b["bytes"], orig.getvalue(), st.write)
                st.session_state.final = {"char": scope, "sig": sig, "bytes": data, "name": orig.name,
                                          "info": info, "auto": True}
                status.update(label="✅ তৈরি হয়েছে", state="complete")
            except Exception as e:
                status.update(label="❌ ব্যর্থ", state="error")
                st.error(str(e))
    f = st.session_state.get("final")
    if f and f["char"] == scope and f["sig"] == sig:
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
