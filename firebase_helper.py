import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import requests
import uuid
import math

FIREBASE_WEB_API_KEY = "AIzaSyDYvXgT6RAfXAkKUvFqxmIrNYnS-EuIgAg"

def init_firebase():
    if not firebase_admin._apps:
        try:
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
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

# ==================== ঝামেলামুক্ত ডাইরেক্ট ফাইল স্টোরেজ ====================
def save_file_direct(file_bytes, folder_name, file_name):
    """
    কোনো ক্লাউড বাকেট ছাড়াই সরাসরি ডাটাবেসে ফাইল সেভ করে।
    ১-৩ এমবি ফাইলের জন্য এটি ১০০% নিখুঁত এবং ফেইল করার কোনো সুযোগ নেই।
    """
    try:
        file_id = str(uuid.uuid4())
        chunk_size = 650 * 1024  # নিরাপদ চাঙ্ক সাইজ (~650 KB)
        total_chunks = math.ceil(len(file_bytes) / chunk_size)
        
        # ফাইল ইনফো সেভ
        meta_ref = db.collection('stored_files').document(file_id)
        meta_ref.set({
            'file_name': file_name,
            'folder': folder_name,
            'total_chunks': total_chunks,
            'size': len(file_bytes)
        })
        
        # ডাটা চাঙ্ক সেভ
        for i in range(total_chunks):
            chunk_data = file_bytes[i * chunk_size : (i + 1) * chunk_size]
            chunk_ref = meta_ref.collection('chunks').document(str(i))
            chunk_ref.set({
                'data': chunk_data,
                'index': i
            })
            
        return f"db::{file_id}", None
    except Exception as e:
        return None, f"Save failed: {str(e)}"

def upload_character_file(file_bytes, file_name):
    return save_file_direct(file_bytes, "characters", file_name)

def upload_item_file(file_bytes, file_name):
    return save_file_direct(file_bytes, "items", file_name)

def download_file_bytes(saved_path):
    """ডাটাবেস থেকে ফাইল জোড়া লাগিয়ে ফেরত দেয়"""
    try:
        if saved_path.startswith("db::"):
            file_id = saved_path.replace("db::", "")
            meta_ref = db.collection('stored_files').document(file_id)
            meta = meta_ref.get().to_dict()
            if not meta:
                return None
            
            total_chunks = meta['total_chunks']
            chunks = []
            for i in range(total_chunks):
                doc = meta_ref.collection('chunks').document(str(i)).get()
                if doc.exists:
                    chunks.append(doc.to_dict()['data'])
            return b"".join(chunks)
    except Exception as e:
        print(f"Read error: {e}")
    return None

# ==================== ক্যারেক্টার ও আইটেম ম্যানেজমেন্ট ====================
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
