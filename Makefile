gen-proto:
	@echo "build go protobuf..."
	protoc -I ../protocol/proto  --python_out=protocol --pyi_out=protocol ../protocol/proto/*.proto
	@echo "done"

build:
	pyinstaller -n console main.py --hidden-import uuid

clean:
	rm -rf build
	rm -rf dist
	rm -rf *.spec
	rm -rf *.spec.py
	rm -rf *.spec.pyc
	rm -rf *.spec.pyo

rebuild: clean build
