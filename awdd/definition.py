from abc import ABC, abstractmethod
from enum import *

from . import *


class PropertyFlags(IntFlag):
    NONE = 0x00
    REPEATED = 0x01


class IntegerFormat(IntEnum):
    TIMESTAMP = 0x01
    METRIC_ID = 0x02
    TRIGGER_ID = 0x03
    PROFILE_ID = 0x04
    COMPONENT_ID = 0x05
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
    ERROR_CODE = 0x05
    INTEGER_32 = 0x06
    INTEGER_UNSIGNED = 0x07
    BYTE_COUNT = 0x08
    SEQUENCE_NUMBER = 0x09
    BEDF_OPERATOR = 0x0A
    BOOLEAN = 0x0C
    ENUM = 0x0B
    STRING = 0x0D
    BYTES = 0x0E
    PACKED_UINT_32 = 0x15
    PACKED_TIMES = 0x11
    PACKED_ERRORS = 0x14
    OBJECT = 0x1B


class PropertyExtensionType(IntEnum):
    NONE = 0x00
    ADD_PROPERTY = 0x01
    REPLACE_PROPERTY = 0x02


class ManifestExtensionScopeType(IntEnum):
    ROOT_SCOPE = 0x00
    LOCAL_SCOPE = 0x01
    GLOBAL_SCOPE = 0x02
    CONFIGURATION_SCOPE = 0x03


class ManifestPropertyTag(IntEnum):
    INDEX = 0x01
    TYPE = 0x02
    FLAGS = 0x03
    DISPLAY_NAME = 0x04
    PII = 0x05
    STRING_FORMAT = 0x06
    OBJECT_TYPE = 0x07
    ENUM_TYPE = 0x08
    INTEGER_FORMAT = 0x09
    EXTENSION_OPERATION = 0x0A
    EXTENSION_TAG = 0x0B
    EXTENSION_SCOPE = 0x0C


class ManifestDefinitionTag(IntEnum):
    DEFINE_OBJECT = 0x01
    DEFINE_TYPE = 0x02


class ManifestTypeDefinitionTag(IntEnum):
    DISPLAY_NAME = 0x01
    ENUM_MEMBER = 0x02


class ManifestObjectDefinitionTag(IntEnum):
    DISPLAY_NAME = 0x01
    PROPERTY_DEFINITION = 0x02


class ManifestEnumMemberTag(IntEnum):
    DISPLAY_NAME = 0x01
    VALUE_INT = 0x02
    VALUE_SIGNED = 0x03


def to_type_descriptor(target: Union[None, int, 'ManifestDefinition']) -> Optional[str]:
    if target:
        if isinstance(target, int):
            return hex(target)

        if target.name:
            return target.name

        return hex(target)

    return None


class ManifestProperty:
    index: int
    name: Optional[str]
    type: PropertyType
    flags: PropertyFlags
    version: int
    pii: bool
    integer_format: Optional[IntegerFormat]
    string_format: Optional[StringFormat]
    object_type: Union[None, int, 'ManifestObjectDefinition']
    extension_scope: ManifestExtensionScopeType
    extends: Union[None, int, 'ManifestDefinition']
    target: Union[None, int, 'ManifestDefinition']
    enum: Union[None, int, 'ManifestTypeDefinition']
    content: List[Tag]
    extension_flags: PropertyExtensionFlags

    def __str__(self):
        name = "anonymous" if self.name is None else self.name

        if self.type == PropertyType.OBJECT:
            object_target = f"class:{to_type_descriptor(self.object_type)} "
        else:
            object_target = ""

        if self.extends:
            object_extends = f"extends:{to_type_descriptor(self.extends)} "
        else:
            object_extends = ""

        return f"<PropertyDefinition {name} type:{repr(self.type)} tag:{hex(self.index)} flags:{repr(self.flags)} " \
               f"{object_target}{object_extends}>"

    def __init__(self, parent):
        self.type = PropertyType.UNKNOWN
        self.name = None
        self.type_name = None
        self.parent = parent
        self.extends = None
        self.pii = False
        self.extension_scope = ManifestExtensionScopeType.NONE
        self.integer_format = None
        self.string_format = None
        self.flags = PropertyFlags.NONE
        self.extension_flags = None

    def parse(self, content: bytes):
        self.content = decode_tags(content, ManifestPropertyTag)

        for tag in self.content:
            if tag.index == ManifestPropertyTag.TYPE:
                self.type = PropertyType(tag.value)

            elif tag.index == ManifestPropertyTag.FLAGS:
                self.flags = PropertyFlags(tag.value)

            elif tag.index == ManifestPropertyTag.INDEX:
                self.index = tag.value

            elif tag.index == ManifestPropertyTag.ENUM_TYPE:
                self.enum = tag.value

            elif tag.index == ManifestPropertyTag.PII:
                if tag.value == 0:
                    self.pii = False
                elif tag.value == 1:
                    self.pii = True
                else:
                    raise ManifestError(f"Unknown value for PII {tag.value}")

            elif tag.index == ManifestPropertyTag.OBJECT_TYPE:
                self.object_type = to_complete_tag(self.parent.category, tag.value)

            elif tag.index == ManifestPropertyTag.INTEGER_FORMAT:
                self.integer_format = IntegerFormat(tag.value)

            elif tag.index == ManifestPropertyTag.STRING_FORMAT:
                self.string_format = StringFormat(tag.value)

            elif tag.index == ManifestPropertyTag.DISPLAY_NAME:
                self.name = tag.value.decode('utf-8')

            elif tag.index == ManifestPropertyTag.EXTENSION_EXTENDS:
                self.extends = tag.value

            elif tag.index == ManifestPropertyTag.EXTENSION_FLAGS:
                self.extension_flags = PropertyExtensionFlags(tag.value)

            else:
                raise ManifestError(f"Unhandled tag {tag.index} with value {tag.value}")

        self.flags = PropertyFlags(self.flags)

        try:
            self.type = PropertyType(self.type)
        except ValueError:
            raise ManifestError(
                f"Unable to set type for property {self.name if self.name is not None else 'anonymous'} for class "
                "{self.parent.name} to type {hex(self.type)}")

    def bind(self, defs: Dict[int, 'ManifestDefinition']):
        if self.extends and isinstance(self.extends, int):
            if self.extends not in defs:
                print(f"Invalid Tag?")
            else:
                self.extends = defs[self.extends]

        if self.type == PropertyType.OBJECT and isinstance(self.object_type, int):
            if self.object_type not in defs:
                print(f"Invalid Tag?")
            else:
                self.object_type = defs[self.object_type]


T = TypeVar('T', bound='ManifestDefinition')


class ManifestDefinition(ABC):
    TAG = 0

    content: List[Tag]
    category: int
    index: int
    name: Optional[str]

    def __init__(self, category: int, index: int):
        self.category = category
        self.index = index
        self.name = '__anonymous__'

    def composite_tag(self) -> int:
        return to_complete_tag(self.category, self.index)

    @abstractmethod
    def parse(self, data: bytes):
        pass

    @classmethod
    def from_tag(cls: Type[T], category: int, index: int, tag: Tag) -> T:
        if tag.index != cls.TAG:
            raise ManifestError(f"Attempted to parse the wrong definition, value {tag.index} is not of type {cls.TAG}")
        return cls.from_bytes(category, index, tag.value)

    @classmethod
    def from_bytes(cls: Type[T], category: int, index: int, data: bytes) -> T:
        result = cls(category, index)
        result.parse(data)
        return result

    def bind(self, defs: Dict[int, 'ManifestDefinition']):
        pass


class ManifestEnumMember:
    name: str | int
    value: int
    display: str

    def __init__(self, index: int, data: bytes):
        self.index = index
        self.data = data
        reader = io.BytesIO(data)

        while tag := decode_tag(reader, ManifestEnumMemberTag):
            if tag.index == ManifestEnumMemberTag.DISPLAY_NAME:
                if tag.value is str:
                    self.name = tag.value.decode('utf-8')
                else:
                    self.name = tag.value

            elif tag.index == ManifestEnumMemberTag.VALUE_INT:
                self.value = tag.value

            elif tag.index == ManifestEnumMemberTag.VALUE_SIGNED:
                # TODO: this is a special INT case - seems to be twos complement of length
                # encoded integer, value seen was '\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01'
                # implying signed int64

                self.value = tag.value

            else:
                raise ManifestError(f"Unknown tag type in EnumMember definition {hex(tag.index)} = {tag.value}")

    def __str__(self):
        return f"<ManifestEnumMember {self.name} = {hex(self.value)}>"


class ManifestTypeDefinition(ManifestDefinition):
    TAG = 2

    entries: List[ManifestEnumMember]
    extend: Union[None, int, 'ManifestDefinition']

    def __init__(self, category, index):
        super().__init__(category, index)
        self.content = []
        self.entries = []

    def __str__(self):
        return f"<ManifestTypeDefinition {self.name} value_count:{len(self.entries)}>"

    def parse(self, data: bytes):
        self.content = decode_tags(data, ManifestTypeDefinitionTag)

        for index, tag in enumerate(self.content):
            if tag.index == ManifestTypeDefinitionTag.DISPLAY_NAME:
                self.name = tag.value.decode('utf-8')

            elif tag.index == ManifestTypeDefinitionTag.ENUM_MEMBER:
                self.entries.append(ManifestEnumMember(index, tag.value))

            else:
                raise ManifestError(f"Unknown property in type {self.name} - {tag.index} ({tag.value})")


class ManifestObjectDefinition(ManifestDefinition):
    TAG = 1

    properties: List[ManifestProperty]

    def __init__(self, category, index):
        super().__init__(category, index)

        self.properties = []
        self.content = []

    def __str__(self):
        if self.name is not None:
            return f"<ManifestObject name:{self.name} property_count:{len(self.properties)}>"
        else:
            return f"<ManifestObject __anonymous__ property_count:{len(self.properties)}>"

    def parse(self, content: bytes):
        self.content = decode_tags(content, ManifestObjectDefinitionTag)

        for tag in self.content:
            if tag.index == ManifestObjectDefinitionTag.PROPERTY_DEFINITION:
                prop = ManifestProperty(self)
                prop.parse(tag.value)
                self.properties.append(prop)

            elif tag.index == ManifestObjectDefinitionTag.DISPLAY_NAME:
                self.name = tag.value.decode('utf-8')

            else:
                raise ManifestError(f"Unknown tag {hex(tag.index)} in object {self.name}")

    def bind(self, defs: Dict[int, 'ManifestDefinition']):
        for prop in self.properties:
            prop.bind(defs)
