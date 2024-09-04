.PHONY: clean-pkg
clean-pkg:
	@rm -rf build dist *.egg-info

.PHONY: clean
clean: clean-pkg

.PHONY: dev-deps
dev-deps:
	@pip install -r requirements-dev.txt
