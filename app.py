import streamlit as st
import firebase_helper
import processing

st.set_page_config(page_title="Unity Character Customizer", page_icon="🎮", layout="wide")

CATEGORIES = ["Hair", "Head", "Accessory", "Body / Top", "Bottom", "Shoes"]

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Public Customizer", "Admin Panel"])

# ==================== পাবলিক পেজ ====================
if page == "Public Customizer":
    st.title("🎮 Character Customizer")
    st.info("আপনার পছন্দের অংশগুলো পরিবর্তন করুন। সিলেক্ট না করলে তা অরিজিনাল থাকবে।")
    
    characters = firebase_helper.get_all_characters()
    all_items = firebase_helper.get_all_items()

    if not characters:
        st.warning("এখনো কোনো ক্যারেক্টার যোগ করা হয়নি।")
    else:
        st.subheader("1. Choose Base Character")
        char_names = [c["name"] for c in characters]
        selected_char_name = st.selectbox("Select Character:", char_names)
        selected_char = next(c for c in characters if c["name"] == selected_char_name)

        st.markdown("---")
        st.subheader("2. Select Components to Modify (Optional)")

        selected_items_for_job = {}
        cols = st.columns(2)
        for idx, cat in enumerate(CATEGORIES):
            cat_items = [itm for itm in all_items if itm.get("category") == cat]
            options = ["Original (No Change)"] + [itm["name"] for itm in cat_items]
            
            with cols[idx % 2]:
                chosen_opt = st.selectbox(f"🔘 {cat}:", options, key=f"sel_{cat}")
                if chosen_opt != "Original (No Change)":
                    item_obj = next(itm for itm in cat_items if itm["name"] == chosen_opt)
                    selected_items_for_job[cat] = item_obj

        st.markdown("---")
        if st.button("🚀 Create Bundle", type="primary", use_container_width=True):
            if not selected_items_for_job:
                st.warning("আপনি কোনো আইটেম সিলেক্ট করেননি! বান্ডেলটি ১০০% অরিজিনাল থাকবে।")
            else:
                with st.spinner("প্রসেসিং হচ্ছে... দয়া করে অপেক্ষা করুন।"):
                    base_bytes = firebase_helper.download_file_bytes(selected_char["file_path"])
                    if not base_bytes:
                        st.error("মূল ক্যারেক্টার ফাইলটি লোড করতে সমস্যা হচ্ছে।")
                    else:
                        items_to_apply = {}
                        for cat, itm in selected_items_for_job.items():
                            items_to_apply[cat] = {
                                "data": itm,
                                "model_bytes": firebase_helper.download_file_bytes(itm.get("model_path")),
                                "tex_d_bytes": firebase_helper.download_file_bytes(itm.get("tex_d_path")),
                                "tex_n_bytes": firebase_helper.download_file_bytes(itm.get("tex_n_path")),
                                "tex_s_bytes": firebase_helper.download_file_bytes(itm.get("tex_s_path"))
                            }
                        
                        success, result_bytes, logs = processing.process_character_bundle(base_bytes, selected_char, items_to_apply)
                        
                        if success and result_bytes:
                            st.success("🎉 সফলভাবে কাস্টমাইজড বান্ডেল তৈরি হয়েছে!")
                            st.download_button(
                                label=f"⬇️ Download {selected_char_name}_Custom.bundle",
                                data=result_bytes,
                                file_name=f"{selected_char_name}_Custom.bundle",
                                mime="application/octet-stream",
                                use_container_width=True
                            )
                        else:
                            st.error("বান্ডেল তৈরিতে সমস্যা হয়েছে।")
                            for l in logs: st.write(l)

# ==================== অ্যাডমিন প্যানেল ====================
elif page == "Admin Panel":
    st.title("🔒 Admin Panel")
    
    if not st.session_state.admin_logged_in:
        st.subheader("Admin Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                res = firebase_helper.login_admin(email, password)
                if "idToken" in res:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Login failed.")
    else:
        col1, col2 = st.columns([8, 2])
        col1.success("আপনি সফলভাবে লগইন করেছেন!")
        if col2.button("Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()
        
        tab1, tab2 = st.tabs(["👤 Characters", "📦 Items"])
        
        # ----------------- Characters Tab -----------------
        with tab1:
            with st.expander("➕ Add New Character", expanded=False):
                with st.form("add_char_form", clear_on_submit=True):
                    c_name = st.text_input("Character Name")
                    c_desc = st.text_area("Description")
                    c_file = st.file_uploader("Upload Base AssetBundle")
                    
                    st.write("Target Path IDs:")
                    c_cfg = {}
                    for cat in CATEGORIES:
                        st.markdown(f"**{cat}**")
                        c1, c2, c3, c4 = st.columns(4)
                        m_id = c1.text_input("Mesh ID", value="0", key=f"am_{cat}")
                        d_id = c2.text_input("Tex D ID", value="0", key=f"ad_{cat}")
                        n_id = c3.text_input("Tex N ID", value="0", key=f"an_{cat}")
                        s_id = c4.text_input("Tex S ID", value="0", key=f"as_{cat}")
                        c_cfg[cat] = {"mesh_id": m_id.strip(), "d_id": d_id.strip(), "n_id": n_id.strip(), "s_id": s_id.strip()}
                    
                    if st.form_submit_button("Save Character"):
                        if c_name and c_file:
                            path, err = firebase_helper.save_file_direct(c_file.read(), "characters", c_file.name)
                            if path and firebase_helper.add_character(c_name, c_desc, path, c_cfg):
                                st.success("Character added!")
                                st.rerun()
                            else: st.error("Failed to save.")
                        else: st.warning("Name and File required.")

            st.markdown("### Manage Characters")
            chars = firebase_helper.get_all_characters()
            for c in chars:
                with st.expander(f"👤 {c.get('name', 'Unknown')}"):
                    c_id = c['doc_id']
                    
                    # Edit & Delete Buttons
                    col_a, col_b = st.columns(2)
                    if col_a.button("✏️ Edit", key=f"edt_c_{c_id}"):
                        st.session_state[f"edit_mode_{c_id}"] = True
                    if col_b.button("🗑️ Delete", key=f"del_c_{c_id}"):
                        firebase_helper.delete_character(c_id)
                        st.rerun()

                    # Edit Form
                    if st.session_state.get(f"edit_mode_{c_id}", False):
                        st.warning("আপনি এডিট মোডে আছেন। সেভ করতে নিচের Save Changes-এ চাপুন।")
                        with st.form(f"form_c_{c_id}"):
                            e_name = st.text_input("Name", value=c.get('name', ''))
                            e_desc = st.text_area("Description", value=c.get('description', ''))
                            e_file = st.file_uploader("Replace Bundle File (Optional)")
                            
                            e_cfg = {}
                            c_comp = c.get('components', {})
                            for cat in CATEGORIES:
                                cat_vals = c_comp.get(cat, {})
                                st.markdown(f"**{cat}**")
                                c1, c2, c3, c4 = st.columns(4)
                                m = c1.text_input("Mesh ID", value=cat_vals.get("mesh_id", "0"), key=f"em_{cat}_{c_id}")
                                d = c2.text_input("Tex D", value=cat_vals.get("d_id", "0"), key=f"ed_{cat}_{c_id}")
                                n = c3.text_input("Tex N", value=cat_vals.get("n_id", "0"), key=f"en_{cat}_{c_id}")
                                s = c4.text_input("Tex S", value=cat_vals.get("s_id", "0"), key=f"es_{cat}_{c_id}")
                                e_cfg[cat] = {"mesh_id": m.strip(), "d_id": d.strip(), "n_id": n.strip(), "s_id": s.strip()}
                            
                            if st.form_submit_button("💾 Save Changes"):
                                r_path = None
                                if e_file: r_path, _ = firebase_helper.save_file_direct(e_file.read(), "characters", e_file.name)
                                firebase_helper.update_character(c_id, e_name, e_desc, e_cfg, r_path)
                                st.session_state[f"edit_mode_{c_id}"] = False
                                st.rerun()
                            if st.form_submit_button("Cancel"):
                                st.session_state[f"edit_mode_{c_id}"] = False
                                st.rerun()

        # ----------------- Items Tab -----------------
        with tab2:
            with st.expander("➕ Add New Item", expanded=False):
                with st.form("add_item_form", clear_on_submit=True):
                    i_name = st.text_input("Item Name")
                    i_cat = st.selectbox("Category", CATEGORIES)
                    i_mod = st.file_uploader("3D Model File")
                    i_d = st.file_uploader("Texture D (Main Image)", type=["png", "jpg"])
                    i_n = st.file_uploader("Texture N (Normal)", type=["png", "jpg"])
                    i_s = st.file_uploader("Texture S (Specular)", type=["png", "jpg"])
                    
                    if st.form_submit_button("Save Item"):
                        if i_name and (i_mod or i_d):
                            mp, dp, np, sp = None, None, None, None
                            if i_mod: mp, _ = firebase_helper.save_file_direct(i_mod.read(), "items", i_mod.name)
                            if i_d: dp, _ = firebase_helper.save_file_direct(i_d.read(), "items", i_d.name)
                            if i_n: np, _ = firebase_helper.save_file_direct(i_n.read(), "items", i_n.name)
                            if i_s: sp, _ = firebase_helper.save_file_direct(i_s.read(), "items", i_s.name)
                            
                            if firebase_helper.add_item_files(i_name, i_cat, mp, dp, np, sp):
                                st.success("Item saved!")
                                st.rerun()
                        else: st.warning("Name and at least a model or Texture D required.")

            st.markdown("### Manage Items")
            items = firebase_helper.get_all_items()
            for itm in items:
                with st.expander(f"📦 {itm.get('name', 'Unknown')} [{itm.get('category', '')}]"):
                    i_id = itm['doc_id']
                    
                    c_a, c_b = st.columns(2)
                    if c_a.button("✏️ Edit", key=f"edt_i_{i_id}"):
                        st.session_state[f"edit_item_{i_id}"] = True
                    if c_b.button("🗑️ Delete", key=f"del_i_{i_id}"):
                        firebase_helper.delete_item(i_id)
                        st.rerun()
                    
                    if st.session_state.get(f"edit_item_{i_id}", False):
                        st.warning("এডিট মোড চালু আছে।")
                        with st.form(f"form_i_{i_id}"):
                            ei_name = st.text_input("Name", value=itm.get('name', ''))
                            ei_cat = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(itm.get('category', CATEGORIES[0])))
                            ei_mod = st.file_uploader("Replace Model (Optional)")
                            ei_d = st.file_uploader("Replace Texture D (Optional)", type=["png", "jpg"])
                            ei_n = st.file_uploader("Replace Texture N (Optional)", type=["png", "jpg"])
                            ei_s = st.file_uploader("Replace Texture S (Optional)", type=["png", "jpg"])
                            
                            if st.form_submit_button("💾 Save Item"):
                                n_m, n_d, n_nn, n_s = None, None, None, None
                                if ei_mod: n_m, _ = firebase_helper.save_file_direct(ei_mod.read(), "items", ei_mod.name)
                                if ei_d: n_d, _ = firebase_helper.save_file_direct(ei_d.read(), "items", ei_d.name)
                                if ei_n: n_nn, _ = firebase_helper.save_file_direct(ei_n.read(), "items", ei_n.name)
                                if ei_s: n_s, _ = firebase_helper.save_file_direct(ei_s.read(), "items", ei_s.name)
                                
                                firebase_helper.update_item_files(i_id, ei_name, ei_cat, n_m, n_d, n_nn, n_s)
                                st.session_state[f"edit_item_{i_id}"] = False
                                st.rerun()
                            if st.form_submit_button("Cancel"):
                                st.session_state[f"edit_item_{i_id}"] = False
                                st.rerun()
