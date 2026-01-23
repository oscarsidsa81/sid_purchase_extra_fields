# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sid_date_planned = fields.Char(
        string="Fecha de recepción",
        compute="_compute_sid_date_planned",
        store=True,
        readonly=True,
        help="Texto con la fecha prevista de recepción (derivada de date_planned).",
    )
    # Copia almacenada del HS code para la línea
    sid_hs_code_po_line = fields.Char (
        string="HS Code (po)",
        related="sid_hs_code",
        store=True,
        readonly=False,
        help="HS Code de la línea de Compra",
    )

    sid_hs_code = fields.Char (
        string="HS Code (Product)",
        related="product_id.hs_code",
        store=False,
        readonly=False,
        help="HS Code del Producto",
    )

    sid_order_id_purchase_order_line_count = fields.Integer(
        string="Order Reference count",
        compute="_compute_sid_order_line_count",
        store=False,
        readonly=True,
        help="Número de líneas del pedido.",
    )

    sid_parcial = fields.Boolean(
        string="Recepción parcial",
        default=False,
        help="Marca manual para indicar que la recepción será/ha sido parcial.",
    )

    sid_pendiente = fields.Monetary(
        string="Base pendiente",
        currency_field="currency_id",
        compute="_compute_sid_pendiente",
        store=True,
        readonly=True,
        help="Suma de (qty_to_invoice * price_unit) de las líneas.",
    )

    sid_regularizado = fields.Boolean(
        string="Regularizado sin Factura",
        default=False,
        help=(
            "Regularizado sin factura. Se utiliza cuando el proveedor no envía una factura "
            "para completar el pedido. Permite el uso del botón 'Revisar Facturación' en líneas de compra."
        ),
    )

    sid_total = fields.Monetary(
        string="Base facturada",
        currency_field="currency_id",
        compute="_compute_sid_total",
        store=True,
        readonly=True,
        help="Suma de (qty_invoiced * price_unit) de las líneas.",
    )

    # --------------------
    # Computes
    # --------------------

    @api.depends("order_line.date_planned", "date_planned")
    def _compute_sid_date_planned(self):
        """Replica el comportamiento del campo Studio: si existe date_planned en el pedido,
        úsalo; si no, usa la mínima date_planned de las líneas.
        """
        for order in self:
            dt = getattr(order, "date_planned", False) or False
            if not dt and order.order_line:
                dates = order.order_line.mapped("date_planned")
                dates = [d for d in dates if d]
                dt = min(dates) if dates else False
            if dt:
                # dt es datetime en Odoo; fields.Datetime.to_string produce 'YYYY-MM-DD HH:MM:SS'
                order.sid_date_planned = fields.Datetime.to_string(dt)
            else:
                order.sid_date_planned = False

    @api.depends("order_line")
    def _compute_sid_order_line_count(self):
        for order in self:
            order.sid_order_id_purchase_order_line_count = len(order.order_line)

    @api.depends("order_line.qty_to_invoice", "order_line.price_unit", "order_line.currency_id")
    def _compute_sid_pendiente(self):
        for order in self:
            total = 0.0
            for line in order.order_line:
                total += (line.qty_to_invoice or 0.0) * (line.price_unit or 0.0)
            order.sid_pendiente = total

    @api.depends("order_line.qty_invoiced", "order_line.price_unit", "order_line.currency_id")
    def _compute_sid_total(self):
        for order in self:
            total = 0.0
            for line in order.order_line:
                total += (line.qty_invoiced or 0.0) * (line.price_unit or 0.0)
            order.sid_total = total
