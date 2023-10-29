import dataclasses
import enum
from typing import Any, Optional, Callable

import msgpack


class _EncoderStore:
    _ext_type_code = 1
    code_to_type_map: dict[int, type] = {}
    code_to_encoder_map: dict[int, Callable] = {}
    code_to_decoder_map: dict[int, Callable] = {}

    @classmethod
    def encoder(cls, obj: Any) -> bytes:
        code = hash(type(obj).__name__)
        tp = cls.code_to_type_map.get(code)
        if not type(obj) == tp:
            msg = f'Unknown type: {obj!r}'
            raise TypeError(msg)
        encode = getattr(tp, 'encode', _EncoderStore.code_to_encoder_map.get(code))
        return msgpack.ExtType(cls._ext_type_code, dumps((code, encode(obj))))

    @classmethod
    def decoder(cls, _ext_type_code: int, data: bytes) -> Any:
        if not _ext_type_code == cls._ext_type_code:
            return msgpack.ExtType(_ext_type_code, data)
        code, encoded = loads(data)
        tp = cls.code_to_type_map.get(code)
        if not tp and not hash(tp.__name__) == code:
            msg = f'Unknown type with code: {code}'
            raise TypeError(msg)

        decoder = getattr(tp, 'decode', _EncoderStore.code_to_decoder_map.get(code))
        if not decoder:

            def decoder(encoded):
                return tp(*encoded)

        return decoder(encoded)


def register(
    tp: type,
    encoder: Optional[Callable] = None,
    decoder: Optional[Callable] = None,
) -> type:
    code = hash(tp.__name__)
    if encoder:
        _EncoderStore.code_to_encoder_map[code] = encoder

    if decoder:
        _EncoderStore.code_to_decoder_map[code] = decoder

    _EncoderStore.code_to_type_map[code] = tp
    return tp


def dataclass(tp):
    tp = register(dataclasses.dataclass(slots=True)(tp))
    print(tp.__dict__['a'])
    tp.encode = lambda i: tuple(getattr(i, s) for s in tp.__slots__)
    return tp
    # return (register(tp))


class Enum(enum.Enum):
    def __init_subclass__(cls):
        _ = register(cls)

    def encode(self):
        return (self.value,)


def loads(data: bytes) -> any:
    return msgpack.loads(
        data,
        ext_hook=_EncoderStore.decoder,
        raw=False,
        strict_map_key=False,
    )


def dumps(obj: any) -> bytes:
    return msgpack.dumps(obj, default=_EncoderStore.encoder, use_bin_type=False)
