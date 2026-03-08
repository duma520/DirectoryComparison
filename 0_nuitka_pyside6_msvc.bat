nuitka --standalone ^
    --enable-plugin=pyside6 ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=icon.ico ^
    --include-data-files=icon.ico=icon.ico ^
    --include-package=PySide6 ^
    --include-module=PySide6.QtCore ^
    --include-module=PySide6.QtGui ^
    --include-module=PySide6.QtWidgets ^
    --follow-imports ^
    --jobs=4 ^
    --output-dir=build_output ^
    DirectoryComparison.py