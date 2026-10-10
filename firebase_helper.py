import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st

def init_firebase():
    # যদি ফায়ারবেস আগে থেকে কানেক্ট করা না থাকে, তবেই কানেক্ট করবে
    if not firebase_admin._apps:
        try:
            # Streamlit secrets থেকে ফায়ারবেসের তথ্য নেওয়া হচ্ছে
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'bundle-38c98.firebasestorage.app'
            })
        except Exception as e:
            st.error(f"Firebase connection error: {e}")
    return firestore.client()

# ডাটাবেস ক্লায়েন্ট ইনিশিয়ালাইজ করা
db = init_firebase()