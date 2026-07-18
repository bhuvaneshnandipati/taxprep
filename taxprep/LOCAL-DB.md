# Using your own computer as the database (instead of Neon)

You get more storage/connections than Neon's free tier, at a real cost:
**the app only works while your computer is on, awake, and connected to the internet.**
If it sleeps or loses power, every user sees errors until it's back.

This uses **ngrok** to tunnel to your local Postgres. No router/firewall changes —
ngrok makes an *outbound* connection from your computer, so nothing has to be
opened to the internet on your end.

## 1. Install Postgres locally
**Windows**: download the installer from postgresql.org, run it, remember the
password you set for the `postgres` superuser.
**Mac**: `brew install postgresql@16 && brew services start postgresql@16`
**Linux**: `sudo apt install postgresql`

## 2. Create the database and a dedicated user
Open a terminal (Windows: "SQL Shell (psql)" from the Start menu) and run:
```sql
CREATE DATABASE taxprep;
CREATE USER taxprep_user WITH PASSWORD 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON DATABASE taxprep TO taxprep_user;
```

## 3. Install ngrok and expose port 5432
1. Sign up free at ngrok.com, install the agent, then:
   ```bash
   ngrok config add-authtoken <your-authtoken-from-the-ngrok-dashboard>
   ngrok tcp 5432
   ```
2. ngrok prints a forwarding address like:
   ```
   Forwarding   tcp://0.tcp.ngrok.io:19835 -> localhost:5432
   ```
   Keep this terminal window open — closing it drops the tunnel.

## 4. Build your DATABASE_URL
```
postgresql://taxprep_user:choose-a-strong-password@0.tcp.ngrok.io:19835/taxprep
```
(host and port come from the ngrok forwarding line above)

## 5. Configure Render
In your Render service's Environment tab:
- `DATABASE_URL` → the URL from step 4
- `DB_SSLMODE` → `disable` (your local Postgres has no SSL certificate — the
  managed-database default of `require` will fail the connection)

Redeploy. Check `https://your-api.onrender.com/health`.

## Important caveats
- **ngrok's free address changes every time you restart the tunnel.** If you
  restart your computer or ngrok, you must copy the new address into Render's
  `DATABASE_URL` and redeploy. (ngrok's paid plans offer a fixed address if
  this becomes annoying.)
- **Keep your computer from sleeping** — Windows: Settings → System → Power →
  set Sleep to "Never" while plugged in. Mac: System Settings → Battery →
  Prevent automatic sleep.
- **Back up your data.** Unlike Neon, nobody but you is backing up this
  database. Consider `pg_dump taxprep > backup.sql` periodically.
- **Security**: only you and ngrok's relay ever see raw traffic to port 5432 —
  ngrok's agent talks to Postgres over localhost, so you are not opening a
  port on your router. Still use a strong, unique password for `taxprep_user`.
- If this ever becomes annoying, Neon's free tier (0.5 GB, no expiry, always
  on) is almost certainly less hassle than keeping a home PC online 24/7 —
  worth revisiting if reliability matters more than raw capacity.
