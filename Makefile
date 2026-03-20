GIT_HASH=$(shell git rev-parse --short HEAD)

gen-proto:
	@echo "build go protobuf..."
	protoc -I ../protocol/proto  --python_out=protocol --pyi_out=protocol ../protocol/proto/*.proto
	@echo "done"

build:
	python -m nuitka --standalone \
		--output-dir=dist \
		--output-filename=console_${GIT_HASH} \
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
	mv dist/main.dist dist/console_${GIT_HASH}
	mkdir -p application/app application/assets
	mv dist/console_${GIT_HASH} application/app
	cp -r assets/* application/assets
	cd application && ln -s ./app/console_${GIT_HASH}/console_${GIT_HASH} console



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
