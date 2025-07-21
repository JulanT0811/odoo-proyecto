# -*- coding: utf-8 -*-
# from odoo import http


# class Unys(http.Controller):
#     @http.route('/unys/unys', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/unys/unys/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('unys.listing', {
#             'root': '/unys/unys',
#             'objects': http.request.env['unys.unys'].search([]),
#         })

#     @http.route('/unys/unys/objects/<model("unys.unys"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('unys.object', {
#             'object': obj
#         })

