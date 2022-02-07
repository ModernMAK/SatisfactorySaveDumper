# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from contextlib import contextmanager
from struct import Struct
from typing import BinaryIO, Tuple, Any, List, Union

StructAble = Union[Struct, str, bytes]
UInt8 = Struct("B")
UInt16 = Struct("H")
UInt32 = Struct("I")
UInt64 = Struct("L")
Byte = Struct("c")


class StructIO:
    str_null_terminated_default = False

    def __init__(self, stream: BinaryIO, str_null_terminated: bool = None):
        self.stream = stream
        self._str_null_terminated = str_null_terminated or self.str_null_terminated_default

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def EOS(self) -> bool:
        with self.bookmark():
            return len(self.read(1)) == 0

    def read(self, n: int = ...) -> bytes:
        return self.stream.read(n)

    def write(self, value: bytes) -> int:
        return self.stream.write(value)

    def seek(self, offset: int, whence: int = None) -> int:
        return self.stream.seek(offset, whence) if whence else self.stream.seek(offset)

    def tell(self) -> int:
        return self.stream.tell()

    @contextmanager
    def window(self, start: int = None, end: int = None, size: int = None):
        yield Window(self.stream, start, end, size, str_null_terminated=self._str_null_terminated)

    @contextmanager
    def bookmark(self):
        pos = self.stream.tell()
        yield
        self.stream.seek(pos)

    def unpack(self, layout: StructAble) -> Any:
        layout = self._parse_struct(layout)

        buffer = self.stream.read(layout.size)
        result = layout.unpack(buffer)
        if isinstance(result, tuple) and len(result) == 1:
            return result[0]
        else:
            return result

    def pack(self, layout: StructAble, data: Any) -> int:
        layout = self._parse_struct(layout)

        buffer = layout.pack(data)
        return self.stream.write(buffer)

    def unpack_len_encoded_bytes(self, length_layout: StructAble = UInt32, data_layout: StructAble = Byte) -> bytes:
        length_layout = self._parse_struct(length_layout)
        data_layout = self._parse_struct(data_layout)

        count: int = self.unpack(length_layout)
        return self.read(count * data_layout.size)

    def unpack_len_encoded(self, length_layout: StructAble = UInt32, data_layout: StructAble = Byte) -> Tuple:
        length_layout = self._parse_struct(length_layout)
        data_layout = self._parse_struct(data_layout)

        count: int = self.unpack(length_layout)
        items = [self.unpack(data_layout) for _ in range(count)]
        return tuple(items)

    def pack_len_encoded_bytes(self, value: bytes, length_layout: StructAble = UInt32) -> int:
        length_layout = self._parse_struct(length_layout)

        count: int = len(value)
        written = self.pack(length_layout, count)
        written += self.write(value)
        return written

    def pack_len_encoded(self, value: List, data_layout: StructAble, length_layout: StructAble = UInt32) -> int:
        length_layout = self._parse_struct(length_layout)
        data_layout = self._parse_struct(data_layout)

        count: int = len(value)
        written = self.pack(length_layout, count)
        for item in value:
            written += self.pack(data_layout, item)
        return written

    def unpack_len_encoded_str(self, length_layout: StructAble = UInt32, encoding: str = None, errors: str = None, null_terminated: bool = None) -> str:
        null_terminated = null_terminated or self._str_null_terminated
        length_layout = self._parse_struct(length_layout)
        count: int = self.unpack(length_layout)
        bm = self.tell()
        buffer: bytes = self.read(count)
        try:
            decoded = self._decode(buffer, encoding, errors)
            if null_terminated:
                if len(decoded) > 0 and decoded[-1] != "\0":
                    raise ValueError(f"Expected null terminated string; null-charachter was not found! '{decoded}'")
                else:
                    decoded = decoded[:-1]
            return decoded
        except UnicodeDecodeError:
            raise ValueError(bm, "0x" + bm.to_bytes(4, "big").hex())

    def pack_len_encoded_str(self, value: str, length_layout: StructAble = UInt32, encoding: str = None, errors: str = None, null_terminated: bool = None) -> int:
        null_terminated = null_terminated or self._str_null_terminated

        if null_terminated and (len(value) > 0 and value[-1] != "\0"):
            value += "\0"

        length_layout = self._parse_struct(length_layout)
        buffer = self._encode(value, encoding, errors)
        count: int = len(buffer)
        written = self.pack(length_layout, count)
        written += self.write(buffer)
        return written

    @classmethod
    def _encode(cls, value: str, encoding: str = None, errors: str = None) -> bytes:
        if not encoding:
            return value.encode(errors=errors) if errors else value.encode()
        else:
            return value.encode(encoding=encoding, errors=errors) if errors else value.encode(encoding=encoding)

    @classmethod
    def _decode(cls, value: bytes, encoding: str = None, errors: str = None) -> str:
        if not encoding:
            return value.decode(errors=errors) if errors else value.decode()
        else:
            return value.decode(encoding=encoding, errors=errors) if errors else value.decode(encoding=encoding)

    @classmethod
    def _parse_struct(cls, layout: StructAble) -> Struct:
        return layout if isinstance(layout, Struct) else Struct(layout)


class Window(StructIO):
    @classmethod
    def __parse_start_end_size(cls, now: int, start: int = None, end: int = None, size: int = None) -> Tuple[int, int]:
        if start:
            if end and size:
                raise NotImplementedError
            elif end:
                return start, end - start
            elif size:
                return start, size
            else:
                raise NotImplementedError
        elif end:
            if size:
                return end - size, size
            else:
                return 0, end
        elif size:
            return now, size
        else:
            raise NotImplementedError

    def __init__(self, stream: BinaryIO, start: int = None, end: int = None, size: int = None, str_null_terminated: bool = None):
        super(Window, self).__init__(stream, str_null_terminated)
        start, size = self.__parse_start_end_size(stream.tell(), start, end, size)
