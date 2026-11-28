import os, tempfile, shutil, sys
sys.path.insert(0, r"D:\\123\\4\\win")
tmp = tempfile.mkdtemp(prefix="hak-folder-")
os.environ["HOUSAMO_DATA_DIR"] = tmp.replace("\\", "/")
os.environ["HOUSAMO_NO_ADB"] = "1"
from app import config, vault as vault_mod
settings = config.Settings()
v = vault_mod.Vault("housamo")
key = b"housamo-test-key-0123456789abcdef"
entry, created = v.add("test", key, kind="account")
v.save()
folder = os.path.join(tmp, "scan")
os.makedirs(folder)
with open(os.path.join(folder, "auth.txt"), "w", encoding="utf-8") as fh:
    fh.write("housamo-test-key-0123456789abcdef")
from qtui import service as service_mod
svc = service_mod.Service(settings)
print("before", len(svc.vault.entries))
print("folder", svc.import_folder(folder))
print("after", len(svc.vault.entries))
print("clear", svc.clear_all(), len(svc.vault.entries))
shutil.rmtree(tmp)