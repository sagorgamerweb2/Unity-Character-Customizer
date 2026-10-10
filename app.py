import streamlit as st
import firebase_helper
import processing

st.set_page_config(page_title="Unity Character Customizer", page_icon="🎮", layout="wide")

# লগইনের স্ট্যাটাস সেভ রাখা
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
    
    # লগইন না থাকলে লগইন ফর্ম দেখাবে
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
    
    # লগইন সফল হলে ড্যাশবোর্ড দেখাবে
    else:
        st.success("Welcome to the secure Admin Panel!")
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()
        
        st.markdown("---")
        st.subheader("Add New Base Character")
        
        char_name = st.text_input("Character Name")
        char_desc = st.text_area("Character Description (Optional)")
        
        # এখানে Error ছিল, যা এখন ঠিক করে দেওয়া হয়েছে
        uploaded_file = st.file_uploader("Upload Base AssetBundle")
        
        if st.button("Upload & Save Character"):
            if char_name and uploaded_file:
                with st.spinner("Uploading file and saving data... Please wait."):
                    file_bytes = uploaded_file.read()
                    
                    # স্টোরেজে আপলোড
                    file_path = firebase_helper.upload_character_file(file_bytes, uploaded_file.name)
                    
                    if file_path:
                        # ডাটাবেসে সেভ
                        success = firebase_helper.add_character(char_name, char_desc, file_path)
                        if success:
                            st.success(f"Character '{char_name}' added successfully!")
                        else:
                            st.error("Database save failed.")
                    else:
                        st.error("File upload failed. Please check Firebase Storage.")
            else:
                st.warning("Please enter a character name and upload a file.")
