# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    # HS code del producto (delivery)
    sid_hs_code = fields.Char(
        string="Code HS",
        related="product_id.hs_code",
        store=False,
        readonly=True,
        help="z.HS Code",
    )

    # Copia almacenada del HS code para la línea
    sid_hs_code_po_line = fields.Char(
        string="HS Code (po)",
        related="sid_hs_code",
        store=True,
        readonly=False,
        help="HS Code",
    )

    sid_invoice = fields.Selection(
        selection=[
            ("facturar", "Facturar"),
            ("abono", "Abono"),
            ("facturado", "Facturado"),
            ("pendiente", "Pendiente"),
        ],
        string="Facturación",
        compute="_compute_sid_invoice",
        store=True,
        readonly=True,
    )

    supplier_country = fields.Many2one(
        "res.country",
        string="País Origen",
        related="order_id.partner_id.country_id",
        store=True,
        readonly=True,
    )

    pending_line = fields.Selection(
        selection=[
            ("true", "Sí"),
            ("false", "No"),
        ],
        string="Pendiente",
        compute="_compute_pending_line",
        store=True,
        readonly=True,
    )

    sid_qty_inv_sale = fields.Float(
        string="Cantidad Facturada Venta",
        related="sale_line_id.qty_invoiced",
        store=True,
        readonly=True,
    )

    sid_po_line_delay = fields.Selection(
        selection=[
            ("1_week_del", "Retraso 1 semana"),
            ("2_week_del", "Retraso 1-2 semanas"),
            ("4_week_del", "Retraso 4 semanas"),
            ("more_del", "Retraso + de un mes"),
            ("2_days", "Quedan 2 días"),
            ("7_days", "Quedan 7 días"),
            ("14_days", "Quedan 14 días"),
            ("30_days", "Quedan 30 días"),
            ("sin_ret", "+30 días"),
        ],
        string="Retraso por ítem",
        compute="_compute_sid_po_line_delay",
        store=True,
        readonly=True,
    )

    sid_sale_date = fields.Datetime(
        string="Fecha Venta",
        related="sale_line_id.calculated_date",
        store=True,
        readonly=True,
        help="Fecha Contrato Venta",
    )

    sid_unit_price_difference = fields.Monetary(
        string="Balance Venta-Compra",
        currency_field="currency_id",
        store=True,
        readonly=False,
        help="Campo legado (sin cómputo en la exportación).",
    )

    sid_unit_weight_product = fields.Float(
        string="Peso unitario (producto)",
        related="product_id.weight",
        store=False,
        readonly=True,
    )

    sid_unit_weight_po_line = fields.Float(
        string="Peso Unitario (po)",
        related="sid_unit_weight_product",
        store=True,
        readonly=False,
    )

    sid_weight_subtotal = fields.Float(
        string="Peso Total",
        compute="_compute_sid_weight_subtotal",
        store=True,
        readonly=True,
    )

    # --------------------
    # Computes
    # --------------------

    @api.depends("contract_date", "estimated_date", "pending_line")
    def _compute_sid_po_line_delay(self):
        """
        Basamos el cálculo en las fechas funcionales del módulo de compras:
        - contract_date (si existe / si está informada)
        - estimated_date (alternativa)
        y solo tiene sentido si la línea está pendiente.
        """
        today = fields.Date.context_today(self)

        for line in self:
            if line.pending_line != "true":
                line.sid_po_line_delay = False
                continue

            # Prioridad: contractual > estimada
            base_date = line.contract_date or line.estimated_date
            if not base_date:
                line.sid_po_line_delay = False
                continue

            planned_date = fields.Date.to_date(base_date)
            diff_days = (planned_date - today).days

            if diff_days <= -31:
                line.sid_po_line_delay = "more_del"
            elif diff_days <= -28:
                line.sid_po_line_delay = "4_week_del"
            elif diff_days <= -14:
                line.sid_po_line_delay = "2_week_del"
            elif diff_days <= -7:
                line.sid_po_line_delay = "1_week_del"
            elif diff_days <= 2:
                line.sid_po_line_delay = "2_days"
            elif diff_days <= 7:
                line.sid_po_line_delay = "7_days"
            elif diff_days <= 14:
                line.sid_po_line_delay = "14_days"
            elif diff_days <= 30:
                line.sid_po_line_delay = "30_days"
            else:
                line.sid_po_line_delay = "sin_ret"

    def write(self, vals):
        """
        Ojo: pending_line es compute/store, así que NO suele venir en vals.
        Para no perder sincronizaciones, trackeamos también los campos que
        pueden cambiar pending_line o la fecha base del cálculo.
        """
        track_keys = {
            "sid_po_line_delay",  # por si alguien lo fuerza (poco probable, pero consistente)
            "contract_date",
            "estimated_date",
            # pending_line depende de estos
            "product_qty",
            "qty_received",
        }
        track = any(k in vals for k in track_keys)

        before = {}
        if track:
            for pol in self:
                before[pol.id] = pol.sid_po_line_delay

        res = super().write(vals)

        if track:
            self._sync_sale_delay_flag(before_map=before)

        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._sync_sale_delay_flag(before_map={})
        return lines

    def _sync_sale_delay_flag(self, before_map):
        """
        Sincroniza en sale.order.line el boolean sid_has_po_delay:
        - True si sid_po_line_delay indica retraso vencido
        - False en caso contrario
        """
        SaleLine = self.env["sale.order.line"].sudo()
        updates = {}  # sale_line_id -> bool

        for pol in self:
            old = before_map.get(pol.id, None)
            new = pol.sid_po_line_delay

            if old is not None and old == new:
                continue

            sale_line = getattr(pol, "sale_line_id", False)
            if not sale_line:
                continue

            delay_is_late = new in ("1_week_del", "2_week_del", "4_week_del", "more_del")
            updates[sale_line.id] = delay_is_late

        if not updates:
            return

        for sale_line_id, flag in updates.items():
            SaleLine.browse(sale_line_id).write({"sid_has_po_delay": flag})

    @api.depends("qty_to_invoice", "qty_received", "product_qty", "qty_invoiced")
    def _compute_sid_invoice(self):
        for line in self:
            qty_to_invoice = round(line.qty_to_invoice or 0.0, 2)
            qty_invoiced = round(line.qty_invoiced or 0.0, 2)
            qty_received = round(line.qty_received or 0.0, 2)
            product_qty = round(line.product_qty or 0.0, 2)

            if qty_to_invoice > 0:
                line.sid_invoice = "facturar"
            elif qty_to_invoice < 0:
                line.sid_invoice = "abono"
            elif qty_invoiced == qty_received and qty_invoiced >= product_qty:
                line.sid_invoice = "facturado"
            else:
                line.sid_invoice = "pendiente"

    @api.depends("product_qty", "qty_received")
    def _compute_pending_line(self):
        for line in self:
            product_qty = round(line.product_qty or 0.0, 2)
            qty_received = round(line.qty_received or 0.0, 2)
            line.pending_line = "true" if product_qty > qty_received else "false"

    @api.depends("qty_received", "product_qty", "sid_unit_weight_po_line")
    def _compute_sid_weight_subtotal(self):
        for line in self:
            qty_received = line.qty_received or 0.0
            product_qty = line.product_qty or 0.0
            unit_w = line.sid_unit_weight_po_line or 0.0
            qty = qty_received if qty_received > product_qty else product_qty
            line.sid_weight_subtotal = unit_w * qty
