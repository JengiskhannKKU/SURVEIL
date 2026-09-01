.PHONY: install docker sync check-version

# Install oculus into the local venv (editable).
install:
	venv/bin/pip install -e . -q

# Rebuild all Docker images (oculus:latest — shared by the backend and
# CLI services — plus the frontend image) from current source.
docker:
	docker compose build

# Rebuild both from current source and confirm they report the same version.
sync: install docker check-version
	@echo "Local venv and oculus:latest are in sync."

# Fail loudly if the local venv and Docker image disagree on version —
# run this after any change to catch drift immediately instead of
# discovering it later as "docker and oculus not the same version".
check-version:
	@LOCAL=$$(venv/bin/oculus --version | awk '{print $$NF}'); \
	DOCKER=$$(docker run --rm --entrypoint sh oculus:latest -c "oculus --version" | awk '{print $$NF}'); \
	if [ "$$LOCAL" != "$$DOCKER" ]; then \
		echo "VERSION MISMATCH: local venv=$$LOCAL  docker=$$DOCKER"; \
		echo "Run 'make sync' to rebuild both from current source."; \
		exit 1; \
	fi; \
	echo "Versions match: $$LOCAL"
