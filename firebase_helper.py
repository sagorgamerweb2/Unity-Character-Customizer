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
            st.error(f"Firebase error: {e}")
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

# ==================== ফাইল ম্যানেজমেন্ট ====================
def save_file_direct(file_bytes, folder_name, file_name):
    try:
        file_id = str(uuid.uuid4())
        chunk_size = 650 * 1024
        total_chunks = math.ceil(len(file_bytes) / chunk_size)
        
        meta_ref = db.collection('stored_files').document(file_id)
        meta_ref.set({'file_name': file_name, 'folder': folder_name, 'total_chunks': total_chunks, 'size': len(file_bytes)})
        
        for i in range(total_chunks):
            chunk_ref = meta_ref.collection('chunks').document(str(i))
            chunk_ref.set({'data': file_bytes[i * chunk_size : (i + 1) * chunk_size], 'index': i})
            
        return f"db::{file_id}", None
    except Exception as e:
        return None, str(e)

def download_file_bytes(saved_path):
    try:
        if not saved_path or not saved_path.startswith("db::"): return None
        file_id = saved_path.replace("db::", "")
        meta = db.collection('stored_files').document(file_id).get().to_dict()
        if not meta: return None
        
        chunks = []
        for i in range(meta['total_chunks']):
            doc = db.collection('stored_files').document(file_id).collection('chunks').document(str(i)).get()
            if doc.exists: chunks.append(doc.to_dict()['data'])
        return b"".join(chunks)
    except Exception:
        return None

def delete_file_direct(saved_path):
    try:
        if not saved_path or not saved_path.startswith("db::"): return
        file_id = saved_path.replace("db::", "")
        meta_ref = db.collection('stored_files').document(file_id)
        meta = meta_ref.get().to_dict()
        if meta:
            for i in range(meta.get('total_chunks', 0)):
                meta_ref.collection('chunks').document(str(i)).delete()
            meta_ref.delete()
    except Exception:
        pass

# ==================== ক্যারেক্টার CRUD ====================
def add_character(name, description, file_path, components_config):
    try:
        db.collection('characters').add({
            'name': name, 'description': description, 'file_path': file_path, 'components': components_config
        })
        return True
    except: return False

def update_character(doc_id, name, description, components_config, new_file_path=None):
    try:
        doc_ref = db.collection('characters').document(doc_id)
        data = {'name': name, 'description': description, 'components': components_config}
        if new_file_path:
            old = doc_ref.get().to_dict()
            if old and old.get('file_path'): delete_file_direct(old['file_path'])
            data['file_path'] = new_file_path
        doc_ref.update(data)
        return True
    except: return False

def delete_character(doc_id):
    try:
        doc_ref = db.collection('characters').document(doc_id)
        old = doc_ref.get().to_dict()
        if old and old.get('file_path'): delete_file_direct(old['file_path'])
        doc_ref.delete()
        return True
    except: return False

# ==================== আইটেম CRUD ====================
def add_item_files(name, category, model_path, tex_d_path, tex_n_path, tex_s_path):
    try:
        db.collection('items').add({
            'name': name, 'category': category, 'model_path': model_path, 'tex_d_path': tex_d_path, 'tex_n_path': tex_n_path, 'tex_s_path': tex_s_path
        })
        return True
    except: return False

def update_item_files(doc_id, name, category, new_model=None, new_d=None, new_n=None, new_s=None):
    try:
        doc_ref = db.collection('items').document(doc_id)
        old = doc_ref.get().to_dict() or {}
        data = {'name': name, 'category': category}
        
        if new_model:
            if old.get('model_path'): delete_file_direct(old['model_path'])
            data['model_path'] = new_model
        if new_d:
            if old.get('tex_d_path'): delete_file_direct(old['tex_d_path'])
            data['tex_d_path'] = new_d
        if new_n:
            if old.get('tex_n_path'): delete_file_direct(old['tex_n_path'])
            data['tex_n_path'] = new_n
        if new_s:
            if old.get('tex_s_path'): delete_file_direct(old['tex_s_path'])
            data['tex_s_path'] = new_s

        doc_ref.update(data)
        return True
    except: return False

def delete_item(doc_id):
    try:
        doc_ref = db.collection('items').document(doc_id)
        old = doc_ref.get().to_dict()
        if old:
            for k in ['model_path', 'tex_d_path', 'tex_n_path', 'tex_s_path']:
                if old.get(k): delete_file_direct(old[k])
        doc_ref.delete()
        return True
    except: return False

# ==================== ডাটা রিডিং (গ্যারান্টিড আইডি সহ) ====================
def get_all_characters():
    chars = []
    try:
        for doc in db.collection('characters').stream():
            data = doc.to_dict()
            data['doc_id'] = doc.id  # আসল ফায়ারবেস আইডি
            chars.append(data)
    except: pass
    return chars

def get_all_items():
    items = []
    try:
        for doc in db.collection('items').stream():
            data = doc.to_dict()
            data['doc_id'] = doc.id  # আসল ফায়ারবেস আইডি
            items.append(data)
    except: pass
    return items
