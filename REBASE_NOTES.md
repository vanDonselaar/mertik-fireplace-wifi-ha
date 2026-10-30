# jkfran upstream replay notes

## Source snapshots and scope

- Upstream: `jkfran/mertik-fireplace-wifi-ha` `main` at `ca9abc51e62cc39736333600baca0cefe4be6347` (fresh `git fetch upstream` confirmed this tip).
- Original Vincent fork: `origin/main` at `ce4160d19c02be447e7906188f487d68ce801f63`.
- Shared base: `6859c22f75e9a2969d92883235a7f5ce9970365f`.
- Result branch: `rebase/jkfran-main`, based directly on the upstream tip. Local only: no push, PR, Home Assistant changes, or physical fireplace commands.

## Replay method and deviations

An actual 17-commit `git rebase --onto` was attempted first. The first commit produced whole-file conflicts in protocol, switch, and number modules: Vincent's CRLF-era implementation intersects upstream's protocol refactor and changed entity constructors. That attempt was aborted. Instead, the final Vincent feature semantics were replayed as one consolidated feature commit, preserving upstream's source structure, followed by documentation. This is a feature replay onto upstream, **not** a one-to-one history-preserving rebase.

- `4e320ad`: targeted zero-flame regression and fix, before the feature replay.
- `ca8b14e`: consolidated feature replay and regression coverage.
- Original intermediate UI fixes and reversions are represented by their final behavior, not separate rebased commits.
- Deliberate bug fixes beyond replay: zero flame sends standby instead of negative-indexing the maximum step; threshold 254 handles raw 255 as the sole nonzero step without division by zero; explicit reconfigure threshold edits also update an existing overriding option.
- Review follow-up: reproduced two real reloads after reconfiguring a loaded entry. Reconfigure now uses `async_update_and_abort`, leaving changed-entry reloads to the registered listener. Explicit scheduling preserves the old helper's behavior when no listener is registered (including unloaded entries) or input is unchanged. The options listener is retained. Checked the installed Core 2026.2.3 helper implementations and the official May 7, 2026 Home Assistant developer guidance, “Deprecating config entry listener with reloading methods in config flow.”
- Reconfigure preserves upstream connection validation and duplicate prevention, updates a changed host-based unique ID, and checks older entries that have no unique ID. Upstream metadata/version/branding are retained rather than restoring Vincent's older manifest/HACS metadata.
- Upstream optimistic-window coordinator API and its tests remain available. Vincent's main and pilot controls do **not** activate those windows: their state comes from reported status (including the igniting flag), not an optimistic flame-height cache.
- There is exactly one immediate status query after a non-status command; Vincent's redundant second query after setting flame height is intentionally omitted.

## Original → replayed feature mapping

| Original commit(s) | Preserved result / location |
| --- | --- |
| `1d8e13a`, `a01438e` | Separate `MertikPilotLightSwitchEntity`, unique ID `{entry_id}-PilotLightOnOff`; pilot ON ignites, pilot OFF fully shuts down. Main ON sets flame 12, main OFF sends standby and retains pilot. `switch.py`, coordinator and protocol guard-flame/standby accessors. All other existing entity unique IDs remain unchanged. |
| `1d8e13a`, `af47832`, `ce4160d` | Low-flame calibration defaults to raw threshold 116. Raw 116 is off; 117–123 remain on. Height remains status-derived from offset `[14:16]`, mapped to 0–12. No DaveJesse protocol or locally remembered requested flame level. `mertik.py`. |
| `5a10d47`, `e7fd6b8`, `2722b79`, `2d07fe4` | Dynamic fireplace/pilot/aux icons, `igniting` and `shutting_down` main-switch attributes, switch device classes, gas-burner number icon and thermometer-lines sensor icon. `switch.py`, `number.py`, `sensor.py`. |
| `f0fb4e2`, `4e7ccdb` | All six entities share `(DOMAIN, entry_id)` device grouping. Upstream's `has_entity_name=True`, short secondary names, primary `name=None`, `DeviceInfo`, correct sensor device class and native Celsius remain in place. No duplicate platform forwarding. |
| `da6976d`, `82af88b`, `2d07fe4` | Immediate refresh centrally in protocol `_send_command`, followed by HA coordinator state notification after successful entity commands. Aux/light remain driven by parsed status; aux retains the existing main-burner-on gate. `mertik.py`, existing entity notification paths. |
| `0f5bb1c` | `raw_flame_height` and number `raw_value` attribute. `mertik.py`, `number.py`. |
| `1be6ba9`, `22b1179`, `3f51f5d`, `ed46636`, `ce4160d` | `flame_height_threshold`, precedence options → entry data → default 116. Numeric box range 0–254 in initial setup, reconfigure and options; options listener reloads entry. English labels and source strings maintained alongside upstream errors/abort messages. `const.py`, `config_flow.py`, `__init__.py`, `strings.json`, `translations/en.json`. |

No thermostat was added.

## Upstream maintenance preserved

- Executor-based device construction; `ConfigEntryNotReady` on connection/setup failure.
- `UpdateFailed` coordinator errors and 10-second polling.
- Config-flow connection check and duplicate prevention, extended to reconfigure/legacy entries.
- Protocol constants, named offsets/command tables, reconnect timeout/logging, parser structure.
- Single centralized platform setup, unload support, correct native sensor API and shared device registry information.
- Tests, requirements, pytest configuration, branding assets and `.github/workflows/tests.yml`; workflow contents are byte-for-byte unchanged from upstream.

## Executed validation

Environment: isolated ignored `.venv`, CPython 3.13.18, Home Assistant 2026.2.3, pytest 9.0.0, pytest-homeassistant-custom-component 0.13.316. Dependencies installed from upstream `requirements_test.txt`. No virtual environment files are committed.

- RED: zero-flame regression failed against upstream, demonstrating `16FF` (maximum) instead of `1600` (standby). It passed after the targeted fix.
- RED: main ON/OFF and three-switch setup checks failed against upstream behavior before replay; calibration/raw-value, command-refresh, number-range and configuration/reload regressions were also exercised failing before their respective changes.
- RED: real registered-listener reconfigure regression failed with `Expected async_reload to have been awaited once. Awaited 2 times.` before the fix (1 failed, 3 passed in 0.21s including loaded/unloaded and changed/unchanged cases).
- `tests/test_config_reload.py` additionally exercises initial user-flow setup and two successive options edits through real setup/unload/reload, with hardware and platform boundaries mocked. All cases finish loaded with exactly one registered listener; changed settings reach device construction.
- `.venv/bin/pytest -q`: **221 passed in 1.62s**.
- `.venv/bin/pytest --disable-socket --allow-unix-socket -q`: **221 passed in 1.60s**. Network access disabled; Unix sockets allowed for the test event loop. Hardware sockets are mocked.
- `.venv/bin/python -m compileall -q custom_components tests`: exit 0.
- `git diff --check` and `git diff --check upstream/main`: exit 0.
- `git diff --exit-code upstream/main -- .github/workflows`: exit 0.
- Original replay's baseline-aware Ruff comparison: upstream 36 findings, replay 32, **no new findings** by file/rule count. Ruff is not available on PATH for this follow-up. Existing unrelated lint findings were not broadly fixed. Follow-up added-line security scan found no secrets or unsafe execution patterns.

Outdated upstream test expectations were deliberately updated for threshold 116, flame maximum 12, exposed minimum 0, three switches, Vincent's switch command semantics/icons, stored threshold default and the new final refresh command. Original command payload checks still assert the first command, while new tests assert the follow-up refresh and notification ordering.

Tests verify encoding, HA behavior and the preserved calibration assumptions, not physical ignition/shutdown or appliance safety. No live-device validation was performed.
