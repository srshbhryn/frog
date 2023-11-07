import dataclasses
import enum
from typing import Any, Optional, Callable, TYPE_CHECKING, Union

import msgpack


class _EncoderStore:
    _ext_type_code = 1
    code_to_type_map: dict[int, type] = {}
    code_to_encoder_map: dict[int, Callable] = {}
    code_to_decoder_map: dict[int, Callable] = {}

    @classmethod
    def encoder(cls, obj: Any) -> Union[bytes, msgpack.ExtType]:
        code = hash(type(obj).__name__)
        tp = cls.code_to_type_map.get(code)
        if tp is None or not isinstance(obj, tp):
            msg = f'Unknown type: {obj!r}'
            raise TypeError(msg)
        encode = getattr(tp, 'encode', None) or _EncoderStore.code_to_encoder_map[code]
        return msgpack.ExtType(cls._ext_type_code, dumps((code, encode(obj))))

    @classmethod
    def decoder(cls, _ext_type_code: int, data: bytes) -> Any:
        if _ext_type_code != cls._ext_type_code:
            return msgpack.ExtType(_ext_type_code, data)
        code, encoded = loads(data)
        tp = cls.code_to_type_map.get(code)
        if tp is None or hash(tp.__name__) != code:
            msg = f'Unknown type with code: {code}'
            raise TypeError(msg)

        decoder = getattr(tp, 'decode', None) or _EncoderStore.code_to_decoder_map.get(code)

        if decoder is None:
            return tp(*encoded)

        return decoder(encoded)


def register(
    tp: type,
    encoder: Optional[Callable] = None,
    decoder: Optional[Callable] = None,
) -> None:
    code = hash(tp.__name__)
    if encoder:
        _EncoderStore.code_to_encoder_map[code] = encoder

    if decoder:
        _EncoderStore.code_to_decoder_map[code] = decoder

    _EncoderStore.code_to_type_map[code] = tp



def dataclass(tp):
    register(tp)
    if TYPE_CHECKING:
        assert dataclasses.is_dataclass(tp)
        assert hasattr(tp, '__slots__')

    setattr(tp, 'encode', lambda i: tuple(getattr(i, s) for s in tp.__slots__))

    return tp

class Enum(enum.Enum):
    def __init_subclass__(cls):
        register(cls)

    def encode(self):
        return (self.value,)


def loads(data: bytes) -> Any:
    return msgpack.loads(
        data,
        ext_hook=_EncoderStore.decoder,
        raw=False,
        strict_map_key=False,
    )


def dumps(obj: Any) -> bytes:
    return msgpack.dumps(obj, default=_EncoderStore.encoder, use_bin_type=False)
