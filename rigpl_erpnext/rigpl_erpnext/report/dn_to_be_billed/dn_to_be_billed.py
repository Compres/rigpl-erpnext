from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import getdate, nowdate, flt, cstr

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()
	data = get_dn_entries(filters)

	return columns, data

def get_columns():
	return [
		"DN #:Link/Delivery Note:120", "Customer:Link/Customer:200" ,"Date:Date:100",
		"Item Code:Link/Item:130","Description::350", "DN Qty:Float:70",
		"DN Price:Currency:70", "DN Amount:Currency:80", "Taxes::100", "SO #:Link/Sales Order:140",
		"SO Date:Date:80", "Sales Person::150",
		"Unbilled Qty:Float:80", "Unbilled Amount:Currency:80",
		"Trial:Int:60"
	]

def get_dn_entries(filters):
	conditions = get_conditions(filters)[0]
	si_cond = get_conditions(filters)[1]
	so_cond = get_conditions(filters)[2]
	
	query = """select dn.name, dn.customer, dn.posting_date, dni.item_code, 
	dni.description, dni.qty, dni.base_rate, dni.base_amount, dn.taxes_and_charges,
	dni.against_sales_order, so.transaction_date, st.sales_person,

	(dni.qty - ifnull((select sum(sid.qty) FROM `tabSales Invoice Item` sid, `tabSales Invoice` si 
		WHERE sid.delivery_note = dn.name and
		sid.parent = si.name and
		sid.qty > 0 AND
		sid.dn_detail = dni.name %s), 0)),

	(dni.base_amount - ifnull((select sum(sid.base_amount) from `tabSales Invoice Item` sid, `tabSales Invoice` si
        	where sid.delivery_note = dn.name and
			sid.parent = si.name and
			sid.qty > 0 AND
        	sid.dn_detail = dni.name %s), 0)),

	dni.item_name, dni.description, so.track_trial
	
	FROM `tabDelivery Note` dn, `tabDelivery Note Item` dni, `tabSales Order` so, `tabSales Team` st

	WHERE dn.docstatus = 1 AND so.docstatus = 1
		AND st.parenttype = "Customer"
		AND st.parent = dn.customer
		AND so.name = dni.against_sales_order %s
    	AND dn.name = dni.parent
    	AND (dni.qty - ifnull((select sum(sid.qty) FROM `tabSales Invoice Item` sid, `tabSales Invoice` si
        	WHERE sid.delivery_note = dn.name
				AND sid.parent = si.name
				AND sid.qty > 0
				AND sid.dn_detail = dni.name %s), 0)>=0.01) %s
	
	ORDER BY dn.posting_date asc """ % (si_cond, si_cond, so_cond, si_cond, conditions)
	dn = frappe.db.sql(query ,as_list=1)

	return dn

def get_conditions(filters):
	conditions = ""
	si_cond = ""
	so_cond = ""

	if filters.get("customer"):
		conditions += " and dn.customer = '%s'" % filters["customer"]

	if filters.get("from_date"):
		if filters.get("to_date"):
			if getdate(filters.get("from_date"))>getdate(filters.get("to_date")):
				frappe.msgprint("From Date cannot be greater than To Date", raise_exception=1)
		conditions += " and dn.posting_date >= '%s'" % filters["from_date"]
		si_cond += " AND si.posting_date >= '%s'" % filters ["from_date"]

	if filters.get("to_date"):
		conditions += " and dn.posting_date <= '%s'" % filters["to_date"]
		si_cond += " AND si.posting_date <= '%s'" % filters ["to_date"]
		
	if filters.get("draft")=="Yes":
		si_cond += " and si.docstatus != 2"
	else:
		si_cond += " and si.docstatus = 1"
	
	if filters.get("trial") == "Yes":
		so_cond = "and so.track_trial = 1"
	else:
		so_cond = "and (so.track_trial <> 1 or so.track_trial is null)"
	
	return conditions, si_cond, so_cond
