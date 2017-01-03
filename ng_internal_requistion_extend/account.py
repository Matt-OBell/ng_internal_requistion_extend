from osv import fields, osv
import decimal_precision as dp
from tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class partner_sub_account(osv.osv):#probuse19feb
    _name = "sub.account"
    _inherit = ['mail.thread']
    _description = "Sub Account"
    def name_get(self, cursor, user, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            return []
        res = []
        data_partner = self.pool.get('sub.account').browse(cursor, user, ids, context=context)
        for partner in data_partner:
            name = partner.name + ' ' + partner.number
            res.append((partner.id, name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        if name:
            ids = self.search(cr, uid, ['|', ('number', operator, name), ('name', operator, name) ] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})

    
    _columns = {
        'name': fields.char('Sub-Account Name', size=264, required=True, track_visibility='onchange'),
        'partner_id': fields.many2one('res.partner', 'Customer', required=True, track_visibility='onchange'),
        'notes1': fields.text('Notes'),
        'notes2': fields.text('Additional Information'),
        'desc': fields.char('Description', size=1012),
        'number': fields.char('Child Account Number', track_visibility='onchange'),
        'parent_account_number': fields.related('partner_id', 'parent_acc_no', string="Parent Account Number",type='char',readonly=True,store=True),
        'date': fields.date('Create Date', required=True),
        'active_date': fields.date('Activation Date', required=False, track_visibility='onchange'),
        'user_id': fields.many2one('res.users', 'Responsible', readonly=False, track_visibility='onchange', required=True),


        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city_id' : fields.many2one('res.city','City'),
#        'city': fields.char('City', size=128),
        'city': fields.related('city_id', 'name', type='char',store=True,readonly=1),
        'state_id': fields.many2one("res.country.state", 'State'),
        'country_id': fields.many2one('res.country', 'Country'),
        'country': fields.related('country_id', type='many2one', relation='res.country', string='Country',
                                  deprecated="This field will be removed as of OpenERP 7.1, use country_id instead"),
        'email': fields.char('Email', size=240),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'mobile': fields.char('Mobile', size=64),
        'birthdate': fields.char('Birthdate', size=64),
        'contact_name': fields.char('Contact Person', size=264, required=False, select=True),
        'website': fields.char('Website', size=64, help="Website of Partner or Company"),
        
        'company_id': fields.many2one('res.company', 'Company', select=1),
        
        'state': fields.selection([('new', 'New'), ('active', 'Activated'), ('suspended', 'Suspended')\
                                         , ('terminated', 'Terminated'), ('cancel','Cancelled')], 'Status',
                                        required=False, track_visibility='onchange', readonly=True),

        
    }
    def active(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state': 'active'})
    def new(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state': 'new'})
    def suspended(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state': 'suspended'})
    def terminated(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state': 'terminated'})
    def cancel(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state': 'cancel'})
    def on_change_city(self, cr, uid, ids, city_id, context=None):
        result = {}
        if context is None:
            context = {}
        if not city_id:
            return result
        city = self.pool.get("res.city").browse(cr, uid, city_id, context=context)
        result['city'] = city.name
        result['state_id'] = city.state_id.id
        return {'value': result}
    
    def onchange_state(self, cr, uid, ids, state_id, context=None):
        if state_id:
            country_id = self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id
            return {'value':{'country_id':country_id}}
        return {}
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        value = {'parent_acc_no': ''}
        if partner_id:
            parent_acc_no = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context).parent_acc_no
            value = {'parent_account_number': parent_acc_no}
        return {'value': value}
    
    _defaults ={
        'date': fields.date.context_today,
        'user_id': lambda s, cr, u, c: u,
#        'state': 'new',
        'company_id': lambda self, cr, uid, ctx: self.pool.get('res.company')._company_default_get(cr, uid, 'res.partner', context=ctx),
        'country_id': lambda self, cr, uid, ctx: self.pool.get('res.country').search(cr, uid, [('name','=', 'Nigeria')], context=ctx)[0],
                }
    def create(self, cr, uid, datas, context=None):
        seq_obj = self.pool.get('ir.sequence')
        data_obj = self.pool.get('ir.model.data')
        datas.update({'state':'new'})
#        parent_seq_id = data_obj.get_object_reference(cr, uid, 'netcom', 'sequence_account_no_partner')[1]
        child_seq_id = data_obj.get_object_reference(cr, uid, 'ng_internal_requistion_extend', 'sequence_sub_account_no_partner')[1]
#        if datas.get('parent_partner_id'):#todo: remove this condtion since field is hide from view.
#            parent_acc_no = self.browse(cr, uid, datas['parent_partner_id']).parent_acc_no
#        else:
#            parent_acc_no = seq_obj.get(cr, uid, 'partner.account.number')
#        datas.update({'parent_acc_no':parent_acc_no})
        old_partner_ids = self.search(cr, uid, [('partner_id', '=', datas.get('partner_id'))])#probuse19feb 
        if old_partner_ids:#probuse19feb 
            seq_obj._alter_sequence(cr, child_seq_id, 1, (len(old_partner_ids) + 1))#probuse19feb 
        else:#probuse19feb 
            seq_obj._alter_sequence(cr, child_seq_id, 1, 1)#probuse19feb 
        datas.update({'number': seq_obj.get(cr, uid, 'sub.partner.account.number')})#probuse19feb 
        partner_id = super(partner_sub_account, self).create(cr, uid, datas, context)
        return partner_id

    def write(self, cr, uid, ids, vals, context=None):
        return super(partner_sub_account, self).write(cr, uid, ids, vals, context=context)
    
partner_sub_account()#probuse19feb