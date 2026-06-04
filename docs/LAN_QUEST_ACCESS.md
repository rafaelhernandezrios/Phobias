# LAN + Meta Quest access / Acceso por IP y Quest

## Quick checklist

1. **Same Wi‑Fi** — PC server and Quest on the same network (avoid “guest” Wi‑Fi).
2. **On the server PC** (after connecting to that Wi‑Fi):
   ```cmd
   npm run cert
   npm run lan-urls
   ```
3. **Windows firewall** (once, as Administrator):
   ```cmd
   scripts\open-firewall-windows.cmd
   ```
4. **Start experiment** on the server PC:
   ```cmd
   npm run experiment:mock
   ```
5. **Quest browser** — open exactly (replace IP):
   ```
   https://192.168.x.x:8443/disclaimer-participant.html
   ```
   Accept the certificate warning **once**.

6. **Researcher PC** (can be the same machine):
   ```
   https://192.168.x.x:8443/researcher.html
   ```

## Common mistakes

| Problem | Fix |
|--------|-----|
| Quest uses `127.0.0.1` | Use the **PC’s LAN IP** from `npm run lan-urls` |
| Page does not load | Firewall + same Wi‑Fi + server running |
| Certificate error | Run `npm run cert` **on the server PC on that Wi‑Fi** |
| Changed network | Run `npm run cert` again (new IP in certificate) |

## Participant flow (VR only wait)

`disclaimer-participant.html` → Accept → VR **“Waiting for researcher”** → researcher **Start** → 360° videos.

Do not use `127.0.0.1` on the Quest.
