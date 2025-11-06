"""Sales tab view widget."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from ...models import Sale
from ...services import SaleLine, SalesService
from .dialogs import SaleDialog
from .model import SalesTableModel

logger = logging.getLogger(__name__)


@dataclass
class SaleSelection:
    rows: List[Sale]

    @property
    def count(self) -> int:
        return len(self.rows)

    def ensure_single(self) -> Sale | None:
        if self.count != 1:
            return None
        return self.rows[0]


class SalesView(QWidget):
    """Composite widget for sales management."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = SalesTableModel()
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)

        self._search_field = QLineEdit()
        self._search_field.setPlaceholderText("Search by buyer…")
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

    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Sales Actions", self)
        toolbar.setMovable(False)

        add_action = toolbar.addAction("Add Sale")
        add_action.triggered.connect(self._add_sale)

        edit_action = toolbar.addAction("Edit Sale")
        edit_action.triggered.connect(self._edit_selected)

        delete_action = toolbar.addAction("Delete Sale")
        delete_action.triggered.connect(self._delete_selected)

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

    def refresh(self) -> None:
        with session_scope() as session:
            service = SalesService(session)
            sales = service.list_sales()
        self._model.set_rows(sales)
        self._apply_search_filter(self._search_field.text())

    def _apply_search_filter(self, text: str) -> None:
        text = text.strip().lower()
        selection_model = self._table.selectionModel()
        selection_model.clearSelection()

        if not text:
            self._table.viewport().update()
            return

        for row_index, sale in enumerate(self._model.all_rows()):
            if text in (sale.buyer or "").lower():
                index = self._model.index(row_index, 0)
                selection_model.select(index, selection_model.Select | selection_model.Rows)

    def _show_context_menu(self, position) -> None:
        menu = QMenu(self)
        menu.addAction("Add Sale", self._add_sale)
        selection = self._current_selection()
        if selection.count:
            menu.addSeparator()
            menu.addAction("Edit Sale", self._edit_selected)
            menu.addAction("Delete Sale", self._delete_selected)
        menu.exec(self._table.viewport().mapToGlobal(position))

    def _add_sale(self) -> None:
        with session_scope() as session:
            dialog = SaleDialog(session=session, parent=self)
            if dialog.exec() != SaleDialog.Accepted:
                return
            result = dialog.result_data()
            if result is None:
                return

            sale = Sale(
                buyer=result.buyer,
                sale_date=result.sale_date,
            )

            service = SalesService(session)
            lines = [
                SaleLine(
                    inventory_item_id=line.inventory_item_id,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                )
                for line in result.lines
            ]

            try:
                service.create_sale(sale, lines)
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed tocreate sale")
                QMessageBox.critical(self, "Add Sale", f"Failed to create sale:\n{exc}")
                return

        self.refresh()

    def _edit_selected(self) -> None:
        selection = self._current_selection()
        sale = selection.ensure_single()
        if sale is None:
            QMessageBox.information(self, "Edit Sale", "Select one sale to edit.")
            return

        with session_scope() as session:
            db_sale = session.get(Sale, sale.id)
            if db_sale is None:
                QMessageBox.warning(self, "Edit Sale", "Selected sale no longer exists.")
                return

            dialog = SaleDialog(session=session, parent=self, existing=db_sale)
            if dialog.exec() != SaleDialog.Accepted:
                return
            result = dialog.result_data()
            if result is None:
                return

            db_sale.buyer = result.buyer
            db_sale.sale_date = result.sale_date

            service = SalesService(session)
            lines = [
                SaleLine(
                    inventory_item_id=line.inventory_item_id,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                )
                for line in result.lines
            ]

            try:
                service.update_sale(db_sale, lines)
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to update sale")
                QMessageBox.critical(self,
                                     "Edit Sale",
                                     f"Failed to update sale:\n{exc}")
                return

        self.refresh()

    def _delete_selected(self) -> None:
        selection = self._current_selection()
        if selection.count == 0:
            QMessageBox.information(self, "Delete Sales", "No sales selected.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Sales",
            f"Delete {selection.count} selected sale(s)? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        with session_scope() as session:
            service = SalesService(session)
            for sale in selection.rows:
                db_sale = session.get(Sale, sale.id)
                if db_sale:
                    service.delete_sale(db_sale)
            try:
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to delete sales")
                QMessageBox.critical(self, "Delete Sales", f"Failed to delete sales:\n{exc}")
                return

        self.refresh()

    def _current_selection(self) -> SaleSelection:
        selection_model = self._table.selectionModel()
        selected_rows = selection_model.selectedRows()
        rows: List[Sale] = []
        for index in selected_rows:
            rows.append(self._model.row_at(index.row()))
        return SaleSelection(rows)