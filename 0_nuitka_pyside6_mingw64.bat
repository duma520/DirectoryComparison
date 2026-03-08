cls
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist build_output rmdir /s /q build_output

nuitka --standalone ^
    --enable-plugin=pyside6 ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=icon.ico ^
    --include-data-files=icon.ico=icon.ico ^
    --include-package=PySide6 ^
    --follow-imports ^
    --jobs=4 ^
    --mingw64 ^
    --output-dir=build_output ^
    your_script.py

