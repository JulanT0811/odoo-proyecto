# -*- coding: utf-8 -*-
{
    'name': "UNYS",

    'summary': "Gestión de Cuentas, Operaciones y Transferencias para Socios UNYS",
   

    'description': """
        Módulo diseñado para la gestión integral de cuentas de socios,
        registros de operaciones (depósitos, retiros) y transferencias
        dentro del sistema UNYS. Permite administrar saldos, tipos de cuenta
        y estados, con roles específicos para Cajeros y Socios.
    """,


    'author': "XD",
    'website': "https://www.tu_empresa.com", 

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list. 'Accounting' or 'Human Resources' might be more specific
    # depending on the actual purpose, but 'Customizations' is fine for generic custom modules.
    'category': 'Accounting/Accounting', # O 'Customizations', si es más general
    'version': '1.0', 

    
    'depends': [
        'base', 
    ],

    # always loaded
    'data': [
        
        'security/unys_groups.xml',
        'security/ir.model.access.csv',
        'views/views_unys_cuenta.xml',
        'data/sequence_data.xml', 
        'data/users_data.xml',
        'views/view_unys_operaciones.xml',
        # 'views/views.xml', 
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml', 
    ],

    'installable': True,
    'application': True, 
    'auto_install': False,
    'license': 'LGPL-3', 
}