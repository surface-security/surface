.PHONY: style
style:
	black --target-version=py39 \
	      --line-length=120 \
		  --skip-string-normalization \
		  surface

.PHONY: style_check
style_check:
	black --target-version=py39 \
	      --line-length=120 \
		  --skip-string-normalization \
		  --check \
		  surface

coverage:
	cd surface && pytest -n4 --cov --cov-report=xml

tmpbuild:
	docker buildx build --platform linux/amd64 \
	                    -f dev/Dockerfile \
						-t ghcr.io/fopina/surface:tmpbuild \
						--load \
						.

tmpbuildarm:
	docker buildx build --platform linux/arm/v7 \
	                    -f dev/Dockerfile \
						-t ghcr.io/fopina/surface:tmpbuild \
						--push \
						.
