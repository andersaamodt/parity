# Parity has joined Wizardry

Parity now lives in [Wizardry](https://github.com/andersaamodt/wizardry) as a
small family of POSIX shell spells. There is no separate Parity package or
runtime to install.

The spells answer three questions:

- What Wizardry capabilities have been proven to work on each platform?
- What checks remain before a capability can be considered working?
- Which authorized device is eligible to perform a requested job?

After installing Wizardry, use:

```sh
parity report
parity plan android_termux
parity record --help
parity route --help
```

Wizardry's command parser resolves those phrases to the `parity-report`,
`parity-plan`, `parity-record`, and `parity-route` spells.

Parity remains deliberately conservative:

- **Green** requires real evidence that discovery, installation, execution, and
  the intended outcome all passed.
- **Yellow** means evidence is incomplete, simulated, stale, or waiting on a
  prerequisite.
- **Red** means the capability is unavailable on that platform.

The manifests and bundled evidence are simple tab-separated text files beside
the spells. Runtime device inventories and evidence stay outside the repository.

## Development

Parity follows the same rules as every other Wizardry spell: `#!/bin/sh`, POSIX
tools, a `--help` contract, and a corresponding behavioral test under `.tests/`.
Changes should be made and tested in the Wizardry repository.

## License

Parity remains available under the [Open Wizardry License 3.1](LICENSE).
