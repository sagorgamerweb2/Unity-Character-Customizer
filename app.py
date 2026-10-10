import streamlit as st
import firebase_helper
import processing

st.set_page_config(page_title="Unity Character Customizer", page_icon="🎮", layout="wide")

CATEGORIES = ["Hair", "Head", "Accessory", "Body / Top", "Bottom", "Shoes"]

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Public Customizer", "Admin Panel"])

# ==================== পাবলিক পেজ (PUBLIC CUSTOMIZER) ====================
if page == "Public Customizer":
    st.title("🎮 Character Customizer")
    st.caption("Customize only the components you want. Unselected parts stay original.")
    
    characters = firebase_helper.get_all_characters()
    all_items = firebase_helper.get_all_items()

    if not characters:
        st.info("No characters available. Please check back later.")
    else:
        st.subheader("1. Choose Base Character")
        char_names = [c["name"] for c in characters]
        selected_char_name = st.selectbox("Select Character:", char_names)
        selected_char = next(c for c in characters if c["name"] == selected_char_name)
        if selected_char.get("description"):
            st.info(f"ℹ️ {selected_char['description']}")

        st.markdown("---")
        st.subheader("2. Select Components to Modify (Optional)")
        st.write("যে কয়টি অংশ পরিবর্তন করতে চান শুধু সেগুলো সিলেক্ট করুন। বাকিগুলো মূল ফাইলের মতোই থাকবে:")

        selected_items_for_job = {}
        cols = st.columns(2)
        for idx, cat in enumerate(CATEGORIES):
            cat_items = [itm for itm in all_items if itm.get("category") == cat]
            options = ["Default (Keep Original)"] + [itm["name"] for itm in cat_items]
            
            with cols[idx % 2]:
                chosen_opt = st.selectbox(f"🔘 {cat}:", options, key=f"sel_{cat}")
                if chosen_opt != "Default (Keep Original)":
                    item_obj = next(itm for itm in cat_items if itm["name"] == chosen_opt)
                    selected_items_for_job[cat] = item_obj

        st.markdown("---")
        
        # পরিবর্তনগুলোর সামারি দেখানো
        if selected_items_for_job:
            st.write("📝 **Selected for modification:**")
            for cat, itm in selected_items_for_job.items():
                st.write(f"• **{cat}:** `{itm['name']}`")
        else:
            st.caption("No custom items selected. Default components will remain untouched.")

        if st.button("🚀 Create Bundle", type="primary", use_container_width=True):
            if not selected_items_for_job:
                st.warning("Please choose at least one item to modify, or the bundle will remain 100% original.")
            else:
                with st.spinner("Modifying bundle... Please wait."):
                    base_bytes = firebase_helper.download_file_bytes(selected_char["file_path"])
                    if not base_bytes:
                        st.error("Failed to load base character bundle.")
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
                        
                        success, result_bytes, logs = processing.process_character_bundle(
                            base_bytes, selected_char, items_to_apply
                        )
                        
                        with st.expander("View Processing Logs", expanded=False):
                            for l in logs: st.text(l)
                        
                        if success and result_bytes:
                            st.success("🎉 Modified AssetBundle created successfully!")
                            out_filename = f"{selected_char_name}_Customized.bundle"
                            st.download_button(
                                label=f"⬇️ Download {out_filename}",
                                data=result_bytes,
                                file_name=out_filename,
                                mime="application/octet-stream",
                                use_container_width=True
                            )
                        else:
                            st.error("Bundle creation failed. Check logs.")

# ==================== অ্যাডমিন প্যানেল ====================
elif page == "Admin Panel":
    st.title("🔒 Admin Panel")
    
    if not st.session_state.admin_logged_in:
        st.subheader("Admin Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            res = firebase_helper.login_admin(email, password)
            if "idToken" in res:
                st.session_state.admin_logged_in = True
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Login failed. Check your email and password.")
    
    else:
        st.success("Admin Logged In")
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()
        
        st.markdown("---")
        tab1, tab2 = st.tabs(["👤 Manage Characters", "📦 Manage Items"])
        
        # ----------------- ক্যারেক্টার ট্যাব -----------------
        with tab1:
            with st.expander("➕ Add New Base Character", expanded=False):
                char_name = st.text_input("Character Name")
                char_desc = st.text_area("Character Description (Optional)")
                uploaded_char_file = st.file_uploader("Upload Base AssetBundle", key="new_char_file")
                
                st.markdown("##### Base Character Target Path IDs (6 Categories)")
                components_config = {}
                for cat in CATEGORIES:
                    with st.expander(f"⚙️ {cat} Target IDs"):
                        c1, c2 = st.columns(2)
                        with c1:
                            m_id = st.text_input(f"{cat} Mesh Path ID", value="0", key=f"add_m_{cat}")
                            d_id = st.text_input(f"{cat} Texture D ID", value="0", key=f"add_d_{cat}")
                        with c2:
                            n_id = st.text_input(f"{cat} Texture N ID", value="0", key=f"add_n_{cat}")
                            s_id = st.text_input(f"{cat} Texture S ID", value="0", key=f"add_s_{cat}")
                        components_config[cat] = {
                            "mesh_id": m_id.strip(), "d_id": d_id.strip(), "n_id": n_id.strip(), "s_id": s_id.strip()
                        }

                if st.button("Save New Character"):
                    if char_name and uploaded_char_file:
                        with st.spinner("Saving character..."):
                            f_path, _ = firebase_helper.save_file_direct(uploaded_char_file.read(), "characters", uploaded_char_file.name)
                            if f_path and firebase_helper.add_character(char_name, char_desc, f_path, components_config):
                                st.success(f"Character '{char_name}' added successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to save.")
                    else:
                        st.warning("Provide character name and AssetBundle file.")

            st.markdown("---")
            st.subheader("Saved Characters (View / Edit / Delete)")
            chars = firebase_helper.get_all_characters()
            if not chars:
                st.info("No characters added yet.")
            else:
                for c in chars:
                    with st.expander(f"👤 {c['name']}"):
                        st.write(f"**Description:** {c.get('description', 'N/A')}")
                        
                        edit_key = f"edit_toggle_{c['id']}"
                        if edit_key not in st.session_state:
                            st.session_state[edit_key] = False
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✏️ Edit Character", key=f"btn_edit_{c['id']}"):
                                st.session_state[edit_key] = not st.session_state[edit_key]
                                st.rerun()
                        with col_b:
                            if st.button("🗑️ Delete Character", key=f"btn_del_{c['id']}", type="secondary"):
                                firebase_helper.delete_character(c['id'])
                                st.success("Character deleted successfully!")
                                st.rerun()
                        
                        # এডিট ফরম
                        if st.session_state[edit_key]:
                            st.markdown("#### ✏️ Edit Character Information")
                            new_name = st.text_input("Name", value=c['name'], key=f"en_{c['id']}")
                            new_desc = st.text_area("Description", value=c.get('description', ''), key=f"ed_{c['id']}")
                            new_file = st.file_uploader("Replace Base AssetBundle (Optional)", key=f"ef_{c['id']}")
                            
                            st.markdown("##### Update Path IDs")
                            new_cfg = {}
                            curr_components = c.get("components", {})
                            for cat in CATEGORIES:
                                cat_vals = curr_components.get(cat, {})
                                with st.expander(f"⚙️ {cat} IDs"):
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        m = st.text_input(f"Mesh ID", value=cat_vals.get("mesh_id", "0"), key=f"em_{cat}_{c['id']}")
                                        d = st.text_input(f"Texture D ID", value=cat_vals.get("d_id", "0"), key=f"ed_{cat}_{c['id']}")
                                    with c2:
                                        n = st.text_input(f"Texture N ID", value=cat_vals.get("n_id", "0"), key=f"en_{cat}_{c['id']}")
                                        s = st.text_input(f"Texture S ID", value=cat_vals.get("s_id", "0"), key=f"es_{cat}_{c['id']}")
                                    new_cfg[cat] = {"mesh_id": m.strip(), "d_id": d.strip(), "n_id": n.strip(), "s_id": s.strip()}
                            
                            if st.button("💾 Save Changes", key=f"save_edit_{c['id']}"):
                                rep_path = None
                                if new_file:
                                    rep_path, _ = firebase_helper.save_file_direct(new_file.read(), "characters", new_file.name)
                                if firebase_helper.update_character(c['id'], new_name, new_desc, new_cfg, rep_path):
                                    st.success("Changes saved!")
                                    st.session_state[edit_key] = False
                                    st.rerun()

        # ----------------- আইটেম ট্যাব -----------------
        with tab2:
            with st.expander("➕ Add New Component Item", expanded=False):
                item_name = st.text_input("Item Name (e.g., Red Jacket, Punk Hair)")
                category = st.selectbox("Category", CATEGORIES)
                
                st.markdown("##### 📁 Upload 3D Model & Images")
                up_model = st.file_uploader("3D Model File", key="new_itm_model")
                up_tex_d = st.file_uploader("Texture D (Main Image)", type=["png", "jpg", "jpeg"], key="new_itm_d")
                up_tex_n = st.file_uploader("Texture N (Normal Map)", type=["png", "jpg", "jpeg"], key="new_itm_n")
                up_tex_s = st.file_uploader("Texture S (Specular Map)", type=["png", "jpg", "jpeg"], key="new_itm_s")
                
                if st.button("Save New Item"):
                    if item_name and (up_model or up_tex_d):
                        with st.spinner("Saving item..."):
                            m_p, d_p, n_p, s_p = None, None, None, None
                            if up_model: m_p, _ = firebase_helper.save_file_direct(up_model.read(), "items", up_model.name)
                            if up_tex_d: d_p, _ = firebase_helper.save_file_direct(up_tex_d.read(), "items", up_tex_d.name)
                            if up_tex_n: n_p, _ = firebase_helper.save_file_direct(up_tex_n.read(), "items", up_tex_n.name)
                            if up_tex_s: s_p, _ = firebase_helper.save_file_direct(up_tex_s.read(), "items", up_tex_s.name)
                            
                            if firebase_helper.add_item_files(item_name, category, m_p, d_p, n_p, s_p):
                                st.success(f"Item '{item_name}' added successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to add item.")
                    else:
                        st.warning("Provide an item name and at least a model file or Texture D image.")

            st.markdown("---")
            st.subheader("Saved Items (View / Edit / Delete)")
            saved_items = firebase_helper.get_all_items()
            if not saved_items:
                st.info("No items added yet.")
            else:
                for itm in saved_items:
                    with st.expander(f"📦 {itm['name']} [{itm['category']}]"):
                        edit_itm_key = f"edit_itm_toggle_{itm['id']}"
                        if edit_itm_key not in st.session_state:
                            st.session_state[edit_itm_key] = False
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✏️ Edit Item", key=f"btn_edit_itm_{itm['id']}"):
                                st.session_state[edit_itm_key] = not st.session_state[edit_itm_key]
                                st.rerun()
                        with col2:
                            if st.button("🗑️ Delete Item", key=f"btn_del_itm_{itm['id']}", type="secondary"):
                                firebase_helper.delete_item(itm['id'])
                                st.success("Item deleted successfully!")
                                st.rerun()
                        
                        # আইটেম এডিট ফরম
                        if st.session_state[edit_itm_key]:
                            st.markdown("#### ✏️ Edit Item")
                            e_itm_name = st.text_input("Name", value=itm['name'], key=f"ein_{itm['id']}")
                            e_itm_cat = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(itm['category']), key=f"eic_{itm['id']}")
                            
                            e_up_model = st.file_uploader("Replace 3D Model (Optional)", key=f"eim_{itm['id']}")
                            e_up_d = st.file_uploader("Replace Texture D (Optional)", type=["png", "jpg", "jpeg"], key=f"eid_{itm['id']}")
                            e_up_n = st.file_uploader("Replace Texture N (Optional)", type=["png", "jpg", "jpeg"], key=f"ein_t_{itm['id']}")
                            e_up_s = st.file_uploader("Replace Texture S (Optional)", type=["png", "jpg", "jpeg"], key=f"eis_{itm['id']}")
                            
                            if st.button("💾 Save Item Changes", key=f"btn_save_itm_{itm['id']}"):
                                nm, nd, nn, ns = None, None, None, None
                                if e_up_model: nm, _ = firebase_helper.save_file_direct(e_up_model.read(), "items", e_up_model.name)
                                if e_up_d: nd, _ = firebase_helper.save_file_direct(e_up_d.read(), "items", e_up_d.name)
                                if e_up_n: nn, _ = firebase_helper.save_file_direct(e_up_n.read(), "items", e_up_n.name)
                                if e_up_s: ns, _ = firebase_helper.save_file_direct(e_up_s.read(), "items", e_up_s.name)
                                
                                if firebase_helper.update_item_files(itm['id'], e_itm_name, e_itm_cat, nm, nd, nn, ns):
                                    st.success("Item updated successfully!")
                                    st.session_state[edit_itm_key] = False
                                    st.rerun()
