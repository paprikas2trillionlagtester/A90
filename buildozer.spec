[app]

# Disguise name — change this to anything innocent
title = Battery Monitor
package.name = batterymonitor
package.domain = com.util

source.dir = .
source.include_exts = py,mp3,wav,kv,png,jpg,atlas

version = 1.0

# Only Kivy needed — jnius ships automatically with the android bootstrap
requirements = python3==3.11.6,kivy==2.3.0

orientation = portrait
fullscreen   = 1

# Keep screen on; wake lock keeps CPU alive so timer fires in background
android.permissions = WAKE_LOCK, RECEIVE_BOOT_COMPLETED, VIBRATE
android.wakelock    = True

# Allow running after reboot (optional — remove if you don't want that)
android.add_activities =

android.api    = 33
android.minapi = 26
android.ndk    = 25b

# Build both 64-bit and 32-bit so it runs on basically any Android phone
android.archs = arm64-v8a, armeabi-v7a

# Uncomment + fill in to sign a release APK (needed for Play Store)
# android.keystore      = my.keystore
# android.keystore_pass = changeme
# android.keyalias      = mykey
# android.keyalias_pass = changeme

[buildozer]
log_level    = 2
warn_on_root = 1
