import firebase_admin
from firebase_admin import credentials, firestore, storage
import streamlit as st
import requests

# আপনার দেওয়া Web API Key
FIREBASE_WEB_API_KEY = "AIzaSyDYvXgT6RAfXAkKUvFqxmIrNYnS-EuIgAg"

def init_firebase():
    if not firebase_admin._apps:
        try:
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'bundle-38c98.firebasestorage.app'
            })
        except Exception as e:
            st.error(f"Firebase connection error: {e}")
    return firestore.client()

db = init_firebase()

def login_admin(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    try:
        r = requests.post(url, json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def upload_character_file(file_bytes, file_name):
    try:
        bucket = storage.bucket()
        blob = bucket.blob(f"characters/{file_name}")
        blob.upload_from_string(file_bytes)
        return f"characters/{file_name}"
    except Exception as e:
        print(f"Storage error: {e}")
        return None

def add_character(name, description, file_path):
    try:
        doc_ref = db.collection('characters').document()
        doc_ref.set({
            'id': doc_ref.id,
            'name': name,
            'description': description,
            'file_path': file_path
        })
        return True
    except Exception as e:
        return False

def get_all_characters():
    chars = []
    try:
        docs = db.collection('characters').stream()
        for doc in docs:
            chars.append(doc.to_dict())
    except Exception:
        pass
    return chars
