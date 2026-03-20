#!/bin/bash
DATE=$(date +%Y%m%d)
python -m nuitka --standalone \
  --output-dir=dist \
  --output-filename=console_${DATE} \
  --include-data-dir=assets=assets \
  --include-package=protocol \
  --include-module=uuid \
  --include-module=qfluentwidgets \
  --include-package=pkg \
  --include-package=components \
  --include-module=index \
  --include-module=loader \
  --include-module=monitor \
  --include-module=controller \
  --include-module=debug \
  --include-module=about \
  --include-module=setting \
  --include-module=guide \
  --enable-plugin=pyqt5 \
  --assume-yes-for-downloads \
  main.py
mv dist/main.dist dist/console_${DATE}
