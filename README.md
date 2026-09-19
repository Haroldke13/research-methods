# Research Methods

> **For viewing and review only.** A self-directed practice build on synthetic
> data. No client commissioned it, nothing was delivered to anyone, and no real
> person, employer or customer appears in it.
>
> **Comments are encouraged** — open an issue, or comment on any line in a pull
> request.

**Status:** builds and serves.

## Layout

```
flask/          the application — edit here, this is the source of truth
cpanel_extra/   the cPanel-only files the build folds in
build_cpanel.sh regenerates cpanel/ from flask/
cpanel/         GENERATED for hosting. Never edit; it is overwritten.
```

## Run it locally

```bash
cd flask
python3 -m venv .venv
.venv/bin/pip install -r ../cpanel_extra/requirements.txt
.venv/bin/flask --app app:create_app run
```

## Deploy it

```bash
./build_cpanel.sh --publish      # rebuild, then stage into ~/Desktop/CPANEL/research-methods
~/Desktop/CPANEL_PUSH.sh check research-methods
```

Then follow [`cpanel/DEPLOY_STEPS.md`](cpanel/DEPLOY_STEPS.md). Intended
subdomain: **research-methods.harold-datascience.co.ke**

## Provenance

`flask/` is the application exactly as the model produced it, copied from `CHATGPT_SOLUTIONS/entry-level-researcher-and-assistance-4425e12f2d14/files/` and not edited.

Everything under `cpanel_extra/` and the generated `cpanel/` folder is packaging added so it can be hosted.
