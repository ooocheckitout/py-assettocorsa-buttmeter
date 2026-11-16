# AC Python app: UI functions

Every `ac` function that builds or controls a window element. Function names are taken from the
`ac` module's function table in `acs.exe`; parameters and return values come from the Kunos Python
docs and this repo. Rows marked ⚠ are undocumented and inferred.

`apps/python/Showcase/Showcase.py` creates one of each element, to see how they look in-game.

**Conventions**

- `id`: the int returned by `newApp` or an `add*` call. Every other call takes it first.
- Setters, `add*Listener` and `addRenderCallback` return `1` on success, `-1` on failure.
- Creators return the new id, or `-1` on failure.
- Colours are floats `0`–`1`. Flags are ints, `0` = off, `1` = on.

## Window (`newApp`)

| Function | Params | Returns | Does |
|---|---|---|---|
| `newApp(name)` | `name: str` | window id | Creates a window and its sidebar entry. `name` is also the icon file name (`content/gui/icons/<name>_ON.png` / `_OFF.png`). |
| `setTitle(id, text)` | `text: str` | 1/-1 | Changes the text drawn in the title bar. The sidebar name stays the same. |
| `setTitlePosition(id, x, y)` | px | 1/-1 | Moves the title text inside the window. |
| `setIconPosition(id, x, y)` | px | 1/-1 | Moves the icon in the window's corner. Coordinates off-screen hide it. |
| `setBackgroundTexture(id, path)` | path relative to AC root | 1/-1 | Uses a PNG as the window background. |
| `addRenderCallback(id, fn)` | `fn(deltaT: float)` | 1/-1 | Calls `fn` every frame after the window is drawn. `gl*` calls only work inside it. |
| `addOnAppActivatedListener(id, fn)` | `fn(*args)` ⚠ | 1/-1 | Fires when the window is shown from the sidebar. |
| `addOnAppDismissedListener(id, fn)` | `fn(*args)` ⚠ | 1/-1 | Fires when the window is hidden. |
| `addOnChatMessageListener(id, fn)` | `fn(message, author)` | 1/-1 | Fires when an online chat message arrives. |

## Shared: windows and all controls

| Function | Params | Returns | Does |
|---|---|---|---|
| `setPosition(id, x, y)` | px. Window: screen position. Control: relative to its window's top-left. | 1/-1 | Moves it. |
| `getPosition(id)` | | `[x, y]` | Current position. |
| `setSize(id, w, h)` | px. A window's size includes its title strip. | 1/-1 | Resizes it. Controls inside a window do not move or scale with it. |
| `getSize(id)` | | `[w, h]` | Current size. |
| `setVisible(id, v)` | 0/1 | 1/-1 | Shows or hides it. Controls can't be deleted, so hide them instead. |
| `drawBorder(id, v)` | 0/1 | 1/-1 | Turns the border on or off. |
| `drawBackground(id, v)` | 0/1 | 1/-1 | Turns the background fill on or off. |
| `setBackgroundColor(id, r, g, b)` | floats, no alpha | 1/-1 | Background colour. |
| `setBackgroundOpacity(id, a)` | float | 1/-1 | Background alpha. On windows, AC resets it while hovered or dragged: set it every frame in the render callback. |
| `setFocus(id, v)` ⚠ | 0/1 | 1/-1 | Gives it keyboard focus (text input). |

**Text styling** (label, button, text box, text input):

| Function | Params | Returns | Does |
|---|---|---|---|
| `setText(id, text)` | `str` | 1/-1 | Changes the caption or content. |
| `getText(id)` | | `str` | Current text. |
| `setFontSize(id, px)` | float | 1/-1 | Font size. |
| `setFontColor(id, r, g, b, a)` | floats | 1/-1 | Text colour. |
| `setFontAlignment(id, a)` | `"left"`, `"center"`, `"right"` | 1/-1 | Horizontal alignment inside the control. |
| `initFont(0, name, italic, bold)` | `name`: font family; `italic`, `bold`: 0/1 | 1/-1 | Loads a font once, in `acMain`. |
| `setCustomFont(id, name, italic, bold)` | as `initFont` | 1/-1 | Applies a font loaded with `initFont`. |
| `setFont(id, ...)` ⚠ | undocumented | ? | Present in the exe; arguments unknown. |

## Label

| Function | Params | Returns | Does |
|---|---|---|---|
| `addLabel(window, text)` | `window`: window id, `text: str` | label id | Static text, transparent by default. |

Uses the shared and text-styling functions. No events.

## Button

| Function | Params | Returns | Does |
|---|---|---|---|
| `addButton(window, text)` | | button id | A clickable box with a caption. |
| `addOnClickedListener(id, fn)` | `fn(x, y)`: click position | 1/-1 | Fires on click. Also works on labels and windows ⚠. |

## Checkbox

| Function | Params | Returns | Does |
|---|---|---|---|
| `addCheckBox(window, text)` | | checkbox id | A toggle box, caption to its right. |
| `setValue(id, v)` | 0/1 | 1/-1 | Sets checked or unchecked. |
| `getValue(id)` | | 0 or 1 ⚠ | Current state. |
| `addOnCheckBoxChanged(id, fn)` | `fn(name: str, value: int)`: `1` checked, `-1` unchecked | 1/-1 | Fires on toggle. |

## Spinner

| Function | Params | Returns | Does |
|---|---|---|---|
| `addSpinner(window, text)` | | spinner id | A number with − and + buttons; `text` is drawn above it. |
| `setRange(id, min, max)` | floats | 1/-1 | Clamps the value. |
| `setStep(id, step)` | **int** | 1/-1 | Change per − / + click. A float raises `TypeError: integer argument expected, got float`, so the smallest step is 1. |
| `setValue(id, v)` | float | 1/-1 | Sets the value. **Fires the change listener.** |
| `getValue(id)` | | float | Current value. |
| `addOnValueChangeListener(id, fn)` | `fn(value: float)` | 1/-1 | Fires on any change, including your own `setValue` / `setRange` calls. Guard against re-entry. |

## Progress bar

| Function | Params | Returns | Does |
|---|---|---|---|
| `addProgressBar(window, text)` | | bar id | A horizontal fill bar. |
| `setRange(id, min, max)` | floats | 1/-1 | Value range mapped from empty to full. |
| `setValue(id, v)` / `getValue(id)` | float | 1/-1 / float | Fill level. |

No events.

## Text input (single line)

| Function | Params | Returns | Does |
|---|---|---|---|
| `addTextInput(window, text)` | | input id | An editable one-line field. |
| `setText` / `getText` | | | Content. |
| `addOnValidateListener(id, fn)` | `fn(text: str)` | 1/-1 | Fires when the user presses Enter. |

## Text box (multi-line)

| Function | Params | Returns | Does |
|---|---|---|---|
| `addTextBox(window, text)` | | box id | A read-only multi-line text area, scrolls ⚠. |
| `setText` / `getText` | `\n` separates lines | | Content. |

## List box

| Function | Params | Returns | Does |
|---|---|---|---|
| `addListBox(window, text)` | | list id | A paged list of items. |
| `addItem(id, text)` | `str` | index or 1/-1 ⚠ | Appends an item. |
| `removeItem(id, index)` | int | 1/-1 | Removes the item at `index`. |
| `getItemCount(id)` | | int | Number of items. |
| `setItemNumberPerPage(id, n)` | int | 1/-1 | Rows visible at once; paging arrows appear when there are more. |
| `highlightListBoxItem(id, index)` | int | 1/-1 | Selects an item from code. |
| `getSelectedItems(id)` | | list of indexes ⚠ | Current selection. |
| `setAllowMultiSelection(id, v)` | 0/1 | 1/-1 | Allows selecting several items. |
| `setAllowDeselection(id, v)` | 0/1 | 1/-1 | Lets a click on a selected item deselect it. |
| `addOnListBoxSelectionListener(id, fn)` | `fn(name: str, index: int)` | 1/-1 | Fires when an item is selected. |
| `addOnListBoxDeselectionListener(id, fn)` | `fn(name: str, index: int)` | 1/-1 | Fires when an item is deselected. |

## Graph

| Function | Params | Returns | Does |
|---|---|---|---|
| `addGraph(window, text)` | | graph id | A scrolling line chart. |
| `setRange(id, min, max, points)` | `min`/`max`: y range; `points`: samples kept (x width) | 1/-1 | Graph takes 4 arguments; spinner and progress bar take 3. |
| `addSerieToGraph(id, r, g, b)` | line colour | 1/-1 ⚠ | Adds a line. Series are indexed 0, 1, … in order added. |
| `addValueToGraph(id, serie, v)` | `serie`: index, `v`: float | 1/-1 | Pushes one sample. Call every frame from `acUpdate`. |

## GL drawing (inside `addRenderCallback` only)

| Function | Params | Returns | Does |
|---|---|---|---|
| `glColor4f(r, g, b, a)` / `glColor3f(r, g, b)` | floats | 1/-1 | Colour for the shapes drawn next. |
| `glQuad(x, y, w, h)` | px, relative to the window | 1/-1 | Filled rectangle. |
| `glBegin(mode)` | `acsys.GL.Lines`, `LineStrip`, `Triangles`, `Quads` | 1/-1 | Starts a primitive. |
| `glVertex2f(x, y)` | px | 1/-1 | Adds a vertex. |
| `glEnd()` | | 1/-1 | Finishes and draws the primitive. |
| `newTexture(path)` | PNG path relative to AC root | texture id, or -1 | Loads an image. Call once, outside the render callback. |
| `glQuadTextured(x, y, w, h, tex)` | `tex`: texture id | 1/-1 | Draws the image, tinted by the current colour ⚠. |

## Debug

| Function | Params | Returns | Does |
|---|---|---|---|
| `console(text)` | `str` | 1/-1 | Prints to the in-game console. |
| `log(text)` | `str` | 1/-1 | Writes to `Documents/Assetto Corsa/logs/py_log.txt`. |

## Gotchas

- AC keeps no reference to callbacks. Store every callback (a module-level list) or a freed
  lambda crashes the game natively.
- No layout engine: every control is placed in absolute px. Scaling means recomputing positions.
- AC's embedded Python is 3.3: no f-strings, no third-party imports.

Not covered: car, session, camera and server functions (`getCarState`, `getFocusedCar`,
`getTrackName`, `freeCamera*`, `sendChatMessage`, ...). See `docs/lifecycle-cheatsheet.md` for hooks.
