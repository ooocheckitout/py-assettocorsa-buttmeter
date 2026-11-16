# AC Python app: hooks and callbacks

- **Hook:** a module-level function that AC/CSP looks up by name and calls. Define it, don't register it.
- **Callback:** a function you register with an `ac.add*` call. It's bound to one window or control.

Verified against CSP v0.3.0-preview675 (`dwrite.dll`), `acs.exe` and the Kunos Python docs.
Rows marked ⚠ have arguments or timing that are inferred rather than documented.

## Hooks — Vanilla

| Function | When it runs | Outcome |
|---|---|---|
| `acMain(ac_version: str) -> str` | Once, at session load | Create windows and controls. The returned string is the app name. |
| `acUpdate(deltaT: float)` | Every frame, even while the window is dismissed. `deltaT` is seconds since the last frame. | Per-frame logic. |
| `acShutdown()` | Once, when the session ends normally | Final cleanup. **CSP skips it on live reload.** |

## Hooks — CSP

| Function | When it runs | Outcome |
|---|---|---|
| `ext_acDispose()` ⚠ | On live reload, on the **old** module, before CSP deletes its windows | Release sockets, ports and threads. If it raises, the reload is aborted (the context menu has "Reload app without disposing"). |
| `ext_acReload()` ⚠ | On live reload, on the **newly loaded** module | Setup that only runs after a reload. Not called at session start. |

Reload order (CSP): `ext_acDispose` (old) → delete windows → re-import the main module and modules from the app folder → `acMain` ⚠ → `ext_acReload` (new). `acShutdown` is not called.

## Callbacks — Vanilla

Each registration returns `1` on success and `-1` on failure.

| Register with | Callback signature | When it fires | Outcome |
|---|---|---|---|
| `ac.addRenderCallback(control_identifier: int, value: callable)` | `fn(deltaT: float)` | Each time the window finishes rendering | Draw with `ac.gl*`. |
| `ac.addOnAppActivatedListener(control_identifier: int, value: callable)` | `fn(*args)` ⚠ | The user opens or shows the window from the taskbar | React to the window being shown. |
| `ac.addOnAppDismissedListener(control_identifier: int, value: callable)` | `fn(*args)` ⚠ | The user closes or hides the window | React to the window being hidden. |
| `ac.addOnClickedListener(control_identifier: int, value: callable)` | `fn(x: float, y: float)` | A button or control is clicked | Handle the click. `x`/`y` is the click position. |
| `ac.addOnValueChangeListener(control_identifier: int, value: callable)` | `fn(value: float)` | A spinner value changes | Handle the new value. |
| `ac.addOnValidateListener(control_identifier: int, value: callable)` | `fn(string: str)` | Text input is submitted (Enter) | Handle the entered text. |
| `ac.addOnCheckBoxChanged(control_identifier: int, value: callable)` | `fn(name: str, value: int)` | A checkbox is toggled | `value`: `1` = checked, `-1` = unchecked. |
| `ac.addOnListBoxSelectionListener(control_identifier: int, value: callable)` | `fn(name: str, id: int)` | A list box item is selected | `id` = position in the list. |
| `ac.addOnListBoxDeselectionListener(control_identifier: int, value: callable)` | `fn(name: str, id: int)` | A list box item is deselected | `id` = position in the list. |
| `ac.addOnChatMessageListener(ac_window_id: int, call_back_function: callable)` | `fn(message: str, author: str)` | An online chat message arrives | Handle the message. |

## Callbacks — CSP

None. CSP's 213 `ac.ext_*` functions include no listener or callback registration
(see `extension/internal/python/functions.txt`).
