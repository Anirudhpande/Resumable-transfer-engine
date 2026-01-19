import os
import json

from metadata import generate_source_metadata
from manifest import manifest_builder
from transfer import transfer_directory

METADATA_PATH = "metadata.json"
MANIFEST_PATH = "manifest.json"


def main():
    # ===== CONFIG =====
    src_root = r"D:\WEB DEV"
    dest_base = r"E:"
    chunk_size = 32 * 1024 * 1024  # 32 MB
    # ==================

    # Derive destination folder name from source
    folder_name = os.path.basename(src_root.rstrip("\\/"))
    dest_root = os.path.join(dest_base, folder_name)

    os.makedirs(dest_root, exist_ok=True)

    try:
        # 1️⃣ Generate metadata (fresh every run)
        metadata = generate_source_metadata(src_root, chunk_size)
        with open(METADATA_PATH, "w") as f:
            json.dump(metadata, f, indent=4)

        # 2️⃣ Build manifest (fresh every run)
        manifest = manifest_builder(
            metadata,
            MANIFEST_PATH,
            src_root,
            dest_root
        )

        # 3️⃣ Transfer using manifest
        transfer_directory(manifest, MANIFEST_PATH)

        print(f"[✓] Copy completed → {dest_root}")

    except Exception as e:
        print("[✗] Transfer failed:", e)
        print("State files preserved for debugging / resume")
        return

    # 4️⃣ Cleanup temporary state (ONLY after success)
    if os.path.exists(METADATA_PATH):
        os.remove(METADATA_PATH)

    if os.path.exists(MANIFEST_PATH):
        os.remove(MANIFEST_PATH)

    print("[✓] Temporary state cleaned up")


if __name__ == "__main__":
    main()
