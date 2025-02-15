gen-proto:
	@echo "build go protobuf..."
	protoc -I ../protocol/proto  --python_out=protocol --pyi_out=protocol ../protocol/proto/*.proto
	@echo "done"

build:
	pyinstaller -n console_inone .\main.py --hidden-import uuid --onefile 