# Deploying research-methods to cPanel

Target: **https://research-methods.harold-datascience.co.ke**

No SSH on this account, so every step below is the panel or File Manager.

## 1. Create the subdomain

*Domains → Create A New Domain.*

- Domain: `research-methods.harold-datascience.co.ke`
- Document Root: `apps/research-methods/public`   ← **not** `apps/research-methods`

The document root is a separate folder holding only public assets. nginx serves
whatever is in it and ignores `.htaccess`, so application source must never sit
there — that is how source code ends up downloadable.

## 2. Upload

Zip this folder, upload through File Manager to `apps/research-methods`, extract there.

## 3. Create the Python application

*Software → Setup Python App → Create Application.*

| Field | Value |
|---|---|
| Python version | 3.11 |
| Application root | `apps/research-methods` |
| Application URL | `research-methods.harold-datascience.co.ke` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

## 4. Environment variables

Add each line of `.env.example` as a variable in that same screen. Do **not**
upload a `.env` file — this bundle deliberately ships none.

## 5. Install dependencies

Put `requirements.txt` in the *Configuration files* box and press **Run Pip
Install**.

> **Quota.** This one needs matplotlib, numpy, pandas, scipy, statsmodels, so its virtualenv is large — check `~/Desktop/CPANEL_PUSH.sh quota` before installing, because a full disk takes every app on the account down, not just this one.

## 6. Harden

Append `htaccess.append.txt` to the subdomain's `.htaccess`. Never replace that
file — Passenger writes its own directives into it.

## 7. Restart and check

```
https://research-methods.harold-datascience.co.ke/?cb=1                    -> 200
https://research-methods.harold-datascience.co.ke/healthz?cb=1             -> 200
https://research-methods.harold-datascience.co.ke/passenger_wsgi.py?cb=1   -> must 404
```

nginx caches hard, so always add a unique query string before concluding a
change did not apply. If the answer differs, you were reading a cache.

## If it 500s

Passenger writes the traceback to `~/apps/research-methods/stderr.log`. Read it first;
it names the failure almost every time.

