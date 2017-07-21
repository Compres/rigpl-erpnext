# -*- coding: utf-8 -*-
# Copyright (c) 2015, Rohit Industries Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.controllers.item_variant import (get_variant, copy_attributes_to_variant,
	make_variant_item_code, validate_item_variant_attributes, ItemVariantExistsError)
import json

#Run this script every hour but to ensure that there is no server overload run it only for 1 template at a time

def check_wrong_variants():
	limit_set = int(frappe.db.get_single_value("Stock Settings", "automatic_sync_field_limit"))
	is_sync_allowed = frappe.db.get_single_value("Stock Settings", 
		"automatically_sync_templates_data_to_items")
	if is_sync_allowed == 1:
		templates = frappe.db.sql("""SELECT it.name, (SELECT count(name) 
			FROM `tabItem` WHERE variant_of = it.name) 
			FROM `tabItem` it WHERE it.has_variants = 1 
			AND it.disabled = 0 AND it.end_of_life >= CURDATE()
			ORDER BY (SELECT count(name) FROM `tabItem` 
				WHERE variant_of = it.name) ASC""", as_list=1)
		fields_edited = 0
		for t in templates:
			print (str(t[0]) + " Has No of Variants = " + str(t[1]))
			if fields_edited <= limit_set:
				temp_doc = frappe.get_doc("Item", t[0])
				variants = frappe.db.sql("""SELECT name FROM `tabItem` WHERE variant_of = '%s'
					ORDER BY modified DESC"""%(t[0]), as_list=1)
				#Check all variants' fields are matching with template if 
				#not then copy the fields else go to next item
				for item in variants:
					print ("Checking Item = " + item[0])
					it_doc = frappe.get_doc("Item", item[0])
					fields_edited += check_and_copy_attributes_to_variant(temp_doc, it_doc)
					#print (str(fields_edited) + " ##################")
			else:
				print ("Limit of " + str(limit_set) + " fields reached. Run again for more updating")
				break
				


def check_and_copy_attributes_to_variant(template, variant):
	from frappe.model import no_value_fields
	check = 0
	save_chk = 0
	exclude_fields = ["item_code", "item_name", "show_in_website", "variant_of", "has_variants", 
		"description", "web_long_description", "item_variant_restrictions", "show_in_website",
		"show_variant_in_website", "website_specifications", "brand", "thumbnail"]
	for field in template.meta.fields:
		# "Table" is part of `no_value_field` but we shouldn't ignore tables
		if (field.fieldtype == 'Table' or field.fieldtype not in no_value_fields) \
			and (not field.no_copy) and field.fieldname not in exclude_fields:
			if variant.get(field.fieldname) != template.get(field.fieldname):
				variant.set(field.fieldname, template.get(field.fieldname))
				save_chk = 1
				print ("Updated Item " + variant.name + " Field Changed = " + str(field.label) + 
					" Updated Value to " + str(template.get(field.fieldname)))
				check += 1
	if save_chk == 1:
		variant.save()
		print ("Item Code " + variant.name + " Saved")
	return check
