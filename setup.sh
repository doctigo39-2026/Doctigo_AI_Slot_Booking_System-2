#!/usr/bin/env bash
set -e

# If your submodule is PUBLIC, this is enough:
git submodule sync --recursive
git submodule update --init --recursive

# If your submodule is PRIVATE, uncomment the next block and add GH_READ_TOKEN to Streamlit secrets.
# This rewrites github.com URLs so git uses your token for submodule checkout.
# if [ -n "${GH_READ_TOKEN:-}" ]; then
#   git config --global url."https://${GH_READ_TOKEN}@github.com/".insteadOf "https://github.com/"
#   git submodule sync --recursive
#   git submodule update --init --recursive
# fi

# Install submodule dependencies if present (don’t fail build if missing)
if [ -f edge_core/requirements.txt ]; then
  pip install -r edge_core/requirements.txt || true
fi
