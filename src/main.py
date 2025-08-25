import BaseModel

class CreateScanInfoRequest(BaseModel) :
    member_id : int
    img_path : str

