[app]
title = Musify
package.name = musify
package.domain = org.musify
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy==2.3.0,mutagen,plyer,android
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE,READ_MEDIA_AUDIO,INTERNET
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
