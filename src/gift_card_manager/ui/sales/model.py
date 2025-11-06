"""Sales table model."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from ...models import Sale


class SalesTableModel(QAbstractTableModel):
    """Qt model representing sales."""

    HEADERS = ["Date", "Buyer", "Total", "Cost", "Profit"]

    def __init__(self, rows: Sequence[Sale] | None = None) -> None:
        super().__init__()
        self._rows: List[Sale] = list(rows or [])

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent and parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent and parent.isValid():
            return 0
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None

        sale = self._rows[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            return self._display_value(sale, column)

        if role == Qt.TextAlignmentRole and column in (2, 3, 4):
            return Qt.AlignRight | Qt.AlignVCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def set_rows(self, rows: Sequence[Sale]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_at(self, row_index: int) -> Sale:
        return self._rows[row_index]

    def all_rows(self) -> List[Sale]:
        return list(self._rows)

    def _display_value(self, sale: Sale, column: int):
        if column == 0:
            return sale.sale_date.strftime("%Y-%m-%d") if sale.sale_date else ""
        if column == 1:
            return sale.buyer or ""
        if column == 2:
            return self._format_currency(sale.total_value)
        if column == 3:
            return self._format_currency(sale.total_cost)
        if column == 4:
            return self._format_currency(sale.profit)
        return ""

    @staticmethod
    def _format_currency(value: Decimal | float | int | None) -> str:
        if value is None:
            return ""
        if isinstance(value, Decimal):
            return f"${value:.2f}"
        return f"${Decimal(value):.2f}"