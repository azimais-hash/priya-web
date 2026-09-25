# Moving mindfullypriya.com from Wix to Vercel

Prepared 2026-09-25. The record set as Wix serves it today is in `dns-before.md`.

Facts that shape the plan:

- The domain is registered with **123-Reg** (expires 2028-01-09).
- **Nameservers are Wix's** (`ns6.wixdns.net`, `ns7.wixdns.net`), so Wix currently
  answers every DNS question for the domain, email included.
- **Email is not Wix.** MX points at `mx0/mx1.123-reg.co.uk`, and SPF is
  `v=spf1 include:secureserver.net -all` (123-Reg is GoDaddy-owned, hence
  secureserver). This must survive the move or Priya stops receiving email.
- DMARC is a CNAME to Wix (`_dmarc.wixemails.com`), so it disappears with Wix and
  has to be recreated.
- No DKIM selector answers today, so there is nothing to carry across.
- `mindfullypriya.com` and `www.mindfullypriya.com` are already added to the
  Vercel project `priya-web`, waiting on DNS.

## Route: move nameservers to 123-Reg

Keeping Wix as the DNS host while pointing the site elsewhere works, but it leaves
Priya's DNS inside an account she is about to cancel. Moving DNS to the registrar
removes Wix from the chain entirely.

### Step 1, at 123-Reg, before touching nameservers

Create the zone with every record below, so it is ready the moment the nameservers
change. TTL 3600 (one hour) everywhere, except drop the apex A records to 300 for
the switchover if 123-Reg allows it.

| Type | Name | Value | Purpose |
|---|---|---|---|
| A | `@` | `76.76.21.21` | The website, on Vercel |
| A | `www` | `76.76.21.21` | Same, for www |
| MX | `@` | `10 mx0.123-reg.co.uk` | Email, unchanged |
| MX | `@` | `20 mx1.123-reg.co.uk` | Email, unchanged |
| TXT | `@` | `v=spf1 include:secureserver.net -all` | Email, unchanged |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:hello@mindfullypriya.com` | Replaces the Wix DMARC record |

Nothing else in the current zone needs to travel: the rest is Wix's own site
infrastructure.

### Step 2, switch the nameservers

At 123-Reg, set the domain's nameservers back to 123-Reg's own defaults. Resolution
moves over within a few hours, up to 48 in the worst case, and both the old Wix site
and the new one answer correctly during that window because each nameserver set is
internally consistent.

### Step 3, immediately after

1. Remove the `X-Robots-Tag: noindex` header from `vercel.json` and redeploy, or
   Google is told to ignore the live site.
2. Check the certificate: `vercel domains inspect mindfullypriya.com` should show
   both names verified, and https should load without a warning.
3. Send a test email to `hello@mindfullypriya.com` from an outside address, and send
   one from it, before anyone assumes email survived.
4. In Search Console, submit `https://www.mindfullypriya.com/sitemap.xml` and
   request indexing for the home page, `/reclamation` and `/for-organisations`.
5. Watch the redirects: `/general-7`, `/general-6`, `/shop`, the product page and
   `/category/all-products` should all 301, not 404.

### Step 4, only once everything is confirmed

Cancel the Wix plan. Keep the Wix account itself for a month so the old content is
recoverable, and keep `data/cache/` in the SEO repo, which holds a crawl of every
old page.

## What breaks if this is rushed

- Changing nameservers before the zone exists at 123-Reg takes email down as well as
  the website.
- Wix Bookings, Wix Events and the Wix shop stop working at cutover. The site no
  longer links to any of them: booking is Cal.com, programme places are a Tally
  enquiry, and the shop has been retired.
- The SEO fleet writes drafts into Wix through the Wix MCP. That job needs
  repointing at this repo before the Wix account closes.
