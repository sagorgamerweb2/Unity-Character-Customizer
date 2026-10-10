import io
import UnityPy
from PIL import Image

def process_character_bundle(base_bundle_bytes, selected_char, items_to_apply):
    """
    মূল ক্যারেক্টারের নির্দিষ্ট Path ID অনুযায়ী আইটেমের থ্রিডি মডেল ও গ্যালারির ছবি (D, N, S) ইমপোর্ট করে।
    """
    logs = []
    def log(msg):
        logs.append(msg)

    try:
        log("Stage 1: Loading Base Character AssetBundle...")
        base_env = UnityPy.load(base_bundle_bytes)
        
        # মূল ফাইলের সব অবজেক্ট ম্যাপ করা
        base_objects = {str(obj.path_id): obj for obj in base_env.objects}
        log(f"Stage 1 Success: Found {len(base_objects)} objects in character bundle.")

        char_components = selected_char.get("components", {})

        # প্রতিটি সিলেক্ট করা ক্যাটাগরি প্রসেস করা
        for cat_name, item_files in items_to_apply.items():
            item_data = item_files["data"]
            log(f"\n---> Applying [{cat_name}]: {item_data['name']}")

            # ক্যারেক্টার থেকে এই ক্যাটাগরির মূল Path ID-গুলো নেওয়া
            cat_cfg = char_components.get(cat_name, {})
            target_mesh_id = str(cat_cfg.get("mesh_id", "0")).strip()
            target_d_id = str(cat_cfg.get("d_id", "0")).strip()
            target_n_id = str(cat_cfg.get("n_id", "0")).strip()
            target_s_id = str(cat_cfg.get("s_id", "0")).strip()

            # ১. থ্রিডি মডেল রিপ্লেস করা
            model_bytes = item_files.get("model_bytes")
            if model_bytes and target_mesh_id != "0" and target_mesh_id in base_objects:
                dst_mesh = base_objects[target_mesh_id]
                try:
                    # যদি আপলোড করা ফাইলটি Unity ফাইল হয়
                    m_env = UnityPy.load(model_bytes)
                    src_mesh = next((o for o in m_env.objects if o.type.name == "Mesh"), None)
                    if src_mesh:
                        dst_mesh.set_raw_data(src_mesh.get_raw_data())
                    else:
                        dst_mesh.set_raw_data(model_bytes)
                except Exception:
                    # সরাসরি ডাম্প বাইট হিসেবে রিপ্লেস
                    dst_mesh.set_raw_data(model_bytes)
                dst_mesh.save()
                log(f"• 3D Mesh successfully replaced into Path ID: {target_mesh_id}")

            # ২. Texture D ছবি ইমপোর্ট করা
            tex_d_bytes = item_files.get("tex_d_bytes")
            if tex_d_bytes and target_d_id != "0" and target_d_id in base_objects:
                dst_tex = base_objects[target_d_id]
                try:
                    data = dst_tex.read()
                    img = Image.open(io.BytesIO(tex_d_bytes))
                    data.image = img
                    data.save()
                    log(f"• Texture D image imported into Path ID: {target_d_id}")
                except Exception as e:
                    log(f"• Texture D error: {e}")

            # ৩. Texture N ছবি ইমপোর্ট করা
            tex_n_bytes = item_files.get("tex_n_bytes")
            if tex_n_bytes and target_n_id != "0" and target_n_id in base_objects:
                dst_tex = base_objects[target_n_id]
                try:
                    data = dst_tex.read()
                    img = Image.open(io.BytesIO(tex_n_bytes))
                    data.image = img
                    data.save()
                    log(f"• Texture N image imported into Path ID: {target_n_id}")
                except Exception as e:
                    log(f"• Texture N error: {e}")

            # ৪. Texture S ছবি ইমপোর্ট করা
            tex_s_bytes = item_files.get("tex_s_bytes")
            if tex_s_bytes and target_s_id != "0" and target_s_id in base_objects:
                dst_tex = base_objects[target_s_id]
                try:
                    data = dst_tex.read()
                    img = Image.open(io.BytesIO(tex_s_bytes))
                    data.image = img
                    data.save()
                    log(f"• Texture S image imported into Path ID: {target_s_id}")
                except Exception as e:
                    log(f"• Texture S error: {e}")

        # স্টেজ ৫: নতুন বান্ডেল আউটপুট তৈরি
        log("\nStage 5: Packaging modified AssetBundle...")
        output_stream = io.BytesIO()
        for file in base_env.files.values():
            output_stream.write(file.save())
        final_bytes = output_stream.getvalue()
        if len(final_bytes) == 0:
            final_bytes = base_env.file.save()

        log(f"Stage 5 Success: Final bundle ready ({len(final_bytes)} bytes).")
        return True, final_bytes, logs

    except Exception as e:
        log(f"Error during processing: {str(e)}")
        return False, None, logs
