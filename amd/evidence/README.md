# Evidence

One folder per real GPU run, written by `amd/run_on_amd.sh` and committed unedited, including runs that failed. Each holds `summary.json`, `selfcheck.log`, raw outputs and traces, `vram-raw.log`, `vram-samples.csv`, `service.log`, the probes, `pip-freeze.txt` and a `MANIFEST.sha256` over all of it.

No run exists yet. `trailmark/evidence.py` reads these folders on each request to the status page, and a run only counts if its summary and manifest pass the checks there.
