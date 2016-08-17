from __future__ import unicode_literals
import frappe
from datetime import datetime
from frappe.utils import flt

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	items, item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_map(filters, items)
	pl_map = get_pl_map(filters, items)
	value_map = get_value_map(filters, items)
	lpr_map = get_lpr_map(filters, items)

	data = []
	for item in sorted(iwb_map):
		for wh in sorted(iwb_map[item]):
			qty_dict = iwb_map[item][wh]
			if qty_dict.bal_qty > 0:
				data.append([item,item_map[item]["desc"], wh,
				qty_dict.bal_qty,
				pl_map.get(item,{}).get("LP"),
				qty_dict.val_rate,
				qty_dict.value,
				item_map[item]["bm"],
				item_map[item]["quality"], item_map[item]["tt"],
				item_map[item]["d1"], item_map[item]["w1"],
				item_map[item]["l1"], item_map[item]["d2"],
				item_map[item]["l2"], item_map[item]["rm"],
				item_map[item]["brand"],
				value_map.get(item,{}).get("vr"),
				lpr_map.get(item,{}).get("lpr")
				])
				

	return columns, data

def get_columns(filters):
	"""return columns based on filters"""

	columns = ["Item:Link/Item:120"] + ["Description::300"] + \
	["Warehouse:Link/Warehouse:150"] + ["Quantity:Float:80"] + ["List Price:Currency:80"] + \
	["VR:Currency:80"] + ["Value:Currency:100"] + \
	["BM::80"] + ["Qual::80"] +["TT::120"] + ["D1:Float:50"] + \
	["W1:Float:50"] + ["L1:Float:60"] + ["D2:Float:50"] + \
	["L2:Float:60"] + ["Is RM::50"] + ["Brand::60"] + ["Set Value:Currency:80"] + \
	["Last PO Price:Currency:80"]

	return columns

#get all details
def get_stock_ledger_entries(filters, items):
	
	
	return frappe.db.sql("""SELECT sle.item_code, sle.warehouse,
		sle.posting_date, sle.posting_time, sle.qty_after_transaction ,
		sle.valuation_rate, sle.stock_value
		FROM `tabStock Ledger Entry` sle
		WHERE IFNULL(sle.is_cancelled, 'No') = 'No' {condition}
			AND sle.item_code IN (%s)
		ORDER BY sle.posting_date, sle.posting_time,
			sle.item_code, sle.warehouse, sle.name""".format(condition=conditions) %(", ".join(['%s']*len(items))), \
		tuple([d.name for d in items]), as_dict=1)

def get_item_warehouse_map(filters, items):
	iwb_map = {}
	test = {}
	conditions, conditions_it = get_conditions(filters)
	wh = frappe.db.sql("""SELECT name FROM `tabWarehouse` WHERE disabled = 'No' AND is_group = 0
		ORDER BY name""", as_list=1)
	
	for w in wh:
		for it in items:

			query = """SELECT sle.item_code, sle.warehouse, sle.posting_date, 
				sle.posting_time, sle.qty_after_transaction as balance, sle.valuation_rate,
				sle.stock_value FROM `tabStock Ledger Entry` sle
				WHERE IFNULL(sle.is_cancelled, 'No') = 'No'
				AND sle.warehouse = '%s' AND sle.item_code = '%s' %s
				ORDER BY sle.posting_date DESC, sle.posting_time DESC
				LIMIT 1"""%(w[0], it.name, conditions)

			entries = frappe.db.sql(query, as_dict=1)

			if entries:
				iwb_map.setdefault(entries[0].item_code, {}).setdefault(entries[0].warehouse, \
				frappe._dict({"bal_qty": entries[0].balance, "val_rate": entries[0].valuation_rate, \
				"value": entries[0].stock_value}))
	return iwb_map

def get_item_details(filters):
	conditions, conditions_it = get_conditions(filters)
	item_map = {}
	query = """SELECT it.name AS "name", it.description AS "desc",
		IFNULL(bm.attribute_value, "-") AS "bm", IFNULL(brand.attribute_value, "-") AS "brand",
		IFNULL(h_qual.attribute_value, IFNULL (c_qual.attribute_value, "-")) AS "quality",
		IFNULL(tt.attribute_value, "-") AS "tt",
		CAST(d1.attribute_value AS DECIMAL(8,3)) AS "d1",
		CAST(w1.attribute_value AS DECIMAL(8,3)) AS "w1",
		CAST(l1.attribute_value AS DECIMAL(8,3)) AS "l1",
		CAST(d2.attribute_value AS DECIMAL(8,3)) AS "d2",
		CAST(l2.attribute_value AS DECIMAL(8,3)) AS "l2",
		IFNULL(rm.attribute_value, "-") AS "rm"
		FROM `tabItem` it
		LEFT JOIN `tabItem Variant Attribute` rm ON it.name = rm.parent
			AND rm.attribute = 'Is RM'
		LEFT JOIN `tabItem Variant Attribute` bm ON it.name = bm.parent
			AND bm.attribute = 'Base Material'
		LEFT JOIN `tabItem Variant Attribute` h_qual ON it.name = h_qual.parent
			AND h_qual.attribute = 'HSS Quality'
		LEFT JOIN `tabItem Variant Attribute` c_qual ON it.name = c_qual.parent
			AND c_qual.attribute = 'Carbide Quality'
		LEFT JOIN `tabItem Variant Attribute` brand ON it.name = brand.parent
			AND brand.attribute = 'Brand'
		LEFT JOIN `tabItem Variant Attribute` tt ON it.name = tt.parent
			AND tt.attribute = 'Tool Type'
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
		WHERE IFNULL(it.end_of_life, '2099-12-31') > CURDATE() %s""" %conditions_it
	
	items = frappe.db.sql(query , as_dict = 1)
	if items:
		pass
	else:
		frappe.throw("No Items Found in given Criterion")
	for d in items:item_map.setdefault(d.name, d)
	return items, item_map

def get_pl_map(filters, items):
	if filters.get("pl"):
		conditions = " p.price_list = '%s'" % filters["pl"]
	pl_map_int = frappe.db.sql ("""SELECT p.item_code, p.price_list, p.price_list_rate AS LP
		FROM `tabItem Price` p
		WHERE {condition} AND p.item_code IN (%s)""".format(condition=conditions) \
		%(", ".join(['%s']*len(items))), tuple([d.name for d in items]), as_dict=1)
	pl_map={}

	for d in pl_map_int:
		pl_map.setdefault(d.item_code,d)
	return pl_map

def get_value_map(filters, items):
	if filters.get("pl"):
		conditions = " v.price_list = '%s'" %filters["pl"]
		
	value_map_int = frappe.db.sql ("""SELECT v.item_code, v.price_list, v.valuation_rate AS vr
	FROM `tabValuation Rate` v
	WHERE {condition} AND v.disabled = 'No' AND v.item_code IN (%s)""".format(condition=conditions)\
	%(", ".join(['%s']*len(items))), tuple([d.name for d in items]), as_dict=1)
	
	value_map={}
	for d in value_map_int:
		value_map.setdefault(d.item_code,d)

	return value_map
	
def get_lpr_map(filters, items):
	lpr_map={}
	cond_po = " AND pr.posting_date <= '%s'" %filters["date"]
	for it in items:
		grn = frappe.db.sql("""SELECT pri.item_code, pri.base_net_rate AS lpr
			FROM `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pri
			WHERE pr.name = pri.parent AND pri.item_code = '%s' %s
			ORDER BY pr.posting_date DESC
			LIMIT 1"""%(it.name, cond_po), as_dict=1)
		if grn:
			lpr_map.setdefault(grn[0].item_code, frappe._dict({"lpr": grn[0].lpr}))
	return lpr_map
	
def get_conditions(filters):
	conditions = ""
	conditions_it = ""
	if filters.get("item"):
		conditions += " AND sle.item_code='%s'" % filters["item"]
		conditions_it += " AND it.name ='%s'" % filters["item"]

	if filters.get("warehouse"):
		conditions += " AND sle.warehouse='%s'" % filters["warehouse"]

	if filters.get("date"):
		conditions += " AND sle.posting_date <= '%s'" % filters["date"]

	if filters.get("rm"):
		conditions_it += " AND rm.attribute_value = '%s'" % filters["rm"]

	if filters.get("bm"):
		conditions_it += " AND bm.attribute_value = '%s'" % filters["bm"]

	if filters.get("brand"):
		conditions_it += " AND brand.attribute_value = '%s'" % filters["brand"]
		
	if filters.get("tt"):
		conditions_it += " AND tt.attribute_value = '%s'" % filters["tt"]
		
	return conditions, conditions_it