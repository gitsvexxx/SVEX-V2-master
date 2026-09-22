# VPS deployment

This project is configured for Docker Compose with Django/Gunicorn, PostgreSQL 16, and Caddy for automatic HTTPS. SQLite is not used.

## 1. Prepare DNS

Create an `A` record for your domain pointing to the VPS public IP. If you use `www`, create a second `A` or `CNAME` record. Ports 80 and 443 must be reachable from the internet.

## 2. Install Docker on the VPS

These commands assume Ubuntu/Debian and an account with sudo access:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
exit
```

Reconnect over SSH after `exit`, then verify:

```bash
docker --version
docker compose version
```

## 3. Upload the project

If the project is not in GitHub, copy it from your computer with `scp`:

```bash
scp -r "/path/to/SVEX-V2-master" user@YOUR_SERVER_IP:/opt/
ssh user@YOUR_SERVER_IP
cd /opt/SVEX-V2-master
```

Alternatively, put the project in a private Git repository and use `git clone` on the VPS.

## 4. Create the production environment file

```bash
cp .env.example .env
nano .env
```

Set at least these values:

```env
DOMAIN=example.com
DEBUG=False
ALLOWED_HOSTS=example.com,www.example.com
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
SECRET_KEY=generate-a-long-random-value

POSTGRES_DB=svex
POSTGRES_USER=svex
POSTGRES_PASSWORD=generate-a-different-long-random-value
POSTGRES_HOST=db
POSTGRES_PORT=5432

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

Generate safe values with:

```bash
openssl rand -hex 48
```

Never commit `.env` or send it to anyone. It is ignored by Git and excluded from the Docker build context.

## 5. Start the application

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose exec web python manage.py createsuperuser
```

Caddy will request and renew the HTTPS certificate automatically after DNS points to the VPS and ports 80/443 are open.

View logs if something fails:

```bash
docker compose logs -f web
docker compose logs -f caddy
docker compose logs -f db
```

## 6. VPS firewall

With UFW, allow SSH, HTTP, and HTTPS only:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Do not expose PostgreSQL or Django port 8000 publicly. The Compose file keeps both internal to the Docker network.

## 7. Updates and backups

After uploading new code:

```bash
docker compose up -d --build
```

Back up PostgreSQL regularly:

```bash
mkdir -p backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > "backups/svex-$(date +%F).sql"
```

The database is stored in the `postgres_data` Docker volume. Backups should also be copied off the VPS.

## Important security notes

- Change both generated secrets before starting production.
- Keep `DEBUG=False`.
- Do not publish `.env`, database dumps, uploaded KYC files, or private keys.
- The application currently contains credential-management features; review them carefully before accepting real users or funds.
