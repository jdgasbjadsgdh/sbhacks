# Offline checks

No game process or account is needed. Test inputs are the pinned upstream
WebBreak file and selected SBPE 1.7.0 headers, scripts and embedded mouse
handler, downloaded with hash checks. The helper extracts no game executable
and requires a fresh fixture directory outside an installed SBPE folder.

Install `cffi`, `pillow` and `unicorn` in a Python virtual environment, then:

```sh
python tools/prepare_test_inputs.py /tmp/sbpe-connectivity-fixture
SBPE_WINDOWS_ROOT=/tmp/sbpe-connectivity-fixture python -m unittest discover -s windows -p 'test_*.py'
node web/test_sc_boss.js
node web/test_install.js
```

Browser fixtures require Playwright and its Chromium, or a `CHROME_PATH`
pointing to Chrome. `PLAYWRIGHT_MODULE` can specify the installed module path.
They open isolated headless pages; they never connect to StarBreak.

```sh
node web/test_browser_sc.js
node web/test_browser_arm_all.js
```

On macOS, compile and run these fixtures with Apple Clang, once for `arm64`
and once for `x86_64` (Rosetta required on Apple silicon):

```sh
xcrun clang -arch arm64 -std=c11 -fsanitize=address,undefined -g -o /tmp/rush-test mac/tests/test_rush_reentry.c -lz -lpthread
/tmp/rush-test
```

Also run `test_emergency_hotkey.c`, `test_hide_connectivity_ui.c`,
`test_network_progress.c` and `test_stream_receiver.c` with the same flags.
The Rush suite includes the previous loading, staged preview, camera, input,
deferred reconnect and native-send-entry regressions. Fixture errors such as
`fixture native error` are intentional fault injection; check the final test
result. See [Rush and SC](../docs/RUSH-AND-SC.md) for live-validation limits.

Build complete packages on macOS using:

```sh
python tools/build_connectivity.py --output /tmp/sbpe-connectivity-packages
```

The builder verifies the pinned WebBreak input, compiles the Mac dylib and
writes ZIPs with individual file hashes, a manifest and archive checksums.
