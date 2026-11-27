import os, zipfile
root = os.path.join("win", "dist")
out = os.path.join("dist", "AuthKeyManager-win64.zip")
if os.path.exists(out):
    os.remove(out)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for base, _, files in os.walk(os.path.join(root, "AuthKeyManager")):
        for f in files:
            p = os.path.join(base, f)
            z.write(p, os.path.relpath(p, root).replace(os.sep, "/"))
print("zip", os.path.getsize(out))
