# -*- coding: utf-8 -*-
import io
P = "android/build_apk.py"
s = io.open(P, encoding="utf-8").read()
old = '''    base = os.path.join(BUILD, "base.apk")
    run([aapt2, "link", "-o", base, "-I", ANDROID_JAR,
         "--manifest", os.path.join(HERE, "AndroidManifest.xml"),
         "--min-sdk-version", MIN_SDK, "--target-sdk-version", "34",
         "--version-code", VERSION_CODE, "--version-name", VERSION_NAME] + flat)'''
new = '''    base = os.path.join(BUILD, "base.apk")
    gen_dir = os.path.join(BUILD, "gen")
    run([aapt2, "link", "-o", base, "-I", ANDROID_JAR,
         "--manifest", os.path.join(HERE, "AndroidManifest.xml"),
         "--min-sdk-version", MIN_SDK, "--target-sdk-version", "34",
         "--version-code", VERSION_CODE, "--version-name", VERSION_NAME,
         "--java", gen_dir] + flat)'''
assert s.count(old) == 1
s = s.replace(old, new)

old2 = '''    if not srcs:
        raise SystemExit("no java sources")'''
new2 = '''    for dirpath, _, files in os.walk(gen_dir):
        for f in files:
            if f.endswith(".java"):
                srcs.append(os.path.join(dirpath, f))
    if not srcs:
        raise SystemExit("no java sources")'''
assert s.count(old2) == 1
s = s.replace(old2, new2)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("build script updated")