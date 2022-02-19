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
