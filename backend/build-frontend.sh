#!/usr/bin/env bash
set -o errexit

cd "$(dirname "$0")/../front-end"
corepack enable
pnpm i --frozen-lockfile
pnpm build

cd ../backend
rm -rf frontend_dist
cp -R ../front-end/dist frontend_dist
