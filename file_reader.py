# You need to implement the "get" and "head" functions.
from os import path


class FileReader:
    def __init__(self):
        pass

    def get(self, filepath, cookies):
        """
        Returns a binary string of the file contents, or None.
        """
        # print(filepath)
        if path.isfile(filepath):
            file = open(filepath, "rb")
            data = file.read()
            file.close()
            return data
        if path.isdir(filepath):
            return f"<html><body><h1>{filepath}</h1></body></html>".encode()

        return None

    def head(self, filepath, cookies):
        """
        Returns the size to be returned, or None.
        """
        # print(filepath)
        if path.isfile(filepath):
            file_size = path.getsize(filepath)
            return file_size
        if path.isdir(filepath):
            return f"<html><body><h1>{filepath}</h1></body></html>".encode()

        return None
