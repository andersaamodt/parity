# Parity

Parity is Wizardry's evidence-first cross-platform audit, neutral remote routing
layer, and shared test-laboratory interface. It does not recognize speech or
perform faux-user input: Dictator produces intent, Artificer performs target OS
and app automation, and Parity describes capabilities, chooses eligible targets,
and records receipts and evidence.

## What is implemented

- Machine-readable capability and platform manifests, including host/client roles
- Strict traffic-light evidence semantics
- Authorization-friendly job and execution-receipt schemas
- Deterministic device, prerequisite, and transport routing
- Android Wi-Fi debugging and iOS official-debugging manual gates
- A cross-platform outcome test plan that keeps simulations yellow
- Human-readable and JSON audit reports
- A standard-library-only Python core with automated tests

The bundled baseline is deliberately conservative. Wizardry's README is evidence
that macOS is its working primary platform and that its other official paths are
untested or under validation; it is not sufficient evidence that each individual
user outcome passes. Thus no baseline capability is green until a run proves the
outcome is discoverable in the menu, installed as needed, executable, and passing
on the platform.

Windows native is unavailable; WSL is represented separately. iOS is not a
Wizardry host and appears only as a constrained mobile test/control target.

## Use

Python 3.9 or newer is sufficient; there are no runtime dependencies.

```sh
python3 -m parity report
python3 -m parity report --json
python3 -m parity plan --platform android_termux
python3 -m parity record \
  --capability mobile_debug_control --platform android_termux \
  --kind manual_on_device --missing-prerequisite wifi_debugging_enabled
python3 -m parity route \
  --request tests/fixtures/android_request.json \
  --devices tests/fixtures/devices.json
python3 -m unittest discover -s tests -v
```

When running directly from a checkout, set `PYTHONPATH=src`, or install the
project into a virtual environment with `python3 -m pip install -e .`.

`record` prints a record to standard output so the lab can append it to an
external evidence bundle. A manual gate remains yellow even if other checks are
marked passed. Omitting any check also remains yellow.

## Evidence rules

An audit result is:

- **green** only when menu discovery, installation/preinstallation, execution,
  and the exact user outcome all pass with referenced real-platform evidence;
- **yellow** when a prerequisite remains or evidence is missing, partial, or
  simulated;
- **red** when the outcome is unavailable on the platform.

Runtime device inventories, receipts, and evidence should live outside this
repository. The ignored `evidence/` and `receipts/` names are available for
short-lived local work, but an external lab-artifact location is preferred.

## Data and boundaries

- `src/parity/data/capabilities.json` — user outcomes and authorization scopes
- `src/parity/data/platforms.json` — official host/client distinctions and gates
- `src/parity/data/baseline_evidence.json` — source assertions, not device proof
- `src/parity/schemas/` — stable job and receipt envelopes
- `src/parity/transport.py` — protocol boundary for local/LAN/Tor/debug adapters

Transport adapters submit the job unchanged to an executor and return a receipt;
they do not reinterpret intent. Routing is deterministic: authorization is
checked first, candidates are sorted by device id, and transport preference is
honored in request order.
