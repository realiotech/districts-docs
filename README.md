# Districts Documentation

Documentation site for [Districts](https://districts.xyz), served at
<https://doc.districts.xyz/districts/>.

Built with [Docusaurus 2](https://docusaurus.io/). Migrated from GitBook.

`doc.districts.xyz` is temporary, so this site can be compared against the
GitBook original still serving `docs.districts.xyz`. Cutover means pointing
`docs.districts.xyz` here and deleting the GitBook CNAME.

## Local development

```bash
npm install
npm start          # dev server
npm run build      # production build into ./build
npm run serve      # serve the production build locally
```

## Deployment

Pushes to `main` build a container image and pin its tag in the
[gitops](https://github.com/realiotech/gitops) repo at
`districts-docs/overlays/prod/deployment.yaml`, which ArgoCD syncs to the prod
cluster. See `.github/workflows/prod.yaml`.

The site is served by nginx under the `/districts/` path to match the URLs the
GitBook site used, so `baseUrl` in `docusaurus.config.js` and the `location`
block in `conf/conf.d/default.conf` must stay in agreement.

## Importing content from GitBook

`scripts/gitbook-import.py` converts a tree of GitBook markdown into the
`docs/` layout Docusaurus expects. It handles the GitBook boilerplate header,
`{% embed %}` blocks, unclosed `<br>` tags, and `/files/<id>` asset references.

```bash
# from a GitBook Git Sync checkout
python3 scripts/gitbook-import.py --source ../gitbook-export --out docs

# or straight from the published site
python3 scripts/gitbook-import.py --fetch https://docs.districts.xyz/districts --out docs
```

Re-running is safe: it rewrites `docs/` from the source each time.
