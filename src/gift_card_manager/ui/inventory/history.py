"""Dialog for viewing inventory movements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Sequence

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from PySide6.QtCore import Qt

from ...models import InventoryMovement


@dataclass
class MovementRow:
    movement_date: datetime | None
    source_type: str
    quantity_change: int
    cost_change: Decimal
    notes: str | None


class InventoryMovementDialog(QDialog):
    """Displays a table listing the movements for an inventory item."""

    HEADERS = ["Date", "Source", "Quantity", "Cost", "Notes"]

    def __init__(
        self,
        *,
        item_name: str,
        movements: Sequence[InventoryMovement],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Inventory Movements — {item_name}")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Recent movements for: <b>{item_name}</b>"))

        table = QTableWidget(len(movements), len(self.HEADERS), self)
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.verticalHeader().setVisible(False)

        for row_index, movement in enumerate(movements):
            row = MovementRow(
                movement_date=movement.movement_date,
                source_type=getattr(movement.source_type, "value", str(movement.source_type)),
                quantity_change=movement.quantity_change,
                cost_change=Decimal(movement.cost_change or 0).quantize(Decimal("0.01")),
                notes=movement.notes,
            )
            self._populate_row(table, row_index, row)

        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.resize(640, 360)

    def _populate_row(self, table: QTableWidget, row: int, data: MovementRow) -> None:
        date_str = data.movement_date.strftime("%Y-%m-%d %H:%M") if data.movement_date else ""
        table.setItem(row, 0, QTableWidgetItem(date_str))
        table.setItem(row, 1, QTableWidgetItem(data.source_type.title()))
        qty_item = QTableWidgetItem(str(data.quantity_change))
        qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        table.setItem(row, 2, qty_item)
        cost_item = QTableWidgetItem(f"${data.cost_change:.2f}")
        cost_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        table.setItem(row, 3, cost_item)
        table.setItem(row, 4, QTableWidgetItem(data.notes or ""))