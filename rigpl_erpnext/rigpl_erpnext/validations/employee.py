# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import msgprint
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

def validate(doc,method):
	#Validation for Age of Employee should be Greater than 18 years at the time of Joining.
	dob = datetime.strptime(doc.date_of_birth, "%Y-%m-%d")
	doj = datetime.strptime(doc.date_of_joining, "%Y-%m-%d")
	if relativedelta(doj, dob).years < 18:
		frappe.msgprint("Not Allowed to Create Employees under 18 years of Age", raise_exception = 1)
	if doc.relieving_date:
		if doc.relieving_date < time.strftime("%Y-%m-%d"):
			if doc.status <> "Left":
				frappe.msgprint("Status has to be 'LEFT' as the Relieving Date is populated",raise_exception =1)
	#Generate employee number on the following logic
	#Employee Number would be YYYYMMDDXXXXC, where:
	#YYYYMMDD = Date of Joining in YYYYMMDD format
	#XXXX = Serial Number of the employee from the ID this is NUMBERIC only
	#C= Check DIGIT
	if doc.date_of_joining:
		doj = doc.date_of_joining[:4]+doc.date_of_joining[5:7]
		id = ""
		for i in range(len(doc.name)):
			if doc.name[i].isdigit():
				id = id+doc.name[i]
		code = doj+id
		check = fn_check_digit(doc, code)
		code = code + str(check)
		doc.employee_number = code

		
###############~Code to generate the CHECK DIGIT~###############################
#Link: https://wiki.openmrs.org/display/docs/Check+Digit+Algorithm
################################################################################
def fn_check_digit(doc,id_without_check):

	# allowable characters within identifier
	valid_chars = "0123456789ABCDEFGHJKLMNPQRSTUVYWXZ"

	# remove leading or trailing whitespace, convert to uppercase
	id_without_checkdigit = id_without_check.strip().upper()

	# this will be a running total
	sum = 0;

	# loop through digits from right to left
	for n, char in enumerate(reversed(id_without_checkdigit)):

			if not valid_chars.count(char):
					raise Exception('InvalidIDException')

			# our "digit" is calculated using ASCII value - 48
			digit = ord(char) - 48

			# weight will be the current digit's contribution to
			# the running total
			weight = None
			if (n % 2 == 0):

					# for alternating digits starting with the rightmost, we
					# use our formula this is the same as multiplying x 2 &
					# adding digits together for values 0 to 9.  Using the
					# following formula allows us to gracefully calculate a
					# weight for non-numeric "digits" as well (from their
					# ASCII value - 48).
					weight = (2 * digit) - int((digit / 5)) * 9
			else:
					# even-positioned digits just contribute their ascii
					# value minus 48
					weight = digit

			# keep a running total of weights
			sum += weight

	# avoid sum less than 10 (if characters below "0" allowed,
	# this could happen)
	sum = abs(sum) + 10

	# check digit is amount needed to reach next number
	# divisible by ten. Return an integer
	return int((10 - (sum % 10)) % 10)
