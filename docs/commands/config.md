# `taintwatch config`

Manage the config file.

## Subcommands

| Command | Description |
|---|---|
| `taintwatch config init` | Write a starter `config.toml`. |
| `taintwatch config path` | Print the resolved config file path. |

## `taintwatch config init`

### Synopsis

```sh
taintwatch config init [--root PATH] [--force]
```

### Options

| Flag | Description |
|---|---|
| `--root PATH` | Pre-fill `[scan] roots` with this path. |
| `--force` | Overwrite an existing config. By default, `init` refuses if the file already exists. |

### Behavior

Writes a fully-commented `config.toml` to the platform-appropriate location:

- **Windows** `%APPDATA%\taintwatch\config.toml`
- **macOS** `~/Library/Application Support/taintwatch/config.toml`
- **Linux** `~/.config/taintwatch/config.toml`

### Example

```sh
taintwatch config init --root ~/code
```

## `taintwatch config path`

### Synopsis

```sh
taintwatch config path
```

Prints the absolute path of the config file (whether or not it exists). Useful for piping into editors:

```sh
$EDITOR "$(taintwatch config path)"
```

## See also

- [configuration.md](../configuration.md) — full config reference
