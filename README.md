# Parity

Parity is a [Wizardry](https://github.com/andersaamodt/wizardry) spellbook for
cross-platform capability audits and authorized device routing.

It answers three questions:

- What Wizardry capabilities have been proven to work on each platform?
- What checks remain before a capability can be considered working?
- Which authorized device is eligible to perform a requested job?

## Install

Clone Parity, then link the repository into your personal spellbook:

```sh
git clone https://github.com/andersaamodt/parity.git ~/parity
learn --link ~/parity
```

Open a new terminal, then use the spells directly:

```sh
parity-report
parity-plan android_termux
parity-record --help
parity-route --help
```

Each spell has its own `--help` page.

## Evidence states

Parity is deliberately conservative:

- **Green** requires real evidence that discovery, installation, execution, and
  the intended outcome all passed.
- **Yellow** means evidence is incomplete, simulated, stale, or waiting on a
  prerequisite.
- **Red** means the capability is unavailable on that platform.

## Data

Capabilities, platforms, and baseline evidence are tab-separated text files
read with POSIX tools. Live device inventories and evidence stay outside the
repository.

The spell source is in the repository root. Bundled data is under `.parity/`,
and matching behavioral tests are under `.tests/`.

## Development

Parity spells use `#!/bin/sh`, POSIX tools, and a `--help` contract. Run all
behavioral tests with:

```sh
.tests/test-all
```

## License

Parity is available under the [Open Wizardry License 3.1](LICENSE).
