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
    
    characters = firebase_helper.get_all_characters()
    all_items = firebase_helper.get_all_items()

    if not characters:
        st.info("No characters uploaded yet by admin.")
    else:
        st.subheader("1. Choose a Base Character")
        char_names = [c["name"] for c in characters]
        selected_char_name = st.selectbox("Select Character:", char_names)
        
        # সিলেক্টেড ক্যারেক্টারের ডাটা বের করা
        selected_char = next(c for c in characters if c["name"] == selected_char_name)
        if selected_char.get("description"):
            st.caption(selected_char["description"])

        st.markdown("---")
        st.subheader("2. Customize Components (6 Categories)")

        # ৬টি ক্যাটাগরি থেকে একটি করে আইটেম সিলেক্ট করা
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
                with st.spinner("Downloading assets and building bundle... Please wait."):
                    # ১. মূল ক্যারেক্টার বান্ডেল ডাউনলোড
                    base_bytes = firebase_helper.download_file_bytes(selected_char["file_path"])
                    
                    if not base_bytes:
                        st.error("Failed to load base character file.")
                    else:
                        # ২. সিলেক্ট করা প্রতিটি আইটেমের ডাম্প ফাইল ডাউনলোড
                        items_to_apply = {}
                        has_error = False
                        
                        for cat, itm in selected_items_for_job.items():
                            dump_bytes = firebase_helper.download_file_bytes(itm["file_path"])
                            if dump_bytes:
                                items_to_apply[cat] = {"data": itm, "dump_bytes": dump_bytes}
                            else:
                                st.error(f"Failed to fetch item file for: {itm['name']}")
                                has_error = True
                                break
                        
                        if not has_error:
                            status_placeholder = st.empty()
                            # ৩. প্রসেসিং ইঞ্জিন চালানো
                            success, result_bytes, logs = processing.process_character_bundle(
                                base_bytes, items_to_apply
                            )
                            
                            # লগ দেখানো
                            with st.expander("View Processing Logs", expanded=True):
                                for l in logs:
                                    st.text(l)
                            
                            # ৪. ডাউনলোড বাটন দেখানো
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
                                st.error("Bundle creation failed. Check the logs above.")

# ==================== অ্যাডমিন প্যানেল (ADMIN PANEL) ====================
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
        
        # ট্যাব ১: ক্যারেক্টার এবং তার ৬টি ক্যাটাগরির Base Path ID কনফিগারেশন
        with tab1:
            st.subheader("Add New Base Character")
            char_name = st.text_input("Character Name")
            char_desc = st.text_area("Character Description (Optional)")
            uploaded_char_file = st.file_uploader("Upload Base AssetBundle", key="char_uploader")
            
            st.markdown("##### Base Character Components Path IDs (6 Categories)")
            st.caption("Enter the original Path IDs of this character's parts (Mesh and D, N, S textures).")
            
            components_config = {}
            for cat in CATEGORIES:
                with st.expander(f"⚙️ {cat} Component IDs"):
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
                    with st.spinner("Uploading character and saving configuration..."):
                        file_bytes = uploaded_char_file.read()
                        file_path = firebase_helper.upload_character_file(file_bytes, uploaded_char_file.name)
                        if file_path:
                            if firebase_helper.add_character(char_name, char_desc, file_path, components_config):
                                st.success(f"Character '{char_name}' and component IDs saved successfully!")
                                st.rerun()
                            else:
                                st.error("Database save failed.")
                        else:
                            st.error("Storage upload failed.")
                else:
                    st.warning("Please provide character name and file.")

            st.markdown("---")
            st.subheader("Saved Characters List")
            chars = firebase_helper.get_all_characters()
            if chars:
                for c in chars:
                    with st.expander(f"👤 {c['name']}"):
                        st.write(f"**Bundle Path:** `{c.get('file_path')}`")
                        st.json(c.get("components", {}))
            else:
                st.info("No characters saved yet.")

        # ট্যাব ২: আইটেম ম্যানেজমেন্ট
        with tab2:
            st.subheader("Add New Component Item")
            item_name = st.text_input("Item Name (e.g., Red Jacket, Black Hair)")
            category = st.selectbox("Category", CATEGORIES)
            uploaded_item_file = st.file_uploader("Upload Item Import/Dump File", key="item_uploader")
            
            st.markdown("##### Item Path IDs Configuration")
            col1, col2 = st.columns(2)
            with col1:
                d_id = st.text_input("Texture2D D Path ID", value="0")
                n_id = st.text_input("Texture2D N Path ID", value="0")
            with col2:
                s_id = st.text_input("Texture2D S Path ID", value="0")
                mesh_id = st.text_input("3D Mesh Path ID", value="0")
            
            if st.button("Upload & Save Item"):
                if item_name and uploaded_item_file:
                    with st.spinner("Uploading item and saving configuration..."):
                        file_bytes = uploaded_item_file.read()
                        file_path = firebase_helper.upload_item_file(file_bytes, uploaded_item_file.name)
                        if file_path:
                            if firebase_helper.add_item(item_name, category, file_path, d_id, n_id, s_id, mesh_id):
                                st.success(f"Item '{item_name}' saved under '{category}' successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to save item.")
                        else:
                            st.error("Failed to upload file.")
                else:
                    st.warning("Please provide item name and file.")
            
            st.markdown("---")
            st.subheader("Saved Items List")
            saved_items = firebase_helper.get_all_items()
            if saved_items:
                for itm in saved_items:
                    with st.expander(f"📦 {itm['name']} [{itm['category']}]"):
                        st.write(f"**Mesh Path ID:** `{itm.get('mesh_id')}`")
                        st.write(f"**Texture D ID:** `{itm.get('d_id')}` | **N ID:** `{itm.get('n_id')}` | **S ID:** `{itm.get('s_id')}`")
