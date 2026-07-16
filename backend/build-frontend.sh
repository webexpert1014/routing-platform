#!/usr/bin/env bash
set -o errexit

cd "$(dirname "$0")/../front-end"

if ! command -v pnpm >/dev/null 2>&1; then
	corepack enable
	corepack prepare pnpm@11.12.0 --activate
fi

pnpm i --frozen-lockfile
pnpm build

cd ../backend
rm -rf frontend_dist
cp -R ../front-end/dist frontend_dist
