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
from openerp import tools
from tools.translate import _

class product_product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'budget_type' :  fields.selection([('product', 'External'),('budget_code', 'Internal')], string='Requisition Product Type',help="If Internal this product will be used in IR request with type Internal and budget code. Keep External always for product which can be sold to customer.")#budget
    }
    _defaults = {
        'budget_type' : 'product'
    }
product_product()

class purchase_order_line(osv.osv):
    _inherit = "purchase.order.line"
    _columns = {
        'budget_code_id' : fields.many2one('product.budget.code', 'Budget Code'),#budget
        'type' :  fields.selection([('product', 'External'),('budget_code', 'Internal')], string='Type')#budget
    }
    _defaults = {
        'type' : 'product'
    }

purchase_order_line()

class purchase_line(osv.osv):
    _inherit = "purchase.order"

    #Overwrite here, to add logic if po line type = budget code then pass expense account id from budget code form instead of property.
    def _choose_account_from_po_line(self, cr, uid, po_line, context=None):
        fiscal_obj = self.pool.get('account.fiscal.position')

        if po_line.type == 'product':#call super if user try to create invoice with type = product (not budget code!)
            return super(purchase_line, self)._choose_account_from_po_line(cr, uid, po_line, context)
        
        if po_line.type == 'budget_code' and not po_line.budget_code_id:
            return super(purchase_line, self)._choose_account_from_po_line(cr, uid, po_line, context)

        #If PO line type= budget code then we have to use account configured on budget code instead of taking from product or property.
        if po_line.type == 'budget_code':
            acc_id = po_line.budget_code_id.account_id.id #pass account from budget code.
        fpos = po_line.order_id.fiscal_position or False
        return fiscal_obj.map_account(cr, uid, fpos, acc_id)

    _columns = {
        'type' :  fields.selection([('product', 'External'),('budget_code', 'Internal')], string='Type', readonly=False, states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)], 'done':[('readonly',True)]})#budget
    }
    _defaults = {
        'type' : 'product'
    }

    #Override from base to notify budget manager for confirm PO. #ng
#     def wkf_confirm_order(self, cr, uid, ids, context=None):
#         res = super(purchase_line, self).wkf_confirm_order(cr, uid, ids, context=context)
#         po_data = self.browse(cr, uid, ids, context=context)[0]
#         model_obj = self.pool.get('ir.model.data')
#         res_obj = self.pool.get('res.groups')
#         view_model, m_id = model_obj.get_object_reference(cr, uid, 'ng_internal_requistion_extend', 'budget_manager_po')
#         m_data = res_obj.browse(cr, uid, m_id)
#         manager_list = []
#         #find the partner related to Budget Control group
#         for user in m_data.users:
#            manager_list.append(user.partner_id.id)
#         #Send the message to all Budget Control Manager for reminder of PO Approval
#         self.message_post(cr, uid, ids, 
#                           body = _("Dear Sir/Madam, <br/><br/> Purchase Order %s  has been approved by Purchasing Manager.\
#                            and now awaiting your approval. <br/><br/>Kindly Approve.<br/><br/> Thank you, <br/> %s" %(po_data.name, po_data.company_id.name)) ,
#                           type = 'comment',
#                           subtype = "mail.mt_comment",context = context,
#                           model = 'purchase.order', res_id = po_data.id, 
#                           partner_ids = manager_list)
# 
#         return res

purchase_line()

class internal_requisition_line(osv.osv):
    _inherit = "internal.requisition.line"
    _columns = {
        'forcase_qty': fields.related('product_id', 'virtual_available', type='float', string='Forecasted Quantity'),
        'available_qty': fields.related('product_id', 'qty_available', type='float', string='Available Quantity'),
        'supplier_ids': fields.many2many('res.partner', 'multi_supplier_internal_req', 'multiple_id', 'partner_id', 'Suppliers' ),#probuse
        'budget_code_id' : fields.many2one('product.budget.code', 'Budget Code'),#budget
        'type' :  fields.selection([('product', 'External'),('budget_code', 'Internal')], string='Type'),#budget
        'state': fields.selection([('draft', 'New'),('confirm1','Confirmed'),('approve','Approved by Department'),('approve1','Approved by Department'),('confirmed', 'Waiting Availability'), ('assigned', 'Available'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, select=True),#Overwrite here from main module.
    }
    
    def on_change_type(self, cr, uid, ids, type, context=None):
        if context is None:
            context = {}
        if not type:
            return {}
        if type == 'budget_code':#internal
            return {'domain': {'product_id': [('type', '=', 'product'), ('budget_type', '=', 'budget_code')]}}
        if type == 'product':
            return {'value': {'budget_code_id': False}, 'domain': {'product_id': [('type', '!=', 'consu'), ('budget_type', '=', 'product')]}}
        return {}

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

    def action_approve(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'approve1'})

    def action_approve1(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'approve1'})

    def onchange_budget_code_id(self, cr, uid, ids, budget_code_id, context=None):#budget
        if not context:
            context ={}
        if not budget_code_id:
            return {}
        budget_data = self.pool.get('product.budget.code').browse(cr, uid, [budget_code_id], context)[0]
        name = budget_data.name or ''
        code = budget_data.code or ''
        
        desc = code + ' ' + name
        
        return {'value' : {'product_qty' : 1.0,
                           'desc' : desc
                           }}

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

    #TODO: implement messages system
    def wkf_confirm_order(self, cr, uid, ids, context=None):
        todo = []
        for po in self.browse(cr, uid, ids, context=context):
            if po.amount_total <= 0.0:
                raise osv.except_osv(_('Error!'),_('You cannot confirm a purchase order if total is zero or less.'))
        return super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context)

    def on_change_mrequisition_id(self, cr, uid, ids, mrequisition_id, context=None):
        if context is None:
            context = {}
        if not mrequisition_id:
            return {}
        if mrequisition_id:
            mr = self.pool.get('purchase.requisition.multiple').browse(cr, uid, [mrequisition_id], context=context)[0]
            if mr:
                return {'value': {'ir_number': mr.ir_id.name}}
        return {}

    STATE_SELECTION = [
        ('draft', 'Draft Quotation'),
        ('sent', 'RFQ Sent'),
        ('confirmed', 'Awaiting Budget Control'),
        ('approved', 'Purchase Order'),
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ]
    _inherit = "purchase.order"
    _columns = {
        'ir_number': fields.char('IR Number', states={'approved':[('readonly',True)], 'done':[('readonly',True)]}),
#         'site_id': fields.many2one("sub.account", "Site ID", help='Sub-Account from internal requisition form or multiple requisition.'),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True, help="The status of the purchase order or the quotation request. A quotation is a purchase order in a 'Draft' status. Then the order has to be confirmed by the user, the status switch to 'Confirmed'. Then the supplier must confirm the order to change the status to 'Approved'. When the purchase order is paid and received, the status becomes 'Done'. If a cancel action occurs in the invoice or in the reception of goods, the status becomes in exception.", select=True),
    }
    
class purchase_requisition(osv.osv):
    _inherit = "purchase.requisition.multiple"
    
#     #Pass now site_id to Purchase order from MR.
#     def make_purchase_order(self, cr, uid, ids, partner_id, context=None):
#         res = super(purchase_requisition, self).make_purchase_order(cr, uid, ids, partner_id, context)
#         for i in res:
#             mr_browse = self.browse(cr, uid, [i], context)[0]
#             if mr_browse.site_id:
#                 self.pool.get('purchase.order').write(cr, uid, [res[i]], {'site_id': mr_browse.site_id.id})
#         return res
    
    _columns = {
        'line_ids' : fields.one2many('purchase.requisition.multiple.line','requisition_id','Products to Purchase',readonly=False, states={'done': [('readonly', True)]}),
#         'site_id': fields.related("ir_id", "site_id", string="Site ID", type='many2one', track_visibility='onchange',relation='sub.account' ,help='Sub-Account from internal requisition form.'),
        'type' :  fields.selection([('product', 'External'),('budget_code', 'Internal')], string='Request Type', required= True)#budget
        
    }
    _defaults = {
        'type' : 'product'
    }
 
class internal_requisition(osv.osv):
    _inherit = "internal.requisition"
    
    def reset_prev(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)
    def reset_prev1(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)
    def reset_prev2(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'approve'}, context=context)
    def decline_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def decline(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)

    def _check_split_po(self, cr, uid, ids, context=None):
        for ir in self.browse(cr, uid, ids, context):
            if not ir.is_split_po:
                for ir_line in ir.line_ids:
                    if ir_line.supplier_ids:
                        return False
        return True

    def _check_type(self, cr, uid, ids, context=None):
        for ir in self.browse(cr, uid, ids, context):
            t = ir.type
            for ir_line in ir.line_ids:
                if t != ir_line.type:
                    return False
        return True

    _constraints = [
        (_check_split_po, 'You can not select suppliers on requision lines if Split PO lines box is not checked.', ['is_split_po','line_ids']),
         (_check_type, 'Request type on IR form and type of IR lines must be same.', ['type']),
    ]

    _columns = {
                'bill_control_approved': fields.boolean('Approved by Billing Control'),
                
                #Override line_ids to make it readonly=False
                'line_ids' : fields.one2many('internal.requisition.line','requisition_id','Products internally Requested',readonly=False, states={'done': [('readonly', True)], 'approve_by_dept': [('readonly', True)]}),
                
                'employee_id': fields.many2one('hr.employee', 'Employee', track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]}),
                'department_id':fields.many2one('hr.department','Department', readonly=True, states={'draft': [('readonly', False)]}, help='Select the department the Requester wants the requisition delivered.'), #override
                'state': fields.selection([
                                   ('draft','New'),
                                   ('confirm','Awaiting Department Approval'),
                                   ('approve_by_dept','Approved By Department'),#added this here.
                                   ('approve','Approved By Department'),
                                   ('approve_by_bill','Approved'),#added this here.
                                   ('waiting','Waiting Availability'),
                                   ('delivery','Internal Order Generated'),
                                   ('ready','Ready to Process'),
                                   ('done','Done'),
                                   ('cancel','Cancelled'),
                                   ], 'State', required=True,readonly=True, track_visibility='onchange'),
                'customer_id': fields.many2one("res.partner", 'Customer', track_visibility='onchange'),
#                 'site_id': fields.many2one("sub.account", "Site ID", readonly=False, states={'done': [('readonly', True)]}, help='Sub-Account for the selected Customer.', track_visibility='onchange'),
#                 'sars_ticket': fields.char("SAR Ticket", size=10, required=1, readonly=False, states={'approve_by_dept': [('readonly', True)], 'done': [('readonly', True)]}, track_visibility='onchange'),
                
                'ir_officer_id': fields.many2one('res.users', 'IR Officer', readonly=False, states={'done': [('readonly', True)]}, help="Please select the Supply Chain Officer responsible for this Internal Requisition."),
                
                'is_split_po': fields.boolean("Split PO Line?", help="Check this box to issue PO Lines to multiple vendors."),#probuse
                'id': fields.integer('ID', readonly=True),
                'type' :  fields.selection([('product', 'External'),('budget_code', 'Internal')], string='Request Type', required= True, readonly=True, states={'draft': [('readonly', False)]},),#budget
                'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse',help="This warehouse's stock location will be used  to issue this internal requisition", required=False, readonly=False, states={'done': [('readonly', True)], 'approve_by_dept': [('readonly', True)]}),   
                }


    _defaults = {
        'type' : 'budget_code',
        'name' : 'Draft Requisition'
    }

    def confirm(self, cr, uid, ids, context=None):
        res = super(internal_requisition, self).confirm(cr, uid, ids, context=context)
        ir_data = self.browse(cr, uid, ids, context=context)[0]
        #Send the message to department manager to approve IR.
        if ir_data.manager_id.user_id:
            self.message_post(cr, uid, ids, 
                              body = _("Dear %s, <br/><br/> %s has sent you a requisition\
                                and waiting for your approval as department manager. \
     <br/><br/> Thank you, <br/> %s" %(ir_data.manager_id.name, ir_data.user_id.name, ir_data.company_id.name)) ,
                              type = 'comment',
                              subtype = "mail.mt_comment",context = context,
                              model = 'internal.requisition', res_id = ir_data.id, 
                              partner_ids = [ir_data.manager_id.user_id.partner_id.id])
        return res

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
        ir_data = self.browse(cr, uid, ids, context=context)[0]
        model_obj = self.pool.get('ir.model.data')
        res_obj = self.pool.get('res.groups')
        ir_data = self.browse(cr, uid, ids, context=context)[0]
        model_obj = self.pool.get('ir.model.data')
        res_obj = self.pool.get('res.groups')
        view_model, m_id = model_obj.get_object_reference(cr, uid, 'ng_internal_requistion_extend', 'bill_manager_ir')
        m_data = res_obj.browse(cr, uid, m_id)
        manager_list = []
        #find the partner related to Billing Officer group
        for user in m_data.users:
           manager_list.append(user.partner_id.id)
        #Send the message to all BIliing Officer for reminder of IR Approval
        if ir_data.type == 'product':
            self.message_post(cr, uid, ids, 
                              body = _("Dear Sir/Madam, <br/><br/> Requisition %s  has been approved by %s as department manager\
                               and now awaiting your approval as Billing control officer. <br/><br/> Thank you, <br/> %s" %(str(seq_no), ir_data.manager_id.name, ir_data.company_id.name)) ,
                              type = 'comment',
                              subtype = "mail.mt_comment",context = context,
                              model = 'internal.requisition', res_id = ir_data.id, 
                              partner_ids = manager_list)
        else:
            ir_data = self.browse(cr, uid, ids, context=context)[0]
            model_obj = self.pool.get('ir.model.data')
            res_obj = self.pool.get('res.groups')
            view_model, m_id = model_obj.get_object_reference(cr, uid, 'purchase', 'group_purchase_manager')
            m_data = res_obj.browse(cr, uid, m_id)
            manager_list = []
            #find the partner related to Purchase Manager group
            for user in m_data.users:
               manager_list.append(user.partner_id.id)
            #Send the message to all Purchase Manager for reminder of IR Approval
            self.message_post(cr, uid, ids, 
                              body = _("Dear Sir/Madam, <br/><br/> Requisition %s  has been approved by department manager \
                               and now awaiting your approval as purchase manager. <br/><br/>Kindly Approve.<br/><br/>Thank you, <br/> %s" %(str(seq_no), ir_data.company_id.name)) ,
                              type = 'comment',
                              subtype = "mail.mt_comment",context = context,
                              model = 'internal.requisition', res_id = ir_data.id, 
                              partner_ids = manager_list)

        for intreq in self.browse(cr, uid, ids, context):
            lines = map(lambda x:x.id, intreq.line_ids)
            line_obj.action_approve(cr, uid, lines, context)
        #self.write(cr,uid,ids,{'name':seq_no, 'state':'approve_by_dept'},context=context)

        flag = True#for service type of products in IR lines no need to check availibilty.. so show create rfq button directly.
        for x in ir_data.line_ids:
            if not x.product_id.type == 'service':
                flag = False


        if ir_data.type == 'budget_code':#2. Only Budget Code (for Internal IR) without product
            flag1 = True
            for y in ir_data.line_ids:
                if y.product_id:
                    flag1 = False#
            if flag1 and not ir_data.type == 'product':
                self.write(cr, uid, ids, {'need_rfq': True}, context=context)

        if ir_data.type == 'product':#for external, we need bill control approval.
            self.write(cr,uid,ids,{'name':seq_no, 'state':'approve'}, context=context)
        else:#for internal, we do not need bill control approval. so directly write the state.
            if flag:
                self.write(cr, uid, ids, {'need_rfq': True}, context=context)#for service type products , create rfq button always visible.
            self.write(cr,uid,ids,{'name':seq_no, 'state':'approve_by_bill'},context=context)
        return True

    def approve_by_bill_control(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('internal.requisition.line')
        ir_data = self.browse(cr, uid, ids, context=context)[0]
        model_obj = self.pool.get('ir.model.data')
        res_obj = self.pool.get('res.groups')
        view_model, m_id = model_obj.get_object_reference(cr, uid, 'purchase', 'group_purchase_manager')
        m_data = res_obj.browse(cr, uid, m_id)
        manager_list = []
        #find the partner related to Purchase Manager group
        for user in m_data.users:
           manager_list.append(user.partner_id.id)
        #Send the message to all Purchase Manager for reminder of IR Approval
        self.message_post(cr, uid, ids, 
                          body = _("Dear Sir/Madam, <br/><br/> Requisition %s  has been approved by Billing Control.\
                           and now awaiting your approval as purchase manager. <br/><br/>Kindly Approve.<br/><br/>Thank you, <br/> %s" %(ir_data.name, ir_data.company_id.name)) ,
                          type = 'comment',
                          subtype = "mail.mt_comment",context = context,
                          model = 'internal.requisition', res_id = ir_data.id, 
                          partner_ids = manager_list)

        flag = True#for service type of products in IR lines no need to check availibilty.. so show create rfq button directly.
        for x in ir_data.line_ids:
            if not x.product_id.type == 'service':
                flag = False
        if flag:
            self.write(cr, uid, ids, {'need_rfq': True}, context=context)

        if ir_data.type == 'budget_code':#2. Only Budget Code (for Internal IR) without product
            flag1 = True
            for y in ir_data.line_ids:
                if y.product_id:
                    flag1 = False#
            if flag1:
                self.write(cr, uid, ids, {'need_rfq': True}, context=context)

        return self.write(cr,uid,ids,{'state':'approve_by_bill', 'bill_control_approved': True},context=context)

    def check_availability(self, cr, uid, ids, context=None):
        ir_data = self.browse(cr, uid, ids, context=context)[0]

#It should be:
#1. Service Type of Product (for external IR)
#2. Only Budget Code (for Internal IR)
#For these two, if user click on check availability and MR and PO is already confirmed or validated, then it should directly move to Done State.

        #------------Only Budget Code (for Internal IR)--------Make state of IR done.----------------start---------
        if ir_data.type == 'budget_code':#2. Only Budget Code (for Internal IR)
            flag1 = True
            for y in ir_data.line_ids:
                if y.product_id:
                    flag1 = False#
            if flag1 and ir_data.type == 'budget_code' and not ir_data.purchase_ids and not ir_data.ir_ids:
                raise osv.except_osv(_('Error !'),_('No need to check availability since all products in requisition lines are with budget code only. You can directly create purcahse order.'))
            if flag1 and ir_data.ir_ids:
                for mr in ir_data.ir_ids:
                    if mr.state != 'done':
                        raise osv.except_osv(_('Error !'),_('No need to check availability since all products in requisition lines are with budget code only. Purcahse order already created in system. Please check Multiple requisition or RFQ tab on form.'))
                    else:
                        for po in mr.purchase_ids:
                            if po.state not in ('approved', 'done', 'cancel'):
                                raise osv.except_osv(_('Error !'),_('No need to check availability since all products in requisition lines are with budget code only. Purcahse order already created in system. Please check Multiple requisition or RFQ tab on form.'))

            if flag1 and ir_data.type == 'budget_code' and ir_data.purchase_ids:
                for po in ir_data.purchase_ids:
                    if po.state not in ('approved', 'done', 'cancel'):
                       raise osv.except_osv(_('Error !'),_('No need to check availability since all products in requisition lines are type of service. Purcahse order already created in system. Please check Multiple requisition or RFQ tab on form.'))

            if flag1 and ir_data.ir_ids:
                for mr in ir_data.ir_ids:
                    if mr.state == 'done':
                        for po in mr.purchase_ids:
                            if po.state in ('approved', 'done'):
                                return self.write(cr, uid, [ir_data.id], {'state': 'done'}, context=context)
            if flag1 and len(ir_data.purchase_ids) >= 1:
                for po in ir_data.purchase_ids:
                    if po.state in ('approved', 'done'):
                        return self.write(cr, uid, [ir_data.id], {'state': 'done'}, context=context)
        #------------------------------------End----------------------------------------------------------

        #------------------------------------start-----------For Ir line with all services + External IR case.-------------------------
        flag = True#for service type of products in IR lines no need to check availibilty.. so show create rfq button directly.
        for x in ir_data.line_ids:
            if not x.product_id.type == 'service':
                flag = False#No need to check availability since all products in requisition lines are type of service.

        if flag and ir_data.type == 'product' and not ir_data.purchase_ids and not ir_data.ir_ids:
            raise osv.except_osv(_('Error !'),_('No need to check availability since all products in requisition lines are type of service. You can directly create purcahse order.'))
        if flag and ir_data.type == 'product' and ir_data.ir_ids:
            for mr in ir_data.ir_ids:
                if mr.state != 'done':
                    raise osv.except_osv(_('Error !'),_('No need to check availability since all products in requisition lines are type of service. Purcahse order already created in system. Please check Multiple requisition or RFQ tab on form.'))
                else:
                    for po in mr.purchase_ids:
                        if po.state not in ('approved', 'done', 'cancel'):
                            raise osv.except_osv(_('Error !'),_('No need to check availability since all products in requisition lines are type of service. Purcahse order already created in system. Please check Multiple requisition or RFQ tab on form.'))

        if flag and ir_data.type == 'product' and ir_data.purchase_ids:
            for po in mr.purchase_ids:
                if po.state not in ('approved', 'done', 'cancel'):
                   raise osv.except_osv(_('Error !'),_('No need to check availability since all products in requisition lines are type of service. Purcahse order already created in system. Please check Multiple requisition or RFQ tab on form.'))

        if flag and ir_data.type == 'product' and len(ir_data.ir_ids) >= 1:
            for mr in ir_data.ir_ids:
                if mr.state == 'done':
                    for po in mr.purchase_ids:
                        if po.state in ('approved', 'done'):
                            return self.write(cr, uid, [ir_data.id], {'state': 'done'}, context=context)

        if flag and ir_data.type == 'product' and len(ir_data.purchase_ids) >= 1:
            for po in ir_data.purchase_ids:
                if po.state in ('approved', 'done'):
                    return self.write(cr, uid, [ir_data.id], {'state': 'done'}, context=context)
        #----------------------------------End--------------------------------------            

        for req in self.browse(cr, uid, ids, context):
            if req.type == 'product' and not req.bill_control_approved:#for external type we need bill contrl approval.
                raise osv.except_osv(_('Error !'),_('Please take approval from billing control officer!'))
        return super(internal_requisition, self).check_availability(cr, uid, ids, context=context)

    def force_availability(self,cr,uid,ids,context=None):
        ir_data = self.browse(cr, uid, ids, context=context)[0]
        flag = True#for service type of products in IR lines no need to check availibilty.. so show create rfq button directly.
        for x in ir_data.line_ids:
            if not x.product_id.type == 'service':
                flag = False
        if flag:
            raise osv.except_osv(_('Error !'),_('No need to force availability since all products in requisition lines are type of service. You can directly create purcahse order.'))

        for req in self.browse(cr, uid, ids, context):
            if req.type == 'product' and not req.bill_control_approved:#for external type we need bill contrl approval.
                raise osv.except_osv(_('Error !'),_('Please take approval from billing control officer!'))
        return super(internal_requisition, self).force_availability(cr,uid,ids,context)

    def process(self,cr, uid, ids, context=None):#this methoid will call when user press generate internal order. We override it because we need to stop generation of internal order in case of all IR lines with type of service.
        ir_data = self.browse(cr, uid, ids, context=context)[0]
        flag = True#for service type of products in IR lines no need to check availibilty.. so show create rfq button directly.
        for x in ir_data.line_ids:
            if not x.product_id.type == 'service':
                flag = False
        if flag:
            raise osv.except_osv(_('Error !'),_('You can not generate internal order since all requisition lines having items of type service.'))
        return super(internal_requisition, self).process(cr, uid, ids, context=context)
        
    def approve(self, cr,uid, ids, context=None):#complete overwrite here from main module.
        #seq_no = self.pool.get('ir.sequence').get(cr, uid, 'internal.requisition')
        line_obj = self.pool.get('internal.requisition.line')
        
        ir_data = self.browse(cr, uid, ids, context=context)[0]
        model_obj = self.pool.get('ir.model.data')
        res_obj = self.pool.get('res.groups')
        view_model, m_id = model_obj.get_object_reference(cr, uid, 'ng_internal_requistion_extend', 'bill_manager_ir')
        m_data = res_obj.browse(cr, uid, m_id)
        manager_list = []
        #find the partner related to Billing Officer group
        for user in m_data.users:
           manager_list.append(user.partner_id.id)
        #Send the message to all BIliing Officer for reminder of IR Approval
        self.message_post(cr, uid, ids, 
                          body = _("Dear Sir/Madam, <br/><br/> Requisition %s  has been approved by %s as IR officer.\
                           and now awaiting your approval as Billing control officer. <br/><br/> Thank you, <br/> %s" %(ir_data.name, ir_data.ir_officer_id.name, ir_data.company_id.name)) ,
                          type = 'comment',
                          subtype = "mail.mt_comment",context = context,
                          model = 'internal.requisition', res_id = ir_data.id, 
                          partner_ids = manager_list)
        for intreq in self.browse(cr, uid, ids, context):
            lines = map(lambda x:x.id, intreq.line_ids)
            line_obj.action_approve1(cr, uid, lines, context)#probuse
        self.write(cr,uid,ids,{'state':'approve'},context=context)
        return True

    def cancel(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'bill_control_approved': False, 'need_rfq': False},context=context)
        return super(internal_requisition, self).cancel(cr,uid,ids,context=None)

class product_budget_code(osv.osv):#budget
    _name = 'product.budget.code'
    _description = 'Product Budget Code'
    
    _columns = {
            'account_id' : fields.many2one('account.account', 'Budget Account', required=True),
            'name' : fields.char('Budget Name', required=True),
            'code' : fields.char('Budget Code', required=True),
            'active' : fields.boolean('Active')
        }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
                    ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'code'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['code']:
                name = record['code'] + ' ' + name
            res.append((record['id'], name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        if name:
            ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('code', operator, name)] + args, limit=limit, context=context or {})
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})
    
    _defaults = {
            'active' : True
    }

    _sql_constraints = [
       ('code_uniq', 'unique(code)', 'Code must be unique per budget code!'),
   ]

    def onchange_account(self, cr, uid, ids, account_id, context=None):
        res = {}
        if account_id:
            account_data = self.pool.get('account.account').browse(cr, uid, [account_id], context)[0]
            code = account_data.code
            name = account_data.name
            res.update({
                        'name': name,
                        'code' : code
                        })
        return {'value': res}
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
