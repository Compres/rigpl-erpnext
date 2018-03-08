# -*- coding: utf-8 -*-
# Copyright (c) 2015, Rohit Industries Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.model.document import Document
from datetime import datetime
from frappe.utils import getdate, cint, add_months, date_diff, add_days, nowdate, \
	get_datetime_str, cstr, get_datetime, time_diff, time_diff_in_seconds

class SalarySlipPayment(Document):
	def validate(self):
		self.validate_salary_slip()
	
	def validate_salary_slip(self):
		ssp_date = getdate(self.posting_date)
		for d in self.salary_slip_payment_details:
			
			#Validate if the Salary Slip has not been paid earlier or later
			old_ssp = frappe.db.sql("""SELECT ssp.name, sspd.salary_slip 
				FROM `tabSalary Slip Payment` ssp, `tabSalary Slip Payment Details` sspd
				WHERE ssp.name = sspd.parent AND ssp.docstatus != 2 
				AND sspd.salary_slip = '%s' AND ssp.name != '%s'""" % (d.salary_slip, self.name), as_dict=1)
			if old_ssp:
				old_ssp = old_ssp[0]
				frappe.throw(("Salary Slip {0} is already paid vide Salary Slip \
					Payment # {1} in Row # {2}").format(d.salary_slip, old_ssp.name, d.idx))
			
			#Checks if the same Salary Slip is not entered in the Salary Slip Payment more than once
			for x in self.salary_slip_payment_details:
				if d.salary_slip == x.salary_slip and d.idx != x.idx:
					frappe.throw(("Salary Slip {0} already entered in Row # {1} for Employee {2}")\
					.format(d.salary_slip, x.idx, d.employee_name))
			
			ss = frappe.get_doc("Salary Slip", d.salary_slip)
			d.posting_date = ss.posting_date
			d.employee = ss.employee
			d.employee_name = ss.employee_name
			d.gross_pay = ss.gross_pay
			d.total_deductions = ss.total_deduction
			d.net_pay = ss.net_pay
			d.rounded_pay = ss.rounded_total
			ss_date = getdate(d.posting_date)
			if ss_date != ssp_date:
				frappe.throw(("Posting Date in Row # {1} is different from Posting Date \
				of Salary Slip Payment").format(d.employee, d.idx))

	def on_update(self):
		pass
		'''
		jvd_dict = self.get_jv_accounts()
		chk_jv = self.get_existing_jv()

		#post JV for accrual for later payment on saving
		jv_accrue = frappe.get_doc({
			"doctype": "Journal Entry",
			"entry_type": "Journal Entry",
			"series": "JV1617",
			"user_remark": "Salary/Wages Accural Against Salary Slip Payment #" + self.name,
			"posting_date": self.posting_date,
			"employment_type": self.employment_type,
			"accounts": jvd_dict
			})
		if chk_jv:
			name = chk_jv[0][0]
			jv_exist = frappe.get_doc("Journal Entry", name)
			jv_exist.accounts= []
			for i in jvd_dict:
				jv_exist.append("accounts", i)
			jv_exist.posting_date = self.posting_date
			jv_exist.save()
			frappe.msgprint('{0}{1}'.format("Update JV# ", jv_exist.name))
		else:
			jv_accrue.insert()
			frappe.msgprint('{0}{1}'.format("Created New JV# ", jv_accrue.name))
	'''
	
	def on_submit(self):
		pass
		'''
		chk_jv = self.get_existing_jv()
		if chk_jv:
			name = chk_jv[0][0]
			jv_exist = frappe.get_doc("Journal Entry", name)
			jv_exist.submit()
			frappe.msgprint('{0}{1}'.format("Submitted JV# ", jv_exist.name))
		'''
		
	def on_cancel(self):
		pass
		'''
		chk_jv = self.get_existing_jv()
		
		if chk_jv:
			name = chk_jv[0][0]
			jv_exist = frappe.get_doc("Journal Entry", name)
			jv_exist.cancel()
			frappe.msgprint('{0}{1}'.format("Cancelled JV# ", jv_exist.name))
		'''
		
	def get_existing_jv(self):
		chk_jv = frappe.db.sql("""SELECT jv.name FROM `tabJournal Entry` jv, 
			`tabJournal Entry Account` jva WHERE jva.parent = jv.name AND jv.docstatus != 2 AND
			jva.reference_name = '%s' GROUP BY jv.name"""% self.name, as_list=1)
		return chk_jv
			
	def get_jv_accounts(self):
		earn_dict = {}
		ded_dict = {}
		con_dict = {}
		jvd_dict = []
		total_rounded = 0
		ec_not_posted = 0
		sne = 0
		
		#Below loop would check all the salary slips and get their amounts in total
		#individually for each employee for expenses payable.
		#total rounded is posted in expenses payable with employee individually
		for d in self.salary_slip_payment_details:
			ss = frappe.get_doc("Salary Slip", d.salary_slip)
			exp_payable = 0
			exp_payable = d.rounded_pay
			total_rounded += d.rounded_pay
			arrear = ss.arrear_amount
			leave = ss.leave_encashment_amount
			add = 0
			for e in ss.earnings:
				etype = frappe.get_doc("Salary Component", e.salary_component)
				if e.expense_claim is None and etype.only_for_deductions ==0:
					if etype.account in earn_dict:
						earn_dict[etype.account] += e.amount
						if add == 0:
							earn_dict[etype.account] += arrear + leave
							add = 1
					else:
						earn_dict[etype.account] = e.amount
						if add == 0:
							earn_dict[etype.account] += arrear + leave
							add = 1
										
			for e in ss.earnings:
				etype = frappe.get_doc("Salary Component", e.salary_component)
				if e.expense_claim and etype.only_for_deductions == 0:
					#Check if the Expense Claim is already posted and also is it posted in
					#Expenses Payable or NOT.
					posted = frappe.db.sql("""SELECT name FROM `tabGL Entry` 
						WHERE voucher_type = 'Expense Claim' AND voucher_no = '%s'
						AND docstatus = 1""" %(e.expense_claim), as_list=1)
					#If the expense claim is not posted then post it with SSP else
					#reduce the netpayable by EC amount so that there is balance in JV
					if posted is None:
						exp_claim = frappe.get_doc("Expense Claim", e.expense_claim)
						for ec in exp_claim.expenses:
							ec_type = frappe.get_doc("Expense Claim Type", ec.expense_type)
							if ec_type.default_account in earn_dict:
								earn_dict[ec_type.default_account] += ec.sanctioned_amount
							else:
								earn_dict[ec_type.default_account] = ec.sanctioned_amount
					else:
						ec_not_posted += e.default_amount
						exp_payable = d.rounded_pay - e.default_amount
			jvd_temp = {}
			jvd_temp.setdefault("account", self.salary_slip_accrual_account)
			jvd_temp.setdefault("credit_in_account_currency", exp_payable)
			jvd_temp.setdefault("cost_center", "Default CC Ledger - RIGPL")
			jvd_temp.setdefault("reference_type", "Salary Slip Payment")
			jvd_temp.setdefault("reference_name", self.name)
			jvd_temp.setdefault("party_type", "Employee")
			jvd_temp.setdefault("party", d.employee)
			jvd_dict.append(jvd_temp)
			
			#add for leave encashment and arrears
			#if gross_earn < earn_dict[etype.account]:
			#	earn_dict[etype.account] += (doc.gross_pay - earn_dict[etype.account])
			
			for d in ss.deductions:
				dtype = frappe.get_doc("Salary Component", d.salary_component)
				if d.employee_loan is None:
					if dtype.account in ded_dict:
						ded_dict[dtype.account] += d.amount
					else:
						ded_dict[dtype.account] = d.amount
				elif d.employee_loan:
					eloan = frappe.get_doc("Employee Advance", d.employee_loan)
					if eloan.debit_account in ded_dict:
						ded_dict[eloan.debit_account] += d.amount
					else:
						ded_dict[eloan.debit_account] = d.amount
			
			for c in ss.contributions:
				ctype = frappe.get_doc("Salary Component", c.salary_component)
				if ctype.account in con_dict:
					con_dict[ctype.account] += c.amount
				else:
					con_dict[ctype.account] = c.amount
				
				if ctype.liability_account in con_dict:
					con_dict[ctype.liability_account] += c.amount * (-1)
				else:
					con_dict[ctype.liability_account] = c.amount * (-1)
		total_earn = 0
		total_ded = 0
		total_con = 0
				
		for key in earn_dict:
			jvd_temp = {}
			total_earn += earn_dict[key]
			jvd_temp.setdefault("account", key)
			jvd_temp.setdefault("debit_in_account_currency", earn_dict[key])
			jvd_temp.setdefault("cost_center", "Default CC Ledger - RIGPL")
			jvd_temp.setdefault("reference_type", "Salary Slip Payment")
			jvd_temp.setdefault("reference_name", self.name)
			jvd_dict.append(jvd_temp)
			
		for key in ded_dict:
			jvd_temp = {}
			total_ded += ded_dict[key]
			jvd_temp.setdefault("account", key)
			jvd_temp.setdefault("credit_in_account_currency", ded_dict[key])
			jvd_temp.setdefault("cost_center", "Default CC Ledger - RIGPL")
			jvd_temp.setdefault("reference_type", "Salary Slip Payment")
			jvd_temp.setdefault("reference_name", self.name)
			jvd_dict.append(jvd_temp)
						

		
		sne = total_rounded - (total_earn - total_ded) - ec_not_posted
		if sne < 0:
			jvd_temp = {}
			jvd_temp.setdefault("account", self.rounding_account)
			jvd_temp.setdefault("credit_in_account_currency", sne*(-1))
			jvd_temp.setdefault("cost_center", "Default CC Ledger - RIGPL")
			jvd_temp.setdefault("reference_type", "Salary Slip Payment")
			jvd_temp.setdefault("reference_name", self.name)
			jvd_dict.append(jvd_temp)
		else:
			jvd_temp = {}
			jvd_temp.setdefault("account", self.rounding_account)
			jvd_temp.setdefault("debit_in_account_currency", sne)
			jvd_temp.setdefault("cost_center", "Default CC Ledger - RIGPL")
			jvd_temp.setdefault("reference_type", "Salary Slip Payment")
			jvd_temp.setdefault("reference_name", self.name)
			jvd_dict.append(jvd_temp)
		
		for key in con_dict:
			jvd_temp = {}
			total_con += con_dict[key]
			jvd_temp.setdefault("account", key)
			
			if con_dict[key] < 0:
				jvd_temp.setdefault("credit_in_account_currency", con_dict[key] * (-1))
			else:
				jvd_temp.setdefault("debit_in_account_currency", con_dict[key])
				
			jvd_temp.setdefault("cost_center", "Default CC Ledger - RIGPL")
			jvd_temp.setdefault("reference_type", "Salary Slip Payment")
			jvd_temp.setdefault("reference_name", self.name)
			jvd_dict.append(jvd_temp)
		return jvd_dict
		
	def get_salary_slips(self):

		if not (self.posting_date and self.salary_slip_accrual_account and self.rounding_account):
			msgprint("Posting Date, Salary Slip Accrual Account and Rounding Account \
				 are Mandatory")
			return
		condition_emp = ''
		for d in ['branch', 'department', 'designation']:
			if self.get(d):
				condition_emp += " AND emp." + d + " = '" + self.get(d).replace("'", "\'") + "'"

		query = """SELECT ss.name, ss.employee, ss.employee_name, ss.posting_date,
			ss.gross_pay, ss.net_pay, ss.total_deduction, ss.rounded_total
			FROM `tabSalary Slip` ss, `tabEmployee` emp
			WHERE ss.employee = emp.name AND ss.posting_date = '%s' AND ss.docstatus = 1 %s
			""" % (self.posting_date, condition_emp)

		ss = frappe.db.sql(query, as_dict=1)
					
		self.set('salary_slip_payment_details',[])

		for d in ss:
			exist = frappe.db.sql("""SELECT ssp.name, sspd.salary_slip 
				FROM `tabSalary Slip Payment` ssp, `tabSalary Slip Payment Details` sspd
				WHERE ssp.name = sspd.parent AND ssp.docstatus != 2 
				AND sspd.salary_slip = '%s' AND ssp.name != '%s'""" % (d.name, self.name), as_dict=1)
			if exist:
				pass
			else:
				row = self.append('salary_slip_payment_details', {})
				row.salary_slip = d.name
				row.employee = d.employee
				row.employee_name = d.employee_name
				row.posting_date = d.posting_date
				row.gross_pay = d.gross_pay
				row.net_pay = d.net_pay
				row.rounded_pay = d.rounded_total
				row.total_deductions = d.total_deduction

	def clear_table(self):
		self.set('salary_slip_payment_details',[])
