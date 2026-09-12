Remove-Item build, dist -Recurse -Force -ErrorAction SilentlyContinue
python -m PyInstaller build.spec --noconfirm