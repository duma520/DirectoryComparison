nuitka --standalone ^
    --enable-plugin=pyside6 ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=icon.ico ^
    --include-data-files=icon.ico=icon.ico ^
    --include-module=PySide6.QtCore ^
    --include-module=PySide6.QtGui ^
    --include-module=PySide6.QtWidgets ^
    --include-module=PySide6.QtNetwork ^
    --include-module=PySide6.QtQml ^
    --include-module=PySide6.QtQuick ^
    --include-module=PySide6.QtSvg ^
    --include-module=PySide6.QtPrintSupport ^
    --include-module=PySide6.QtMultimedia ^
    --include-module=PySide6.QtMultimediaWidgets ^
    --include-module=PySide6.QtOpenGL ^
    --include-module=PySide6.QtOpenGLWidgets ^
    --include-module=PySide6.QtSql ^
    --include-module=PySide6.QtTest ^
    --include-module=PySide6.QtXml ^
    --include-module=PySide6.QtConcurrent ^
    --follow-imports ^
    --jobs=4 ^
    --clang ^
    --output-dir=build_output ^
    DirectoryComparison.py

