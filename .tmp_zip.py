import os, zipfile
src = r"D:\123\4\win\dist\AuthKeyManager"
dst = r"D:\123\4\win\dist\AuthKeyManager-win64.zip"
if os.path.exists(dst): os.remove(dst)
count = 0
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for root, dirs, files in os.walk(src):
        dirs.sort(); files.sort()
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, src).replace(os.sep, "/")
            zf.write(path, rel)
            count += 1
print(count, os.path.getsize(dst))