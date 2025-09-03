#!/bin/bash
DATE=$(date +%Y%m%d)
pyinstaller -n console_$(date +%Y%m%d) main.py --hidden-import uuid
