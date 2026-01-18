import os
import hashlib
import json

def transfer_file(src_root, dest_root, rel_path, file_entry, chunk_size, manifest, manifest_path):
    src_path = os.path.join(src_root, rel_path)
    dest_path = os.path.join(dest_root, rel_path)

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    with open(src_path, "rb") as src, open(dest_path, "r+b" if os.path.exists(dest_path) else "wb") as dest:
        for chunk_index, chunk in file_entry["chunks"].items():
            if chunk["status"] == "VERIFIED":
                continue

            offset = int(chunk_index) * chunk_size
            src.seek(offset)
            data = src.read(chunk_size)

            dest.seek(offset)
            dest.write(data)
            dest.flush()

            h = hashlib.sha256(data).hexdigest()
            if h != chunk["expected_hash"]:
                raise RuntimeError(f"Chunk corruption: {rel_path} [{chunk_index}]")

            chunk["status"] = "VERIFIED"

            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=4)

        file_entry["completed"] = True


def transfer_directory(manifest, manifest_path):
    src_root = manifest["source_root"]
    dest_root = manifest["destination_root"]
    chunk_size = manifest["chunk_size"]

    for rel_path, file_entry in manifest["files"].items():
        if file_entry.get("completed"):
            continue

        transfer_file(
            src_root,
            dest_root,
            rel_path,
            file_entry,
            chunk_size,
            manifest,
            manifest_path
        )
