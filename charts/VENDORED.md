# Vendored charts

Both charts are copied from
https://github.com/iankisali/microservice-deployment at commit
`8ed96c8d98625c73b67c7172b6703383ea9e46e9` (directories `chart/microservice`
and `chart/redis`).

The first commit that added them here contains the upstream files unchanged,
so `git log -p charts/` shows exactly what was changed afterwards and why.

## Changes made here

| File | Change | Why |
| --- | --- | --- |
| `*/templates/deployment.yaml` | Render `resources`, `readinessProbe` and `livenessProbe` from values, each only when set | The upstream template has no way to set requests, limits or probes, and none of them can be added through values alone |
| `*/values.yaml` | Add empty defaults for the three keys | An empty map renders nothing, so a release that sets none of them gets the upstream manifest unchanged |
| `*/Chart.yaml` | `version` 0.1.0 to 0.2.0 | The templates changed, so the chart version changes too |

The upstream values files are not vendored. They are still cloned at run
time and passed to Helm unchanged; our settings are layered on top from
`vars/microservices.yml`.