# Deploying to production

Production is a single EC2 box. It runs the Django API under systemd and
serves the built frontend with nginx. CloudFront sits in front of it for
`brainastra.com`.

| | |
|---|---|
| Host | `ubuntu@15.206.125.114` (`ssh -i ~/.ssh/shichida-ec2`) |
| Backend | `~/shichida_backend`, branch `main`, service `shichida` |
| Frontend | built locally, copied to `/var/www/shichida-admin` |
| Site | https://www.brainastra.com |
| Data | DynamoDB, tables prefixed `Shichida-production-` |

Both repos deploy from `main`.

---

## 1. Verify before you deploy — do not skip this

```bash
# Backend
cd schindia_backend
git checkout main && git pull origin main
./venv/bin/python manage.py test          # expect: OK

# Frontend
cd ../Shichida
git checkout main && git pull origin main
npm install
npm run lint                              # expect: no output
npm test                                  # expect: all passing
```

**`npm run lint` is the gate.** `npm run build` runs `tsc -b` first, so a
typecheck failure produces *no bundle at all* — you cannot deploy a
frontend that does not typecheck. An unused variable is enough to stop it.

This has caught a broken `main` on two separate occasions. If something
fails here, fix it and push before going further. Never deploy red.

---

## 2. Backend

```bash
ssh -i ~/.ssh/shichida-ec2 ubuntu@15.206.125.114

cd ~/shichida_backend
git rev-parse --short HEAD                # write this down — rollback point
git fetch origin main
git reset --hard origin/main
./venv/bin/pip install -q -r requirements.txt
sudo systemctl restart shichida
systemctl is-active shichida              # expect: active
```

`reset --hard` is deliberate: the working tree must match `main` exactly.
If someone has hand-edited a file on the server, that edit is discarded —
which is the point, but check `git status` first if you suspect one.

---

## 3. Frontend

Build locally, then **stage and swap**. Never rsync straight into the live
directory: `--delete` removes `index.html` mid-copy and nginx answers 500
to every request until the copy finishes.

```bash
cd Shichida
rm -rf dist && npm run build
grep -o 'assets/[A-Za-z0-9_.-]*\.js' dist/index.html | head -1   # note the hash

rsync -az --delete -e "ssh -i ~/.ssh/shichida-ec2" \
  dist/ ubuntu@15.206.125.114:/tmp/shichida-new/

ssh -i ~/.ssh/shichida-ec2 ubuntu@15.206.125.114 'set -e
  sudo rm -rf /var/www/shichida-admin.new
  sudo cp -a /tmp/shichida-new /var/www/shichida-admin.new
  sudo chown -R ubuntu:ubuntu /var/www/shichida-admin.new
  sudo rm -rf /var/www/shichida-admin.prev
  sudo mv /var/www/shichida-admin /var/www/shichida-admin.prev
  sudo mv /var/www/shichida-admin.new /var/www/shichida-admin
  rm -rf /tmp/shichida-new'
```

The swap is two `mv` calls, so the site is never mid-copy.

### The production API URL

`.env.production.local` (gitignored, create it once) must contain:

```
VITE_INVOICES_API_URL=https://www.brainastra.com
```

Without it the production build throws at startup. With the wrong value —
`localhost:8000`, say — the site loads and every API call silently fails.
Always check the built bundle before deploying:

```bash
grep -c "localhost:8000" dist/assets/*.js    # expect: 0
```

---

## 4. Verify

```bash
cd schindia_backend
./smoke-production.sh                     # expect: 17 passed, 0 failed
```

Then confirm the served bundle is the one you just built:

```bash
echo "built : $(grep -o 'assets/[A-Za-z0-9_.-]*\.js' ../Shichida/dist/index.html | head -1)"
echo "served: $(curl -s https://www.brainastra.com/ | grep -o 'assets/[A-Za-z0-9_.-]*\.js' | head -1)"
```

These must match. A mismatch means the deploy did not take, or someone
else deployed something that is not in `main` — both worth stopping for.
This check has caught a bundle in production that existed in no commit.

Finally, check nothing is erroring:

```bash
ssh -i ~/.ssh/shichida-ec2 ubuntu@15.206.125.114 \
  'sudo journalctl -u shichida --since "5 minutes ago" -p err --no-pager'
```

---

## 5. Rolling back

```bash
# Backend — the hash you wrote down in step 2
ssh -i ~/.ssh/shichida-ec2 ubuntu@15.206.125.114 \
  'cd ~/shichida_backend && git reset --hard <hash> && sudo systemctl restart shichida'

# Frontend — the previous release is kept
ssh -i ~/.ssh/shichida-ec2 ubuntu@15.206.125.114 \
  'sudo rm -rf /var/www/shichida-admin.bad
   sudo mv /var/www/shichida-admin /var/www/shichida-admin.bad
   sudo mv /var/www/shichida-admin.prev /var/www/shichida-admin'
```

`/var/www/shichida-admin.prev` is always the release immediately before the
current one. Roll back once and it is gone — take a copy if you need to
go back further.

---

## Things that will bite you

**Database changes are not automatic.** DynamoDB tables and indexes are
created by `dynamo_backend/setup_tables.py`, which does *not* run on
deploy. If a change adds a table or a GSI, create it explicitly:

```bash
DJANGO_ENV=production ./venv/bin/python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','schindia_backend.settings')
django.setup()
from dynamo_backend.setup_tables import create_all_tables
from dynamo_backend.tables import PREFIX
assert PREFIX == 'Shichida-production'
create_all_tables()"
```

It skips anything that already exists. Adding a GSI to an existing table
is *not* covered — that needs `update_table`, and it must be done one
index at a time. A missing index does not fail loudly; the query just
throws when someone happens to use that screen. Attendance was broken in
production this way for days.

**Secrets live in the systemd unit,** not in `.env`:
`/etc/systemd/system/shichida.service`. python-decouple reads the
environment before `.env`, so the unit always wins — editing `.env` on the
server changes nothing. Values containing spaces must be quoted, or
systemd truncates at the first space.

**Email is capped.** SES is still in sandbox: mail only reaches verified
addresses, and everything else is rejected. The app logs the failure and
carries on, so a user sees "check your email" and nothing arrives.

**CloudFront usually needs no invalidation** — it has been fetching from
origin on each deploy. If a stale build persists, invalidate from the
console; the deploy IAM user has no CloudFront permissions.
