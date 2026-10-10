# ক্যাটাগরি ও স্লটের তালিকা (এক জায়গায় রাখা হয়েছে)
CATEGORIES = [
    ("hair", "Hair — চুল"),
    ("head", "Head — মাথা/মুখ"),
    ("accessory", "Marks / Glasses — মার্কস/চশমা"),
    ("body", "Body / Top — উপরের পোশাক"),
    ("bottom", "Bottom — নিচের পোশাক"),
    ("shoes", "Shoes — জুতা"),
]
CAT_LABEL = dict(CATEGORIES)

# mesh = 3D মডেল, d/n/s = Texture2D ছবি (Diffuse / Normal / Specular)
SLOTS = [
    ("mesh", "3D Mesh Path ID"),
    ("d", "Texture D Path ID"),
    ("n", "Texture N Path ID"),
    ("s", "Texture S Path ID"),
]
