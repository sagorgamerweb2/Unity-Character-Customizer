import firebase_admin
from firebase_admin import credentials, firestore, storage
import streamlit as st
import requests

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
        return None

def upload_item_file(file_bytes, file_name):
    try:
        bucket = storage.bucket()
        blob = bucket.blob(f"items/{file_name}")
        blob.upload_from_string(file_bytes)
        return f"items/{file_name}"
    except Exception as e:
        return None

def download_file_bytes(storage_path):
    """স্টোরেজ থেকে প্রসেসিংয়ের জন্য ফাইল বাইট ডাউনলোড করে"""
    try:
        bucket = storage.bucket()
        blob = bucket.blob(storage_path)
        return blob.download_as_bytes()
    except Exception as e:
        return None

def add_character(name, description, file_path, components_config):
    try:
        doc_ref = db.collection('characters').document()
        doc_ref.set({
            'id': doc_ref.id,
            'name': name,
            'description': description,
            'file_path': file_path,
            'components': components_config
        })
        return True
    except Exception as e:
        return False

def add_item(name, category, file_path, d_id, n_id, s_id, mesh_id):
    try:
        doc_ref = db.collection('items').document()
        doc_ref.set({
            'id': doc_ref.id,
            'name': name,
            'category': category,
            'file_path': file_path,
            'd_id': str(d_id).strip(),
            'n_id': str(n_id).strip(),
            's_id': str(s_id).strip(),
            'mesh_id': str(mesh_id).strip()
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

def get_all_items():
    items = []
    try:
        docs = db.collection('items').stream()
        for doc in docs:
            items.append(doc.to_dict())
    except Exception:
        pass
    return items
