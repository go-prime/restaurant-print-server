import win32api
import win32print
import os


from sqlalchemy import create_engine, select, insert
from sqlalchemy.orm import Session
import datetime
import base64
import re
from typing import Dict, Tuple
from loggers import logger


engine = create_engine("sqlite:///instance//print.db", echo=True)
session = Session(bind=engine)

class PrintError(Exception):
    pass


class ESCPOSFormatter:
    """Convert simple markup to ESC/POS commands"""
    
    def __init__(self):
        # ESC/POS command constants
        self.ESC = b'\x1b'
        self.GS = b'\x1d'
        
        # Text formatting commands
        self.commands = {
            'INIT': self.ESC + b'@',           # Initialize printer
            'BOLD_ON': self.ESC + b'E',        # Bold on
            'BOLD_OFF': self.ESC + b'F',       # Bold off
            'UNDERLINE_ON': self.ESC + b'-1',  # Underline on
            'UNDERLINE_OFF': self.ESC + b'-0', # Underline off
            'SIZE_NORMAL': self.GS + b'!0',    # Normal size
            'SIZE_LARGE': self.GS + b'!1',     # Large size
            'ALIGN_LEFT': self.ESC + b'a0',    # Left align
            'ALIGN_CENTER': self.ESC + b'a1',  # Center align
            'ALIGN_RIGHT': self.ESC + b'a2',   # Right align
            'CUT': self.ESC + b'i',            # Cut paper
            'FEED_LINE': b'\n',                # Line feed
            'MARGIN_LEFT_0': self.ESC + b'l\x00',  # Left margin = 0
            'MARGIN_RIGHT_0': self.ESC + b'Q\x00', # Right margin = 0
        }
    
    def convert_markup_to_escpos(self, text: str) -> bytes:
        """Convert markup text to ESC/POS commands"""
        
        # Initialize with clear margins
        result = self.commands['INIT'] + self.commands['MARGIN_LEFT_0'] + self.commands['MARGIN_RIGHT_0']
        
        # Track current state
        current_state = {
            'bold': False,
            'underline': False,
            'size': 'normal',
            'align': 'left'
        }
        
        # Process the text
        processed_text = self._process_markup(text, current_state)
        result += processed_text.encode('latin-1', errors='ignore')
        
        return result
    
    def _process_markup(self, text: str, state: Dict) -> str:
        """Process markup tags and convert to ESC/POS"""
        
        # Define tag patterns and their ESC/POS equivalents
        patterns = [
            (r'\[B\](.*?)\[/B\]', self._handle_bold),
            (r'\[U\](.*?)\[/U\]', self._handle_underline),
            (r'\[L\](.*?)\[/L\]', self._handle_large),
            (r'\[N\](.*?)\[/N\]', self._handle_normal),
            (r'\[C\](.*?)\[/C\]', self._handle_center),
            (r'\[R\](.*?)\[/R\]', self._handle_right),
            (r'\[CUT\]', self._handle_cut),
            (r'\[FEED:(\d+)\]', self._handle_feed),
        ]
        
        result = text
        
        for pattern, handler in patterns:
            result = re.sub(pattern, handler, result, flags=re.DOTALL)
        
        return result
    
    def _handle_bold(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['BOLD_ON'].decode('latin-1')}{content}{self.commands['BOLD_OFF'].decode('latin-1')}"
    
    def _handle_underline(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['UNDERLINE_ON'].decode('latin-1')}{content}{self.commands['UNDERLINE_OFF'].decode('latin-1')}"
    
    def _handle_large(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['SIZE_LARGE'].decode('latin-1')}{content}{self.commands['SIZE_NORMAL'].decode('latin-1')}"
    
    def _handle_normal(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['SIZE_NORMAL'].decode('latin-1')}{content}"
    
    def _handle_center(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['ALIGN_CENTER'].decode('latin-1')}{content}{self.commands['ALIGN_LEFT'].decode('latin-1')}"
    
    def _handle_right(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['ALIGN_RIGHT'].decode('latin-1')}{content}{self.commands['ALIGN_LEFT'].decode('latin-1')}"
    
    def _handle_cut(self, match) -> str:
        return self.commands['CUT'].decode('latin-1')
    
    def _handle_feed(self, match) -> str:
        lines = int(match.group(1))
        return '\n' * lines

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
    Enhanced print job with formatting support
    '''
    from utils.io import write_string_to_file
    from models import PrintJob

    # Check if already printed
    already_printed = (select(PrintJob)
        .where(PrintJob.document_type == job['documentType'])
        .where(PrintJob.document_number == job['documentNumber'])
        .where(PrintJob.print_status == "Success")
    )

    if session.execute(already_printed).first() and not job.get('reprint'):
        log_error(job, "Document already printed")
        raise PrintError("Document already printed")

    try:
<<<<<<< HEAD
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
=======
        # Decode content
        decoded_content = base64.b64decode(job['content']).decode('utf-8')
        
        # Convert markup to ESC/POS
        formatter = ESCPOSFormatter()
        formatted_content = formatter.convert_markup_to_escpos(decoded_content)
        
    except Exception as e:
        log_error(job, f"Failed to process content: {str(e)}")
        raise ValueError(f"Failed to process content: {str(e)}")
    
    # Write to file
    out_file = os.path.abspath(os.path.join('..', 'temp', job['documentNumber']))
    out = out_file + ".txt"
    
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'wb') as f:
            f.write(formatted_content)
>>>>>>> d67a1051b3c9852358c03dbc252e20206dc2e856
    except Exception as e:
        log_error(job, f"Failed to write file: {str(e)}")
        raise IOError(f"Failed to write file: {str(e)}")
    
    if not os.path.exists(out):
        log_error(job, "File not created.")
        raise FileNotFoundError("File not created.")
    
    print_file(out, printer)

    # Log success
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
