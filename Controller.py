import zlib

from functools import partial
from ImageType import ImageType
from OneTimePad import OneTimePad
from typing import Callable
from VideoType import VideoType
from WavType import WavType

COMPRESSION_LEVEL = 9

class Controller:
    
    def handle_encode(
        self,
        filepath: str,
        secret_message: str,
        nr_lsb_used: int,
        apply_encryption: bool,
        select_output_path: Callable
        ):
        exception = None
        mask = None
        try:
            compressed_message = zlib.compress(bytes(secret_message,'utf-8'), COMPRESSION_LEVEL)

            if apply_encryption: 
                otp = OneTimePad(len(compressed_message))
                final_message = otp.encrypt(compressed_message)
                mask = otp.get_hexmask()
            else:
                final_message = compressed_message

            extension = (filepath.split('.'))[1].lower()

            if extension == "jpg":
                raise ValueError("JPEG files are not supported for encoding. Please use PNG.")

            select_output_path = partial(select_output_path, extension)
            output_path = select_output_path()
            if not output_path:
                raise ValueError("No output path was selected.")

            match extension:
                case "png":
                    ImageType.encode(filepath, final_message, nr_lsb_used, lambda: output_path)
                case "wav":
                    WavType.encode(filepath, final_message, nr_lsb_used, lambda: output_path)
                case "mp4":
                    VideoType.encode(filepath, final_message, nr_lsb_used, lambda: output_path)
                case _:
                    raise ValueError(f"Unable to support encoding for {extension} files!")

        except Exception as e:
            exception = e
        
        return mask, exception

    def handle_decode(
        self,
        filepath: str,
        nr_lsb_used: int,
        mask: bytes
        ):
        exception = None
        decompressed_message = None
        try:
            extension = (filepath.split('.'))[1].lower()
            match extension:
                case "png":
                    secret_message = ImageType.decode(filepath, nr_lsb_used)
                case "jpg":
                    secret_message = ImageType.decode(filepath, nr_lsb_used)
                case "wav":
                    secret_message = WavType.decode(filepath, nr_lsb_used)
                case "mp4":
                    secret_message = VideoType.decode(filepath, nr_lsb_used)
                case _:
                    raise ValueError(f"Unable to support decoding for {extension} files!")
            
            if len(mask):
                if len(mask) != len(secret_message):
                    raise ValueError(f"The length of the mask({len(mask)}) doesn't match with the length of the message ({len(secret_message)})!")
                
                decrypted_message = OneTimePad.decrypt(secret_message, mask)
            else:
                decrypted_message = secret_message

            decompressed_message = zlib.decompress(decrypted_message)

        except Exception as e:
            exception = e
        
        return decompressed_message, exception
