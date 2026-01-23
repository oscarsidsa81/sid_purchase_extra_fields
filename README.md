# SIDSA - Purchase Extra Fields (Odoo 15)

Este módulo recrea en código (Python) los **campos Studio** exportados en `sid_purchase_extra_fields`
para **Pedidos de compra** (`purchase.order`) y **Líneas de pedido de compra** (`purchase.order.line`).

## Qué incluye

### En `purchase.order`

- `sid_date_planned` (Char, almacenado, solo lectura): texto con la fecha prevista de recepción derivada de `date_planned` (o, si no existe en el pedido, la mínima `date_planned` de sus líneas).
- `sid_order_id_purchase_order_line_count` (Integer, no almacenado): contador de líneas.
- `sid_parcial` (Boolean, almacenado): indicador manual de recepción parcial.
- `sid_pendiente` (Monetary, almacenado, solo lectura): suma de `qty_to_invoice * price_unit` en líneas.
- `sid_regularizado` (Boolean, almacenado): “Regularizado sin factura”.
- `sid_total` (Monetary, almacenado, solo lectura): suma de `qty_invoiced * price_unit` en líneas.

### En `purchase.order.line`

- `sid_hs_code` (Char, related, no store): `product_id.hs_code` (depende de `delivery`).
- `sid_hs_code_po_line` (Char, related, **store**): copia almacenada del HS para facilitar reporting/búsqueda.
- `sid_invoice` (Selection, compute, store): estado de facturación con la misma lógica de Studio.
- `sid_pais` (Many2one, related, store): país del proveedor (`order_id.partner_id.country_id`).
- `sid_pendiente` (Selection, compute, store): marca si `product_qty > qty_received`.
- `sid_qty_inv_sale` (Float, related, store): `sale_line_id.qty_invoiced`.
- `sid_sale_date` (Datetime, related, store): `sale_line_id.calculated_date`.
- `sid_unit_weight` (Float, related, store): `product_id.weight`.
- `sid_unit_weight_po_line` (Float, related, store): copia almacenada del peso unitario.
- `sid_weight_subtotal` (Float, compute, store): peso total con la regla de Studio (usa `qty_received` si supera `product_qty`).

> Nota: `sid_retraso` y `sid_unit_price_difference` aparecen en la exportación sin cálculo asociado.
> En este módulo se crean como campos “legado” (almacenados) para que no se pierdan, pero su lógica
> debe implementarse si procede (o rellenarse por procesos externos).

## Dependencias

- `purchase`
- `sale_management` (por `sale_line_id`)
- `delivery` (por `product_id.hs_code`)

## Instalación

1. Copia la carpeta `sid_purchase_extra_fields` a tu ruta de addons.
2. Actualiza la lista de apps.
3. Instala **SIDSA - Purchase Extra Fields**.

## Vistas incluidas

- Se hereda el formulario de pedido de compra y se añaden:
  - Un bloque “Campos extra SIDSA” en “Other Information”.
  - Columnas adicionales en el árbol de líneas del pedido.

## Verificación (grado)

- **Respaldado por fuentes reales (exportación Studio):** definición de campos, `store`, `related`, y lógica de compute replicada tal cual en `sid_invoice`, `sid_weight_subtotal`, `sid_pendiente`, y bases de pedido (`sid_pendiente`, `sid_total`).
- **Parcialmente respaldado:** `sid_date_planned` usa `date_planned` del pedido si existe; si no, usa la mínima `date_planned` de líneas (esto es una adaptación defensiva para evitar fallos por diferencias de modelo).
- **Elaboración propia (❌):** selecciones propuestas de `sid_retraso` y ausencia de cómputo para `sid_unit_price_difference` (se crean por compatibilidad, pero su semántica exacta no consta en la exportación).

