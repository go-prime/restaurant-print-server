import base64
import shutil
import os


def encode_string_to_bytes(s):
    byte_ascii = s.encode('ascii')
    return base64.b64decode(byte_ascii)


def write_string_to_file(ascii_string, filename):
    with open(filename, 'wb') as f:
        f.write(encode_string_to_bytes(ascii_string))


def copy_files_between_machines(source, destination):
    source = os.path.abspath(source)
    shutil.copy(source, destination)


def get_contents_of_folder(folder):
    return os.listdir(folder)

def write_bytes_to_file(data, file_path):
    """
    Write bytes data to a file
    
    Args:
        data: bytes or string data to write
        file_path: path where to write the file
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            if isinstance(data, str):
                # If string, encode to bytes using latin-1 to preserve ESC/POS commands
                f.write(data.encode('latin-1'))
            else:
                # If already bytes, write directly
                f.write(data)
                
    except Exception as e:
        raise IOError(f"Failed to write file {file_path}: {str(e)}")


def main():
    source = "job.html"
    destination = r"\\DESKTOP-UBPGDCQ\shared"
    # copy_files_between_machines(source, destination)
    # print(get_contents_of_folder(destination))

if __name__ == "__main__":
    main()