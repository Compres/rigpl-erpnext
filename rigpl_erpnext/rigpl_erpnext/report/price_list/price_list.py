from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, nowdate

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()
	data = get_item_data(filters)

	return columns, data

def get_columns():
	return [
		"PL ID:Link/Item Price:100", "PL::60", "Item:Link/Item:120", 
		"List Price:Currency:70", "Cur::40", 
		"BM::60", "Brand::60", "QLT::80", "SPL::50", "TT::150",
		"D1:Float:50", "W1:Float:50", "L1:Float:50", "Zn:Float:50", "D2:Float:50",
		"L2:Float:50", "A1:Float:50", "Is PL::50", "Description::400", "ROL:Int:50"
	]

def get_item_data(filters):
	conditions_it = get_conditions(filters)
	bm = filters["bm"]
	pl = " AND itp.price_list = '%s'" % filters.get("pl")
	
	query = """
	SELECT
		IFNULL(itp.name, "-"), IFNULL(itp.price_list, "-"), 
		it.name, itp.price_list_rate, IFNULL(itp.currency, "-"),
		IFNULL(bm.attribute_value, "-"), IFNULL(brand.attribute_value, "-"),
		IFNULL(quality.attribute_value, "-"), IFNULL(spl.attribute_value, "-"),
		IFNULL(tt.attribute_value, "-"),
		CAST(d1.attribute_value AS DECIMAL(8,3)),
		CAST(w1.attribute_value AS DECIMAL(8,3)),
		CAST(l1.attribute_value AS DECIMAL(8,3)),
		CAST(zn.attribute_value AS UNSIGNED),
		CAST(d2.attribute_value AS DECIMAL(8,3)),
		CAST(l2.attribute_value AS DECIMAL(8,3)),
		CAST(a1.attribute_value AS DECIMAL(8,3)), it.pl_item, it.description,
		itr.warehouse_reorder_level
		
	FROM `tabItem` it
	
		LEFT JOIN `tabItem Price` itp ON it.name = itp.item_code %s
		LEFT JOIN `tabItem Variant Attribute` bm ON it.name = bm.parent
			AND bm.attribute = 'Base Material'
		LEFT JOIN `tabItem Variant Attribute` quality ON it.name = quality.parent
			AND quality.attribute = '%s Quality'
		LEFT JOIN `tabItem Variant Attribute` brand ON it.name = brand.parent
			AND brand.attribute = 'Brand'
		LEFT JOIN `tabItem Variant Attribute` tt ON it.name = tt.parent
			AND tt.attribute = 'Tool Type'
		LEFT JOIN `tabItem Variant Attribute` spl ON it.name = spl.parent
			AND spl.attribute = 'Special Treatment'
		LEFT JOIN `tabItem Variant Attribute` d1 ON it.name = d1.parent
			AND d1.attribute = 'd1_mm'
		LEFT JOIN `tabItem Variant Attribute` w1 ON it.name = w1.parent
			AND w1.attribute = 'w1_mm'
		LEFT JOIN `tabItem Variant Attribute` l1 ON it.name = l1.parent
			AND l1.attribute = 'l1_mm'
		LEFT JOIN `tabItem Variant Attribute` d2 ON it.name = d2.parent
			AND d2.attribute = 'd2_mm'
		LEFT JOIN `tabItem Variant Attribute` l2 ON it.name = l2.parent
			AND l2.attribute = 'l2_mm'
		LEFT JOIN `tabItem Variant Attribute` zn ON it.name = zn.parent
			AND zn.attribute = 'Number of Flutes (Zn)'
		LEFT JOIN `tabItem Variant Attribute` a1 ON it.name = a1.parent
			AND a1.attribute = 'a1_deg'
		LEFT JOIN `tabItem Variant Attribute` purpose ON it.name = purpose.parent
			AND purpose.attribute = 'Purpose'
		LEFT JOIN `tabItem Variant Attribute` type ON it.name = type.parent
			AND type.attribute = 'Type Selector'
		LEFT JOIN `tabItem Variant Attribute` mtm ON it.name = mtm.parent
			AND mtm.attribute = 'Material to Machine'
		LEFT JOIN `tabItem Reorder` itr ON it.name = itr.parent
			AND itr.warehouse = it.default_warehouse
	
	WHERE
		IFNULL(it.end_of_life, '2099-12-31') > CURDATE() %s
	
	ORDER BY bm.attribute_value, brand.attribute_value,
		quality.attribute_value, tt.attribute_value,
		CAST(d1.attribute_value AS DECIMAL(8,3)) ASC,
		CAST(w1.attribute_value AS DECIMAL(8,3)) ASC,
		CAST(l1.attribute_value AS DECIMAL(8,3)) ASC,
		CAST(zn.attribute_value AS UNSIGNED) ASC,
		CAST(d2.attribute_value AS DECIMAL(8,3)) ASC,
		CAST(l2.attribute_value AS DECIMAL(8,3)) ASC,
		spl.attribute_value""" %(pl, bm, conditions_it)
	
	data = frappe.db.sql(query , as_list=1)

	return data


def get_conditions(filters):
	conditions_it = ""

	if filters.get("bm"):
		conditions_it += " AND bm.attribute_value = '%s'" % filters["bm"]

	if filters.get("brand"):
		conditions_it += " AND brand.attribute_value = '%s'" % filters["brand"]

	if filters.get("quality"):
		conditions_it += " AND quality.attribute_value = '%s'" % filters["quality"]

	if filters.get("spl"):
		conditions_it += " AND spl.attribute_value = '%s'" % filters["spl"]
		
	if filters.get("purpose"):
		conditions_it += " AND purpose.attribute_value = '%s'" % filters["purpose"]
		
	if filters.get("type"):
		conditions_it += " AND type.attribute_value = '%s'" % filters["type"]
		
	if filters.get("mtm"):
		conditions_it += " AND mtm.attribute_value = '%s'" % filters["mtm"]
		
	if filters.get("tt"):
		conditions_it += " AND tt.attribute_value = '%s'" % filters["tt"]

	if filters.get("item"):
		conditions_it += " AND it.name = '%s'" % filters["item"]
		
	if filters.get("template"):
		conditions_it += " AND it.variant_of = '%s'" % filters["template"]

	if filters.get("is_pl"):
		conditions_it += " AND it.pl_item = 'Yes'"
		
	return conditions_it
