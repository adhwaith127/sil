import frappe
from frappe import _
import re
from bs4 import BeautifulSoup
from sil.services.utils import ensure_column_exists


@frappe.whitelist(allow_guest=True)
def getAllE_BillDetails():
    # Clear the cache
    frappe.clear_cache()

    # for returning all the e-invoice details which are not updated in the tally application.
    return frappe.db.sql("""Select * from `tabe-Invoice Log`;""",as_dict=True)

@frappe.whitelist(allow_guest=True)
def getAllBillDetails():
    # Clear the cache
    frappe.clear_cache()

    # for returning all the e-invoice details which are not updated in the tally application.
    return frappe.db.sql("""Select * from `tabSales Invoice`;""",as_dict=True)    


@frappe.whitelist(allow_guest=True)
def getAllBillItemDetails():
    # Clear the cache
    frappe.clear_cache()

    # for returning all the e-invoice details which are not updated in the tally application.
    return frappe.db.sql("""Select * from `tabSales Invoice Item`;""",as_dict=True)    


@frappe.whitelist(allow_guest=True)
def getAllE_BillDetailsByBillNumber(data):
    try:
        # Clear the cache
        frappe.clear_cache()

        #Parse the JSON data
        data_dict=frappe.parse_json(data)
        #Extract the relevant data
        invoice_no=data_dict.get("InvoiceNo")
        # for returning all the sales invoice details which are not updated in the tally application.
        return frappe.db.sql("""Select * from `tabe-Invoice Log` where `sales_invoice`=%s;""",(invoice_no,),as_dict=True)
    except Exception as e:
        # Log error
        frappe.logger().error(f"Error parsing JSON data: {e}")
        
        return {"success": False, "message": f"An error occurred while processing the request.{e}"}



@frappe.whitelist(allow_guest=True)
def getAllInvoiceDetails(data):
    # Clear the cache
    frappe.clear_cache()
    
    #Parse the JSON data
    data_dict=frappe.parse_json(data)
    #Extract the relevant data
    CompanyName=data_dict.get("CompanyName")
    #invoices={}   
    invoices = frappe.db.sql("""
        SELECT tsi.name,tsi.posting_date,tsi.base_total_taxes_and_charges,tsi.rounded_total,
		tsi.rounding_adjustment,tsi.total_taxes_and_charges,tsi.discount_amount,
		IF(tsi.tax_category='In-State',tsi.total_taxes_and_charges/2,0)CGST_Amount,
		IF(tsi.tax_category='In-State',tsi.total_taxes_and_charges/2,0)SGST_Amount,
		IF(tsi.tax_category='In-State',0,tsi.total_taxes_and_charges)IGST_Amount,
		tsi.customer_name,tsi.customer_address,tsi.paid_amount,tsi.grand_total,
		tsi.total_taxes_and_charges,tsi.remarks,tsi.custom_sales_type,
		tsi.billing_address_gstin,tsi.einvoice_status,customer_address, 
		til.irn, til.acknowledgement_number, til.acknowledged_on, SUBSTRING(tsi.place_of_supply, 1,
		INSTR(tsi.place_of_supply, '-') - 1) AS place_code_of_supply_,
		SUBSTRING(tsi.place_of_supply, INSTR(tsi.place_of_supply, '-')+ 1) AS place_name_of_supply_, 
		tc.custom_customer_category, ta.pincode, tsi.other_charges_calculation,tsi.custom_cluster,
        (NET_TOTAL-(TOTAL-discount_amount)) AS discount_variation 
	FROM `tabSales Invoice` tsi  
		LEFT OUTER JOIN `tabe-Invoice Log` til  ON til.reference_name = tsi.name  
		LEFT OUTER JOIN  `tabCustomer` tc ON tc.name = tsi.customer  
		LEFT OUTER JOIN  `tabAddress` ta  ON ta.name = tsi.customer  
	WHERE tsi.custom_is_tallyupdated = 0 and tsi.docstatus=1 and company=%s ORDER BY tsi.creation;
    """,(CompanyName,),as_dict=True)

    # for invoice in invoices:
    #     if "other_charges_calculation" in invoice:
    #         process_other_charges_calculation(invoice)

    return {"success": True, "invoices": invoices}


def process_other_charges_calculation(invoice):
    other_charges = invoice.get("other_charges_calculation", "")
    if not isinstance(other_charges, str):
        frappe.log_error(f"Value for invoice {invoice.get('name')} is not a string")
        return

    soup = BeautifulSoup(other_charges.strip(), 'html.parser')
    table = soup.find('table')
    if not table:
        frappe.log_error(f"No table found in HTML for invoice {invoice.get('name')}")
        return

    data_dict = {}
    for row in table.find_all('tr')[1:]:
        cells = [remove_html_tags(cell.text.strip()) for cell in row.find_all('td')]
        if len(cells) < 4:
            item, taxable_amount, igst_str = cells
            data_dict[item] = {"Taxable Amount": taxable_amount, "IGST": process_tax_amount(igst_str)}
        else:
            item, taxable_amount, cgst_str, sgst_str = cells
            data_dict[item] = {
                "Taxable Amount": taxable_amount,
                "CGST": process_tax_amount(cgst_str),
                "SGST": process_tax_amount(sgst_str)
            }
    invoice["other_charges_calculation"] = data_dict


def process_tax_amount(tax_str):
    split_values = tax_str.split()
    tax_value = split_values[0]
    tax_currency = split_values[1]
    tax_amount = "".join(split_values[2].split(","))
    return {"Tax": tax_value, "Currency": tax_currency, "Amount": tax_amount}

def remove_html_tags(text):
    return re.sub('<.*?>', '', text)

def ensure_column_exists(doctype, column_name, column_type):
    try:
        if column_name not in frappe.db.get_table_columns(doctype):
            frappe.db.sql(f"ALTER TABLE `tab{doctype}` ADD COLUMN {column_name} {column_type} DEFAULT 0;")
            frappe.db.sql(f"ALTER TABLE `tab{doctype}` ADD CONSTRAINT unique_{doctype}_{column_name} UNIQUE ({column_name});")
    except Exception as e:
        frappe.log_error(f"Error in ensure_column_exists: {str(e)}")

 

@frappe.whitelist(allow_guest=True)
def getAllInvoiceDetailsWithStatus(data):
    try: 
        # Clear the cache
        frappe.clear_cache()

        #Parse the JSON data
        data_dict=frappe.parse_json(data)
        #Extract the relevant data
        status=data_dict.get("InvoiceStatus")
        if status:
            return frappe.db.sql(f"""Select * from `tabSales Invoice` where status=%s;""",(status,),as_dict=True)    
        else:
            return "InvoiceStatus parameter is missing"

    except Exception as e: 
        # write all the exception details in the lo file for further development.
        frappe.log_error(_("Error in getAllInvoiceDetailsWithStatus: {0}").format(str(e)))           
        return frappe.db.sql(f"""Select * from `tabSales Invoice` ;""",as_dict=True)    




@frappe.whitelist(allow_guest=True)
def getAllInvoiceItemDetails(data):
    try: 
        # Clear the cache
        frappe.clear_cache()

        #Parse the JSON data
        data_dict=frappe.parse_json(data)
        #Extract the relevant data
        Invoice_No=data_dict.get("Invoice_no")
        if Invoice_No:
            return frappe.db.sql(f"""SELECT SI.*,SNO.serial_no AS serial_nos FROM `tabSales Invoice Item` SI LEFT OUTER JOIN `tabItem Series No` SNO ON SI.parent=SNO.parent AND SI.Item_code=SNO.item_code where SI.parent=%s;""",(Invoice_No,),as_dict=True)    
        else:
            return "Invoice_no parameter is missing"

    except Exception as e: 
        # write all the exception details in the lo file for further development.
        frappe.log_error(_("Error in getAllInvoiceItemDetails: {0}").format(str(e)))           
        return{"success":False,"message":f"An Error occurred while processing the request.{str(e)}"}       
         
     
@frappe.whitelist(allow_guest=True)
def updateInvoiceUploadStatus(data):
    try:
        # Clear the cache
        frappe.clear_cache()

        # Parse the JSON data
        data_dict = frappe.parse_json(data)
        
        # Extract the relevant data
        invoice_no = data_dict.get("Invoice_no")
        
        if invoice_no:
            try:
                # Update the database record 
                sql_query = """UPDATE `tabSales Invoice` SET custom_is_tallyupdated = 1 WHERE name=%s """
                frappe.db.sql(sql_query, (invoice_no,))
                
                # Commit the transaction
                frappe.db.commit()
                
                # Log successful update
                frappe.logger().info(f"Invoice {invoice_no} updated successfully.")
                
                return {"success": True, "message": "Data updated successfully", "InvoiceNo": invoice_no}   
            except Exception as e:
                # Log error
                frappe.logger().error(f"Error updating invoice {invoice_no}: {e}")
                
                return {"success": False, "message": f"An error occurred while processing the request: {str(e)}"}
        else:
            return {"success": False, "message": "Invoice_no parameter is missing"}
    except Exception as e:
        # Log error
        frappe.logger().error(f"Error parsing JSON data: {e}")
        
        return {"success": False, "message": "An error occurred while processing the request"}


@frappe.whitelist(allow_guest=True)
def updateInvoiceUploadStatusWithDate(data):
    try:
        # Clear the cache
        frappe.clear_cache()

        # Parse the JSON data
        data_dict = frappe.parse_json(data)
        
        # Extract the relevant data
        # invoice_no = data_dict.get("Invoice_no")
        postingDate = data_dict.get("posting_date")

        if postingDate:
            try:
                # Update the database record 
                sql_query = """UPDATE `tabSales Invoice` SET is_tally_updated = 1 WHERE `posting_date`<%s """
                frappe.db.sql(sql_query, (postingDate,))
                
                # Commit the transaction
                frappe.db.commit()
                
                # Log successful update
                frappe.logger().info(f"Status updated successfully.")
                
                return {"success": True, "message": "Data updated successfully"}   
            except Exception as e:
                # Log error
                frappe.logger().error(f"Error updating invoice : {e}")
                
                return {"success": False, "message": f"An error occurred while processing the request: {str(e)}"}
        else:
            return {"success": False, "message": "posting_date parameter is missing"}
    except Exception as e:
        # Log error
        frappe.logger().error(f"Error parsing JSON data: {e}")
        
        return {"success": False, "message": "An error occurred while processing the request"}


# @frappe.whitelist(allow_guest=True)
# def on_submit(invoice_name):
    # Fetch the Sales Invoice document using the provided invoice name
    # sales_invoice = frappe.get_doc('Sales Invoice', invoice_name)
    
    # print(f"sales_invoice:{sales_invoice}")

    # # Create a dictionary to store the invoice details
    # invoice_details = {
    #     'name': sales_invoice.name,
    #     'customer': sales_invoice.customer,
    #     'grand_total': sales_invoice.grand_total,
    #     'items': []
    # }
    
    # # Loop through the items in the invoice and add them to the details
    # for item in sales_invoice.items:
    #     invoice_details['items'].append({
    #         'item_code': item.item_code,
    #         'item_name': item.item_name,
    #         'quantity': item.qty,
    #         'rate': item.rate,
    #         'amount': item.amount
    #     })
    
    # return {"message":"Data saved"}#invoice_details


@frappe.whitelist(allow_guest=True)
def getInvoiceDetails(data):
    try: 
        # Clear the cache
        frappe.clear_cache()

        #Parse the JSON data
        data_dict=frappe.parse_json(data)
        #Extract the relevant data
        Invoice_No=data_dict.get("Invoice_no")
        if Invoice_No:
            return frappe.db.sql(f"""SELECT * FROM `tabSales Invoice` where name=%s;""",(Invoice_No,),as_dict=True)    
        else:
            return "Invoice_no parameter is missing"

    except Exception as e: 
        # write all the exception details in the lo file for further development.
        frappe.log_error(_("Error in getAllInvoiceItemDetails: {0}").format(str(e)))           
        return{"success":False,"message":f"An Error occurred while processing the request.{str(e)}"}       
         
     
@frappe.whitelist()
def get_distinct_sales_invoice_filters():
    
    query = """
        SELECT DISTINCT 
            custom_cluster, 
            custom_cluster_manager, 
            custom_zonal_manager, 
            custom_regional_manager
        FROM `tabSales Invoice`
        WHERE 
            docstatus = 1 
            AND custom_cluster IS NOT NULL 
            AND custom_cluster_manager IS NOT NULL 
            AND custom_zonal_manager IS NOT NULL 
            AND custom_regional_manager IS NOT NULL
    """
    try:
        # Execute query and fetch results
        results = frappe.db.sql(query, as_dict=True)
        return results
    except Exception as e:
        # Return a user-friendly error message
        frappe.throw(_("Error fetching distinct filters: {0}").format(str(e)))


@frappe.whitelist(allow_guest=True)
def getGrandTotalByInvoiceNumber(invoice_number):
    try:
        query = """
            SELECT DISTINCT 
                grand_total
            FROM `tabSales Invoice`
            WHERE 
                name=%s
        """
        # Pass the parameter to the query
        results = frappe.db.sql(query, (invoice_number,), as_dict=True)
        # print("getGrandTotalByInvoiceNumber:")
        # print(results)
        return results
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in getGrandTotalByInvoiceNumber")
        return {"error": str(e)}
    



if __name__=="__main__":
    #Define our DocType and column details
    doctype="Sales Invoice"
    column_name="is_tally_updated"
    column_type="INT"

    # Check and add column if necessary
    check_and_add_column(doctype,doctype.lower,column_name.lower,column_name)
