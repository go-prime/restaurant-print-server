import win32api
import win32print
import os

from flask import g
from sqlalchemy import create_engine, select, insert
from sqlalchemy.orm import sessionmaker
import datetime
import base64
import re
from typing import Dict, Tuple
from loggers import logger


engine = create_engine("sqlite:///instance//print.db", echo=True)
session_factory = sessionmaker(bind=engine)


def get_session():
    """Get the request-local database session."""
    if 'db_session' not in g:
        g.db_session = session_factory()
    return g.db_session


class PrintError(Exception):
    pass


class ESCPOSFormatter:
    """Convert simple markup to ESC/POS commands for TM-T20III"""

    def __init__(self):
        # ESC/POS command constants
        self.ESC = b'\x1b'
        self.GS = b'\x1d'

        # TM-T20III specific commands based on documentation
        self.commands = {
            'INIT': self.ESC + b'@',                    # Initialize printer
            'BOLD_ON': self.ESC + b'E\x01',             # Turn emphasized mode on
            'BOLD_OFF': self.ESC + b'E\x00',            # Turn emphasized mode off
            'UNDERLINE_ON': self.ESC + b'-\x01',        # Turn underline mode on
            'UNDERLINE_OFF': self.ESC + b'-\x00',       # Turn underline mode off
            # Select character size (normal)
            'SIZE_NORMAL': self.GS + b'!\x00',
            # Select character size (double width & height)
            'SIZE_LARGE': self.GS + b'!\x11',
            # Select character size (double width)
            'SIZE_WIDE': self.GS + b'!\x10',
            # Select character size (double height)
            'SIZE_TALL': self.GS + b'!\x01',
            # Select justification (left)
            'ALIGN_LEFT': self.ESC + b'a\x00',
            # Select justification (center)
            'ALIGN_CENTER': self.ESC + b'a\x01',
            # Select justification (right)
            'ALIGN_RIGHT': self.ESC + b'a\x02',
            # Partial cut (one point left uncut)
            'CUT_PARTIAL': self.ESC + b'i',
            # Partial cut (three points left uncut)
            'CUT_FULL': self.ESC + b'm',
            'FEED_LINE': b'\n',                         # Line feed
            'FEED_AND_CUT': self.ESC + b'd\x03' + self.ESC + b'i',  # Feed 3 lines then cut
            'SET_LINE_SPACING_DEFAULT': self.ESC + b'2',  # Select default line spacing
            'DOUBLE_STRIKE_ON': self.ESC + b'G\x01',    # Turn double-strike mode on
            'DOUBLE_STRIKE_OFF': self.ESC + b'G\x00',   # Turn double-strike mode off
        }

    def convert_markup_to_escpos(self, text: str) -> bytes:
        """Convert markup text to ESC/POS commands"""

        # Initialize printer
        result = self.commands['INIT']

        # Process the text
        processed_text = self._process_markup(text)
        result += processed_text.encode('latin-1', errors='ignore')

        return result

    def _process_markup(self, text: str) -> str:
        """Process markup tags and convert to ESC/POS"""

        # Define tag patterns and their ESC/POS equivalents
        patterns = [
            # Text formatting
            (r'\[B\](.*?)\[/B\]', self._handle_bold),
            (r'\[U\](.*?)\[/U\]', self._handle_underline),
            (r'\[DS\](.*?)\[/DS\]', self._handle_double_strike),  # Double strike

            # Size controls
            # Large (double width & height)
            (r'\[L\](.*?)\[/L\]', self._handle_large),
            # Wide (double width)
            (r'\[W\](.*?)\[/W\]', self._handle_wide),
            # Tall (double height)
            (r'\[T\](.*?)\[/T\]', self._handle_tall),
            (r'\[N\](.*?)\[/N\]', self._handle_normal),          # Normal size

            # Alignment
            (r'\[C\](.*?)\[/C\]', self._handle_center),
            (r'\[R\](.*?)\[/R\]', self._handle_right),
            # Explicit left align
            (r'\[LEFT\](.*?)\[/LEFT\]', self._handle_left),

            # Paper control
            (r'\[CUT\]', self._handle_cut),
            (r'\[CUT:FULL\]', self._handle_cut_full),
            (r'\[FEED:(\d+)\]', self._handle_feed),

            # Special commands
            (r'\[BUZZER\]', self._handle_buzzer),
            (r'\[BUZZER:(\d+)\]', self._handle_buzzer_times),
        ]

        result = text

        for pattern, handler in patterns:
            result = re.sub(pattern, handler, result,
                            flags=re.DOTALL | re.IGNORECASE)

        return result

    def _handle_bold(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['BOLD_ON'].decode('latin-1')}{content}{self.commands['BOLD_OFF'].decode('latin-1')}"

    def _handle_underline(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['UNDERLINE_ON'].decode('latin-1')}{content}{self.commands['UNDERLINE_OFF'].decode('latin-1')}"

    def _handle_double_strike(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['DOUBLE_STRIKE_ON'].decode('latin-1')}{content}{self.commands['DOUBLE_STRIKE_OFF'].decode('latin-1')}"

    def _handle_large(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['SIZE_LARGE'].decode('latin-1')}{content}{self.commands['SIZE_NORMAL'].decode('latin-1')}"

    def _handle_wide(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['SIZE_WIDE'].decode('latin-1')}{content}{self.commands['SIZE_NORMAL'].decode('latin-1')}"

    def _handle_tall(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['SIZE_TALL'].decode('latin-1')}{content}{self.commands['SIZE_NORMAL'].decode('latin-1')}"

    def _handle_normal(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['SIZE_NORMAL'].decode('latin-1')}{content}"

    def _handle_center(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['ALIGN_CENTER'].decode('latin-1')}{content}{self.commands['ALIGN_LEFT'].decode('latin-1')}"

    def _handle_right(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['ALIGN_RIGHT'].decode('latin-1')}{content}{self.commands['ALIGN_LEFT'].decode('latin-1')}"

    def _handle_left(self, match) -> str:
        content = match.group(1)
        return f"{self.commands['ALIGN_LEFT'].decode('latin-1')}{content}"

    def _handle_cut(self, match) -> str:
        return self.commands['CUT_PARTIAL'].decode('latin-1')

    def _handle_cut_full(self, match) -> str:
        return self.commands['CUT_FULL'].decode('latin-1')

    def _handle_feed(self, match) -> str:
        lines = int(match.group(1))
        if lines <= 255:  # ESC d command takes a single byte parameter
            return (self.ESC + b'd' + bytes([lines])).decode('latin-1')
        else:
            # For more than 255 lines, use multiple commands or line feeds
            return '\n' * lines

    def _handle_buzzer(self, match) -> str:
        # Sound buzzer once (DLE DC4 fn=3)
        return '\x10\x14\x03'

    def _handle_buzzer_times(self, match) -> str:
        # Sound buzzer multiple times
        times = int(match.group(1))
        # Limit to prevent excessive buzzing
        return '\x10\x14\x03' * min(times, 10)


def log_error(job, error):
    from models import ErrorLog
    logger.error("Error: %s" % error)

    # Get request-local session
    session = get_session()
    try:
        err_log = insert(ErrorLog).values(
            creation_date=datetime.datetime.now(),
            document_number=job['documentNumber'],
            status="Error",
            error=error
        )
        session.execute(err_log)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to log error: {str(e)}")


def print_job(job, printer):
    '''
    Enhanced print job with formatting support
    '''
    from utils.io import write_string_to_file
    from models import PrintJob

    # Get request-local session
    session = get_session()

    try:
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
            # Decode content
            decoded_content = base64.b64decode(job['content']).decode('utf-8')

            # Convert markup to ESC/POS
            formatter = ESCPOSFormatter()
            formatted_content = formatter.convert_markup_to_escpos(
                decoded_content)

        except Exception as e:
            log_error(job, f"Failed to process content: {str(e)}")
            raise ValueError(f"Failed to process content: {str(e)}")

        # Write to file
        out_file = os.path.abspath(os.path.join(
            '..', 'temp', job['documentNumber']))
        out = out_file + ".txt"

        try:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, 'wb') as f:
                f.write(formatted_content)
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

    except Exception as e:
        session.rollback()
        raise


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
