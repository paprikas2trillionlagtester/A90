[app]

title = a90
package.name = a90
package.domain = org.a90

source.dir = .
source.include_exts = py,mp3,wav,kv,png,jpg,atlas

version = 1.0

# Only Kivy needed — jnius ships automatically with the android bootstrap
requirements = python3==3.11.9,kivy==2.3.0

orientation = portrait
fullscreen   = 1

# Wake lock keeps the CPU alive so the pop-up timer fires while backgrounded
android.permissions = WAKE_LOCK, VIBRATE
android.wakelock    = True

android.api    = 33
android.minapi = 26
android.ndk    = 25b

# Build both 64-bit and 32-bit so it runs on basically any Android phone
android.archs = arm64-v8a, armeabi-v7a

# Auto-accept SDK licenses — required for unattended CI builds (GitHub Actions)
android.accept_sdk_license = True

[buildozer]
log_level    = 2
warn_on_root = 1
