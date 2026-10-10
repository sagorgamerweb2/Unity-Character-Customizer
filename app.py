import streamlit as st
import firebase_helper
import processing

st.set_page_config(page_title="Unity Character Customizer", page_icon="🎮", layout="wide")

CATEGORIES = ["Hair", "Head", "Accessory", "Body / Top", "Bottom", "Shoes"]

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Public Customizer", "Admin Panel"])

if page == "Public Customizer":
    st.title("🎮 Character Customizer")
    st.write("Welcome to the public character customizer!")
    
    st.subheader("Available Characters")
    characters = firebase_helper.get_all_characters()
    if characters:
        for char in characters:
            st.success(f"**{char['name']}**")
            if char.get('description'):
                st.write(char['description'])
            st.write("---")
    else:
        st.info("No characters available yet.")

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
        
        # অ্যাডমিন প্যানেলে ট্যাব তৈরি
        tab1, tab2 = st.tabs(["Manage Characters", "Manage Items"])
        
        # ট্যাব ১: ক্যারেক্টার ম্যানেজমেন্ট
        with tab1:
            st.subheader("Add New Base Character")
            char_name = st.text_input("Character Name")
            char_desc = st.text_area("Character Description (Optional)")
            uploaded_char_file = st.file_uploader("Upload Base AssetBundle", key="char_uploader")
            
            if st.button("Upload & Save Character"):
                if char_name and uploaded_char_file:
                    with st.spinner("Uploading and saving character..."):
                        file_bytes = uploaded_char_file.read()
                        file_path = firebase_helper.upload_character_file(file_bytes, uploaded_char_file.name)
                        if file_path:
                            if firebase_helper.add_character(char_name, char_desc, file_path):
                                st.success(f"Character '{char_name}' added successfully!")
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
                    st.write(f"• **{c['name']}** (File: `{c.get('file_path', 'N/A')}`)")
            else:
                st.info("No characters saved yet.")

        # ট্যাব ২: আইটেম ম্যানেজমেন্ট
        with tab2:
            st.subheader("Add New Component Item")
            item_name = st.text_input("Item Name (e.g., Red Jacket, Anime Hair)")
            category = st.selectbox("Category", CATEGORIES)
            uploaded_item_file = st.file_uploader("Upload Item Import/Dump File", key="item_uploader")
            
            st.markdown("##### Path IDs Configuration")
            col1, col2 = st.columns(2)
            with col1:
                d_id = st.text_input("Texture2D D Path ID", value="0", help="Texture variant D ID")
                n_id = st.text_input("Texture2D N Path ID", value="0", help="Texture variant N ID")
            with col2:
                s_id = st.text_input("Texture2D S Path ID", value="0", help="Texture variant S ID")
                mesh_id = st.text_input("3D Mesh Path ID", value="0", help="Mesh object Path ID")
            
            if st.button("Upload & Save Item"):
                if item_name and uploaded_item_file:
                    with st.spinner("Uploading item and saving configuration..."):
                        file_bytes = uploaded_item_file.read()
                        file_path = firebase_helper.upload_item_file(file_bytes, uploaded_item_file.name)
                        if file_path:
                            if firebase_helper.add_item(item_name, category, file_path, d_id, n_id, s_id, mesh_id):
                                st.success(f"Item '{item_name}' added under '{category}' successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to save item to database.")
                        else:
                            st.error("Failed to upload item file.")
                else:
                    st.warning("Please provide item name and file.")
            
            st.markdown("---")
            st.subheader("Saved Items List")
            saved_items = firebase_helper.get_all_items()
            if saved_items:
                for itm in saved_items:
                    with st.expander(f"📦 {itm['name']} [{itm['category']}]"):
                        st.write(f"**Dump File:** `{itm.get('file_path', 'N/A')}`")
                        st.write(f"**Mesh Path ID:** `{itm.get('mesh_id', '0')}`")
                        st.write(f"**Texture2D D ID:** `{itm.get('d_id', '0')}`")
                        st.write(f"**Texture2D N ID:** `{itm.get('n_id', '0')}`")
                        st.write(f"**Texture2D S ID:** `{itm.get('s_id', '0')}`")
            else:
                st.info("No items added yet.")
