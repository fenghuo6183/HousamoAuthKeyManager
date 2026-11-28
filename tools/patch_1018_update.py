# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()

old_url = '"https://api.github.com/repos/fenghuo6183/HousamoAuthKeyManager/releases/latest")'
new_url = '"https://api.github.com/repos/fenghuo6183/HousamoAuthKeyManager/releases?per_page=20")'
assert s.count(old_url) == 1
s = s.replace(old_url, new_url)

old_parse = '''                    java.util.regex.Matcher m1 = java.util.regex.Pattern.compile("\\"tag_name\\"\\\\s*:\\\\s*\\"([^\\"]+)\\"").matcher(body);
                    if (m1.find()) tag = m1.group(1);
                    java.util.regex.Matcher m2 = java.util.regex.Pattern.compile("\\"html_url\\"\\\\s*:\\\\s*\\"([^\\"]+)\\"").matcher(body);
                    if (m2.find()) url = m2.group(1);
                    java.util.regex.Matcher m3 = java.util.regex.Pattern.compile("\\"browser_download_url\\"\\\\s*:\\\\s*\\"([^\\"]+\\\\.apk)\\"").matcher(body);
                    if (m3.find()) apk = m3.group(1);'''
new_parse = '''                    // 按 release 逐段找：取「第一个带 .apk 资产的版本」，避免把只发 Windows 包的版本当成新版 App
                    java.util.regex.Matcher m1 = java.util.regex.Pattern.compile("\\"tag_name\\"\\\\s*:\\\\s*\\"([^\\"]+)\\"").matcher(body);
                    java.util.List<Integer> tags = new ArrayList<Integer>();
                    java.util.List<String> names = new ArrayList<String>();
                    while (m1.find()) {
                        tags.add(m1.start());
                        names.add(m1.group(1));
                    }
                    for (int i = 0; i < tags.size(); i++) {
                        int from = tags.get(i);
                        int to = i + 1 < tags.size() ? tags.get(i + 1) : body.length();
                        String seg = body.substring(from, to);
                        java.util.regex.Matcher ma = java.util.regex.Pattern.compile("\\"browser_download_url\\"\\\\s*:\\\\s*\\"([^\\"]+\\\\.apk)\\"").matcher(seg);
                        if (!ma.find()) continue;
                        tag = names.get(i);
                        apk = ma.group(1);
                        java.util.regex.Matcher mu = java.util.regex.Pattern.compile("\\"html_url\\"\\\\s*:\\\\s*\\"([^\\"]+)\\"").matcher(seg);
                        if (mu.find()) url = mu.group(1);
                        break;
                    }
                    if (tag == null && !names.isEmpty()) {
                        tag = names.get(0);
                        String seg0 = body.substring(tags.get(0), tags.size() > 1 ? tags.get(1) : body.length());
                        java.util.regex.Matcher mu = java.util.regex.Pattern.compile("\\"html_url\\"\\\\s*:\\\\s*\\"([^\\"]+)\\"").matcher(seg0);
                        if (mu.find()) url = mu.group(1);
                    }'''
assert s.count(old_parse) == 1, s.count(old_parse)
s = s.replace(old_parse, new_parse)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
