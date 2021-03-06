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

{
    'name' : 'Internal Requisition Extended',
    'version': '1.0',
    'category': 'Warehouse Management',
    "author" : "Mattobell",
    "website" : "http://www.mattobell.com",
    'description':"",
    'data':[
            'security/hr_security.xml',
            'res_partner_data.xml',
            'res_partner_view.xml',
            'wizard/internal_req_wiz_view.xml',
            'account_view.xml',
            'internal_requisition_view.xml',
            'security/ir.model.access.csv',
            
            ],
    'depends':['ng_internal_requisition', 'ng_purchase_requisition','purchase_double_validation', 'ng_city',
               'ng_item_code','account_budget'],
               
    'installable':True,
    'auto_install':False
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
