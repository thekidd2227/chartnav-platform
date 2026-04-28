# chartnavmd.com — DNS & Deployment
**Registrar:** GoDaddy | **Host options:** Vercel (primary) · Netlify (fallback)

---

## Pre-deploy checklist

- [ ] `chartnavmd-site/index.html` in repo and reviewed
- [ ] Webhook URL confirmed and ready for injection
- [ ] `og.jpg` created and uploaded to site root
- [ ] `%%WEBHOOK_URL%%` replaced in index.html (see §5)
- [ ] `vercel.json` created (see §4)
- [ ] Domain `chartnavmd.com` accessible in GoDaddy account

---

## 1 — Deploy to Vercel

```bash
# Option A: CLI
cd chartnavmd-site
npx vercel --prod

# Option B: Dashboard
# Connect folder chartnavmd-site as a new Vercel project
# Set root directory to: chartnavmd-site
```

Vercel will display the deployment URL and required DNS values.

---

## 2 — Add domain in Vercel

1. **Project → Settings → Domains**
2. Add `chartnavmd.com` → Vercel shows required records
3. Add `www.chartnavmd.com` → Vercel configures automatic 301 redirect www → apex

---

## 3 — DNS records (GoDaddy)

Log in → **My Products → Domains → chartnavmd.com → DNS**

### Vercel (recommended)

| Type  | Name | Value                  | TTL |
|-------|------|------------------------|-----|
| A     | @    | `76.76.21.21`          | 600 |
| CNAME | www  | `cname.vercel-dns.com` | 600 |

> Verify Vercel's current A record IP at [vercel.com/docs/projects/domains](https://vercel.com/docs/projects/domains) — IPs can change.

### Netlify (fallback)

| Type  | Name | Value                           | TTL |
|-------|------|---------------------------------|-----|
| A     | @    | `75.2.60.5`                     | 600 |
| CNAME | www  | `apex-loadbalancer.netlify.com` | 600 |

> Then: Netlify → Site → Domain Management → Add custom domain → set apex as primary.

---

## 4 — vercel.json (security headers + redirect)

Create `chartnavmd-site/vercel.json`:

```json
{
  "version": 2,
  "cleanUrls": true,
  "trailingSlash": false,
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options",           "value": "nosniff" },
        { "key": "X-Frame-Options",                  "value": "DENY" },
        { "key": "Referrer-Policy",                  "value": "strict-origin-when-cross-origin" },
        { "key": "Strict-Transport-Security",        "value": "max-age=63072000; includeSubDomains; preload" },
        { "key": "Permissions-Policy",               "value": "camera=(), microphone=(), geolocation=()" }
      ]
    }
  ],
  "redirects": [
    { "source": "/assessment", "destination": "/#assessment", "permanent": false },
    { "source": "/security",   "destination": "/#security",   "permanent": false }
  ]
}
```

---

## 5 — Webhook token injection

### Sed replacement (CI/CD)

```bash
# Replace placeholder in index.html before deploy
sed -i "s|%%WEBHOOK_URL%%|${LEAD_WEBHOOK_URL}|g" \
  chartnavmd-site/index.html
```

### Vercel environment variable approach (more secure)

1. Add `LEAD_WEBHOOK_URL` in Vercel → Settings → Environment Variables
2. Create `chartnavmd-site/api/submit.js` serverless function:

```javascript
// chartnavmd-site/api/submit.js
export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();

  const WEBHOOK = process.env.LEAD_WEBHOOK_URL;
  if (!WEBHOOK) {
    console.log('[ChartNav MD] Lead (no webhook):', req.body);
    return res.status(200).json({ ok: true });
  }

  await fetch(WEBHOOK, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...req.body, source: 'chartnavmd.com' }),
  });

  return res.status(200).json({ ok: true });
}
```

3. Update `handleSubmit` in index.html to POST to `/api/submit` instead of webhook directly.  
   This keeps the webhook URL server-side and never exposed in page source.

---

## 6 — SSL

Both Vercel and Netlify provision **Let's Encrypt TLS automatically** after DNS resolves.  
No manual certificate management required.

**Propagation:** 15 min – 48 h depending on TTL and upstream cache.

---

## 7 — Post-deploy validation

```bash
# DNS resolution
dig +short chartnavmd.com A
dig +short www.chartnavmd.com CNAME

# SSL
curl -I https://chartnavmd.com
# Expect: HTTP/2 200, strict-transport-security header

# www redirect
curl -I https://www.chartnavmd.com
# Expect: HTTP 301 → https://chartnavmd.com

# OG meta present
curl -s https://chartnavmd.com | grep -i "og:image"

# Security headers present
curl -s -D - https://chartnavmd.com | grep -i "x-frame-options"

# Form smoke test
# 1. Open https://chartnavmd.com/#assessment
# 2. Fill form (leave company_website empty)
# 3. Submit
# 4. Verify: console.log OR webhook receipt in your monitoring tool
# 5. Confirm success state renders

# Compliance language present
curl -s https://chartnavmd.com | grep -i "does not claim"
```

---

## 8 — Cross-site links

Update `arcgsystems.com/chartnav` footer to include:
```
chartnavmd.com — standalone practice landing page
```

`chartnavmd.com` footer already links to:
- `arcgsystems.com/chartnav`
- `arcgsystems.com/chartnav/security`
- `arcgsystems.com/privacy`
- `arcgsystems.com/terms`

Update privacy and terms links once Chartnav-specific legal pages exist.

---

## Blockers — do not launch without resolving

| # | Item | Blocks |
|---|------|--------|
| 1 | `LEAD_WEBHOOK_URL` — must be set | Form submissions |
| 2 | GoDaddy DNS access for `chartnavmd.com` | Site going live |
| 3 | `og.jpg` created and placed at root | Social previews |
| 4 | Legal review of "What We Do Not Claim" section | Compliance confidence |
| 5 | Vercel project created and `vercel.json` committed | Deploy |
