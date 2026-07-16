#!/usr/bin/env bash
set -o errexit

cd "$(dirname "$0")/../front-end"

npm install -g pnpm@10.26.2
pnpm i --frozen-lockfile
pnpm build

cd ../backend
rm -rf frontend_dist
cp -R ../front-end/dist frontend_dist
