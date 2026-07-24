# infrastructure/docker/Dockerfile
#
# Base: Ubuntu + Python. Creates a non-root "tester" user (Homebrew refuses to run as
# root), installs everything Homebrew-on-Linux needs to build/install, and lays out:
#
#   ~tester/BrewE2E       - the BrewE2E / brew_tui python implementation (this repo's src/)
#   ~tester/BrewTuiData   - where brew-tui's sqlite package DB lives (HOMEBREW_DB_PATH)
#
# Build (from repo root, so both src/ and infrastructure/ are in the build context):
#   docker build -f infrastructure/docker/Dockerfile -t brew-tui:base .
#
# Run:
#   docker run -it --name brew-tui-dev brew-tui:base

FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

# --- OS packages: python for BrewE2E, build-essential/curl/git/etc for Homebrew itself ---
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        procps \
        curl \
        file \
        git \
        ca-certificates \
        sudo \
        locales \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# --- tester user: Homebrew requires a non-root user, and sudo for a few build steps ---
RUN useradd --create-home --shell /bin/bash tester \
    && usermod -aG sudo tester \
    && echo "tester ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/tester \
    && chmod 0440 /etc/sudoers.d/tester

# --- layout expected by BrewTUI/BrewE2E: DB under ~tester/BrewTuiData ---
ENV HOMEBREW_DB_PATH=/home/tester/BrewTuiData/brew.db \
    BREW_E2E_HOME=/home/tester/BrewE2E \
    PYTHONPATH=/home/tester/BrewE2E/src

RUN mkdir -p /home/tester/BrewTuiData \
    && chown -R tester:tester /home/tester/BrewTuiData

# --- ship the BrewE2E implementation baked into the image ---
COPY --chown=tester:tester src/brew_tui /home/tester/BrewE2E/src/brew_tui
COPY --chown=tester:tester pyproject.toml /home/tester/BrewE2E/pyproject.toml

# --- helper scripts tester runs *inside* the container ---
COPY --chown=tester:tester infrastructure/docker/install-homebrew.sh /home/tester/install-homebrew.sh
COPY --chown=tester:tester infrastructure/docker/run-brewe2e.sh /home/tester/run-brewe2e.sh
COPY infrastructure/docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /home/tester/install-homebrew.sh /home/tester/run-brewe2e.sh /entrypoint.sh

RUN pip3 install --break-system-packages --no-cache-dir SQLAlchemy>=2.0

USER tester
WORKDIR /home/tester

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
