# -*- coding: utf-8 -*-
##############################################################################
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013-Present Acespritech Solutions Pvt. Ltd. (<http://acespritech.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import osv, fields



class res_partner(osv.osv):
    _inherit = "res.partner"
    
    _columns = {
        'currency_id': fields.many2one('res.currency', 'Currency', required=False),#probuse
        'parent_partner_id':fields.many2one('res.partner', 'Parent Partner'),
        'parent_acc_no': fields.char('Parent Account Number',readonly=True),
        'child_acc_no': fields.char('Child Account Number',readonly=True),
        'cust_srv_no': fields.char('Customer Service No.', size=128),
        'cust_status': fields.selection([('active', 'Active'), ('suspended', 'Suspended')\
                                         , ('terminated', 'Terminated')], 'Customer Status',
                                        required=False),
    }

#     '''For Account Number Auto Generation.'''
#     def _get_currency(self, cr, uid, context=None):#probuse
#         u = self.pool.get('res.users').browse(cr, uid, [uid], context=context)#probuse
#         if u:#probuse
#             c = u[0].company_id.currency_id.id#probuse
#             return c#probuse
#         else:#probuse
#             return False#probuse
#     
#     _defaults = {#probuse
#         'currency_id': _get_currency,#probuse
#     }#probuse
    
    def create(self, cr, uid, datas, context=None):
        seq_obj = self.pool.get('ir.sequence')
        data_obj = self.pool.get('ir.model.data')
        parent_seq_id = data_obj.get_object_reference(cr, uid, 'ng_internal_requistion_extend', 'sequence_account_no_partner')[1]
        child_seq_id = data_obj.get_object_reference(cr, uid, 'ng_internal_requistion_extend', 'sequence_sub_account_no_partner')[1]
        if datas.get('customer', False) and datas['customer']:
            if datas.get('parent_partner_id'):#todo: remove this condtion since field is hide from view.
                parent_acc_no = self.browse(cr, uid, datas['parent_partner_id']).parent_acc_no
            else:
                parent_acc_no = seq_obj.get(cr, uid, 'partner.account.number')
            datas.update({'parent_acc_no':parent_acc_no})
#        old_partner_ids = self.search(cr, uid, [('parent_acc_no', '=', parent_acc_no)])#probuse19feb 
#        if old_partner_ids:#probuse19feb 
#            seq_obj._alter_sequence(cr, child_seq_id, 1, (len(old_partner_ids) + 1))#probuse19feb 
#        else:#probuse19feb 
#            seq_obj._alter_sequence(cr, child_seq_id, 1, 1)#probuse19feb 
#        datas.update({'child_acc_no': seq_obj.get(cr, uid, 'sub.partner.account.number')})#probuse19feb 
        partner_id = super(res_partner, self).create(cr, uid, datas, context)
        return partner_id

    def write(self, cr, uid, ids, vals, context=None):
        if not ids:
            return True
        data = self.browse(cr, uid, ids, context)[0]
        seq_obj = self.pool.get('ir.sequence')
        if vals.get('customer', False) and vals['customer'] and not vals.get('parent_acc_no', False) and not data.parent_acc_no:
            parent_acc_no = seq_obj.get(cr, uid, 'partner.account.number')
            vals.update({'parent_acc_no':parent_acc_no})
#        if vals.has_key('parent_partner_id'):#todo: remove this condtion since field is hide from view.
#            parent_acc_no = ''
#            if vals.get('parent_partner_id', False):
#                parent_acc_no = self.browse(cr, uid, vals['parent_partner_id']).parent_acc_no
#            vals.update({'parent_acc_no':parent_acc_no})
        return super(res_partner, self).write(cr, uid, ids, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}
        return super(res_partner, self).copy(cr, uid, id, default, context=context)

    def name_get(self, cursor, user, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            return []
        res = []
        data_partner = self.pool.get('res.partner').browse(cursor, user, ids, context=context)
        for partner in data_partner:
            if partner.customer:
                name = (partner.name).encode('utf-8') + ' '
                if partner.parent_acc_no:
                    name += str(partner.parent_acc_no) + ' '
                if partner.child_acc_no:
                    name += str(partner.child_acc_no)
                res.append((partner.id, name))
            else:
                res.append((partner.id, partner.name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        if name:
            ids = self.search(cr, uid, ['|', ('parent_acc_no', operator, name), ('child_acc_no', operator, name) ] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})

    def onchange_parent_partner(self, cr, uid, ids, parent_partner, context=None):
        value = {'parent_acc_no': ''}
        if parent_partner:
            parent_acc_no = self.browse(cr, uid, parent_partner, context=context).parent_acc_no
            value = {'parent_acc_no': parent_acc_no}
        return {'value': value}

    def _display_address(self, cr, uid, address, without_company=False, context=None):
        ''' for coutry wise ,address.country_id and address.country_id.address_format '''
        address_format = "%(street)s\n%(street2)s\n%(city)s %(state_name)s %(zip)s\n%(country_name)s"
        args = {
            'state_code': address.state_id and address.state_id.code or '',
            'state_name': address.state_id and address.state_id.name or '',
            'country_code': address.country_id and address.country_id.code or '',
            'country_name': address.country_id and address.country_id.name or '',
            'company_name': address.parent_id and address.parent_id.name or '',
        }
        for field in self._address_fields(cr, uid, context=context):
            args[field] = getattr(address, field) or ''
        if without_company:
            args['company_name'] = ''
        elif address.parent_id:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args


res_partner()
