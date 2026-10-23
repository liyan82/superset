# Patent 1024 production host

patent1024.com runs Superset from `docker-compose-non-dev.yml`, but Postgres 16
and Redis 7 are not containers: they run on the host as systemd services
(`postgresql@16-main`, `redis-server`). The containers reach them through the
Docker bridge address `172.18.0.1`, which is why `DATABASE_HOST` and
`REDIS_HOST` point there on the server.

## Host services must start after Docker

Both services bind `172.18.0.1` explicitly (`listen_addresses` in
`postgresql.conf`, `bind` in `/etc/redis/redis.conf`). That address only exists
once dockerd has created the bridge, and systemd starts both services before
Docker by default. On boot this fails in two different ways:

- **Redis** cannot bind, exits, and hits systemd's restart limit. Superset then
  answers every request with
  `Error 111 connecting to 172.18.0.1:6379. Connection refused.`
- **Postgres** logs `could not bind IPv4 address "172.18.0.1"` and keeps
  running on localhost only, so the containers cannot reach the database.

The server has a drop-in for each unit to order it after Docker and keep
retrying until the bridge appears. When rebuilding the host, recreate it:

```bash
for svc in redis-server postgresql@16-main; do
  mkdir -p /etc/systemd/system/$svc.service.d
  cat > /etc/systemd/system/$svc.service.d/wait-for-docker-bridge.conf <<'EOF'
# The config binds 172.18.0.1 (the Docker bridge for Superset), which only
# exists once dockerd is up. Order after Docker and keep retrying meanwhile.
[Unit]
After=docker.service
Wants=docker.service
StartLimitIntervalSec=0

[Service]
Restart=on-failure
RestartSec=5
EOF
done
systemctl daemon-reload
```

Any other host service that binds `172.18.0.1` needs the same drop-in.

To check after a reboot:

```bash
systemctl is-active redis-server postgresql@16-main
redis-cli -h 172.18.0.1 ping          # PONG
curl -fsS http://127.0.0.1:8088/health
```
