# -*- coding: utf-8 -*-
# Copyright (c) 2018, Rohit Industries Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import shippo
from frappe.model.document import Document

class BookShipment(Document):
	def validate(self):
		shippo.api_key = 'shippo_test_f5d185588211112c34bad49fcaac3f52372b8fb6'
		from_address_doc = frappe.get_doc("Address", self.from_address)
		to_address_doc = frappe.get_doc("Address", self.to_address)
		address_from = {
		    "name": from_address_doc.address_title,
		    "company": from_address_doc.address_title,
		    "street1": from_address_doc.address_line1,
		    "street2": from_address_doc.address_line2,
		    "city": from_address_doc.city,
		    "state": from_address_doc.state,
		    "zip": from_address_doc.pincode,
		    "country": from_address_doc.country,
		    "phone": from_address_doc.phone,
		    "email": from_address_doc.email_id
			}
		address_to = {
		    "name": to_address_doc.address_title,
		    "company": to_address_doc.address_title,
		    "street1": to_address_doc.address_line1,
		    "street2": to_address_doc.address_line2,
		    "city": to_address_doc.city,
		    "state": to_address_doc.state,
		    "zip": to_address_doc.pincode,
		    "country": to_address_doc.country,
		    "phone": to_address_doc.phone,
		    "email": to_address_doc.email_id
			}
		parcels = {}
		for pkg in self.shipment_package_details:
			package_doc = frappe.get_doc("Shipment Package", pkg.shipment_package)
			parcels["parcel_" + str(pkg.idx)] = {
				"length": package_doc.length,
				"width": package_doc.width,
				"height": package_doc.height,
				"distance_unit": package_doc.uom,
				"weight": pkg.package_weight,
				"mass_unit": pkg.weight_uom
			}

		final_pkgs = []
		for pkgs in parcels:
			pkg = parcels.get(pkgs)
			final_pkgs.append(pkg.copy())
		frappe.msgprint(str(final_pkgs))

		shipment = shippo.Shipment.create(
		    address_from = address_from,
		    address_to = address_to,
		    parcels = final_pkgs,
		    async = False
		)
		frappe.msgprint(str(shipment))
