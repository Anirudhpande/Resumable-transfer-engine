import json
import os 

def manifest_builder(source_metadata, manifest_path):
    manifest = {
        "version" : source_metadata["version"],
        "chunk_size" : source_metadata["chunk_size"],
        "files" : {}
    }

    for rel_path, file_info in source_metadata["files"].items():
        chunks = {}

        for chunk_index, chunk_info in file_info["chunks"].items():
            chunks[chunk_index] = {
                "status": "MISSING",
                "expected_hash" : chunk_info["hash"]

            }

        manifest["files"][rel_path] = {
            "size" : file_info["size"],
            "chunks" : chunks
        }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)

    return manifest

with open("data.json", "r") as f:
    source_metadata = json.load(f)

real = manifest_builder(source_metadata, r"D:\manifest_path\manifest.json")

print(real)