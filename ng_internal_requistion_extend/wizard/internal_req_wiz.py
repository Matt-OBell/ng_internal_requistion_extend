# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Mattobell (<http://www.mattobell.com>)
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import time

from osv import osv,fields
from tools.translate import _

class internal_req_po_split(osv.osv_memory):
    _name = "po.split.wizard"
    
    def test_lines_po_state(self, cr, uid, ids):
        for ir in self.pool.get('internal.requisition').browse(cr, uid, ids):
            for line in ir.line_ids:
                if line.state in  ('assigned','done','cancel'):
                    continue
                if not line.po_created:
                    return False
        return True
    
    def split_po(self, cr, uid, ids, context):
        self.create_all(cr, uid, ids, context)
        return {'type': 'ir.actions.act_window_close'}

    def create_all(self, cr, uid, ids, context):
        ir = context.get('active_id', False)
        ir_obj = self.pool.get('internal.requisition')
        intreq_line_obj = self.pool.get('internal.requisition.line')
        po_obj = self.pool.get('purchase.order')
        po_line_obj = self.pool.get('purchase.order.line')
        purchase_order = False
        for rec in ir_obj.browse(cr, uid, [ir], context):
            if rec.purchase_ids:
                raise osv.except_osv(_('Error !'),_('Purchase Order is already generated for this request !'))
            else:
                if rec.is_split_po:
                    comp = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
                    if comp.policy_id.max <= 1:
                        raise osv.except_osv(_('Error !'), _('You can not use Split PO Line if requisition policy at company level has max supplier set to 1.'))
                    if not comp.policy_id:
                        raise osv.except_osv(_('Error !'), _('You can not create RFQ/MR. No requisition policy set.'))
                    m = comp.policy_id.min#1
                    n = comp.policy_id.max#20
                    supplier_list = []
                    for x in rec.line_ids:
                        for sup in x.supplier_ids:
                            if sup.id not in supplier_list:
                                supplier_list.append(sup.id)
                    if len(supplier_list) < m or len(supplier_list) > n:
                        raise osv.except_osv(_('Error'), _('The state of this requisition can not be change. Please check your internal requisition policy. You should have minimum %s suppliers and maximum %s suppliers while setting suppliers in requisition line.')%(m, n))

                
                po_lines = {}
#                comp = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
#                m=comp.policy_id.min
#                n=comp.policy_id.max
#                sids = []
#                for s in rec.supplier_ids:
#                    sids.append(s.id)
#                if len(rec.supplier_ids) < m or len(rec.supplier_ids) > n:
#                    raise osv.except_osv(_('Error'), _('You can not create RFQ. Please check your requisition policy on company settings. You should have minimum %s suppliers and maximum %s suppliers')%(m, n))
                if comp.policy_id.max > 1:
                    flag = True
                    vals_mr = {
#                        'name':self.pool.get('ir.sequence').get(cr, uid, 'purchase.order.multiple'),
#                        'origin':req.requisition_id.name,
#                        'partner_id':supp.id,
#                        'partner_address_id':self.pool.get('res.partner').address_get(cr, uid, [supp.id], ['delivery'])['delivery'],
                        'date_start': rec.date_start,
                        'origin': rec.name,
#                        'pricelist_id':supp.property_product_pricelist_purchase.id,
#                        'partner_ids':[(6,0,sids)],#no need in case of split lines.
#                        'line_ids':[(0,0,line)],
                        'user_id':uid,
                        'exclusive': 'multiple',
                        'company_id':rec.company_id.id,
                        'ir_id':rec.id,
                        'is_split_po':rec.is_split_po,
                        'site_id':rec.site_id.id,#netcom
                        'type':rec.type, 
                        }
                    mr_id = self.pool.get('purchase.requisition.multiple').create(cr, uid, vals_mr, context=context)
                    ir_obj.write(cr, uid, ir, {'need_rfq': False}, context)
                    for line in rec.line_ids:

                        flag = True#11 june 2015...if all type of products are service then confirmed state will never come so had use flag.
                        for x in rec.line_ids:
                            if not x.product_id.type == 'service':
                                flag = False
                        if rec.type == 'budget_code':
                            flag1 = True
                            for y in rec.line_ids:
                                if y.product_id:
                                    flag1 = False#
                            if flag1:
                                flag = True

                        if line.state == 'confirmed' or flag == True:
#                            onchange = self.pool.get('purchase.order.line').onchange_product_id(cr, uid, [], supp.property_product_pricelist_purchase.id, line.product_id.id, line.product_qty, line.product_uom_id.id, 
#                                                         supp.id, date_order=time.strftime('%Y-%m-%d'))
#                            schedule_date = onchange.get('value',{}).get('date_planned')
                            vals = {}
                            if not(line.po_created or line.state in  ('assigned','done','cancel')):
                                l_Supplier = []
                                for l in line.supplier_ids:
                                    l_Supplier.append(l.id)
                                if line.type == 'product':
                                    vals = {
                                          'product_id':line.product_id.id,
                                          'product_qty':line.product_qty - line.product_id.virtual_available,
                                          'product_uom_id':line.product_uom_id.id,
                                          'company_id':line.company_id.id,
                                          'requisition_id':mr_id,
                                          'supplier_ids': [(6,0, l_Supplier )],
                                          'type':rec.type, 
                                          }
                                else:
                                    if line.product_id:
                                        qty_final = line.product_qty - line.product_id.virtual_available
                                    else:
                                        qty_final = line.product_qty
                                    vals = {
                                          'product_id':line.product_id and line.product_id.id or False,
                                          'product_qty': qty_final,
                                          'product_uom_id':line.product_uom_id.id,
                                          'company_id':line.company_id.id,
                                          'requisition_id':mr_id,
                                          'supplier_ids': [(6,0, l_Supplier )],
                                          'type':rec.type, 
                                          'budget_code_id': line.budget_code_id and line.budget_code_id.id or False,
                                          'desc': line.desc
                                          }
                                self.pool.get('purchase.requisition.multiple.line').create(cr, uid, vals, context=context)
#                                po_lines[supp].append((0,0,vals))
#                                intreq_line_obj.write(cr, uid, line.id, {'product_id': line.product_id.id, 'po_created':True,'price_unit':onchange.get('value',{}).get('price_unit')}, context)
                                intreq_line_obj.write(cr, uid, line.id, {'product_id': line.product_id.id, 'po_created':True}, context)
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
