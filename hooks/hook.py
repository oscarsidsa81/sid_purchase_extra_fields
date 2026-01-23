# hooks.py
from odoo import api, SUPERUSER_ID

def post_init_fill_sid_has_po_delay(cr, registry):
    """
    Al instalar el módulo:
    - fuerza recompute del delay en purchase.order.line (store=True)
    - rellena sid_has_po_delay en sale.order.line enlazadas
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    POL = env["purchase.order.line"].sudo()
    SOL = env["sale.order.line"].sudo()

    # 1) Recompute de sid_po_line_delay para que haya valores correctos
    # (incluye su depends: contract_date/estimated_date/pending_line)
    lines = POL.search([("sale_line_id", "!=", False)])
    if lines:
        # En Odoo 15, esto suele ser suficiente para recalcular campos store en batch.
        # invalidar + recompute evita depender de write().
        lines.invalidate_cache(fnames=["sid_po_line_delay", "pending_line"])
        env.add_to_compute(POL._fields["sid_po_line_delay"], lines)
        env.add_to_compute(POL._fields["pending_line"], lines)
        env.recompute()

    # 2) Construir el set de sale_line_ids con retraso vencido
    late_lines = POL.search([
        ("sale_line_id", "!=", False),
        ("sid_po_line_delay", "in", ("1_week_del", "2_week_del", "4_week_del", "more_del")),
    ])
    late_sale_line_ids = set(late_lines.mapped("sale_line_id").ids)

    # 3) Actualizar sale.order.line en 2 writes (batch)
    #    - True para las que están en late_sale_line_ids
    #    - False para las que tengan alguna purchase line enlazada pero no estén late
    linked_sale_lines = SOL.search([("id", "in", list(set(lines.mapped("sale_line_id").ids)))])
    if linked_sale_lines:
        if late_sale_line_ids:
            linked_sale_lines.filtered(lambda s: s.id in late_sale_line_ids).write({"sid_has_po_delay": True})
        linked_sale_lines.filtered(lambda s: s.id not in late_sale_line_ids).write({"sid_has_po_delay": False})
