# Parity

Parity shows which project capabilities work on which platforms—and what
evidence supports that answer.

It has three jobs:

- report what has been proven to work;
- choose an eligible device for an authorized job; and
- record what happened so the result can be audited later.

Parity was built for [Wizardry](https://github.com/andersaamodt/wizardry), but
other projects can describe their own capabilities and platforms with a profile.

## How it fits together

A caller gives Parity a structured request. Parity checks the requested
capability, authorization, available devices, and transport options. It then
chooses an eligible target and records the result returned by the executor.

Parity does not recognize speech or control a device itself. Raw mouse,
keyboard, and mobile-device operations belong to the separate `actuator`
project. Parity decides **whether and where** a job may run; the named executor
does the work.

## Quick start

Parity requires Python 3.9 or newer and has no runtime dependencies.

```sh
git clone https://github.com/andersaamodt/parity.git
cd parity
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .

parity report
```

The report begins with a platform summary and then lists the status of every
capability on every supported platform.

Run the test suite with:

```sh
python3 -m unittest discover -s tests -v
```

## Everyday commands

Show the evidence-backed capability report:

```sh
parity report
parity report --json
```

Create a test plan for a platform:

```sh
parity plan --platform android_termux
```

Choose an authorized target from a device inventory:

```sh
parity route \
  --request tests/fixtures/android_request.json \
  --devices tests/fixtures/devices.json
```

Record one lab observation:

```sh
parity record \
  --capability mobile_debug_control \
  --platform android_termux \
  --kind manual_on_device \
  --missing-prerequisite wifi_debugging_enabled
```

`record` prints JSON to standard output. The lab can append that record to an
external evidence bundle; Parity does not silently store runtime results in the
repository.

The `execute` command is for callers that already have an actuator request and
device inventory:

```sh
parity execute \
  --request /path/to/actuator-request.json \
  --devices /path/to/devices.json \
  --actuator-command actuator
```

## Reading a report

Parity uses three deliberately strict states:

- **Green:** the capability was discovered, installed when needed, executed,
  and proven to produce the intended outcome on the real platform.
- **Yellow:** evidence is missing, partial, simulated, stale, or blocked by a
  prerequisite.
- **Red:** the capability is unavailable on that platform.

A simulation can help development, but it cannot make a result green. A manual
gate also remains yellow until it has been completed and supported by evidence.

The bundled baseline is intentionally conservative. Wizardry currently treats
macOS as its primary working platform while other paths remain under validation.
Windows is represented through WSL rather than native Windows, and iOS appears
only as a constrained test and control target.

## Using Parity with another project

A project profile names the project, its user-facing capabilities, its
platforms, and the executor for each capability:

```sh
parity --profile /path/to/profile.json report
parity --profile /path/to/profile.json plan
```

Profiles describe what should be audited; they are not the source of truth for
the product itself. A profile may include an `arche` digest that identifies the
product definition it came from. If that definition changes, older evidence
stays yellow until the capability is tested again.

Runtime device inventories, execution receipts, and evidence should live
outside this repository. The ignored `evidence/` and `receipts/` directories are
available for short-lived local work.

## For contributors

The small Python core is under `src/parity/`:

- `core.py` contains audit and routing decisions.
- `lab.py` creates test plans and evidence records.
- `transport.py` contains the executor boundary.
- `data/` contains the bundled Wizardry profile and baseline evidence.
- `schemas/` defines the JSON exchanged with other tools.

Keep routing deterministic and evidence claims conservative. Authorization is
checked before target selection, candidates are ordered by device id, and
transport preference follows the request. Device control belongs in an
executor, not in Parity's decision layer.

## License

Parity is available under the [Open Wizardry License 3.1](LICENSE).
