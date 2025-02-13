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

    out_file = os.path.abspath(os.path.join('..', 'temp', job['documentNumber']))
    out = out_file + ".txt"
    document_name = job['documentNumber'] + ".txt"

    write_string_to_file(job['content'], out)
    if not os.path.exists(out):
        log_error(job, "File not created.")
        raise PrintError("File not created.")

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
    file_path = os.path.abspath(file_path)
    all_printers = [printer[2] for printer in win32print.EnumPrinters(6)]
    if not printer in all_printers:
        raise PrintError("Printer not found")

    win32api.ShellExecute(0, "print", file_path, f'"{printer}"', ".", 3)


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
