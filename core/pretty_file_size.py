class File_Size_Converter:
    bytes=0
    value = 0
    unit = "bytes"
    triverse_order = [
        "bytes",
        "kilo_bytes",
        "mega_bytes",
        "giga_bytes",
        "tera_bytes",
        "peta_bytes",
        "exa_bytes",
        "zetta_bytes",
        "yotta_bytes"
    ]
    def __init__(self, Bytes):
        """
        Enter file size in bytes to convert the size into some other unit.
        """
        if type(Bytes)==str:
            self.unit = None
            self.value = Bytes
        if type(Bytes)==int:
            self.bytes = Bytes
            self.unit = "bytes"
            self.kilo_bytes = self.bytes/1024
            self.mega_bytes = self.kilo_bytes/1024
            self.giga_bytes = self.mega_bytes/1024
            self.tera_bytes = self.giga_bytes/1024
            self.peta_bytes = self.tera_bytes/1024
            self.exa_bytes = self.peta_bytes/1024
            self.zetta_bytes = self.exa_bytes/1024
            self.yotta_bytes = self.zetta_bytes/1024
            str(self)
    
    def __str__(self):
        if self.unit.endswith("bytes") and self.bytes>=1:
            self.value = 0
            self.unit = "bytes"
            for attr_name in self.triverse_order:
                if attr_name.endswith("bytes") and not attr_name.startswith("get"):
                    value = self.__getattribute__(attr_name)
                    if value>=1:
                        self.unit = attr_name
                        self.value = round(value, 2)
                    
            return f"{self.value} {self.unit}"
        
        return f"coudn't retrive file size"
    
    def _get_tuple(self):
        return self.value, self.unit

    def get_bytes(self):
        return self.bytes
    
    def get_kilo_bytes(self):
        return self.kilo_bytes
    
    def get_mega_bytes(self):
        return self.mega_bytes
    
    def get_giga_bytes(self):
        return self.giga_bytes
    
    def get_tera_bytes(self):
        return self.tera_bytes
    
    def get_peta_bytes(self):
        return self.peta_bytes
    
    def get_exa_bytes(self):
        return self.exa_bytes
    
    def get_zetta_bytes(self):
        return self.zetta_bytes
    
    def get_yotta_bytes(self):
        return self.yotta_bytes


# from core.pretty_file_size import File_Size_Converter
# a=File_Size_Converter(999999)