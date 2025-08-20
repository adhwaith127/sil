import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate
from datetime import datetime
import json
import traceback
import sil.services.sales_invoice_api as sales_invoice_api
import sil.services.sales_order_api as sales_order_api

class PaymentEntryError(Exception):

    """Custom exception for Payment Entry errors."""

    pass


def get_cost_centers_by_company(company_name):
    cost_centers = frappe.get_all("Cost Center", filters={"company": company_name}, fields=["name", "cost_center_name"])

    return cost_centers


@frappe.whitelist(allow_guest=True)
def getAllPaymentReceiptDetails():
    try:
        query = """
                SELECT *
                FROM `tabPayment Receipt` 
            """               
        return frappe.db.sql(query, as_dict=True)  

    except Exception as e:
        frappe.log_error()
        return []



@frappe.whitelist(allow_guest=True)
def getAllPaymentEntryDetails():
    try:
        query = """
                SELECT *
                FROM `tabSIL Payment Details` 
            """               
        return frappe.db.sql(query, as_dict=True) 

    except Exception as e:
        frappe.log_error()
        return []


@frappe.whitelist(allow_guest=True)
def get_payment_details():
    try:
        # Fetch all payment receipts
        receipts_query = """
            SELECT *
            FROM `tabPayment Receipt`
        """
        payment_receipts = frappe.db.sql(receipts_query, as_dict=True)

        # Fetch all SIL payment details
        payment_details_query = """
            SELECT *
            FROM `tabSIL Payment Details`
        """
        payment_details = frappe.db.sql(payment_details_query, as_dict=True)

        # Group payment details by parent
        details_by_parent = {}
        for detail in payment_details:
            parent = detail.get('parent')
            if parent not in details_by_parent:
                details_by_parent[parent] = []
            details_by_parent[parent].append(detail)

        # Combine the data in a nested structure
        for receipt in payment_receipts:
            receipt['payment_details'] = details_by_parent.get(receipt['name'], [])

        # Filter out internal transfers
        payment_receipts = [receipt for receipt in payment_receipts if receipt.get('payment_type') != 'Internal Transfer']

        return payment_receipts

    except Exception as e:
        # Log the error with additional details
        frappe.log_error(message=str(e), title="Error in get_combined_payment_details_nested")
        return []


"""
for inserting the payment details from the 'Payment Receipt' doctype
"""
@frappe.whitelist(allow_guest=True)
def create_entries_payment(customer, paid_amount, payment_date, mode_of_payment, references):
    try:
        # Validate inputs
        if not all([customer, paid_amount > 0, payment_date, mode_of_payment, references]):
            raise ValueError("Invalid input parameters")

        # Create a new Payment Entry document
        payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': 'Receipt',  # Receipt for Customer payments
            'party_type': 'Customer',   # Payment is from a customer
            'party': customer,          # Customer name
            'paid_amount': paid_amount, # Total paid amount
            'payment_date': payment_date, # Date of payment
            'mode_of_payment': mode_of_payment,  # Mode of payment
            'posting_date': payment_date,  # Posting Date
        })

        # Loop through the references to add multiple entries to the Payment Entry
        for ref in references:
            # Validate reference details
            if not all([ref.get('reference_doctype'), ref.get('reference_name'), ref.get('total_amount'), ref.get('outstanding_amount'), ref.get('allocated_amount')]):
                raise ValueError("Invalid reference details")

            # Add Payment Entry References (e.g., linking to invoices or sales orders)
            payment_entry.append('references', {
                'reference_doctype': ref['reference_doctype'],  # Invoice or Sales Order
                'reference_name': ref['reference_name'],        # The name of the reference (e.g., SO-0001 or INV-0001)
                'total_amount': ref['total_amount'],             # The total amount for this reference
                'outstanding_amount': ref['outstanding_amount'], # The outstanding amount for this reference
                'allocated_amount': ref['allocated_amount'],     # The amount allocated from this payment
            })
        
        # Insert the document to save it to the database
        payment_entry.insert()

        # Optionally, submit the Payment Entry if required
        payment_entry.submit()

        # Return a success message with the Payment Entry name
        return {'status': 'success', 'message': 'Payment Entry created successfully with multiple references', 'payment_entry_name': payment_entry.name}

    except ValueError as e:
        frappe.log_error(frappe.get_traceback(), f"Payment Entry Error for Customer: {customer}")
        return {'status': 'error', 'message': str(e)}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Payment Entry Error for Customer: {customer}")
        return {'status': 'error', 'message': str(e)}



@frappe.whitelist()
def update_status_in_payment_info(doc_name, new_value):
    """
    Update a field value in a specific DocType.
    
    :param doc_name: Name of the document (record) to update.
    :param field_name: Name of the field to update.
    :param new_value: The new value to assign to the field.
    """
    try:
        # Fetch the document
        doc = frappe.get_doc('Payment Intimation', doc_name)
        
        # Update the field value
        if hasattr(doc, 'custom_status'):
            setattr(doc, 'custom_status', new_value)
        else:
            frappe.throw(_("Field custom_status does not exist in the DocType"))
        
        # Save the document with the updated field
        doc.save()
        
        # Optionally, commit changes to the database immediately
        frappe.db.commit()
        
        return {
            "status": "Success",
            "message": _("Field custom_status updated successfully.")
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Update Field Error")
        frappe.throw(_("An error occurred while updating the field: {0}").format(str(e)))     


def validate_inputs(payment_type, customer, invoice_name, payment_amount, payment_account):
    """Validate input parameters."""
    if not all([customer, invoice_name, payment_amount > 0, payment_account, payment_type]):
        raise PaymentEntryError("Invalid input parameters")


def get_exchange_rates(account_currency, company_currency):
    """Fetch exchange rates based on the currencies."""
    target_exchange_rate = 1.0
    source_exchange_rate = 1.0
    if account_currency and account_currency != company_currency:
        target_exchange_rate = frappe.db.get_value("Currency Exchange", 
                                                   {"from_currency": company_currency, "to_currency": account_currency}, 
                                                   "exchange_rate") or 1.0
        source_exchange_rate = frappe.db.get_value("Currency Exchange", 
                                                   {"from_currency": account_currency, "to_currency": company_currency}, 
                                                   "exchange_rate") or 1.0
    return target_exchange_rate, source_exchange_rate


def add_payment_references(payment_entry, invoice_name, payment_amount):
    """Add references to the payment entry."""
    payment_entry.append("references", {
        "reference_doctype": "Sales Invoice",
        "reference_name": invoice_name,
        "allocated_amount": payment_amount
    })

  
def create_payment_for_sales_invoice(payment_type, customer, invoice_name, payment_amount,
                                     payment_account, mode_of_payment, reference_number=None, 
                                     custom_deposited_by_customer=None, cheque_reference_date=None,outstanding_amount=None,
                                     receipt_number=None):
    try:
        # print("create_payment_for_sales_invoice:")
        # Validate inputs
        # validate_inputs(payment_type, customer, invoice_name, payment_amount, payment_account)

        # Fetch the currency for the "Paid To" account
        account_currency = frappe.db.get_value("Account", payment_account, "account_currency")
        company_currency = frappe.get_cached_value("Company", frappe.defaults.get_global_default("company"), "default_currency")

        # Get exchange rates
        target_exchange_rate, source_exchange_rate = get_exchange_rates(account_currency, company_currency)


        # Create a new Payment Entry
        payment_entry = frappe.new_doc("Payment Entry")
        
        # Set mandatory fields
        payment_entry.payment_type = payment_type  # Can also be "Pay"
        payment_entry.posting_date = nowdate()
        payment_entry.company = frappe.defaults.get_global_default("company")
        payment_entry.party_type = "Customer"  # Can also be "Supplier"
        payment_entry.party = customer
        payment_entry.paid_amount = float(payment_amount) # Amount paid
        payment_entry.received_amount = float(payment_amount)  # Amount received (same as paid_amount if no deductions)
        payment_entry.paid_to = payment_account  # Bank account or cash ledger
        payment_entry.reference_no=reference_number if reference_number else ""
        payment_entry.reference_date=cheque_reference_date if cheque_reference_date else ""

        totalAmt = sales_invoice_api.getGrandTotalByInvoiceNumber(invoice_name, customer)
        
        doc = frappe.get_doc('Customer', customer)
        if doc.custom_customer_location_type == 'International':
            conversion_rate = sales_invoice_api.exchange_rate_conversion(invoice_name)
            outstanding_amount = float(outstanding_amount) * conversion_rate

        # Optional: Set references (e.g., link to sales invoice)
        payment_entry.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": invoice_name,
            "total_amount": totalAmt,
            "outstanding_amount": float(outstanding_amount),
            "allocated_amount": float(payment_amount)
        })
        print("#############################################################################################################")
        print(f"payment amount: {payment_amount}")
        print(f"outstanding amount:{outstanding_amount}")
        
        print("#############################################################################################################")
        # Insert and submit the Payment Entry
        payment_entry.insert()
        payment_entry.submit()
        
        frappe.db.commit()  # Commit the changes to the database

        if receipt_number:
            update_status_in_payment_info(receipt_number,'Paid')

        # return {"status": "success", "message": f"Payment Entry created successfully: "}

    except PaymentEntryError as e:
        # Log validation errors
        frappe.log_error(traceback.format_exc(), f"Validation Error: {str(e)}")
        # return {"status": "error", "message": str(e)}

    except Exception as e:
        # Log other errors with detailed traceback
        error_message = f"Payment Entry Error for Customer: {customer}, Invoice: {invoice_name}, " \
                        f"Payment Type: {payment_type}, Amount: {payment_amount}, " \
                        f"Payment Account: {payment_account}, Mode of Payment: {mode_of_payment}, " \
                        f"Reference Number: {reference_number}, Deposited By: {custom_deposited_by_customer}, " \
                        f"Cheque Reference Date: {cheque_reference_date}. " \
                        f"Error: {str(e)}"

        frappe.log_error(traceback.get_traceback(), error_message)
        # return {"status": "error", "message": str(e)}



def create_payment_for_sales_order(payment_type, customer, invoice_name, payment_amount,
                                     payment_account, mode_of_payment, reference_number=None, 
                                     custom_deposited_by_customer=None, cheque_reference_date=None,outstanding_amount=None,
                                     receipt_number=None):
    try:
        # Validate inputs
        # if not all([customer, invoice_name, payment_amount > 0, payment_account, payment_type]):
        #     raise ValueError("Invalid input parameters")

        # Fetch the currency for the "Paid To" account
        account_currency = frappe.db.get_value("Account", payment_account, "account_currency")
        company_currency = frappe.get_cached_value("Company", frappe.defaults.get_global_default("company"), "default_currency")

        # Get exchange rates
        target_exchange_rate, source_exchange_rate = get_exchange_rates(account_currency, company_currency)

        # Create a new Payment Entry
        payment_entry = frappe.new_doc("Payment Entry")
        
        # Set mandatory fields
        payment_entry.payment_type = payment_type  # Can also be "Pay"
        payment_entry.posting_date = nowdate()
        payment_entry.company = frappe.defaults.get_global_default("company")
        payment_entry.party_type = "Customer"  # Can also be "Supplier"
        payment_entry.party = customer
        payment_entry.paid_amount = float(payment_amount) # Amount paid
        payment_entry.received_amount = float(payment_amount)  # Amount received (same as paid_amount if no deductions)
        payment_entry.paid_to = payment_account  # Bank account or cash ledger
        payment_entry.reference_no=reference_number if reference_number else ""
        payment_entry.reference_date=cheque_reference_date if cheque_reference_date else ""


        totalAmt = sales_order_api.getGrandTotalByOrderNumber(invoice_name)

        # print("totalAmt:213")
        # print(totalAmt)

        # Optional: Set references (e.g., link to sales invoice)
        payment_entry.append("references", {
            "reference_doctype": "Sales Order",
            "reference_name": invoice_name,
            "total_amount": totalAmt,
            "outstanding_amount": float(outstanding_amount),
            "allocated_amount": float(payment_amount)
        })

        # Insert and submit the Payment Entry
        payment_entry.insert()
        payment_entry.submit()
        
        frappe.db.commit()  # Commit the changes to the database

        if receipt_number:
            update_status_in_payment_info(receipt_number,'Paid')

        # return {"status": "success", "message": f"Payment Entry created successfully: "}

    except ValueError as e:
        frappe.log_error(frappe.get_traceback(), f"Payment Entry Error for Customer: {customer}, Order: {invoice_name}")
        # return {"status": "error", "message": str(e)}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Payment Entry Error for Customer: {customer}, Order: {invoice_name}")
        # return {"status": "error", "message": str(e)}     


"""
for inserting the payment details from the 'Payment Receipt' doctype
"""
@frappe.whitelist(allow_guest=True)
def create_advance_payment(payment_type, customer, invoice_name, payment_amount,
                                     payment_account, mode_of_payment, reference_number=None, 
                                     custom_deposited_by_customer=None, cheque_reference_date=None,outstanding_amount=None,
                                     receipt_number=None):
    try:
        # Fetch the currency for the "Paid To" account
        account_currency = frappe.db.get_value("Account", payment_account, "account_currency")
        company_currency = frappe.get_cached_value("Company", frappe.defaults.get_global_default("company"), "default_currency")

        # Get exchange rates
        target_exchange_rate, source_exchange_rate = get_exchange_rates(account_currency, company_currency)

        # Create a new Payment Entry
        payment_entry = frappe.new_doc("Payment Entry")
        
        # Set mandatory fields
        payment_entry.payment_type = payment_type  # Can also be "Pay"
        payment_entry.posting_date = nowdate()
        payment_entry.company = frappe.defaults.get_global_default("company")
        payment_entry.party_type = "Customer"  # Can also be "Supplier".
        payment_entry.custom_slip_no = invoice_name if invoice_name else ""
        payment_entry.party = customer
        payment_entry.paid_amount = float(payment_amount) # Amount paid
        payment_entry.received_amount = float(payment_amount)  # Amount received (same as paid_amount if no deductions)
        payment_entry.paid_to = payment_account  # Bank account or cash ledger
        payment_entry.reference_no=reference_number if reference_number else ""
        payment_entry.reference_date=cheque_reference_date if cheque_reference_date else ""
        

        # Insert and submit the Payment Entry
        payment_entry.insert()
        payment_entry.submit()
        
        frappe.db.commit()  # Commit the changes to the database

        if receipt_number:
            update_status_in_payment_info(receipt_number,'Paid')

        # return {"status": "success", "message": f"Payment Entry created successfully: "}

    except ValueError as e:
        frappe.log_error(frappe.get_traceback(), f"Advance Payment Entry Error for Customer: {customer}")
        return {'status': 'error', 'message': str(e)}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Advance Payment Entry Error for Customer: {customer}")
        # return {'status': 'error', 'message': str(e)}  


@frappe.whitelist()
def create_payment_for_InternalTransfer(payment_type,
                                     payment_account, mode_of_payment, reference_number=None, 
                                     custom_deposited_by_customer=None, cheque_reference_date=None,amount_received=None,
                                     receipt_number=None,deposit_date=None):
    try:
        # Fetch the currency for the "Paid To" account
        account_currency = frappe.db.get_value("Account", payment_account, "account_currency")
        company_currency = frappe.get_cached_value("Company", frappe.defaults.get_global_default("company"), "default_currency")

        # Get exchange rates
        target_exchange_rate, source_exchange_rate = get_exchange_rates(account_currency, company_currency)

        # Create a new Payment Entry
        payment_entry = frappe.new_doc("Payment Entry")
        
        # Set mandatory fields
        payment_entry.payment_type = payment_type  # Can also be "Pay"
        payment_entry.posting_date = nowdate()
        payment_entry.company = frappe.defaults.get_global_default("company")
        payment_entry.party_type = "Customer"  # Can also be "Supplier"
        payment_entry.party = ''
        payment_entry.paid_amount = float(amount_received) # Amount paid
        payment_entry.received_amount = float(amount_received)  # Amount received (same as paid_amount if no deductions)
        payment_entry.paid_to = payment_account  # Bank account or cash ledger
        payment_entry.reference_no=reference_number if reference_number else ""
        payment_entry.reference_date=cheque_reference_date if cheque_reference_date else "",
        payment_entry.custom_deposit_date= deposit_date
        # Insert and submit the Payment Entry
        payment_entry.insert()
        payment_entry.submit()
        
        frappe.db.commit()  # Commit the changes to the database

        return {"status": "success", "message": f"Payment Entry created successfully: "}

    except ValueError as e:
        frappe.log_error(frappe.get_traceback(), "Payment Entry Error for InternalTransfer")
        return {"status": "error", "message": str(e)}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Entry Error for InternalTransfer")
        return {"status": "error", "message": str(e)}  


@frappe.whitelist()
def insertSalesInvoiceDetails(payment_entry_details, payment_entry,receipt_number=None):
    try:
        # print("insertSalesInvoiceDetails")
        # print("payment_entry_details:")
        # print(payment_entry_details)
        # print("payment_entry:")
        # print(payment_entry)
        
        # payment_details = payment_entry_details[0]
        # if float(payment_entry['custom_employee_liability_amount']) > 0:

            # try:
            #     payment_entry_for_employee_liability(
            #         payment_entry_details['executive'],
            #         payment_entry['custom_employee_liability_amount'],
            #         payment_entry_details['account_paid_to'],
            #         payment_entry_details['name'],
            #         payment_entry_details['reference_number'],
            #         payment_entry_details['chequereference_date']

            #     )
            # except Exception as e:
            #     frappe.log_error(frappe.get_traceback(), "Payment Entry Error for Payment Entry for Employee Liability")

        return create_payment_for_sales_invoice(
                    payment_entry_details['payment_type'],
                    payment_entry['customer'],
                    payment_entry['reference_name'],
                    payment_entry['allocated_amount'],
                    payment_entry_details['account_paid_to'],
                    payment_entry_details['mode_of_payment'],
                    payment_entry_details['reference_number'],
                    payment_entry_details['custom_deposited_by_customer'],
                    payment_entry_details['chequereference_date'],
                    payment_entry['outstanding_amount'],receipt_number
                )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Entry Error for insertSalesInvoiceDetails")
        frappe.throw(_("An error occurred while processing Payment Entry: {0}").format(str(e)))

@frappe.whitelist()
def insertSalesOrderDetails(payment_entry_details, payment_entry,receipt_number=None):
    try:
        # payment_details = payment_entry_details[0]

        create_payment_for_sales_order(
                    payment_entry_details['payment_type'],
                    payment_entry['customer'],
                    payment_entry['reference_name'],
                    payment_entry['allocated_amount'],
                    payment_entry_details['account_paid_to'],
                    payment_entry_details['mode_of_payment'],
                    payment_entry_details['reference_number'],
                    payment_entry_details['custom_deposited_by_customer'],
                    payment_entry_details['chequereference_date'],
                    payment_entry['outstanding_amount'],receipt_number
                )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Entry Error for insertSalesOrderDetails")
        frappe.throw(_("An error occurred while processing Payment Entry: {0}").format(str(e)))

@frappe.whitelist()
def insertInternalTransferDetails(payment_entry_details,receipt_number=None,deposit_date=None):
    try:
        # payment_details = payment_entry_details[0]
        create_payment_for_InternalTransfer(
                   payment_entry_details['payment_type'],
                    payment_entry_details['account_paid_to'],
                    payment_entry_details['mode_of_payment'],
                    payment_entry_details['reference_number'],
                    payment_entry_details['custom_deposited_by_customer'],
                    payment_entry_details['chequereference_date'],
                    payment_entry_details['amount_received'],
                    receipt_number,
                    deposit_date
                )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Entry Error for insertInternalTransferDetails")
        frappe.throw(_("An error occurred while processing Payment Entry: {0}").format(str(e)))

@frappe.whitelist()
def insertAdvanceDetails(payment_entry_details, payment_entry,receipt_number=None):
    try:
        # payment_details = payment_entry_details[0]

        create_advance_payment(
                    payment_entry_details['payment_type'],
                    payment_entry['customer'],
                    payment_entry['reference_name'],
                    payment_entry['allocated_amount'],
                    payment_entry_details['account_paid_to'],
                    payment_entry_details['mode_of_payment'],
                    payment_entry_details['reference_number'],
                    payment_entry_details['custom_deposited_by_customer'],
                    payment_entry_details['chequereference_date'],
                    payment_entry['outstanding_amount'],receipt_number
                )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Entry Error for insertSalesOrderDetails")
        frappe.throw(_("An error occurred while processing Payment Entry: {0}").format(str(e)))

@frappe.whitelist()
def createJournelEntryForSuspense():
    pass 


@frappe.whitelist(allow_guest=True)
def getAllReceiptDetailsFromDoc(payment_type=None, payment_entry_details=None, executive=None,
                                bank_account=None, account_paid_to=None, receipt_number=None,
                                custom_deposited_by_customer=None, amount_received=None, mode_of_payment=None,
                                amount_paid=None, reference_number=None, chequereference_date=None,
                                account_paid_from=None,custom_is_suspense_entry=None,deposit_date=None):
    """
    This method validates the passed details and processes the Payment Receipt.
    """

    try:
        # Check required fields
        required_fields = {
            "payment_type": payment_type,
            "mode_of_payment": mode_of_payment,
            "payment_entry_details": payment_entry_details,
            "executive": executive,
            "bank_account": bank_account,
            "receipt_number": receipt_number,
            "custom_deposited_by_customer": custom_deposited_by_customer,
            "amount_received": amount_received,
            "account_paid_to": account_paid_to,
            "amount_paid": amount_paid,
            "reference_number": reference_number,
            "custom_is_suspense_entry":custom_is_suspense_entry,
            "account_paid_from":account_paid_from,
            "chequereference_date": chequereference_date
        }

        # print("")
        # print("required_fields:123")
        # print(required_fields)

        # if receipt_number:
        #     update_status_in_payment_info(receipt_number,'Pending')
        # Validate required fields
        # missing_fields = [field for field, value in required_fields.items() if value is None or value == ""]
        # if missing_fields:
        #     frappe.throw(_("Missing required fields: {0}").format(", ".join(missing_fields)))

        try:
            payment_entry_details = json.loads(payment_entry_details)  # Convert the JSON string to a list of dictionaries
        except json.JSONDecodeError:
            frappe.throw(_("Invalid payment_entry_details format. Unable to parse."))

        # if payment_type=="Receive" and custom_is_suspense_entry==True:
        #     if not account_paid_from or not amount_paid:
        #         frappe.throw(_("Please enter account paid from and amount paid for suspense entry"))
        #     else:
        #         createJournelEntryForSuspense()

        # print("payment_type : ")
        # print(payment_type)


        if payment_type in ["Internal Transfer"] and custom_is_suspense_entry==True:     
           return insertInternalTransferDetails(required_fields,receipt_number, deposit_date)        
        # Process payment type logic
        elif payment_type in ["Receive", "Pay"]:
            # Iterate through each entry in payment_entry_details
            for entry in payment_entry_details:
                if isinstance(entry, dict):  # Ensure that each entry is a dictionary
                    reference_type = entry.get("reference_type")
                    if reference_type == "Sales Invoice":
                        insertSalesInvoiceDetails(required_fields,entry ,receipt_number)
                    elif reference_type == "Sales Order":
                        insertSalesOrderDetails(required_fields,entry,receipt_number)
                    elif reference_type == "Advance" or reference_type == "Slip No":
                        insertAdvanceDetails(required_fields,entry,receipt_number)
                    else:
                        # Log unknown reference types for debugging
                        frappe.logger().info({
                            "name": entry.get("name"),
                            "customer": entry.get("customer"),
                            "reference_type": reference_type,
                            "reference_name": entry.get("reference_name"),
                            "outstanding_amount": entry.get("outstanding_amount"),
                            "allocated_amount": entry.get("allocated_amount"),
                            "docstatus": entry.get("docstatus"),
                            "parent": entry.get("parent"),
                            "parenttype": entry.get("parenttype")
                        })
                        frappe.throw(_("Unknown reference type in payment details."))
                else:
                    frappe.throw(_("Each entry in payment_entry_details must be a dictionary, found {0}.").format(type(entry)))
        # else:
            # Handle internal transfer or other payment types
            # insertInternalTransferDetails(required_fields,receipt_number)
            
        # Success response
        return {
            "status": "Success",
            "message": _("Payment Receipt details are validated and processed successfully."),
            "data": {
                "payment_type": payment_type,
                "executive": executive,
                "amount_received": amount_received
            }
        }

    except Exception as e:
        # Log error and throw exception
        frappe.log_error({
            "traceback": frappe.get_traceback(),
            "error": str(e),
            "required_fields": required_fields,
        }, "Payment Receipt Validation Error")
        frappe.throw(_("An error occurred while processing Payment Receipt: {0}").format(str(e)))

@frappe.whitelist(allow_guest=True)
def getSuspenseEntries():
    try:
        # First query for Payment Receipt entries
        payment_receipt_query = """
            SELECT
                name as receipt_id_1,
                amount_received as amount_1,
                executive,
                date,
                mode_of_payment,
                COALESCE(reference_number, '') AS reference_number_1,
                COALESCE(chequereference_date, '') AS reference_date_1
            FROM
                `tabPayment Receipt`
            WHERE
                payment_type = 'Internal Transfer'
                AND custom_status = 'Processing'
                AND custom_is_suspense_entry = 1
                AND docstatus = 1
        """
        
        # Second query for Journal Entry Account entries
        journal_entry_query = """
            SELECT 
                jo.parent as receipt_id_1,
                jo.credit as amount_1,
                '' as executive,
                jo.creation as date,
                '' as mode_of_payment,
                '' as reference_number_1,
                '' as reference_date_1
            FROM 
                `tabJournal Entry Account` jo
            INNER JOIN 
                `tabAccount` ta ON jo.account = ta.name
            WHERE  
                jo.docstatus = 1
                AND ta.custom_is_suspense = 1
                AND jo.custom_is_apportion_done != 1
                AND jo.debit = 0
                AND jo.credit != 0

        """
        
        # Execute both queries
        payment_receipt_results = frappe.db.sql(payment_receipt_query, as_dict=True)
        journal_entry_results = frappe.db.sql(journal_entry_query, as_dict=True)
        
        # Combine the results
        combined_results = payment_receipt_results + journal_entry_results
        
        # Format dates if needed
        for result in combined_results:
            if result.get('date'):
                result['date'] = frappe.utils.formatdate(result['date'])
            if result.get('reference_date_1'):
                result['reference_date_1'] = frappe.utils.formatdate(result['reference_date_1'])
                
            # Ensure amount is formatted as float
            if result.get('amount_1'):
                result['amount_1'] = float(result['amount_1'])
                
            # Ensure executive has a value
            if not result.get('executive'):
                result['executive'] = 'N/A'
        
        return combined_results
        
    except Exception as e:
        frappe.log_error(
            message=f"Error Fetching Suspense Entries: {str(e)}\n{frappe.get_traceback()}", 
            title="Error Fetching Suspense Entries"
        )
        return []

    
@frappe.whitelist(allow_guest=True)
def getSuspenseFilters(filters=None):
    filters = frappe.parse_json(filters) if filters else {}

    conditions = []

    # Fixed conditions (always applied)
    conditions.append("payment_type = 'Internal Transfer'")
    conditions.append("custom_status = 'Processing'")
    conditions.append("custom_is_suspense_entry = 1")
    conditions.append("docstatus = 1")
    
    # Apply dynamic filters based on user input
    if filters:
        if filters.get('executive'):
            conditions.append(f"executive = '{filters['executive']}'")
        if filters.get('deposit_date'):
            conditions.append(f"date = '{filters['deposit_date']}'")
        if filters.get('payment_mode'):
            conditions.append(f"mode_of_payment = '{filters['payment_mode']}'")
        if filters.get('reference_no'):
            conditions.append(f"reference_number = '{filters['reference_no']}'")
        if filters.get('reference_date'):
            conditions.append(f"chequereference_date = '{filters['reference_date']}'")
        if filters.get('amount'):
            conditions.append(f"amount_received = '{filters['amount']}'")
    
    # Build the final WHERE clause
    if conditions:
        condition_str = " AND ".join(conditions)
        condition_str = "WHERE " + condition_str
    else:
        condition_str = ""

    # Query to fetch the filtered entries
    query = f"""
        SELECT name, amount_received, executive, date, mode_of_payment,
               COALESCE(reference_number, '') AS reference_number,
               COALESCE(chequereference_date, '') AS reference_date
        FROM `tabPayment Receipt`
        {condition_str}
    """
    
    return frappe.db.sql(query, as_dict=True)

@frappe.whitelist(allow_guest=True)
def UpdateRejectionForPaymentReceipt(receipt_no, remark):
    try:
        # Validate input parameters
        if not receipt_no:
            frappe.throw(_("Receipt No is required."))
        if not remark:
            frappe.throw(_("Remark is required."))

        # Update the Payment Intimation table
        frappe.db.sql("""
            UPDATE `tabPayment Intimation` 
            SET 
                custom_status = 'Rejected',
                custom_receipt_status = 'Rejected',
                custom_rejected_remarks = %s
            WHERE name = %s
        """, (remark, receipt_no,), as_dict=True)



        # Commit the transaction to apply the changes
        frappe.db.commit()

        # Return a success response
        return {
            "status": "success",
            "message": _("Record updated successfully."),
            "data": {
                "receipt_no": receipt_no,
                "remark": remark,
                "custom_status": "Rejected",
                "custom_receipt_status": "Rejected"
            }
        }
    except Exception as e:
        # Log the error in the system
        frappe.log_error(frappe.get_traceback(), 'Error in UpdatePaymentInfoForRejection')

        # Return an error response
        return {
            "status": "error",
            "message": _("An error occurred while updating the record."),
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def payment_entry_for_employee_liability(executive_name, paid_amount, amount_paid_from,
receipt_number=None, reference_number=None,
cheque_reference_date=None, remark=None):
    try:
        # Fetch company details
        company = frappe.defaults.get_global_default("company")
        company_currency = frappe.get_cached_value("Company", company, "default_currency")
        # Fetch currency for the "Paid To" account
        account_currency = frappe.db.get_value("Account", amount_paid_from, "account_currency")
        # Get exchange rates
        target_exchange_rate, source_exchange_rate = get_exchange_rates(account_currency, company_currency)
            
        # Step 2: Create Payment Entry (Only if create_payment_entry is True)
        payment_entry = frappe.get_doc({
            "doctype": "Payment Entry",
            "payment_type": "Pay",
            "posting_date": frappe.utils.nowdate(),
            "company": company,
            "party_type": "Employee",
            "party": executive_name,
            "paid_amount": float(paid_amount),
            "received_amount": float(paid_amount),
            "paid_to": "Employee Advance - SIL",
            "paid_from": amount_paid_from,
            "reference_no": reference_number if reference_number else "",
            "reference_date": cheque_reference_date if cheque_reference_date else "",
            "custom_payment_receipt_ref_no": receipt_number if receipt_number else ""
        })
        
        # Insert and submit Payment Entry
        payment_entry.insert()
        payment_entry.submit()
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"Payment Entry created successfully: {payment_entry.name}",
            "payment_entry_id": payment_entry.name
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Payment Entry Error for Employee Liability")
        return {"status": "error", "message": str(e)}