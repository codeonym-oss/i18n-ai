from collections.abc import Callable, Sequence

from textual.widgets import DataTable
from textual.widgets.data_table import CellKey


class JobGrid(DataTable[str]):
    """A run's atoms as a grid: a row per file, a column per locale, each cell's text from
    `label(file, locale)` until `show` changes it."""

    def __init__(
        self,
        files: Sequence[str],
        locales: Sequence[str],
        label: Callable[[str, str], str],
        *,
        id: str | None = None,
        cursor: bool = True,
    ) -> None:
        super().__init__(id=id, cursor_type="cell" if cursor else "none")
        self._files = list(files)
        self._locales = list(locales)
        self._label = label

    def on_mount(self) -> None:
        self.add_column("File", key="")
        for locale in self._locales:
            self.add_column(locale, key=locale)
        for file in self._files:
            self.add_row(file, *(self._label(file, locale) for locale in self._locales), key=file)

    def show(self, file: str, locale: str, text: str) -> None:
        """`text` in the cell of `file` and `locale`; a cell the grid does not have, as of a file
        added since the plan, is not shown."""
        if file in self._files and locale in self._locales:
            self.update_cell(file, locale, text)

    def under_cursor(self) -> tuple[str, str] | None:
        """The file and locale under the cursor; the locale is empty in the File column. None
        when there is no file."""
        if not self.row_count:
            return None
        key: CellKey = self.coordinate_to_cell_key(self.cursor_coordinate)
        return str(key.row_key.value), str(key.column_key.value)
