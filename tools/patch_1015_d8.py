# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/android/build_apk.py'
s = io.open(p, encoding='utf-8').read()
old = u'''    classes = []
    cdir = os.path.join(BUILD, "classes")
    for dirpath, _, files in os.walk(cdir):
        for f in files:
            if f.endswith(".class"):
                classes.append(os.path.join(dirpath, f))
    run([d8, "--lib", ANDROID_JAR, "--min-api", MIN_SDK, "--release",
         "--output", os.path.join(BUILD, "dex")] + classes + [p for p in LIBS if os.path.exists(p)])'''
assert s.count(old) == 1, 'd8 block'
new = u'''    # 类文件太多会超过 Windows 命令行 8191 字符上限，先打成 jar 再交给 d8
    cdir = os.path.join(BUILD, "classes")
    classes_jar = os.path.join(BUILD, "classes.jar")
    if os.path.exists(classes_jar):
        os.remove(classes_jar)
    with zipfile.ZipFile(classes_jar, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _, files in os.walk(cdir):
            for f in files:
                if f.endswith(".class"):
                    full = os.path.join(dirpath, f)
                    z.write(full, os.path.relpath(full, cdir).replace(os.sep, "/"))
    run([d8, "--lib", ANDROID_JAR, "--min-api", MIN_SDK, "--release",
         "--output", os.path.join(BUILD, "dex"), classes_jar] + [p for p in LIBS if os.path.exists(p)])'''
s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('build_apk patched')
