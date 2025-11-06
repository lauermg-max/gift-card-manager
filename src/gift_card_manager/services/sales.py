"""Sales management services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy.orm import Session

from ..models import InventoryItem, Sale, SaleItem
from ..models.enums import InventorySourceType
from ..services.inventory import InventoryAdjustment, InventoryService


@dataclass(frozen=True)
class SaleLine:
    inventory_item_id: int
    quantity: int
    unit_price: Decimal


class SalesService:
    """Encapsulates sale lifecycle and inventory deductions."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.inventory_service = InventoryService(session)

    def list_sales(self) -> Sequence[Sale]:
        return self.session.query(Sale).order_by(Sale.sale_date.desc(), Sale.id.desc()).all()

    def create_sale(self, sale: Sale, lines: Sequence[SaleLine]) -> Sale:
        sale.total_value = Decimal("0")
        sale.total_cost = Decimal("0")
        sale.profit = Decimal("0")

        self.session.add(sale)
        self.session.flush()

        total_value = Decimal("0")
        total_cost = Decimal("0")

        for line in lines:
            item = self._get_inventory_item(line.inventory_item_id)
            if item.quantity_on_hand < line.quantity:
                raise ValueError(f"Not enough stock for {item.item_name}")

            unit_cost = item.average_cost or Decimal("0")
            cost_change = unit_cost * Decimal(line.quantity)

            sale_item = SaleItem(
                sale_id=sale.id,
                inventory_item_id=item.id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                unit_cost=unit_cost,
                line_total=line.unit_price * Decimal(line.quantity),
                line_cost=cost_change,
            )
            self.session.add(sale_item)

            adjustment = InventoryAdjustment(
                quantity_change=-line.quantity,
                cost_change=-cost_change,
                source_type=InventorySourceType.SALE,
                source_id=sale.id,
                notes=f"Sale {sale.id}",
            )
            self.inventory_service.apply_adjustment(item, adjustment)

            total_value += sale_item.line_total
            total_cost += cost_change

        sale.total_value = total_value.quantize(Decimal("0.01"))
        sale.total_cost = total_cost.quantize(Decimal("0.01"))
        sale.profit = (sale.total_value - sale.total_cost).quantize(Decimal("0.01"))

        return sale

    def update_sale(self, sale: Sale, lines: Sequence[SaleLine]) -> Sale:
        self._restore_inventory(sale)
        for sale_item in list(sale.items):
            self.session.delete(sale_item)
        self.session.flush()
        return self.create_sale(sale, lines)

    def delete_sale(self, sale: Sale) -> None:
        self._restore_inventory(sale)
        for line in list(sale.items):
            self.session.delete(line)
        self.session.delete(sale)

    def _get_inventory_item(self, item_id: int) -> InventoryItem:
        item = self.session.get(InventoryItem, item_id)
        if item is None:
            raise ValueError(f"Inventory item {item_id} not found")
        return item

    def _restore_inventory(self, sale: Sale) -> None:
        for sale_item in sale.items:
            item = sale_item.inventory_item
            if item is None:
                item = self.session.get(InventoryItem, sale_item.inventory_item_id)
            if item is None:
                continue
            adjustment = InventoryAdjustment(
                quantity_change=sale_item.quantity,
                cost_change=sale_item.line_cost or Decimal("0"),
                source_type=InventorySourceType.ADJUSTMENT,
                notes=f"Reversal of sale {sale.id}",
            )
            self.inventory_service.apply_adjustment(item, adjustment)