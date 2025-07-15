import cv2
import sys
import numpy as np
from math import ceil
from typing import Callable
from FileType import FileType


class VideoType(FileType):

    @staticmethod
    def encode(
        input_video_path: str,
        secret_message: bytes,
        nr_lsb_used: int,
        select_output_path: Callable[[], str]
    ) -> None:
        cap = cv2.VideoCapture(input_video_path)

        frames_bytes = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_bytes = frame.tobytes()
            frames_bytes.append(frame_bytes)

        all_frames_bytes = b''.join(frames_bytes)
        message_length = len(secret_message)
        nr_bytes_available = (len(all_frames_bytes) * nr_lsb_used) // 8

        file_size = message_length.to_bytes(4, byteorder='big')  # Fixed 4-byte header
        final_message = file_size + secret_message

        if len(final_message) > nr_bytes_available:
            raise ValueError(
                f"Only able to encode {nr_bytes_available} bytes \
                    in video, but message length is {len(final_message)} bytes!"
            )

        all_frames_bytes = FileType.encode_message_in_carrier_bytes(
            all_frames_bytes, final_message, nr_lsb_used
        )

        output_file_path = select_output_path()
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        try:
            out = cv2.VideoWriter(output_file_path, fourcc, fps, (width, height))
            modified_frames_np = np.frombuffer(all_frames_bytes, dtype=np.uint8)
            modified_frames_np = modified_frames_np.reshape((-1, height, width, 3))
            for frame in modified_frames_np:
                out.write(frame)

            out.release()
            cv2.destroyAllWindows()
        except Exception as e:
            print(str(e))

    @staticmethod
    def decode(
        encoded_video_path: str,
        nr_lsb_used: int
    ) -> bytes:
        cap = cv2.VideoCapture(encoded_video_path)
        frames_bytes = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_bytes = frame.tobytes()
            frames_bytes.append(frame_bytes)

        all_frames_bytes = b''.join(frames_bytes)

        header_bits = 4 * 8  # 4-byte message length header
        rightmost_bit_index = int(ceil(header_bits / nr_lsb_used))

        header_bytes = FileType.decode_message_from_carrier(
            list(all_frames_bytes[:rightmost_bit_index]),
            rightmost_bit_index,
            nr_lsb_used
        )
        message_length = int.from_bytes(header_bytes, byteorder='big')

        total_bits = (4 + message_length) * 8
        if total_bits > len(all_frames_bytes) * nr_lsb_used:
            raise ValueError("No secret message hidden in this video with this app, or the video is corrupted!")

        temp = FileType.decode_message_from_carrier(
            list(all_frames_bytes), total_bits, nr_lsb_used
        )[4:]

        return temp
