"""Gift card inventory view."""

from __future__ import annotations

from dataclasses import dataclass
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
from ...models import GiftCard, Retailer
from ...services import GiftCardService
from .model import GiftCardTableModel


@dataclass
class GiftCardSelection:
    """Represents the currently selected gift cards in the view."""

    rows: List[GiftCard]

    @property
    def count(self) -> int:
        return len(self.rows)

    def ensure_single(self) -> GiftCard | None:
        if self.count != 1:
            return None
        return self.rows[0]


class GiftCardInventoryView(QWidget):
    """Widget showing gift cards with filtering and bulk actions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._model = GiftCardTableModel()
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)

        self._retailer_filter = QComboBox()
        self._retailer_filter.currentIndexChanged.connect(self.refresh)
        self._search_field = QLineEdit()
        self._search_field.setPlaceholderText("Search by SKU or card number…")
        self._search_field.textChanged.connect(self._apply_search_filter)

        self._toolbar = self._build_toolbar()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._toolbar)
        layout.addLayout(self._build_filter_row())
        layout.addWidget(self._table)
        self.setLayout(layout)

        self._load_retailers()
        self.refresh()

        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

    # --------------------------------------------------------------------- UI --
    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Gift Card Actions", self)
        toolbar.setIconSize(toolbar.iconSize())
        toolbar.setMovable(False)

        add_action = toolbar.addAction("Add")
        add_action.triggered.connect(self._add_gift_card)

        edit_action = toolbar.addAction("Edit")
        edit_action.triggered.connect(self._edit_selected)

        delete_action = toolbar.addAction("Delete")
        delete_action.triggered.connect(self._delete_selected)

        refresh_action = toolbar.addAction("Refresh")
        refresh_action.triggered.connect(self.refresh)

        toolbar.addSeparator()
        export_action = toolbar.addAction("Export CSV…")
        export_action.triggered.connect(self._export_csv)

        import_action = toolbar.addAction("Import CSV…")
        import_action.triggered.connect(self._import_csv)

        return toolbar

    def _build_filter_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(8, 0, 8, 0)
        row.addWidget(QLabel("Retailer:"))
        row.addWidget(self._retailer_filter, 1)
        row.addSpacing(16)
        row.addWidget(QLabel("Search:"))
        row.addWidget(self._search_field, 2)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._search_field.clear)
        row.addWidget(clear_button)
        return row

    # ------------------------------------------------------------- Data logic --
    def refresh(self) -> None:
        with session_scope() as session:
            cards = self._load_gift_cards(session)
        self._model.set_rows(cards)
        self._apply_search_filter(self._search_field.text())

    def _load_gift_cards(self, session) -> Iterable[GiftCard]:
        service = GiftCardService(session)
        retailer_code = self._current_retailer_code()
        if retailer_code == "ALL":
            return service.list_gift_cards()
        retailer = (
            session.query(Retailer).filter(Retailer.code == retailer_code).one_or_none()
        )
        if retailer is None:
            return []
        return (
            session.query(GiftCard)
            .filter(GiftCard.retailer_id == retailer.id)
            .order_by(GiftCard.sku)
            .all()
        )

    def _load_retailers(self) -> None:
        self._retailer_filter.blockSignals(True)
        self._retailer_filter.clear()
        self._retailer_filter.addItem("All Retailers", "ALL")
        with session_scope() as session:
            retailers = (
                session.query(Retailer).order_by(Retailer.name).all()
            )
        for retailer in retailers:
            display = f"{retailer.name} ({retailer.code})"
            self._retailer_filter.addItem(display, retailer.code)
        self._retailer_filter.blockSignals(False)

    def _current_retailer_code(self) -> str:
        return self._retailer_filter.currentData(Qt.ItemDataRole.UserRole) or "ALL"

    # ----------------------------------------------------------- Search filter --
    def _apply_search_filter(self, text: str) -> None:
        text = text.strip().lower()
        if not text:
            self._table.clearSelection()
            self._table.viewport().update()
            return

        matches: List[int] = []
        for row_index, card in enumerate(self._model.all_rows()):
            if text in card.sku.lower() or text in card.card_number.lower():
                matches.append(row_index)

        selection_model = self._table.selectionModel()
        selection_model.clearSelection()
        for row in matches:
            index = self._model.index(row, 0)
            selection_model.select(index, selection_model.Select | selection_model.Rows)

    # ----------------------------------------------------------- Context menu --
    def _show_context_menu(self, position) -> None:
        menu = QMenu(self)
        menu.addAction("Add", self._add_gift_card)
        selection = self._current_selection()
        if selection.count >= 1:
            menu.addSeparator()
            menu.addAction("Edit", self._edit_selected)
            menu.addAction("Delete", self._delete_selected)
        menu.exec(self._table.viewport().mapToGlobal(position))

    # --------------------------------------------------------------- Actions --
    def _add_gift_card(self) -> None:
        QMessageBox.information(self, "Add Gift Card", "Add dialog not implemented yet.")

    def _edit_selected(self) -> None:
        selection = self._current_selection()
        card = selection.ensure_single()
        if card is None:
            QMessageBox.information(self, "Edit Gift Card", "Select one gift card to edit.")
            return
        QMessageBox.information(
            self,
            "Edit Gift Card",
            f"Edit dialog not implemented yet for {card.sku}.",
        )

    def _delete_selected(self) -> None:
        selection = self._current_selection()
        if selection.count == 0:
            QMessageBox.information(self, "Delete Gift Cards", "No gift cards selected.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Gift Cards",
            f"Delete {selection.count} selected gift card(s)? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        with session_scope() as session:
            service = GiftCardService(session)
            for card in selection.rows:
                card_db = session.get(GiftCard, card.id)
                if card_db:
                    session.delete(card_db)
            session.commit()

        self.refresh()

    def _export_csv(self) -> None:
        QMessageBox.information(self, "Export CSV", "CSV export UI coming soon.")

    def _import_csv(self) -> None:
        QMessageBox.information(self, "Import CSV", "CSV import UI coming soon.")

    # --------------------------------------------------------- Helper methods --
    def _current_selection(self) -> GiftCardSelection:
        selection_model = self._table.selectionModel()
        selected_rows = selection_model.selectedRows()
        rows: List[GiftCard] = []
        for index in selected_rows:
            rows.append(self._model.row_at(index.row()))
        return GiftCardSelection(rows)