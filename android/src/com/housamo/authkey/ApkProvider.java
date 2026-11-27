package com.housamo.authkey;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;

import java.io.File;
import java.io.FileNotFoundException;

/**
 * 1) 应用内更新：把 getExternalFilesDir("update") 里的 APK 以 content:// 交给系统安装器；
 * 2) 二维码分享：把 cache/qr 里的 PNG 交给别的 App（file:// 在 Android 7+ 会被拒）。
 */
public class ApkProvider extends ContentProvider {

    public static final String AUTHORITY = "com.housamo.authkey.files";

    public static Uri uriFor(File f) {
        return Uri.parse("content://" + AUTHORITY + "/" + f.getName());
    }

    public static Uri uriForQr(File f) {
        return Uri.parse("content://" + AUTHORITY + "/qr/" + f.getName());
    }

    private File base() {
        return new File(getContext().getExternalFilesDir(null), "update");
    }

    private File qrBase() {
        File d = new File(getContext().getCacheDir(), "qr");
        if (!d.exists()) d.mkdirs();
        return d;
    }

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        java.util.List<String> seg = uri.getPathSegments();
        String name = uri.getLastPathSegment();
        if (name == null || name.contains("/") || name.contains("..")) {
            throw new FileNotFoundException("bad name: " + uri);
        }
        File f;
        if (seg.size() >= 2 && "qr".equals(seg.get(0))) {
            f = new File(qrBase(), name);
        } else {
            f = new File(base(), name);
        }
        return ParcelFileDescriptor.open(f, ParcelFileDescriptor.MODE_READ_ONLY);
    }

    @Override
    public String getType(Uri uri) {
        java.util.List<String> seg = uri.getPathSegments();
        if (seg.size() >= 2 && "qr".equals(seg.get(0))) return "image/png";
        return "application/vnd.android.package-archive";
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        return null;
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        return null;
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        return 0;
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        return 0;
    }
}
