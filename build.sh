#!/usr/bin/env bash
set -o errexit

cd "$(dirname "$0")"

export NVM_DIR="${HOME}/.nvm"
if [[ ! -s "${NVM_DIR}/nvm.sh" ]]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.5/install.sh | bash
fi
. "${NVM_DIR}/nvm.sh"
nvm install 24
corepack enable

cd front-end
pnpm i --frozen-lockfile
pnpm build
cd ..
pip install -r backend/requirements.txt
cd backend
python manage.py collectstatic --no-input
python manage.py migrate
