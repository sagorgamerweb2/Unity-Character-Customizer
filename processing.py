import UnityPy

def inspect_asset_bundle(file_bytes):
    """
    এই ফাংশনটি শুধু অ্যাসেট বান্ডেল পড়ে দেখবে ভেতরে কী কী আছে।
    এটি টেস্ট করার জন্য ব্যবহার হবে।
    """
    try:
        env = UnityPy.load(file_bytes)
        objects_info = []
        for obj in env.objects:
            objects_info.append(f"Path ID: {obj.path_id}, Type: {obj.type.name}")
        return objects_info
    except Exception as e:
        return [f"Error loading bundle: {e}"]