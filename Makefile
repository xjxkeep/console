GIT_HASH=$(shell git rev-parse --short HEAD)

gen-proto:
	@echo "build go protobuf..."
	protoc -I ../protocol/proto  --python_out=protocol --pyi_out=protocol ../protocol/proto/*.proto
	@echo "done"

build:
	pyinstaller -n console_${GIT_HASH} main.py --hidden-import uuid
	mkdir -p application/app application/assets
	mv dist/console_${GIT_HASH} application/app
	cp -r assets/* application/assets
	cd application && ln -s  ./app/console_${GIT_HASH}/console_${GIT_HASH} console



clean:
	rm -rf build
	rm -rf dist
	rm -rf *.spec
	rm -rf *.spec.py
	rm -rf *.spec.pyc
	rm -rf *.spec.pyo
	rm -rf application

rebuild: clean build

# 用法: make release V=1.2.0
release:
ifndef V
	$(error 请指定版本号, 例如: make release V=1.2.0)
endif
	@sed -i '' 's/^VERSION = ".*"/VERSION = "$(V)"/' pkg/version.py
	@git add pkg/version.py
	@git commit -m "release: v$(V)"
	@git tag v$(V)
	@echo "Done: pkg/version.py -> $(V), tag v$(V) created"
	@echo "Run 'git push && git push origin v$(V)' to trigger release"
