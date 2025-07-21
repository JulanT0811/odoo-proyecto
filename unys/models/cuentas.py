# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta 

class UnysCuenta(models.Model):
    _name = 'unys.cuenta'
    _description = 'Modelo para manejo de cuentas de UNYS'
    _rec_name = 'numero_cuenta'
    _log_access = False 

    numero_cuenta = fields.Char('Número de Cuenta', readonly=True, required=False, copy=False)
    socio_id = fields.Many2one('res.partner', string='Socio', required=True)
    fecha_apertura = fields.Date('Fecha de Apertura', default=fields.Date.today, required=True)
    saldo_actual = fields.Float('Saldo Actual', default=0.0, required=True)
    estado = fields.Selection([('active', 'Activa'),
                               ('close', 'Cerrada'),
                               ('suspended', 'Suspendida')],
                              string='Estado', default='active', required=True)

    tipo_cuenta = fields.Selection([('ahorros', 'Ahorro'),
                                    ('corriente', 'Corriente')],
                                   string='Tipo de Cuenta', default='ahorros', required=True) 
    user_id = fields.Many2one('res.users', string='Usuario', compute='_compute_user_id', store=True)

    _sql_constraints = [
        ('numero_cuenta_unique', 'unique(numero_cuenta)', '¡El número de cuenta debe ser único!'),
    ]

    @api.depends('socio_id')
    def _compute_user_id(self):
        for record in self:
            if record.socio_id:
                user = self.env['res.users'].search([('partner_id', '=', record.socio_id.id)], limit=1)
                record.user_id = user.id
            else:
                record.user_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('socio_id') and not vals.get('user_id'):
                partner = self.env['res.partner'].browse(vals['socio_id'])
                user = self.env['res.users'].search([('partner_id', '=', partner.id)], limit=1)
                if user:
                    vals['user_id'] = user.id
                else:
                    pass 

           
            if not vals.get('numero_cuenta') or vals.get('numero_cuenta') == _('Nuevo'):
                vals['numero_cuenta'] = self.env['ir.sequence'].next_by_code('unys.cuenta') or _('New')
        return super().create(vals_list)

    def write(self, vals):
       
        if 'numero_cuenta' in vals and vals['numero_cuenta'] != self.numero_cuenta:
            raise ValidationError(_("No se puede modificar el número de cuenta directamente."))
        return super().write(vals)

class UnysMovimientos(models.Model):
    _name = 'unys.movimientos'
    _description = 'Modelo para manejo de movimientos de cuentas en UNYS'
    _order = 'fecha_movimiento desc, id desc'

    cuenta_id = fields.Many2one('unys.cuenta', string='Cuenta', required=True)
    tipo_movimiento = fields.Selection([('deposito', 'Depósito'),
                                        ('retiro', 'Retiro'),
                                        ('tentrada', 'Transferencia Entrada'),
                                        ('tsalida', 'Transferencia Salida')],
                                       string='Tipo de Movimiento', required=True)
    monto = fields.Float('Monto', required=True)
    fecha_movimiento = fields.Datetime('Fecha de Movimiento', default=fields.Datetime.now, required=True)
    descripcion = fields.Text('Descripción')
    saldo_post_movimiento = fields.Float('Saldo Post Movimiento', readonly=True)

    socio_id = fields.Many2one(related='cuenta_id.socio_id', string='Socio', store=True, readonly=True)

    @api.constrains('monto')
    def _check_monto_positivo(self):
        for record in self:
            if record.monto <= 0:
                raise ValidationError(_("El monto del movimiento debe ser un valor positivo."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
     
            cuenta = record.cuenta_id
            if record.tipo_movimiento == 'deposito':
                cuenta.saldo_actual += record.monto
            elif record.tipo_movimiento == 'retiro':
                if cuenta.saldo_actual < record.monto:
                    raise ValidationError(_("Saldo insuficiente para realizar el retiro."))
                cuenta.saldo_actual -= record.monto
       
            record.saldo_post_movimiento = cuenta.saldo_actual
        return records

    def write(self, vals):
        
        return super().write(vals)

class UnysOperaciones(models.TransientModel):
    _name = 'unys.operaciones'
    _description = 'Modelo para manejo de operaciones de cuentas (transient)'

    cuenta_id = fields.Many2one('unys.cuenta', string='Cuenta', required=True)
    socio = fields.Many2one(related='cuenta_id.socio_id', string='Socio', readonly=True)
    saldo = fields.Float(related='cuenta_id.saldo_actual', string='Saldo Actual', readonly=True)
    tipo_operacion = fields.Selection([('deposito', 'Depósito'),
                                       ('retiro', 'Retiro')],
                                      string='Tipo de Operación', required=True)
    monto = fields.Float('Monto', required=True)
    descripcion = fields.Char(string='Descripción')
    fecha_operacion = fields.Datetime('Fecha de Operación', default=fields.Datetime.now, required=True)

    @api.constrains('monto')
    def _check_monto_positivo(self):
        for record in self:
            if record.monto <= 0:
                raise ValidationError(_("El monto de la operación debe ser un valor positivo."))

    def realizar_operacion(self):
        self.ensure_one()
        if self.tipo_operacion == 'deposito':
            self.env['unys.movimientos'].create({
                'cuenta_id': self.cuenta_id.id,
                'tipo_movimiento': 'deposito',
                'monto': self.monto,
                'descripcion': self.descripcion,
                'fecha_movimiento': self.fecha_operacion,
            })
        elif self.tipo_operacion == 'retiro':
            if self.cuenta_id.saldo_actual < self.monto:
                raise ValidationError(_("Saldo insuficiente en la cuenta para realizar el retiro."))
            self.env['unys.movimientos'].create({
                'cuenta_id': self.cuenta_id.id,
                'tipo_movimiento': 'retiro',
                'monto': self.monto,
                'descripcion': self.descripcion,
                'fecha_movimiento': self.fecha_operacion,
            })
        return {'type': 'ir.actions.act_window_close'}


class UnysTransferencias(models.Model):
    _name = 'unys.transferencias'
    _description = 'Modelo para manejo de transferencias entre cuentas en UNYS'
    _order = 'fecha_transferencia desc, id desc' 

    cuenta_origen_id = fields.Many2one('unys.cuenta', string='Cuenta de Origen', required=True)
    cuenta_destino_id = fields.Many2one('unys.cuenta', string='Cuenta Destino', required=True)
    codigo_transferencia = fields.Char('Código de Transferencia', readonly=True, required=False, copy=False)
    monto = fields.Float('Monto', required=True)
    fecha_transferencia = fields.Datetime('Fecha de Transferencia', default=fields.Datetime.now, required=True)
    estado = fields.Selection([('pendiente', 'Pendiente'),
                               ('completado', 'Completado'),
                               ('cancelada', 'Cancelada')],
                              string='Estado', default='pendiente', required=True)
    referencia = fields.Char(string='Referencia')

    _sql_constraints = [
        ('codigo_transferencia_unique', 'unique(codigo_transferencia)', '¡El código de transferencia debe ser único!'),
        ('cuentas_diferentes', 'CHECK(cuenta_origen_id != cuenta_destino_id)', '¡La cuenta de origen y destino deben ser diferentes!'),
    ]

    @api.constrains('monto')
    def _check_monto_positivo(self):
        for record in self:
            if record.monto <= 0:
                raise ValidationError(_("El monto de la transferencia debe ser un valor positivo."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('codigo_transferencia', _('New')) == _('New'):
               
                vals['codigo_transferencia'] = self.env['ir.sequence'].next_by_code('unys.transferencia') or _('New')
        
        records = super().create(vals_list)
        
        for record in records:
            
            cuenta_origen = record.cuenta_origen_id
            cuenta_destino = record.cuenta_destino_id

            if cuenta_origen.saldo_actual < record.monto:
                raise ValidationError(_("Saldo insuficiente en la cuenta de origen para la transferencia."))

     
            cuenta_origen.saldo_actual -= record.monto
            cuenta_destino.saldo_actual += record.monto

          
            self.env['unys.movimientos'].create({
                'cuenta_id': cuenta_origen.id,
                'tipo_movimiento': 'tsalida',
                'monto': record.monto,
                'descripcion': _('Transferencia a %s (Ref: %s)') % (cuenta_destino.numero_cuenta, record.referencia or record.codigo_transferencia),
                'fecha_movimiento': record.fecha_transferencia,
            })

            self.env['unys.movimientos'].create({
                'cuenta_id': cuenta_destino.id,
                'tipo_movimiento': 'tentrada',
                'monto': record.monto,
                'descripcion': _('Transferencia de %s (Ref: %s)') % (cuenta_origen.numero_cuenta, record.referencia or record.codigo_transferencia),
                'fecha_movimiento': record.fecha_transferencia,
            })
            record.estado = 'completado' 

        return records

class UnysPrestamos(models.Model):
    _name = 'unys.prestamos'
    _description = 'Modelo para la gestión de préstamos en UNYS'
    _order = 'fecha_solicitud desc, id desc'

    name = fields.Char('Número de Préstamo', readonly=True, required=True, copy=False, default=lambda self: _('New'))
    cuenta_id = fields.Many2one('unys.cuenta', string='Cuenta', required=True)
    socio_id = fields.Many2one(related='cuenta_id.socio_id', string='Socio', store=True, readonly=True)
    monto_solicitado = fields.Float('Monto Solicitado', required=True)
    fecha_solicitud = fields.Date('Fecha de Solicitud', default=fields.Date.today, required=True)
    estado = fields.Selection([
        ('solicitado', 'Solicitado'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('desembolsado', 'Desembolsado'),
        ('pagado', 'Pagado'),
    ], string='Estado', default='solicitado', required=True)
    monto_aprobado = fields.Float('Monto Aprobado')
    fecha_aprobacion = fields.Date('Fecha de Aprobación')
    fecha_vencimiento = fields.Date('Fecha de Vencimiento')
    interes = fields.Float('Tasa de Interés (%)')
    cuotas = fields.Integer('Número de Cuotas')
    saldo_pendiente = fields.Float('Saldo Pendiente', compute='_compute_saldo_pendiente', store=True)
    descripcion = fields.Text('Descripción')

    @api.constrains('monto_solicitado', 'monto_aprobado')
    def _check_monto_positivo(self):
        for record in self:
            if record.monto_solicitado <= 0:
                raise ValidationError(_("El monto solicitado debe ser un valor positivo."))
            if record.monto_aprobado < 0:
                raise ValidationError(_("El monto aprobado no puede ser negativo."))

    @api.depends('monto_aprobado', 'cuotas') 
    def _compute_saldo_pendiente(self):
        for record in self:
           
            record.saldo_pendiente = record.monto_aprobado

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('unys.prestamos') or _('New')
        return super().create(vals_list)

    def action_aprobar_prestamo(self):
        self.ensure_one()
        if self.estado == 'solicitado':
            self.write({
                'estado': 'aprobado',
                'monto_aprobado': self.monto_solicitado,
                'fecha_aprobacion': fields.Date.today(),
                'fecha_vencimiento': fields.Date.today() + relativedelta(months=self.cuotas), 
            })
           
        else:
            raise ValidationError(_("El préstamo no puede ser aprobado en su estado actual."))

    def action_rechazar_prestamo(self):
        self.ensure_one()
        if self.estado == 'solicitado':
            self.write({'estado': 'rechazado'})
        else:
            raise ValidationError(_("El préstamo no puede ser rechazado en su estado actual."))

    def action_desembolsar_prestamo(self):
        self.ensure_one()
        if self.estado == 'aprobado' and self.monto_aprobado > 0:
            self.cuenta_id.saldo_actual += self.monto_aprobado
            self.env['unys.movimientos'].create({
                'cuenta_id': self.cuenta_id.id,
                'tipo_movimiento': 'deposito',
                'monto': self.monto_aprobado,
                'descripcion': _('Desembolso de préstamo %s') % self.name,
                'fecha_movimiento': fields.Datetime.now(),
            })
            self.write({'estado': 'desembolsado'})
        else:
            raise ValidationError(_("El préstamo debe estar aprobado y tener un monto aprobado para ser desembolsado."))

    def action_marcar_pagado(self):
        self.ensure_one()
        if self.estado == 'desembolsado' and self.saldo_pendiente <= 0:
            self.write({'estado': 'pagado'})
        else:
            raise ValidationError(_("El préstamo debe estar desembolsado y el saldo pendiente debe ser cero para marcarlo como pagado."))
