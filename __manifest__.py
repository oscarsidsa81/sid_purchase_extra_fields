# -*- coding: utf-8 -*-
{
    "name": "SIDSA - Purchase Extra Fields",
    "version": "15.0.1.0.0",
    "category": "Purchases",
    "summary": "Campos extra en pedidos de compra y líneas (HS, pendientes, pesos, bases facturadas, etc.).",
    "author": "SIDSA / Custom",
    "license": "LGPL-3",
    "depends": ["purchase", "sale_management", "delivery"],
    "data": [
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
