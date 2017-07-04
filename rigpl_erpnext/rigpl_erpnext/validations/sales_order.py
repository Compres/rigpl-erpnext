# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import msgprint

def validate(doc,method):
	update_fields(doc,method)
	check_gst_rules(doc,method)

def update_fields(doc,method):
	letter_head_tax = frappe.db.get_value("Sales Taxes and Charges Template", \
		doc.taxes_and_charges, "letter_head")
	doc.letter_head = letter_head_tax
	
	for items in doc.items:
		custom_tariff = frappe.db.get_value("Item", items.item_code, "customs_tariff_number")
		if custom_tariff:
			if len(custom_tariff) == 8:
				items.cetsh_number = custom_tariff 
			else:
				frappe.throw(("Item Code {0} in line# {1} has a Custom Tariff {2} which not  \
					8 digit, please get the Custom Tariff corrected").\
					format(items.item_code, items.idx, custom_tariff))
		else:
			frappe.throw(("Item Code {0} in line# {1} does not have linked Customs \
				Tariff in Item Master").format(items.item_code, items.idx))

def check_gst_rules(doc,method):
	ship_state = frappe.db.get_value("Address", doc.shipping_address_name, "state_rigpl")
	template_doc = frappe.get_doc("Sales Taxes and Charges Template", doc.taxes_and_charges)
	ship_country = frappe.db.get_value("Address", doc.shipping_address_name, "country")
	
	series_template = frappe.db.get_value("Sales Taxes and Charges Template", \
		doc.taxes_and_charges ,"series")
		
	#Check series of Tax with the Series Selected for Invoice
	if series_template != doc.naming_series[2:4] and series_template != doc.name[2:4]:
		frappe.throw(("Selected Tax Template {0} Not Allowed since Series Selected {1} and \
			Invoice number {2} don't match with the Selected Template").format( \
			doc.taxes_and_charges, doc.naming_series, doc.name))
			
	#Check if Shipping State is Same as Template State then check if the tax template is LOCAL
	#Else if the States are different then the template should NOT BE LOCAL
	if ship_state == template_doc.state:
		if template_doc.is_local_sales != 1:
			frappe.throw(("Selected Tax {0} is NOT LOCAL Tax but Shipping Address is \
				in Same State {1}, hence either change Shipping Address or Change the \
				Selected Tax").format(doc.taxes_and_charges, ship_state))
	elif ship_country == 'India' and ship_state != template_doc.state:
		if template_doc.is_local_sales == 1:
			frappe.throw(("Selected Tax {0} is LOCAL Tax but Shipping Address is \
				in Different State {1}, hence either change Shipping Address or Change the \
				Selected Tax").format(doc.taxes_and_charges, ship_state))
	elif ship_country != 'India': #Case of EXPORTS
		if template_doc.state is not None and template_doc.is_exports != 1:
			frappe.throw(("Selected Tax {0} is for Indian Sales but Shipping Address is \
				in Different Country {1}, hence either change Shipping Address or Change the \
				Selected Tax").format(doc.taxes_and_charges, ship_country))

def on_submit(so,method):
	if so.track_trial == 1:
		no_of_team = 0
		
		for s_team in so.get("sales_team"):
			no_of_team = len(so.get("sales_team"))
		
		if no_of_team <> 1:
			frappe.msgprint("Please enter exactly one Sales Person who is responsible for carrying out the Trials", raise_exception=1)
		
		for sod in so.get("items"):
			tt=frappe.new_doc("Trial Tracking")
			tt.prevdoc_detail_docname = sod.name
			tt.against_sales_order = so.name
			tt.customer = so.customer
			tt.item_code = sod.item_code
			tt.qty = sod.qty
			tt.description = sod.description
			tt.base_rate = sod.base_rate
			tt.trial_owner = s_team.sales_person
			tt.status = "In Production"
			tt.insert()
			query = """SELECT tt.name FROM `tabTrial Tracking` tt where tt.prevdoc_detail_docname = '%s' """ % sod.name
			name = frappe.db.sql(query, as_list=1)
			frappe.msgprint('{0}{1}'.format("Created New Trial Tracking Number: ", name[0][0]))
			
			
def on_cancel(so, method):
	if so.track_trial == 1:
		for sod in so.get("items"):
			query = """SELECT tt.name FROM `tabTrial Tracking` tt where tt.prevdoc_detail_docname = '%s' """ % sod.name
			name = frappe.db.sql(query, as_list=1)
			if name:
				frappe.delete_doc("Trial Tracking", name[0])
				frappe.msgprint('{0}{1}'.format("Deleted Trial Tracking No: ", name[0][0]))
