import win32api
import win32print
import os


from sqlalchemy import create_engine, select, insert
from sqlalchemy.orm import Session
import datetime
import base64
from loggers import logger


engine = create_engine("sqlite:///instance//print.db", echo=True)
session = Session(bind=engine)

class PrintError(Exception):
    pass

def log_error(job, error):
    from models import ErrorLog
    logger.error("Error: %s" % error)
    err_log = insert(ErrorLog).values(
        creation_date=datetime.datetime.now(),
        document_number=job['documentNumber'],
        status="Error",
        error=error
    )
    session.execute(err_log)
    session.commit()


def print_job(job, printer):
    '''
    Params:
    ---------
    job: Dict from json passed with request
    printer: printer ID on system

    Returns:
    ---------
    None

    1. Validates file not already printed via database.
    2. Writes job to file.
    3. Validates printer is available.
    4. Initiates print job.
    5. records job parameters to database.
    '''

    from utils.io import write_string_to_file
    from models import PrintJob

    already_printed = (select(PrintJob)
        .where(PrintJob.document_type == job['documentType'])
        .where(PrintJob.document_number == job['documentNumber']))

    if session.execute(already_printed).first():
        log_error(job, "Document already printed")
        raise PrintError("Document already printed")

    try:
        decoded_content = base64.b64decode(job['content']).decode('utf-8')
    except Exception as e:
        log_error(job, f"Failed to decode content: {str(e)}")
        raise ValueError(f"Failed to decode content: {str(e)}")
    
    # Add ESC/POS commands for margin removal
    ESC = '\x1b'
    formatted_content = (
        ESC + '@' +           # Initialize printer
        ESC + 'l' + '\x00' +  # Left margin = 0
        ESC + 'Q' + '\x00' +  # Right margin = 0
        decoded_content +
        ESC + 'i'             # Cut paper
    )
    
    out_file = os.path.abspath(os.path.join('..', 'temp', job['documentNumber']))
    out = out_file + ".txt"
    
    # Write as bytes directly
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'wb') as f:
            f.write(formatted_content.encode('latin-1'))
    except Exception as e:
        log_error(job, f"Failed to write file: {str(e)}")
        raise IOError(f"Failed to write file: {str(e)}")
    
    if not os.path.exists(out):
        log_error(job, "File not created.")
        raise FileNotFoundError("File not created.")
    
    print_file(out, printer)

    print_log = insert(PrintJob).values(
        creation_date=datetime.datetime.now(),
        modified=datetime.datetime.now(),
        document_type=job['documentType'],
        document_number=job['documentNumber'],
        print_status="Success",
        error_message="",
    )

    session.execute(print_log)
    session.commit()


def print_file(file_path, printer):
    """Print file directly to printer using raw data"""
    try:
        # Read the file content
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        # Open printer
        printer_handle = win32print.OpenPrinter(printer)
        
        # Start print job
        job_info = ("Python Print Job", None, "RAW")
        job_id = win32print.StartDocPrinter(printer_handle, 1, job_info)
        
        # Start page
        win32print.StartPagePrinter(printer_handle)
        
        # Send raw data to printer
        win32print.WritePrinter(printer_handle, raw_data)
        
        # End page and job
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
        
        # Close printer
        win32print.ClosePrinter(printer_handle)
        
    except Exception as e:
        raise PrintError(f"Failed to print: {str(e)}")

def main():
    print_file("invoice.txt", "HP598857 (HP DeskJet Plus 4100 series)")
    f = open("invoice.txt", "rb")
    content = f.read()
    decoded_string = base64.b64encode(content).decode('ascii')
    f.close()
    print_job({
        "content": decoded_string,
        "documentNumber": "1000001",
        "documentType": "Sales Invoice",
        "printerCode": "",
    }, "HP598857 (HP DeskJet Plus 4100 series)")


if __name__ == "__main__":
    main()
