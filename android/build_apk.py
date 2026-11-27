# -*- coding: utf-8 -*-
"""Build the Android APK without Gradle (aapt2 + javac + d8 + zipalign + apksigner)."""
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SDK = os.path.join(ROOT, ".tools", "android-sdk")
BT = os.path.join(SDK, "build-tools", "34.0.0")
JDK = os.path.join(ROOT, ".tools", "jdk")
ANDROID_JAR = os.path.join(SDK, "platforms", "android-34", "android.jar")
BUILD = os.path.join(HERE, "build")
DIST = os.path.join(ROOT, "dist")
KS = os.path.join(HERE, "keystore", "release.jks")
KS_PASS = "housamo2024"
ALIAS = "housamo"
APP_NAME = "HousamoAuthKeyManager"
VERSION_CODE = "23"
VERSION_NAME = "1.0.22"
MIN_SDK = "24"
LIBS = [os.path.join(HERE, "libs", n) for n in ("api.jar", "aidl.jar", "shared.jar", "provider.jar", "annotation.jar", "zxing-core.jar")]

ENV = dict(os.environ)
ENV["JAVA_HOME"] = JDK
ENV["PATH"] = os.path.join(JDK, "bin") + os.pathsep + ENV.get("PATH", "")


def run(cmd, cwd=None, capture=True):
    print(">>", " ".join(cmd) if isinstance(cmd, list) else cmd, flush=True)
    p = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=capture,
                       text=True, errors="replace")
    if capture and p.stdout.strip():
        print(p.stdout[-4000:], flush=True)
    if p.returncode != 0:
        if capture and p.stderr.strip():
            print(p.stderr[-4000:], flush=True)
        raise SystemExit("command failed (%d): %s" % (p.returncode, cmd))
    return p


def main():
    for path in (BT, JDK, ANDROID_JAR):
        if not os.path.exists(path):
            raise SystemExit("missing toolchain: %s" % path)

    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(os.path.join(BUILD, "classes"))
    os.makedirs(os.path.join(BUILD, "dex"))
    os.makedirs(DIST, exist_ok=True)

    aapt2 = os.path.join(BT, "aapt2.exe")
    javac = os.path.join(JDK, "bin", "javac.exe")
    d8 = os.path.join(BT, "d8.bat")
    zipalign = os.path.join(BT, "zipalign.exe")
    apksigner = os.path.join(BT, "apksigner.bat")
    keytool = os.path.join(JDK, "bin", "keytool.exe")

    # compile resources (launcher icon) into .flat files for aapt2 link
    flat = []
    res_dir = os.path.join(HERE, "res")
    if os.path.isdir(res_dir):
        res_zip = os.path.join(BUILD, "res.zip")
        run([aapt2, "compile", "--dir", res_dir, "-o", res_zip])
        flat_dir = os.path.join(BUILD, "res-flat")
        with zipfile.ZipFile(res_zip) as z:
            z.extractall(flat_dir)
        for dirpath, _, files in os.walk(flat_dir):
            for f in files:
                if f.endswith(".flat"):
                    flat.append(os.path.join(dirpath, f))

    base = os.path.join(BUILD, "base.apk")
    gen_dir = os.path.join(BUILD, "gen")
    run([aapt2, "link", "-o", base, "-I", ANDROID_JAR,
         "--manifest", os.path.join(HERE, "AndroidManifest.xml"),
         "--min-sdk-version", MIN_SDK, "--target-sdk-version", "34",
         "--version-code", VERSION_CODE, "--version-name", VERSION_NAME,
         "--java", gen_dir] + flat)

    srcs = []
    for dirpath, _, files in os.walk(os.path.join(HERE, "src")):
        for f in files:
            if f.endswith(".java"):
                srcs.append(os.path.join(dirpath, f))
    for dirpath, _, files in os.walk(gen_dir):
        for f in files:
            if f.endswith(".java"):
                srcs.append(os.path.join(dirpath, f))
    if not srcs:
        raise SystemExit("no java sources")
    cp = os.pathsep.join([ANDROID_JAR] + [p for p in LIBS if os.path.exists(p)])
    run([javac, "-encoding", "UTF-8", "-source", "8", "-target", "8",
         "-classpath", cp, "-nowarn", "-d", os.path.join(BUILD, "classes")] + srcs)

    # 类文件太多会超过 Windows 命令行 8191 字符上限，先打成 jar 再交给 d8
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
         "--output", os.path.join(BUILD, "dex"), classes_jar] + [p for p in LIBS if os.path.exists(p)])

    dex = os.path.join(BUILD, "dex", "classes.dex")
    if not os.path.exists(dex):
        raise SystemExit("d8 produced no classes.dex")
    with zipfile.ZipFile(base, "a", zipfile.ZIP_DEFLATED) as z:
        z.write(dex, "classes.dex")

    aligned = os.path.join(BUILD, "aligned.apk")
    run([zipalign, "-p", "-f", "4", base, aligned])

    if not os.path.exists(KS):
        os.makedirs(os.path.dirname(KS), exist_ok=True)
        run([keytool, "-genkeypair", "-keystore", KS, "-alias", ALIAS,
             "-keyalg", "RSA", "-keysize", "2048", "-validity", "10950",
             "-storepass", KS_PASS, "-keypass", KS_PASS, "-noprompt",
             "-dname", "CN=Housamo AuthKey Manager, O=OpenSource, C=CN"])

    out_apk = os.path.join(DIST, "%s-%s.apk" % (APP_NAME, VERSION_NAME))
    run([apksigner, "sign", "--ks", KS, "--ks-key-alias", ALIAS,
         "--ks-pass", "pass:" + KS_PASS, "--key-pass", "pass:" + KS_PASS,
         "--out", out_apk, aligned])
    run([apksigner, "verify", "--print-certs", out_apk])
    size = os.path.getsize(out_apk) / 1024.0
    print("\nAPK OK -> %s (%.1f KB)" % (out_apk, size))


if __name__ == "__main__":
    main()
