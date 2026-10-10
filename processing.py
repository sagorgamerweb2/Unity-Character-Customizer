import io
import UnityPy

def process_character_bundle(base_bundle_bytes, items_to_apply, progress_callback=None):
    """
    UnityPy ব্যবহার করে মূল অ্যাসেট বান্ডেলে নতুন আইটেমগুলোর মেশ এবং টেক্সচার প্রতিস্থাপন করে।
    """
    logs = []
    
    def log(msg):
        logs.append(msg)
        if progress_callback:
            progress_callback(msg)

    try:
        # স্টেজ ১: বেস বান্ডেল লোড ও যাচাই
        log("Stage 1: Loading and inspecting Base Character AssetBundle...")
        base_env = UnityPy.load(base_bundle_bytes)
        
        # বেস বান্ডেলের সব অবজেক্ট ম্যাপ করা (Path ID অনুযায়ী)
        base_objects = {}
        for obj in base_env.objects:
            base_objects[str(obj.path_id)] = obj
        log(f"Stage 1 Success: Found {len(base_objects)} objects in base character.")

        # প্রতিটি সিলেক্টেড আইটেম প্রসেস করা
        for cat_name, item_info in items_to_apply.items():
            if not item_info or not item_info.get("dump_bytes"):
                continue

            item_data = item_info["data"]
            dump_bytes = item_info["dump_bytes"]
            
            log(f"\nProcessing category: [{cat_name}] -> Item: {item_data['name']}")
            
            # আইটেম ডাম্প ফাইল লোড করা
            item_env = UnityPy.load(dump_bytes)
            item_objects = {str(o.path_id): o for o in item_env.objects}

            # স্টেজ ২: মেশ (Mesh) প্রতিস্থাপন
            mesh_id = str(item_data.get("mesh_id", "0")).strip()
            if mesh_id != "0" and mesh_id in base_objects:
                if mesh_id in item_objects:
                    src_mesh_obj = item_objects[mesh_id]
                    dst_mesh_obj = base_objects[mesh_id]
                    # মেশ ডাটা কপি ও রিপ্লেস
                    dst_mesh_obj.set_raw_data(src_mesh_obj.get_raw_data())
                    dst_mesh_obj.save()
                    log(f"Stage 2: Mesh replaced successfully (Path ID: {mesh_id})")
                else:
                    log(f"Warning: Mesh ID {mesh_id} not found in dump file.")

            # স্টেজ ৪: Texture2D ভেরিয়েন্ট (D, N, S) প্রতিস্থাপন
            tex_variants = [
                ("Texture D", item_data.get("d_id")),
                ("Texture N", item_data.get("n_id")),
                ("Texture S", item_data.get("s_id"))
            ]
            
            for tex_name, tid in tex_variants:
                tid_str = str(tid).strip()
                if tid_str != "0" and tid_str in base_objects:
                    if tid_str in item_objects:
                        src_tex = item_objects[tid_str]
                        dst_tex = base_objects[tid_str]
                        # টেক্সচার বাইট ডাটা প্রতিস্থাপন
                        dst_tex.set_raw_data(src_tex.get_raw_data())
                        dst_tex.save()
                        log(f"Stage 4: {tex_name} replaced successfully (Path ID: {tid_str})")
                    else:
                        log(f"Warning: {tex_name} ID {tid_str} not found in dump file.")

        # স্টেজ ৫: নতুন অ্যাসেট বান্ডেল ফাইল তৈরি ও সেভ করা
        log("\nStage 5: Packaging and saving modified AssetBundle...")
        
        output_stream = io.BytesIO()
        # বেস ফাইলের কম্প্রেসড ফাইল সেভ করা
        for file in base_env.files.values():
            output_stream.write(file.save())
            
        final_bytes = output_stream.getvalue()
        if len(final_bytes) == 0:
            # অল্টারনেটিভ সেভ পদ্ধতি
            final_bytes = base_env.file.save()

        log(f"Stage 5 Success: Output bundle created ({len(final_bytes)} bytes).")
        return True, final_bytes, logs

    except Exception as e:
        err_msg = f"Processing Failed: {str(e)}"
        log(err_msg)
        return False, None, logs
