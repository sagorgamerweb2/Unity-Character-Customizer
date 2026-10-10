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
    
    characters = firebase_helper.get_all_characters()
    all_items = firebase_helper.get_all_items()

    if not characters:
        st.info("No characters uploaded yet by admin.")
    else:
        st.subheader("1. Choose a Base Character")
        char_names = [c["name"] for c in characters]
        selected_char_name = st.selectbox("Select Character:", char_names)
        
        selected_char = next(c for c in characters if c["name"] == selected_char_name)
        if selected_char.get("description"):
            st.caption(selected_char["description"])

        st.markdown("---")
        st.subheader("2. Customize Components")

        selected_items_for_job = {}
        for cat in CATEGORIES:
            cat_items = [itm for itm in all_items if itm.get("category") == cat]
            options = ["None (Default)"] + [itm["name"] for itm in cat_items]
            
            chosen_opt = st.selectbox(f"Choose {cat}:", options, key=f"sel_{cat}")
            if chosen_opt != "None (Default)":
                item_obj = next(itm for itm in cat_items if itm["name"] == chosen_opt)
                selected_items_for_job[cat] = item_obj

        st.markdown("---")
        if st.button("🚀 Create Bundle", type="primary"):
            if not selected_items_for_job:
                st.warning("Please select at least one item to customize.")
            else:
                with st.spinner("Processing assets & textures... Please wait."):
                    base_bytes = firebase_helper.download_file_bytes(selected_char["file_path"])
                    
                    if not base_bytes:
                        st.error("Failed to load base character bundle.")
                    else:
                        items_to_apply = {}
                        has_error = False
                        
                        for cat, itm in selected_items_for_job.items():
                            model_bytes = firebase_helper.download_file_bytes(itm.get("model_path"))
                            tex_d_bytes = firebase_helper.download_file_bytes(itm.get("tex_d_path"))
                            tex_n_bytes = firebase_helper.download_file_bytes(itm.get("tex_n_path"))
                            tex_s_bytes = firebase_helper.download_file_bytes(itm.get("tex_s_path"))
                            
                            items_to_apply[cat] = {
                                "data": itm,
                                "model_bytes": model_bytes,
                                "tex_d_bytes": tex_d_bytes,
                                "tex_n_bytes": tex_n_bytes,
                                "tex_s_bytes": tex_s_bytes
                            }
                        
                        success, result_bytes, logs = processing.process_character_bundle(
                            base_bytes, selected_char, items_to_apply
                        )
                        
                        with st.expander("View Processing Logs", expanded=True):
                            for l in logs:
                                st.text(l)
                        
                        if success and result_bytes:
                            st.success("🎉 AssetBundle created successfully!")
                            out_filename = f"{selected_char_name}_Customized.bundle"
                            st.download_button(
                                label=f"⬇️ Download {out_filename}",
                                data=result_bytes,
                                file_name=out_filename,
                                mime="application/octet-stream"
                            )
                        else:
                            st.error("Bundle creation failed. Check logs above.")

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
        st.success("Welcome, Admin!")
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()
        
        st.markdown("---")
        tab1, tab2 = st.tabs(["Manage Characters", "Manage Items"])
        
        # ট্যাব ১: ক্যারেক্টার অ্যাড
        with tab1:
            st.subheader("Add New Base Character")
            char_name = st.text_input("Character Name")
            char_desc = st.text_area("Character Description (Optional)")
            uploaded_char_file = st.file_uploader("Upload Base AssetBundle", key="char_uploader")
            
            st.markdown("##### Base Character Target Path IDs (6 Categories)")
            components_config = {}
            for cat in CATEGORIES:
                with st.expander(f"⚙️ {cat} Target IDs"):
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        m_id = st.text_input(f"{cat} Mesh Path ID", value="0", key=f"base_m_{cat}")
                        d_id = st.text_input(f"{cat} Texture D ID", value="0", key=f"base_d_{cat}")
                    with c_col2:
                        n_id = st.text_input(f"{cat} Texture N ID", value="0", key=f"base_n_{cat}")
                        s_id = st.text_input(f"{cat} Texture S ID", value="0", key=f"base_s_{cat}")
                    components_config[cat] = {
                        "mesh_id": m_id.strip(), "d_id": d_id.strip(), "n_id": n_id.strip(), "s_id": s_id.strip()
                    }

            if st.button("Upload & Save Character"):
                if char_name and uploaded_char_file:
                    with st.spinner("Saving character..."):
                        file_bytes = uploaded_char_file.read()
                        file_path, err = firebase_helper.save_file_direct(file_bytes, "characters", uploaded_char_file.name)
                        if file_path:
                            if firebase_helper.add_character(char_name, char_desc, file_path, components_config):
                                st.success(f"Character '{char_name}' saved successfully!")
                                st.rerun()
                            else:
                                st.error("Database save failed.")
                        else:
                            st.error(f"Upload failed: {err}")
                else:
                    st.warning("Please provide character name and file.")

            st.markdown("---")
            st.subheader("Saved Characters List")
            chars = firebase_helper.get_all_characters()
            if chars:
                for c in chars:
                    with st.expander(f"👤 {c['name']}"):
                        st.json(c.get("components", {}))
            else:
                st.info("No characters saved yet.")

        # ট্যাব ২: সহজ আইটেম অ্যাড (ছবি ও মডেল আপলোড)
        with tab2:
            st.subheader("Add New Component Item")
            item_name = st.text_input("Item Name (e.g., Cool Jacket, Punk Hair)")
            category = st.selectbox("Select Category", CATEGORIES)
            
            st.markdown("##### 📁 Upload 3D Model & Textures (No IDs needed!)")
            up_model = st.file_uploader("1. Upload 3D Model / Mesh Dump File", key="item_model")
            up_tex_d = st.file_uploader("2. Upload Texture D (Image from Gallery)", type=["png", "jpg", "jpeg"], key="item_d")
            up_tex_n = st.file_uploader("3. Upload Texture N (Optional Image)", type=["png", "jpg", "jpeg"], key="item_n")
            up_tex_s = st.file_uploader("4. Upload Texture S (Optional Image)", type=["png", "jpg", "jpeg"], key="item_s")
            
            if st.button("Save Item"):
                if item_name and (up_model or up_tex_d):
                    with st.spinner("Saving item and textures..."):
                        # মডেল সেভ
                        model_path = None
                        if up_model:
                            model_path, _ = firebase_helper.save_file_direct(up_model.read(), "items", up_model.name)
                        
                        # টেক্সচার D সেভ
                        tex_d_path = None
                        if up_tex_d:
                            tex_d_path, _ = firebase_helper.save_file_direct(up_tex_d.read(), "items", up_tex_d.name)

                        # টেক্সচার N সেভ
                        tex_n_path = None
                        if up_tex_n:
                            tex_n_path, _ = firebase_helper.save_file_direct(up_tex_n.read(), "items", up_tex_n.name)

                        # টেক্সচার S সেভ
                        tex_s_path = None
                        if up_tex_s:
                            tex_s_path, _ = firebase_helper.save_file_direct(up_tex_s.read(), "items", up_tex_s.name)

                        # ডাটাবেসে তথ্য রাখা
                        success = firebase_helper.add_item_files(
                            item_name, category, model_path, tex_d_path, tex_n_path, tex_s_path
                        )
                        if success:
                            st.success(f"Item '{item_name}' added under '{category}' successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to save item.")
                else:
                    st.warning("Please provide an item name and at least a model file or Texture D image.")
            
            st.markdown("---")
            st.subheader("Saved Items List")
            saved_items = firebase_helper.get_all_items()
            if saved_items:
                for itm in saved_items:
                    st.write(f"• **{itm['name']}** [{itm['category']}]")
            else:
                st.info("No items added yet.")
