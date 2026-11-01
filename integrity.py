import hashlib

class FileIntegrity:
    @staticmethod
    def get_hash(filepath: str) -> str:
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def verify(file1: str, file2: str) -> bool:
        return FileIntegrity.get_hash(file1) == FileIntegrity.get_hash(file2)