#!/usr/bin/env python3
"""Tjekker, at kilderne i data/sources.csv kan læses anonymt (uden login og uden cookies).

Brug:  python scripts/check_sources_public.py      (kører i GitHub Actions, workflow "Check sources")
Output: data/sources_check.csv  (én række pr. testet URL: status, endelig adresse, vurdering)

For hvert websted testes op til tre sider. Vurdering:
  public        siden svarer 200 uden login
  bot-protected siden svarer med en Cloudflare- eller lignende bot-udfordring (offentlig, men ikke til scripts)
  login         siden sender videre til en login-side eller beder om adgangskode
  error         anden fejl (nede, timeout)
"""
import csv, pathlib, re, urllib.request, urllib.error
from collections import defaultdict
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; DQA-map/1.0; +https://map.danishquantumacademy.dk)"
LOGIN = re.compile(r"(/login|/signin|/sso/|wayf|adfs|/saml|/oauth|/auth/|idp\.)", re.I)
PASSWORD = re.compile(r"<input[^>]+type=[\"']?password", re.I)
CHALLENGE = re.compile(r"(cf-challenge|challenge-platform|Just a moment|Attention Required|cf_chl_)", re.I)

rows = list(csv.DictReader((ROOT / "data/sources.csv").open(encoding="utf-8")))
by_host = defaultdict(list)
for r in rows:
    h = urlparse(r["url"]).netloc
    if len(by_host[h]) < 3 and r["url"] not in by_host[h]:
        by_host[h].append(r["url"])

out = []
for host, urls in sorted(by_host.items()):
    for url in urls:
        rec = {"host": host, "url": url, "status": "", "final_url": "", "verdict": ""}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
            with urllib.request.urlopen(req, timeout=40) as resp:
                body = resp.read(400_000).decode(resp.headers.get_content_charset() or "utf-8", "replace")
                rec["status"], rec["final_url"] = resp.status, resp.geturl()
                if LOGIN.search(urlparse(resp.geturl()).path + urlparse(resp.geturl()).netloc) or PASSWORD.search(body):
                    rec["verdict"] = "login"
                elif CHALLENGE.search(body):
                    rec["verdict"] = "bot-protected"
                else:
                    rec["verdict"] = "public"
        except urllib.error.HTTPError as e:
            body = e.read(200_000).decode("utf-8", "replace") if e.fp else ""
            rec["status"], rec["final_url"] = e.code, e.geturl() if hasattr(e, "geturl") else url
            rec["verdict"] = "bot-protected" if CHALLENGE.search(body) or e.code in (403, 429, 503) and "cloudflare" in str(e.headers).lower() else ("login" if e.code in (401,) else "error")
        except Exception as e:  # noqa: BLE001
            rec["status"], rec["verdict"] = type(e).__name__, "error"
        out.append(rec)
        print(rec["verdict"], rec["status"], url)

with (ROOT / "data/sources_check.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["host", "url", "status", "final_url", "verdict"])
    w.writeheader(); w.writerows(out)
print({v: sum(1 for r in out if r["verdict"] == v) for v in ("public", "bot-protected", "login", "error")})
