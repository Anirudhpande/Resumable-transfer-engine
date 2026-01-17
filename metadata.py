import hashlib
import json
import os

def compute_chunk_hashes(file_path, chunk_size):
    hashes = {}
    
    with open(file_path, "rb") as file:
        index = 0
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            h = hashlib.sha256(chunk).hexdigest()
            hashes[str(index)] = {"hash": h}
            index +=1

    return hashes


def metadata_builder(file_path, chunk_size):
    metadata = {
        "size" : os.path.getsize(file_path),
        "total_chunks": ((os.path.getsize(file_path) + chunk_size - 1) // (chunk_size)),
        "chunks" : compute_chunk_hashes(file_path, chunk_size)
    }
    return metadata



import os

def generate_source_metadata(root_dir, chunk_size):
    metadata = {
        "version": 1,
        "chunk_size": chunk_size,
        "hash_algo": "sha256",
        "files": {}
    }

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)

            rel_path = os.path.relpath(full_path, root_dir)
            rel_path = rel_path.replace("\\", "/")  

            metadata["files"][rel_path] = metadata_builder(
                full_path,
                chunk_size
            )

    return metadata

real = generate_source_metadata(r"D:\moives", 16*1024*1024)

with open("data.json", "w") as file:
    json.dump(real, file, indent = 4)

