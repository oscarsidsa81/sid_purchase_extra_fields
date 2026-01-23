from odoo import api, SUPERUSER_ID

def post_init_fill_sid_has_po_delay(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    POL = env["purchase.order.line"].sudo()
    SOL = env["sale.order.line"].sudo()

    lines = POL.search([("sale_line_id", "!=", False)])
    if not lines:
        return

    # Forzar recompute store: invalidar y tocar write vacío en un campo inocuo NO sirve.
    # En su lugar: recalcular por python llamando al compute y luego escribir el valor.
    lines._compute_pending_line()
    lines._compute_sid_po_line_delay()
    # Escribe en DB para garantizar store (porque compute store no se escribe solo si llamas al compute a mano)
    for l in lines:
        l.write({
            "pending_line": l.pending_line,
            "sid_po_line_delay": l.sid_po_line_delay,
        })

    linked_sale_line_ids = set(lines.mapped("sale_line_id").ids)
    if not linked_sale_line_ids:
        return

    late_sale_line_ids = set(lines.filtered(
        lambda l: l.sid_po_line_delay in ("1_week_del","2_week_del","4_week_del","more_del")
    ).mapped("sale_line_id").ids)

    linked_sale_lines = SOL.search([("id", "in", list(linked_sale_line_ids))])
    if late_sale_line_ids:
        linked_sale_lines.filtered(lambda s: s.id in late_sale_line_ids).write({"sid_has_po_delay": True})
    linked_sale_lines.filtered(lambda s: s.id not in late_sale_line_ids).write({"sid_has_po_delay": False})
