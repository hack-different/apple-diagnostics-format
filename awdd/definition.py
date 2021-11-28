from abc import ABC, abstractmethod
from enum import *

from . import *


class PropertyFlags(IntFlag):
    NONE = 0x00
    REPEATED = 0x01


class IntegerFormat(IntEnum):
    TIMESTAMP = 0x01
    TRIGGER_ID = 0x03
    PROFILE_ID = 0x04
    AVERAGE_TIME = 0x15
    TIME_DELTA = 0x16
    TIMEZONE_OFFSET = 0x17
    ASSOCIATED_TIME = 0x18
    PERIOD_IN_HOURS = 0x19
    TIME_OF_DAY = 0x1E
    SAMPLE_TIMESTAMP = 0x1F


class StringFormat(IntEnum):
    UNKNOWN = 0x00
    UUID = 0x01


class PropertyType(IntEnum):
    UNKNOWN = 0x00
    DOUBLE = 0x01
    FLOAT = 0x02
    INTEGER_64 = 0x03
    INTEGER = 0x04
    UNKNOWN_5 = 0x05
    INTEGER_32 = 0x06
    INTEGER_UNSIGNED = 0x07
    UNKNOWN_8 = 0x08
    UNKNOWN_9 = 0x09
    UNKNOWN_10 = 0x0A
    BOOLEAN = 0x0C
    ENUM = 0x0B
    STRING = 0x0D
    BYTES = 0x0E
    PACKED_UINT_32 = 0x15
    UNKNOWN_17 = 0x11
    UNKNOWN_20 = 0x14
    OBJECT = 0x1B


class PropertySensitivity(IntEnum):
    NONE = 0x00
    SENSITIVE = 0x01
    PRIVATE = 0x03


class ManifestProperty:
    index: int
    name: Optional[str]
    type: PropertyType
    flags: PropertyFlags
    version: int
    integer_format: Optional[IntegerFormat]
    string_format: Optional[StringFormat]
    object_reference: Optional[int]
    list_item_type: Optional[int]
    extension: bool
    target: Optional[int]
    content: Optional[bytes]
    sensitivity: PropertySensitivity

    TAG_INDEX = 0x01
    TAG_TYPE = 0x02
    TAG_FLAGS = 0x03
    TAG_NAME = 0x04
    TAG_OBJECT_REFERENCE = 0x05
    TAG_STRING_FORMAT = 0x06
    TAG_LIST_ITEM_TYPE = 0x07
    TAG_ENUM_INDEX = 0x08
    TAG_INTEGER_FORMAT = 0x09
    TAG_EXTENSION = 0x0A
    TAG_EXTENSION_TARGET = 0x0B
    TAG_SENSITIVITY = 0x0C


    PROPERTY_MAP = {
        TAG_NAME: 'name',
        TAG_INDEX: 'index',
        TAG_TYPE: 'type',
        TAG_FLAGS: 'flags',
        TAG_OBJECT_REFERENCE: 'object_reference',
        TAG_STRING_FORMAT: 'string_format',
        TAG_LIST_ITEM_TYPE: 'list_item_type',
        TAG_ENUM_INDEX: 'enum',
        TAG_INTEGER_FORMAT: 'integer_format',
        TAG_EXTENSION: 'extension',
        TAG_EXTENSION_TARGET: 'target',
        TAG_SENSITIVITY: 'sensitivity'
    }

    def __str__(self):
        name = "anonymous" if self.name is None else self.name
        return f"<PropertyDefinition {name} type:{self.type} index:{hex(self.index)} flags:{self.flags}>"

    def __init__(self, parent):
        self.type = PropertyType.UNKNOWN
        self.name = None
        self.type_name = None
        self.parent = parent
        self.extension = False
        self.index = 0x00
        self.integer_format = None
        self.string_format = None
        self.flags = PropertyFlags.NONE
        self.content = None
        self.unknowns = {}

    def parse(self, content: bytes):
        self.content = content

        tags = decode_tags(content)

        for tag in tags:
            if tag.index == ManifestProperty.TAG_TYPE:
                if tag.tag_type & TagType.LENGTH_PREFIX:
                    type_extended = io.BytesIO(tag.value)
                    while extend_tag := decode_tag(type_extended):
                        if extend_tag.index == 0x01:
                            self.type_name = extend_tag.value
                        else:
                            self.type = PropertyType(extend_tag.value)
                else:
                    self.type = PropertyType(tag.value)

            elif tag.index == ManifestProperty.TAG_FLAGS:
                self.flags = PropertyFlags(tag.value)

            elif tag.index == ManifestProperty.TAG_INTEGER_FORMAT:
                try:
                    self.integer_format = IntegerFormat(tag.value)
                except ValueError as ex:
                    print(f"Unable to set integer format on {self.name} to {hex(tag.value)}", ex)

            elif tag.index == ManifestProperty.TAG_STRING_FORMAT:
                self.string_format = StringFormat(tag.value)

            elif tag.index == ManifestProperty.TAG_NAME:
                self.name = tag.value.decode('utf-8')

            elif tag.index == ManifestProperty.TAG_EXTENSION:
                self.extension = False if tag.value == 0 else True

            else:
                self.__setattr__(ManifestProperty.PROPERTY_MAP[tag.index], tag.value)

        self.flags = PropertyFlags(self.flags)

        try:
            self.type = PropertyType(self.type)
        except ValueError:
            print(
                f"Unable to set type for property {self.name if self.name is not None else 'anonymous'} for class "
                "{self.parent.name} to type {hex(self.type)}")


T = TypeVar('T', bound='ManifestDefinition')


class ManifestDefinition(ABC):
    TAG = 0

    @abstractmethod
    def parse(self, data: bytes):
        pass

    @classmethod
    def from_tag(cls: Type[T], tag: Tag) -> T:
        if tag.index != cls.TAG:
            raise ManifestError(f"Attempted to parse the wrong definition, value {tag.index} is not of type {cls.TAG}")
        return cls.from_bytes(tag.value)

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        result = cls()
        result.parse(data)


class ManifestEnumMember:
    name: str | int
    value: int
    display: str
    unknowns: Dict[int, Any]

    TAG_NAME = 0x01
    TAG_VALUE_INT = 0x02
    TAG_VALUE_SIGNED = 0x03

    def __init__(self, data: bytes):
        self.data = data
        reader = io.BytesIO(data)
        self.unknowns = {}

        while tag := decode_tag(reader):
            print(tag)
            if tag.index == ManifestEnumMember.TAG_NAME:
                if tag.value is str:
                    self.name = tag.value.decode('utf-8')
                else:
                    self.name = tag.value

            elif tag.index == ManifestEnumMember.TAG_VALUE_INT:
                self.value = tag.value

            elif tag.index == ManifestEnumMember.TAG_VALUE_SIGNED:
                # TODO: this is a special INT case - seems to be twos complement of length
                # encoded integer, value seen was '\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01'
                # implying signed int64

                self.value = tag.value

            else:
                print(f"Unknown tag type in EnumMember definition {hex(tag.index)} = {tag.value}")
                self.unknowns[tag.index] = tag.value

    def __str__(self):
        return f"<ManifestEnumMember {self.name} = {hex(self.value)}>"


class ManifestEnumDefinition(ManifestDefinition):
    TAG = 2
    entries: List[ManifestEnumMember]
    name: Optional[str]
    content: Optional[bytes]
    extend: int

    TAG_NAME = 0x01
    TAG_ENUM_MEMBER = 0x02
    TAG_ENUM_MEMBER_NAME = 0x1E

    def __init__(self):
        super().__init__()
        self.entries = []
        self.name = None
        self.content = None

    def __str__(self):
        return f"<ManifestEnumDefinition {self.name} value_count:{len(self.entries)}>"

    def parse(self, data: bytes):
        self.content = data

        tags = decode_tags(data)

        for tag in tags:
            if tag == ManifestEnumDefinition.TAG_NAME:
                self.name = tag.value.decode('utf-8')

            elif tag == ManifestEnumDefinition.TAG_ENUM_MEMBER:
                self.entries.append(ManifestEnumMember(tag.value))


class ManifestObjectDefinition(ManifestDefinition):
    TAG = 1
    content: Optional[bytes]
    name: str
    properties: List[ManifestProperty]

    TAG_NAME = 0x01
    TAG_PROPERTY_DEFINITION = 0x02
    TAG_EXTEND = 0x0A

    def __init__(self):
        super().__init__()

        self.name = '__anonymous__'
        self.properties = []
        self.content = None

    def __str__(self):
        if self.name is not None:
            return f"<ManifestObject name:{self.name} property_count:{len(self.properties)}>"
        else:
            return f"<ManifestObject __anonymous__ property_count:{len(self.properties)}>"

    def parse(self, content: bytes):
        reader = io.BytesIO(content)

        while tag := decode_tag(reader):
            if tag.index == ManifestObjectDefinition.TAG_PROPERTY_DEFINITION:
                prop = ManifestProperty(self)
                prop.parse(tag.value)
                self.properties.append(prop)

            elif tag.index == ManifestObjectDefinition.TAG_NAME:
                self.name = tag.value

            else:
                raise ManifestError(f"Unknown tag {hex(tag.index)} in object {self.name}")
