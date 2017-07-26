# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import msgprint

def validate(doc,method):
	update_fields(doc,method)
	check_gst_rules(doc,method)
	check_delivery_note_rule(doc,method)
	validate_carrier_tracking(doc,method)


def check_delivery_note_rule(doc,method):
	'''
	1. No Sales Invoice without Delivery Note to be mentioned without UPDATE stock, basically \
		above rule is to ensure that if a DN is not made then STOCK is updated via SI
	2. No Partial DN to be ALLOWED to be BILL, this is because if a customer's DN is for 100pcs of
		one item and we send 50pcs then balance 50pcs he can deny especially for Special Items its
		a problem
	3. Also ensure that if there are 5 items in DN then all 5 items are in the SI with equal quantities
	4. Remove the Trial Rule which means NO INVOICING with TT SUBMITTED should be REMOVED.
	5. Disallow making a Sales Invoice for Items without SO but only DN, that is you make DN \
		without SO and then make INVOICE is not POSSIBLE, means you SO => DN => SI or only SI also
		denies SO => SI
	'''
	list_of_dns = []
	list_of_dn_details = []
	
	for d in doc.items:
		if d.delivery_note not in list_of_dns:
			list_of_dns.extend([d.delivery_note])
		
		if d.dn_detail not in list_of_dn_details:
			list_of_dn_details.extend([d.dn_detail])
			
		if d.sales_order is not None:
			if d.delivery_note is None:
				#Rule no.5 in the above description for disallow SO=>SI no skipping DN
				frappe.msgprint(("""Error in Row# {0} has SO# {1} but there is no DN.
				Hence making of Invoice is DENIED""").format(d.idx, d.sales_order), \
				raise_exception=1)
		elif d.delivery_note is not None:
			if d.sales_order is None:
				frappe.msgprint(("""Error in Row# {0} has DN# {1} but there is no SO.
				Hence making of Invoice is DENIED""").format(d.idx, d.delivery_note), \
				raise_exception=1)
			
			#Check the quantity of Invoice is EQUAL to the DN quantity and also check if 
			#the FULL DN is being invoices
			#Below code would check if the items are based on DN or NOT
			#If SI is NOT BASED on DN then it would ensure that the SI has the 
			#update stock button checked.
			
			dn = frappe.get_doc("Delivery Note", d.delivery_note)
			if dn is not None:
				for dnd in dn.items:
					if dnd.name == d.dn_detail:
						if d.qty > 0:
							if dnd.qty != d.qty:
								frappe.msgprint(("""Invoice Qty should be equal to DN Qty \
									in line # {0}""").format(d.idx), raise_exception=1)

	if len(list_of_dns)==1 and list_of_dns[0] == None:
		if doc.update_stock != 1:
			for d in doc.items:
				if d.qty > 0:
					frappe.msgprint("Please check the Update Stock Button since Items are \
						not based on DN", raise_exception=1)
	elif len(list_of_dns)>1:
		for i in range(len(list_of_dns)):
			if list_of_dns[i] is None:
				frappe.msgprint(("""Not allowed to enter items without DN make another invoice \
					for such items check line # {0}""").format((d.idx)+1), raise_exception=1)
			else:
				dn = frappe.get_doc("Delivery Note", list_of_dns[i])
				for d in dn.items:
					if d.name not in list_of_dn_details:
						frappe.msgprint(("""Item Code {0} in DN# {1} is not mentioned in \
						the Invoice""").format(d.item_code, dn.name), raise_exception=1)

def check_gst_rules(doc,method):
	series_template = frappe.db.get_value("Sales Taxes and Charges Template", \
		doc.taxes_and_charges ,"series")
		
	#Check series of Tax with the Series Selected for Invoice
	if series_template != doc.naming_series[:2] and series_template != doc.name[:2]:
		frappe.throw(("Selected Tax Template {0} Not Allowed since Series Selected {1} and \
			Invoice number {2} don't match with the Selected Template").format( \
			doc.taxes_and_charges, doc.naming_series, doc.name))
	

def update_fields(doc,method):
	c_form_tax =frappe.db.get_value("Sales Taxes and Charges Template", doc.taxes_and_charges , \
		"c_form_applicable")
	letter_head_tax = frappe.db.get_value("Sales Taxes and Charges Template", \
		doc.taxes_and_charges, "letter_head")
	
	doc.c_form_applicable = c_form_tax
	doc.letter_head = letter_head_tax

def on_submit(doc,method):
	create_new_carrier_track(doc,method)
	user = frappe.session.user
	query = """SELECT role from `tabUserRole` where parent = '%s' """ %user
	roles = frappe.db.sql(query, as_list=1)
	
	for d in doc.items:
		if d.sales_order is None:
			if d.delivery_note is None:
				if doc.ignore_pricing_rule == 1:
					if any("System Manager" in s  for s in roles):
						pass
					else:
						frappe.msgprint("You are not Authorised to Submit this Transaction \
						ask a System Manager", raise_exception=1)
		if d.sales_order is not None:
			so = frappe.get_doc("Sales Order", d.sales_order)
			if so.track_trial == 1:
				dnd = frappe.get_doc("Delivery Note Item", d.dn_detail)
				sod = dnd.so_detail
				query = """SELECT tt.name FROM `tabTrial Tracking` tt where \
					tt.prevdoc_detail_docname = '%s' """ % sod
				name = frappe.db.sql(query, as_list=1)
				if name:
					tt = frappe.get_doc("Trial Tracking", name[0][0])
					frappe.db.set(tt, 'invoice_no', doc.name)

def on_cancel(doc,method):
	for d in doc.items:
		if d.sales_order is not None:
			so = frappe.get_doc("Sales Order", d.sales_order)
			if so.track_trial == 1:
				dnd = frappe.get_doc("Delivery Note Item", d.dn_detail)
				sod = dnd.so_detail
				query = """SELECT tt.name FROM `tabTrial Tracking` tt where \
					tt.prevdoc_detail_docname = '%s' """ % sod
				name = frappe.db.sql(query, as_list=1)
				if name:
					tt = frappe.get_doc("Trial Tracking", name[0][0])
					frappe.db.set(tt, 'invoice_no', None)

def validate_carrier_tracking(doc,method):
	tracked_transporter = is_tracked_transporter(doc,method)
	if tracked_transporter == 1:
		frappe.msgprint(("{0} is Tracked Automatically all Shipment Data for LR No {1} \
				would be automatically updated in Carrier Tracking Document").format(
				frappe.get_desk_link('Transporters', doc.transporters), doc.lr_no))
	return tracked_transporter

def create_new_carrier_track(doc,method):
	#If SI is from Cancelled Doc then update the Existing Carrier Track
	is_tracked = is_tracked_transporter(doc,method)
	if is_tracked == 1:
		if doc.amended_from:
			existing_track = check_existing_track(doc.amended_from)
			if existing_track:
				exist_track = frappe.get_doc("Carrier Tracking", existing_track[0][0])
				exist_track.awb_number = doc.lr_no
				exist_track.receiver_name = doc.customer
				exist_track.document_name = doc.name
				exist_track.carrier_name = doc.transporters
				exist_track.flags.ignore_permissions = True
				exist_track.save()
				frappe.msgprint(("Updated {0}").format(frappe.get_desk_link('Carrier Tracking', exist_track.name)))
			else:
				create_new_ship_track(doc)

		elif check_existing_track(doc.name) is None:
			#Dont create a new Tracker if already exists
			create_new_ship_track(doc)

def create_new_ship_track(si_doc):
	track = frappe.new_doc("Carrier Tracking")
	track.carrier_name = si_doc.transporters
	track.awb_number = si_doc.lr_no
	track.receiver_document = "Customer"
	track.receiver_name = si_doc.customer
	track.document = "Sales Invoice"
	track.document_name = si_doc.name
	track.flags.ignore_permissions = True
	track.insert()
	frappe.msgprint(("Created New {0}").format(frappe.get_desk_link('Carrier Tracking', track.name)))

def check_existing_track(si_name):
	exists = frappe.db.sql("""SELECT name FROM `tabCarrier Tracking` WHERE document = 'Sales Invoice' AND 
		document_name = '%s'""" %(si_name))
	if exists:
		return exists

def is_tracked_transporter(doc,method):
	ttrans = frappe.get_value ("Transporters", doc.transporters, "track_on_shipway")
	return ttrans
