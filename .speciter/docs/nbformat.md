# nbformat quick guide (docs: nbformat 5.10)

Sources:
- https://nbformat.readthedocs.io/en/latest/api.html
- https://nbformat.readthedocs.io/en/latest/format_description.html
- https://nbformat.readthedocs.io/en/latest/changelog.html

## Read / write `.ipynb`

```python
import nbformat

# Convert to v4 structure on read
nb = nbformat.read("notebook.ipynb", as_version=4)

# Keep notebook's own version on write
nbformat.write(nb, "notebook.ipynb")

# Or force write version
nbformat.write(nb, "notebook-v4.ipynb", version=4)

# No conversion (read/write in file's native version)
nb_native = nbformat.read("notebook.ipynb", as_version=nbformat.NO_CONVERT)
nbformat.write(nb_native, "notebook-native.ipynb", version=nbformat.NO_CONVERT)
```

## Iterate cells

```python
for i, cell in enumerate(nb.cells):
    print(i, cell.cell_type, getattr(cell, "id", None))

code_cells = [c for c in nb.cells if c.cell_type == "code"]
md_cells = [c for c in nb.cells if c.cell_type == "markdown"]
```

## Update cells safely

```python
import nbformat

for cell in nb.cells:
    if cell.cell_type == "markdown" and "TODO" in cell.source:
        cell.source = cell.source.replace("TODO", "DONE")

# Add new cells with constructors (ensures required fields)
nb.cells.append(nbformat.v4.new_markdown_cell("## New section"))
nb.cells.append(nbformat.v4.new_code_cell("print('ok')"))

# Validate before save
nbformat.validate(nb)
nbformat.write(nb, "notebook.ipynb")
```

## Delete cells safely

```python
# Keep only non-empty markdown and all code/raw cells
nb.cells = [
    c for c in nb.cells
    if not (c.cell_type == "markdown" and not c.source.strip())
]

# Or delete by index (reverse order avoids index shift bugs)
to_delete = [2, 5, 8]
for i in sorted(to_delete, reverse=True):
    del nb.cells[i]

nbformat.validate(nb)
nbformat.write(nb, "notebook.ipynb")
```

## Preserve notebook structure

```python
# Top-level keys expected by spec: metadata, nbformat, nbformat_minor, cells
# Keep metadata and ids unless you intentionally change them.

nb2 = nbformat.read("in.ipynb", as_version=4)

# Safe transform pattern: change only cells, preserve top-level fields
updated_cells = []
for cell in nb2.cells:
    if cell.cell_type == "code":
        updated_cells.append(cell)
    else:
        updated_cells.append(cell)

nb2.cells = updated_cells
nbformat.validate(nb2)
nbformat.write(nb2, "out.ipynb")
```

## Optional: capture validation error during read/write

```python
err = {}
nb = nbformat.read("notebook.ipynb", as_version=4, capture_validation_error=err)
if "ValidationError" in err:
    print(err["ValidationError"])
```
