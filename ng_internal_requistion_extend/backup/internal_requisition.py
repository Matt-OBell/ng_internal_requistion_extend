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

from openerp.osv import osv, fields

class internal_requisition_line(osv.osv):
    _inherit = "internal.requisition.line"
    _columns = {
        'forcase_qty': fields.related('product_id', 'virtual_available', type='float', string='Forecasted Quantity'),
        'available_qty': fields.related('product_id', 'qty_available', type='float', string='Available Quantity'),
        'supplier_ids': fields.many2many('res.partner', 'multi_supplier_internal_req', 'multiple_id', 'partner_id', 'Suppliers' )#probuse
    }
    
    def onchange_product_id(self, cr, uid, ids, prod_id=False):
        res = super(internal_requisition_line, self).onchange_product_id(cr, uid, ids, prod_id)
        if not prod_id:
            return res
        product = self.pool.get('product.product').browse(cr, uid, [prod_id])[0]
        if res and 'value' in res:
            res['value'].update({
                'forcase_qty': product.virtual_available,
                'available_qty': product.qty_available,
            })
        return res

class stock_location(osv.osv):
    _inherit = "stock.location"

    def _complete_name(self, cr, uid, ids, name, args, context=None):
#         p) Departmental Stock Location names seem confusing eg “Physical Locations / Company / Stock/Shelf No”
#How can we use a more friendly name
        res = {}
        if context.get('simple_name', False):
            for m in self.browse(cr, uid, ids, context=context):
                res[m.id] = m.name
            return res
        else:
            return super(stock_location, self)._complete_name(cr, uid, ids, name, args, context)
        return super(stock_location, self)._complete_name(cr, uid, ids, name, args, context)

class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'


    _columns = {
        'charges_type': fields.selection([('MRC', 'MRC'), ('NRC', 'NRC')],
                                         string="MRC/NRC", required=False),#override from netcom to make required=false .. error was on purchase order creationg to invoice of supplier.
   
        'child_partner_id_new' : fields.many2one('sub.account', string='Child Account', required=False)#reqquired=false done.
    }
    
class purchase_order(osv.osv):
    _inherit = "purchase.order"
    _columns = {
        'site_id': fields.many2one("sub.account", "Site ID", help='Sub-Account from internal requisition form or multiple requisition.'),
    }
    
class purchase_requisition(osv.osv):
    _inherit = "purchase.requisition.multiple"
    
    #Pass now site_id to Purchase order from MR.
    def make_purchase_order(self, cr, uid, ids, partner_id, context=None):
        res = super(purchase_requisition, self).make_purchase_order(cr, uid, ids, partner_id, context)
        for i in res:
            mr_browse = self.browse(cr, uid, [i], context)[0]
            if mr_browse.site_id:
                self.pool.get('purchase.order').write(cr, uid, [res[i]], {'site_id': mr_browse.site_id.id})
        return res
    
    _columns = {
        'line_ids' : fields.one2many('purchase.requisition.multiple.line','requisition_id','Products to Purchase',readonly=False, states={'done': [('readonly', True)]}),
        'site_id': fields.related("ir_id", "site_id", string="Site ID", type='many2one', track_visibility='onchange',relation='sub.account' ,help='Sub-Account from internal requisition form.'),
    }
class internal_requisition(osv.osv):
    _inherit = "internal.requisition"
    
    def _check_split_po(self, cr, uid, ids, context=None):
        for ir in self.browse(cr, uid, ids, context):
            if not ir.is_split_po:
                for ir_line in ir.line_ids:
                    if ir_line.supplier_ids:
                        return False
        return True

    _constraints = [
        (_check_split_po, 'You can not select suppliers on requision lines if Split PO lines box is not checked.', ['is_split_po','line_ids']),
    ]

    _columns = {
                
                #Override line_ids to make it readonly=False
                'line_ids' : fields.one2many('internal.requisition.line','requisition_id','Products internally Requested',readonly=False, states={'done': [('readonly', True)]}),
                
                'employee_id': fields.many2one('hr.employee', 'Employee', track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]}),
                'department_id':fields.many2one('hr.department','Department', readonly=True, states={'draft': [('readonly', False)]}, help='Select the department the Requester wants the requisition delivered.'), #override
                'state': fields.selection([
                                   ('draft','New'),
                                   ('confirm','Confirmed'),
                                   ('cancel','Cancelled'),
                                   ('approve_by_dept','Approved By Department'),#added this here.
                                   ('approve','Approved'),
                                   ('waiting','Waiting Availability'),
                                   ('delivery','Internal Order Generated'),
                                   ('ready','Ready to Process'),
                                   ('done','Done'),
                                   ], 'State', required=True,readonly=True, track_visibility='onchange'),
                'customer_id': fields.many2one("res.partner", 'Customer', track_visibility='onchange'),
                'site_id': fields.many2one("sub.account", "Site ID", readonly=False, states={'done': [('readonly', True)]}, help='Sub-Account for the selected Customer.', track_visibility='onchange'),
                'sars_ticket': fields.char("SAR Ticket", size=10, required=1, readonly=False, states={'done': [('readonly', True)]}, track_visibility='onchange'),
                
                'ir_officer_id': fields.many2one('res.users', 'IR Officer', readonly=False, states={'done': [('readonly', True)]},),
                
                'is_split_po': fields.boolean("Split PO Line?", help="Check this box to issue PO Lines to multiple vendors."),#probuse
                
                }
    
    def create(self, cr, uid, vals, context=None):
        model_obj = self.pool.get('ir.model.data')
        res_obj = self.pool.get('res.groups')
        view_model, m_id = model_obj.get_object_reference(cr, uid, 'purchase', 'group_purchase_manager')
        view_model, stock_m_id = model_obj.get_object_reference(cr, uid, 'stock', 'group_stock_manager')
        s_data = res_obj.browse(cr, uid, stock_m_id)
        m_data = res_obj.browse(cr, uid, m_id)
        manager_list = []
        for user in m_data.users:
            manager_list.append(user.id)
        for user in s_data.users:
            manager_list.append(user.id)
            
        emp_obj = self.pool.get("hr.employee")
#        if vals.get('employee_id', False):
#            emp_list = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
#            if emp_list:
#                if emp_list[0] != vals['employee_id'] and not uid in manager_list:
#                    raise osv.except_osv(('Warning'), ('You can not change the employee.')) 
        emp_obj = self.pool.get("hr.employee")
#        if vals.get('department_id', False):
#            emp_list = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
#            if emp_list:
#                emp_brw = emp_obj.browse(cr, uid, emp_list[0], context=context)
#                if emp_brw.department_id.id != vals['department_id'] and not uid in manager_list:
#                    raise osv.except_osv(('Warning'), ('You can not change the department.')) 
#        if vals.get('manager_id', False):
#            emp_list = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
#            if emp_list:
#                emp_brw = emp_obj.browse(cr, uid, emp_list[0], context=context)
#                if emp_brw.manager_id.id != vals['manager_id'] and not uid in manager_list:
#                    raise osv.except_osv(('Warning'), ('You can not change the manager.')) 

        user_id = vals.get('user_id',False)
        if uid != 1:
            if uid == user_id or uid in manager_list:
                return super(internal_requisition, self).create(cr, uid, vals, context)
            else:
                raise osv.except_osv(('Warning'), ('You can not create requisition for other user.')) 
        else:
            return super(internal_requisition, self).create(cr, uid, vals, context)
        return super(internal_requisition, self).create(cr, uid, vals, context)
    
    def write(self, cr, uid, ids, vals, context=None):
        model_obj = self.pool.get('ir.model.data')
        res_obj = self.pool.get('res.groups')
        view_model, m_id = model_obj.get_object_reference(cr, uid, 'purchase', 'group_purchase_manager')
        view_model, stock_m_id = model_obj.get_object_reference(cr, uid, 'stock', 'group_stock_manager')
        s_data = res_obj.browse(cr, uid, stock_m_id)
        m_data = res_obj.browse(cr, uid, m_id)
        manager_list = []
        for user in m_data.users:
            manager_list.append(user.id)
        for user in s_data.users:
            manager_list.append(user.id)
        user_id = vals.get('user_id',False)
        
        emp_obj = self.pool.get("hr.employee")
        if vals.get('employee_id', False):
            emp_list = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
            if emp_list:
                if emp_list[0] != vals['employee_id'] and not uid in manager_list:
                    raise osv.except_osv(('Warning'), ('You can not change the employee.')) 
        emp_obj = self.pool.get("hr.employee")
        if vals.get('department_id', False):
            emp_list = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
            if emp_list:
                emp_brw = emp_obj.browse(cr, uid, emp_list[0], context=context)
                if emp_brw.department_id.id != vals['department_id'] and not uid in manager_list:
                    raise osv.except_osv(('Warning'), ('You can not change the department.')) 
        if vals.get('manager_id', False):
            emp_list = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
            if emp_list:
                emp_brw = emp_obj.browse(cr, uid, emp_list[0], context=context)
                if emp_brw.manager_id.id != vals['manager_id'] and not uid in manager_list:
                    raise osv.except_osv(('Warning'), ('You can not change the manager.')) 


        if user_id:
            if uid != 1:
                if uid == user_id or uid in manager_list:
                    return super(internal_requisition, self).write(cr, uid, ids, vals, context=context)
                elif uid != user_id:
                    raise osv.except_osv(('Warning'), ('You can not update requisition for other user.')) 
            else:
                return super(internal_requisition, self).write(cr, uid, ids, vals, context=context)
        return super(internal_requisition, self).write(cr, uid, ids, vals, context=context)

    def on_change_user_id(self, cr, uid, ids, user_id, context=None):
        emp_obj = self.pool.get("hr.employee")
        emp_list = emp_obj.search(cr, uid, [('user_id', '=', user_id)], context=context)
        domain = {}
        manager_list = []
        if emp_list: 
            emp_brw = emp_obj.browse(cr, uid, emp_list[0], context=context)
            model_obj = self.pool.get('ir.model.data')
            res_obj = self.pool.get('res.groups')
            view_model, m_id = model_obj.get_object_reference(cr, uid, 'ng_internal_requistion_extend', 'ir_officer_group')
            m_data = res_obj.browse(cr, uid, m_id)
            manager_list = []
            for user in m_data.users:
               manager_list.append(user.id)
            domain = {'ir_officer_id':
                            [('id', 'in', manager_list)],
                           }
            return {'value':{'employee_id':emp_list[0] or False,
                             'department_id':emp_brw.department_id.id or False,
                             'manager_id':emp_brw.parent_id.id or False}, 'domain': domain} 
        else:
            return {}
         
    def on_change_employee_id(self, cr, uid, ids, employee_id, context=None):
        dept_obj = self.pool.get("hr.employee").browse(cr, uid, employee_id, context=context)
        return {'value':{'department_id':dept_obj.department_id.id or False,
                         'manager_id':dept_obj.parent_id.id or False}}
        
    def approve_by_department(self, cr, uid, ids, context=None):
        seq_no = self.pool.get('ir.sequence').get(cr, uid, 'internal.requisition')
        line_obj = self.pool.get('internal.requisition.line')
        for intreq in self.browse(cr, uid, ids, context):
            lines = map(lambda x:x.id, intreq.line_ids)
            line_obj.action_approve(cr, uid, lines, context)
        self.write(cr,uid,ids,{'name':seq_no,'state':'approve_by_dept'},context=context)
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
