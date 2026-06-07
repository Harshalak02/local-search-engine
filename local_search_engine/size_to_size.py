# check_size.py
import os

folder = "/home/harshal/Downloads"

SUPPORTED = {".pdf", ".docx", ".txt"}

total = 0
count = 0
for dirpath, dirnames, filenames in os.walk(folder):
    for f in filenames:
        if os.path.splitext(f)[1].lower() in SUPPORTED:
            size = os.path.getsize(os.path.join(dirpath, f))
            total += size
            count += 1

print(f"Files      : {count}")
print(f"Total size : {total / (1024*1024):.2f} MB")