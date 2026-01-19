import os

path = r"C:\Users\grunt\sunroom_dev\worker\output\images\76dd04d4-8b49-4639-afb3-dabd732682a5\page_01.png"

print(f"Checking path: {path}")
print(f"Exists? {os.path.exists(path)}")
print(f"Is File? {os.path.isfile(path)}")

# Check directory list
dir_path = os.path.dirname(path)
print(f"Listing directory: {dir_path}")
try:
    print(os.listdir(dir_path))
except Exception as e:
    print(f"Error listing dir: {e}")
