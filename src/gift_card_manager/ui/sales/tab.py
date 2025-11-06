"""Sales tab wrapper."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .view import SalesView


class SalesTab(QWidget):
    """Widget used for the Sales tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(SalesView(self))
        self.setLayout(layout)