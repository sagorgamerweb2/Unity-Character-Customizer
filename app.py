import streamlit as st
import firebase_helper
import processing

# পেজের কনফিগারেশন
st.set_page_config(page_title="Unity Character Customizer", page_icon="🎮", layout="wide")

# সাইডবার নেভিগেশন
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Public Customizer", "Admin Panel"])

if page == "Public Customizer":
    st.title("🎮 Character Customizer")
    st.write("Welcome to the public character customizer!")
    st.info("Here users will be able to select characters and items. (Coming in the next phases)")

elif page == "Admin Panel":
    st.title("🔒 Admin Panel")
    st.write("This is the secure area for managing characters and items.")
    st.info("Admin login and upload forms will be placed here. (Coming in the next phases)")