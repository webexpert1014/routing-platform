#!/usr/bin/env bash
set -o errexit

cd "$(dirname "$0")/../front-end"

npm install -g pnpm@10.26.2
PNPM_BIN="$(npm root -g)/pnpm/bin/pnpm.cjs"
node "$PNPM_BIN" --version
node "$PNPM_BIN" i --frozen-lockfile
node "$PNPM_BIN" build

cd ../backend
rm -rf frontend_dist
cp -R ../front-end/dist frontend_dist
