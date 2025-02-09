gen-proto:
	@echo "build go protobuf..."
	protoc -I ../protocol/proto  --python_out=protocol ../protocol/proto/*.proto
	@echo "done"
