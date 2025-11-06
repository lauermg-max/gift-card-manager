"""Dialogs for recording sales."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Sequence

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...models import InventoryItem, Sale
from ...services import SaleLine, SalesService


@dataclass
class SaleLineEntry:
    inventory_item_id: int
    description: str
    quantity: int
    unit_price: Decimal


@dataclass
class SaleDialogResult:
    buyer: str | None
    sale_date: date
    lines: List[SaleLineEntry]


class SaleDialog(QDialog):
    """Dialog for creating or editing sales."""

    def __init__(
        self,
        *,
        session,
        parent: QWidget | None = None,
        existing: Sale | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Edit Sale" if existing else "Add Sale")
        self._session = session
        self._existing = existing
        self._lines: List[SaleLineEntry] = []
        self._result: SaleDialogResult | None = None

        self._buyer_field = QLineEdit()
        self._date_field = QDateEdit()
        self._date_field.setCalendarPopup(True)
        self._date_field.setDate(QDate.currentDate())

        self._inventory_combo = QComboBox()
        self._load_inventory_items()

        self._quantity_field = QDoubleSpinBox()
        self._quantity_field.setDecimals(0)
        self._quantity_field.setMinimum(1)
        self._quantity_field.setMaximum(1_000_000)
        self._quantity_field.setValue(1)

        self._price_field = QDoubleSpinBox()
        self._price_field.setDecimals(2)
        self._price_field.setMinimum(0.01)
        self._price_field.setMaximum(1_000_000)
        self._price_field.setValue(1.00)

        add_line_button = QPushButton("Add Line")
        add_line_button.clicked.connect(self._add_line)

        remove_line_button = QPushButton("Remove Selected")
        remove_line_button.clicked.connect(self._remove_selected_line)

        self._line_list = QListWidget()

        if existing:
            if existing.buyer:
                self._buyer_field.setText(existing.buyer)
            if existing.sale_date:
                self._date_field.setDate(QDate(existing.sale_date.year, existing.sale_date.month, existing.sale_date.day))
            for sale_item in existing.items:
                inventory_item = sale_item.inventory_item
                description = inventory_item.item_name if inventory_item else f"Item {sale_item.inventory_item_id}"
                entry = SaleLineEntry(
                    inventory_item_id=sale_item.inventory_item_id,
                    description=description,
                    quantity=sale_item.quantity,
                    unit_price=sale_item.unit_price or Decimal("0"),
                )
                self._lines.append(entry)
            self._refresh_line_list()

        form = QFormLayout()
        form.addRow("Buyer", self._buyer_field)
        form.addRow("Sale Date", self._date_field)

        add_line_row = QHBoxLayout()
        add_line_row.addWidget(QLabel("Item"))
        add_line_row.addWidget(self._inventory_combo, 2)
        add_line_row.addWidget(QLabel("Qty"))
        add_line_row.addWidget(self._quantity_field)
        add_line_row.addWidget(QLabel("Price"))
        add_line_row.addWidget(self._price_field)
        add_line_row.addWidget(add_line_button)

        remove_row = QHBoxLayout()
        remove_row.addWidget(remove_line_button)
        remove_row.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(add_line_row)
        layout.addWidget(self._line_list)
        layout.addLayout(remove_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.setMinimumWidth(480)

    def result_data(self) -> SaleDialogResult | None:
        return self._result

    def _load_inventory_items(self) -> None:
        items = (
            self._session.query(InventoryItem)
            .order_by(InventoryItem.item_name)
            .all()
        )
        self._inventory_combo.clear()
        for item in items:
            description = f"{item.item_name} (qty: {item.quantity_on_hand})"
            self._inventory_combo.addItem(description, item)

    def _add_line(self) -> None:
        inventory_item = self._inventory_combo.currentData(Qt.ItemDataRole.UserRole)
        if inventory_item is None:
            QMessageBox.warning(self, "Line Item", "Select an inventory item.")
            return
        quantity = int(self._quantity_field.value())
        if quantity <= 0:
            QMessageBox.warning(self, "Line Item", "Quantity must be greater than zero.")
            return
        unit_price = Decimal(str(self._price_field.value())).quantize(Decimal("0.01"))
        description = inventory_item.item_name or f"Item {inventory_item.id}"
        entry = SaleLineEntry(
            inventory_item_id=inventory_item.id,
            description=description,
            quantity=quantity,
            unit_price=unit_price,
        )
        self._lines.append(entry)
        self._refresh_line_list()

    def _remove_selected_line(self) -> None:
        selected = self._line_list.currentRow()
        if selected < 0:
            return
        self._lines.pop(selected)
        self._refresh_line_list()

    def _refresh_line_list(self) -> None:
        self._line_list.clear()
        for entry in self._lines:
            item = QListWidgetItem(
                f"{entry.description}: {entry.quantity} @ ${entry.unit_price:.2f}"
            )
            self._line_list.addItem(item)

    def accept(self) -> None:
        sale_date = self._date_field.date().toPython()
        buyer = self._buyer_field.text().strip() or None
        if not self._lines:
            QMessageBox.warning(self, "Validation", "Add at least one sale line.")
            return
        self._result = SaleDialogResult(
            buyer=buyer,
            sale_date=sale_date,
            lines=list(self._lines),
        )
        super().accept()