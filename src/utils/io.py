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


def main():
    source = "job.html"
    destination = r"\\DESKTOP-UBPGDCQ\shared"
    # copy_files_between_machines(source, destination)
    # print(get_contents_of_folder(destination))

if __name__ == "__main__":
    main()