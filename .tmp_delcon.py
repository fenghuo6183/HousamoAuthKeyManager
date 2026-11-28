import os
p = r"\\?\D:\123\4\CON"
try:
    os.remove(p)
    print("removed")
except Exception as exc:
    print("failed:", exc)
print("exists:", os.path.exists(p))
