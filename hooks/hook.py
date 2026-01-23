from odoo import api, SUPERUSER_ID

def post_init_fill_sid_has_po_delay(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    POL = env["purchase.order.line"].sudo()
    SOL = env["sale.order.line"].sudo()

    lines = POL.search([("sale_line_id", "!=", False)])
    if not lines:
        return

    # 1) Recompute: primero pending_line, luego sid_po_line_delay
    lines.invalidate_cache(fnames=["pending_line"])
    env.add_to_compute(POL._fields["pending_line"], lines)
    env.recompute()

    lines.invalidate_cache(fnames=["sid_po_line_delay"])
    env.add_to_compute(POL._fields["sid_po_line_delay"], lines)
    env.recompute()

    # 2) Sale lines enlazadas
    linked_sale_line_ids = set(lines.mapped("sale_line_id").ids)
    if not linked_sale_line_ids:
        return

    late_lines = lines.filtered(lambda l: l.sid_po_line_delay in ("1_week_del","2_week_del","4_week_del","more_del"))
    late_sale_line_ids = set(late_lines.mapped("sale_line_id").ids)

    linked_sale_lines = SOL.search([("id", "in", list(linked_sale_line_ids))])

    if late_sale_line_ids:
        linked_sale_lines.filtered(lambda s: s.id in late_sale_line_ids).write({"sid_has_po_delay": True})
    linked_sale_lines.filtered(lambda s: s.id not in late_sale_line_ids).write({"sid_has_po_delay": False})
