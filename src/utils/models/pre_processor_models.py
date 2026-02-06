from dataclasses import dataclass
from uuid import uuid4
@dataclass
class ProcessedFileDTO:
    file_id:str = uuid4().hex
    file_name:str = str()
    file_path:str = str()
    total_loc:int = 0

@dataclass
class UnProcessedFileDTO:
    file_name:str
    file_path:str
    ignore_reason:str
