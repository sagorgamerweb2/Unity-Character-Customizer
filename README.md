# 🎮 Unity Character Customizer

GitHub + Streamlit + Firebase — সবকিছু ফ্রি।

## ফাইল তালিকা
| ফাইল | কাজ |
|---|---|
| app.py | পাবলিক পেজ (ক্যারেক্টার বাছাই → বান্ডেল তৈরি → ডাউনলোড) |
| admin.py | অ্যাডমিন প্যানেল |
| processing.py | Mesh/Texture ইমপোর্ট, কম্প্রেস, সাইজ মেলানো |
| firebase_helper.py | Firebase-এ ফাইল ও তথ্য রাখা |
| mesh_dump.py | UABE টেক্সট ডাম্প পড়ার সহায়ক |
| requirements.txt, .streamlit/ | সেটিংস |

## সেটআপ (ধাপে ধাপে)

### ধাপ ১ — GitHub-এ কোড তোলা
1. ZIP আনজিপ করুন (GitHub ZIP নিজে খোলে না)।
2. GitHub-এ নতুন Repository বানান (নাম যেমন `character-customizer`)।
3. **Add file → Upload files** → সব ফাইল ও `.streamlit` ফোল্ডারসহ আপলোড → Commit।
   - `.streamlit/secrets.toml` বা Firebase `.json` ফাইল **কখনো GitHub-এ দেবেন না**।

### ধাপ ২ — Firebase ডাটাবেস
1. console.firebase.google.com → **Create project** (Analytics বন্ধ রাখুন)।
2. **Build → Firestore Database → Create database** → Location বেছে নিন → **Production mode**।
3. ⚙️ **Project settings → Service accounts → Generate new private key** → একটি `.json` ফাইল ডাউনলোড হবে।
4. Storage চালু করার দরকার নেই (ওটা পেইড)।

### ধাপ ৩ — Streamlit-এ ডিপ্লয়
1. share.streamlit.io → **Create app** → আপনার Repo, Branch `main`, Main file `app.py`।
2. **Advanced settings** → Python version **3.11** → **Secrets** বক্সে নিচেরটা পেস্ট করুন:
```
ADMIN_PASSWORD = "আপনার-শক্ত-পাসওয়ার্ড"
FIREBASE_JSON = '''
(এখানে ডাউনলোড করা .json ফাইলের পুরো লেখা পেস্ট)
'''
```
3. **Deploy**।

## ব্যবহার

### অ্যাডমিন
1. **🔐 অ্যাডমিন** → পাসওয়ার্ড দিয়ে লগইন।
2. **ক্যারেক্টার** → নাম, আনকম্প্রেসড বান্ডেল, আর ৬ ক্যাটাগরির জন্য Mesh/D/N/S Path ID দিন। সেভের সময় ID বান্ডেলে আছে কিনা ও টাইপ ঠিক কিনা অটো যাচাই হয়।
3. **আইটেম** → নাম, ক্যাটাগরি, Mesh ডাম্প ফাইল, D/N/S ছবি আপলোড।
4. **Path ID খুঁজুন** → বান্ডেল দিলে ভিতরের সব Mesh/Texture2D-এর নাম ও ID দেখায়।

### পাবলিক
ক্যারেক্টার বাছুন → প্রতি ক্যাটাগরি থেকে একটি আইটেম → **ধাপ ১+২** (Mesh তারপর Texture ইমপোর্ট) → **ধাপ ৩** (অরিজিনাল বান্ডেল দিলে কম্প্রেস করে সাইজ মিলিয়ে অটো ডাউনলোড)।

## জানা দরকার
- **Mesh ডাম্প:** UABE-তে **Export Raw (.dat)** সবচেয়ে নির্ভরযোগ্য। টেক্সট ডাম্প (.txt) পড়ার চেষ্টা করা হয়, কিন্তু সেটা পরীক্ষামূলক।
- **সাইজ মেলানো:** ফাইনাল ফাইল ছোট হলে শেষে 00 বাইট যোগ হয়। বড় হলে ছোট ছবি ব্যবহার করুন।
- **অটো ডাউনলোড:** কিছু ব্রাউজার আটকে দিতে পারে — তখন নিচের ডাউনলোড বাটন চাপুন।
- **Firebase ফ্রি সীমা:** দিনে ৫০,০০০ রিড, ২০,০০০ রাইট, ১ GB স্টোরেজ। ফাইল zlib দিয়ে ছোট করে রাখা হয় ও ক্যাশ ব্যবহার হয়।
