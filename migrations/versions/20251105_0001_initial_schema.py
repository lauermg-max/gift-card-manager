"""Initial schema

Revision ID: 20251105_0001
Revises: 
Create Date: 2025-11-05 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20251105_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retailers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("requires_pin", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("notes", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.Enum("credit_card", "bank", "gift_card_pool", name="accounttype"), nullable=False),
        sa.Column("balance", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("credit_limit", sa.Numeric(10, 2)),
        sa.Column("notes", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "gift_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("retailer_id", sa.Integer(), sa.ForeignKey("retailers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(length=32), nullable=False),
        sa.Column("card_number", sa.String(length=128), nullable=False),
        sa.Column("card_pin", sa.String(length=64)),
        sa.Column("acquisition_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("face_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("remaining_balance", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.Enum("active", "used", "void", "archived", name="giftcardstatus"), nullable=False),
        sa.Column("purchase_date", sa.Date()),
        sa.Column("notes", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("sku"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("retailer_id", sa.Integer(), sa.ForeignKey("retailers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_number", sa.String(length=100), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("order_email", sa.String(length=200)),
        sa.Column("payment_method", sa.Enum("gift_card", "credit_card", "mixed", name="paymentmethod"), nullable=False),
        sa.Column("subtotal", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("tax", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("shipping", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("total_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("credit_card_spend", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("gift_card_spend", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.Enum("ordered", "shipped", "cancelled", "delivered", name="orderstatus"), nullable=False),
        sa.Column("receipt_path", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=64)),
        sa.Column("upc", sa.String(length=64)),
        sa.Column("quantity_on_hand", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("average_cost", sa.Numeric(10, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("total_cost", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("notes", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("sku"),
        sa.UniqueConstraint("upc"),
    )

    op.create_table(
        "account_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("related_type", sa.Enum("order", "sale", "deposit", "withdrawal", name="accountrelatedtype"), nullable=False),
        sa.Column("related_id", sa.Integer()),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("description", sa.String(length=255)),
        sa.Column("transaction_date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "gift_card_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gift_card_id", sa.Integer(), sa.ForeignKey("gift_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL")),
        sa.Column("amount_used", sa.Numeric(10, 2), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=100)),
        sa.Column("upc", sa.String(length=64)),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("label", sa.String(length=200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inventory_item_id", sa.Integer(), sa.ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.Enum("order", "sale", "adjustment", name="inventorysourcetype"), nullable=False),
        sa.Column("source_id", sa.Integer()),
        sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("order_items.id", ondelete="SET NULL")),
        sa.Column("quantity_change", sa.Integer(), nullable=False),
        sa.Column("cost_change", sa.Numeric(10, 2), nullable=False),
        sa.Column("movement_date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("notes", sa.String(length=500)),
    )

    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("buyer", sa.String(length=255)),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("total_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("profit", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "sale_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_item_id", sa.Integer(), sa.ForeignKey("inventory_items.id", ondelete="SET NULL")),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 4), nullable=False),
        sa.Column("line_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("line_cost", sa.Numeric(10, 2), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sale_items")
    op.drop_table("sales")
    op.drop_table("inventory_movements")
    op.drop_table("attachments")
    op.drop_table("order_items")
    op.drop_table("gift_card_usage")
    op.drop_table("account_transactions")
    op.drop_table("inventory_items")
    op.drop_table("orders")
    op.drop_table("gift_cards")
    op.drop_table("accounts")
    op.drop_table("retailers")
    op.execute("DROP TABLE IF EXISTS alembic_version")