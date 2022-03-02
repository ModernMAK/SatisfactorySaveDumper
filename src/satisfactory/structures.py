from dataclasses import dataclass
from typing import List, ForwardRef, BinaryIO, Dict, Callable

from serialization_tools.structx import Struct
from serialization_tools.vstruct import VStruct

from .shared import NonePropertyError

Property = ForwardRef("Property")


@dataclass(unsafe_hash=True)
class Vector2:
    LAYOUT = Struct("2f")
    x: float
    y: float

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Vector2':
        xy = cls.LAYOUT.unpack_stream(stream)
        return Vector2(*xy)

    def pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.x, self.y)


@dataclass(unsafe_hash=True)
class Vector3(Vector2):
    LAYOUT = Struct("3f")
    z: float

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Vector3':
        xyz = cls.LAYOUT.unpack_stream(stream)
        return Vector3(*xyz)

    def pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.x, self.y, self.z)


@dataclass(unsafe_hash=True)
class Vector4(Vector3):
    LAYOUT = Struct("4f")
    w: float

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Vector4':
        xyzw = cls.LAYOUT.unpack_stream(stream)
        return Vector4(*xyzw)

    def pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.x, self.y, self.z, self.w)


@dataclass(unsafe_hash=True)
class ObjectReference:
    LAYOUT = VStruct("2v")
    level: str
    path: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ObjectReference':
        args = cls.LAYOUT.unpack_stream(stream)
        return ObjectReference(*args)

    def pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.level, self.path)


@dataclass(unsafe_hash=True)
class DateTime:
    unks: bytes  # TODO decipher

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'DateTime':
        return DateTime(stream.read())


@dataclass(unsafe_hash=True)
class Color32:
    LAYOUT = Struct("4c")

    r: int
    g: int
    b: int
    a: int

    @staticmethod
    def _is_byte(value: int) -> bool:
        return 0 <= value <= 255

    @property
    def is_valid(self):
        return self._is_byte(self.r) and self._is_byte(self.g) and self._is_byte(self.b) and self._is_byte(self.a)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Color32':
        rgba = cls.LAYOUT.unpack_stream(stream)
        return Color32(*rgba)

    def pack(self, stream: BinaryIO) -> int:
        if not self.is_valid:
            raise ValueError(self)
        return self.LAYOUT.pack_stream(stream, self.r, self.g, self.b, self.a)


@dataclass(unsafe_hash=True)
class Color:
    LAYOUT = Struct("4f")
    r: float
    g: float
    b: float
    a: float

    @staticmethod
    def _is_valid(value: float) -> bool:
        return 0 <= value <= 1

    @property
    def is_valid(self):
        return self._is_valid(self.r) and self._is_valid(self.g) and self._is_valid(self.b) and self._is_valid(self.a)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Color':
        rgba = cls.LAYOUT.unpack_stream(stream)
        return Color(*rgba)

    def pack(self, stream: BinaryIO) -> int:
        if not self.is_valid:
            raise ValueError(self)
        return self.LAYOUT.pack_stream(stream, self.r, self.g, self.b, self.a)


Quaternion = Vector4
Rotator = Vector3


@dataclass(unsafe_hash=True)
class Structure:
    structure_type: str

    @classmethod
    def unpack_as_type(cls, stream: BinaryIO, type: str) -> 'Structure':
        assert type[-1] != "\0", "Type contains trailing null character! This is likely an error!"
        assert isinstance(type[-1], str), "Type was not converted to string!"

        unpacker = _unpack_map.get(type, DynamicStructure.unpack)
        structure = unpacker(stream)
        structure.structure_type = type
        return structure


@dataclass(unsafe_hash=True)
class DynamicStructure(Structure):
    properties: List[Property]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'DynamicStructure':
        from satisfactory.properties import Property
        # None property used as terminal?
        properties = []
        while True:
            try:
                property = Property.unpack(stream)
                properties.append(property)
            except NonePropertyError:
                break

        return DynamicStructure(None, properties)


@dataclass(unsafe_hash=True)
class Box(Structure):  # Probably an AABB (Axis-Aligned Bounding Box), unk could be enabled?
    min: Vector3
    max: Vector3
    unk: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Box':
        # None property used as terminal?
        min = Vector3.unpack(stream)
        max = Vector3.unpack(stream)
        unk = stream.read(1)

        return Box(None, min, max, unk)


@dataclass(unsafe_hash=True)
class FluidBox(Structure):
    LAYOUT = Struct("f")
    unk: float

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'FluidBox':
        unk = cls.LAYOUT.unpack_stream(stream)
        return FluidBox(None,unk)


@dataclass(unsafe_hash=True)
class GuidStructure(Structure):
    data: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'GuidStructure':
        data = stream.read(16)
        return GuidStructure(None, data)


@dataclass(unsafe_hash=True)
class InventoryItem(Structure):
    LAYOUT = VStruct("i3v")
    a: int
    item_type: str
    b: str
    c: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'InventoryItem':
        args = cls.LAYOUT.unpack_stream(stream)
        return InventoryItem(None, *args)


_unpack_map: Dict[str, Callable] = {
    "Box": Box.unpack,
    # Confusing, I know; UnityDEV here
    #   color via 4 bytes is Color32
    #   color via 4 floats is Color
    "Color": Color32.unpack,
    "LinearColor": Color.unpack,
    "Quat": Quaternion.unpack,
    "Vector": Vector3.unpack,
    "Vector2D": Vector2.unpack,
    "Rotator": Rotator.unpack,
    "InventoryItem": InventoryItem.unpack,
    "FINNetworkTrace": None,
    "FluidBox": FluidBox.unpack,
    "RailroadTrackPosition": None,
    "Guid": GuidStructure.unpack,
    "DateTime": DateTime.unpack,
}
