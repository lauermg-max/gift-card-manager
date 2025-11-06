"""Inventory tab view widget."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ...core import session_scope
from ...models import InventoryItem
from ...models.enums import InventorySourceType
from ...services import InventoryAdjustment, InventoryService
from .dialogs import (
    InventoryAdjustmentDialog,
    InventoryItemDialog,
)
from .model import InventoryTableModel

logger = logging.getLogger(__name__)


@dataclass
class InventorySelection:
    rows: List[InventoryItem]

    @property
    def count(self) -> int:
        return len(self.rows)

    def ensure_single(self) -> InventoryItem | None:
        if self.count != 1:
            return None
        return self.rows[0]


class InventoryView(QWidget):
    """Composite widget for inventory management."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._model = InventoryTableModel()
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)

        self._search_field = QLineEdit()
        self._search_field.setPlaceholderText("Search by item name or SKU…")
        self._search_field.textChanged.connect(self._apply_search_filter)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._build_toolbar())
        layout.addLayout(self._build_filter_row())
        layout.addWidget(self._table)
        self.setLayout(layout)

        self.refresh()

        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

    # ------------------------------------------------------------------ UI --
    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Inventory Actions", self)
        toolbar.setMovable(False)

        add_action = toolbar.addAction("Add Item")
        add_action.triggered.connect(self._add_item)

        edit_action = toolbar.addAction("Edit Item")
        edit_action.triggered.connect(self._edit_selected)

        delete_action = toolbar.addAction("Delete Item")
        delete_action.triggered.connect(self._delete_selected)

        toolbar.addSeparator()

        adjust_action = toolbar.addAction("Adjust Stock")
        adjust_action.triggered.connect(self._adjust_selected)

        toolbar.addSeparator()

        refresh_action = toolbar.addAction("Refresh")
        refresh_action.triggered.connect(self.refresh)

        return toolbar

    def _build_filter_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(8, 4, 8, 4)
        row.addWidget(QLabel("Search:"))
        row.addWidget(self._search_field, 2)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._search_field.clear)
        row.addWidget(clear_button)
        row.addStretch(1)
        return row

    # -------------------------------------------------------------- Data ----
    def refresh(self) -> None:
        with session_scope() as session:
            items = self._load_inventory(session)
        self._model.set_rows(items)
        self._apply_search_filter(self._search_field.text())

    def _load_inventory(self, session) -> Iterable[InventoryItem]:
        return session.query(InventoryItem).order_by(InventoryItem.item_name).all()

    # ---------------------------------------------------------- Search ------
    def _apply_search_filter(self, text: str) -> None:
        text = text.strip().lower()
        selection_model = self._table.selectionModel()
        selection_model.clearSelection()

        if not text:
            self._table.viewport().update()
            return

        for row_index, item in enumerate(self._model.all_rows()):
            if text in (item.item_name or "").lower() or text in (item.sku or "").lower():
                index = self._model.index(row_index, 0)
                selection_model.select(index, selection_model.Select | selection_model.Rows)

    # ---------------------------------------------------- Context menu -----
    def _show_context_menu(self, position) -> None:
        menu = QMenu(self)
        menu.addAction("Add Item", self._add_item)
        selection = self._current_selection()
        if selection.count:
            menu.addSeparator()
            menu.addAction("Edit Item", self._edit_selected)
            menu.addAction("Delete Item", self._delete_selected)
            menu.addSeparator()
            menu.addAction("Adjust Stock", self._adjust_selected)
        menu.exec(self._table.viewport().mapToGlobal(position))