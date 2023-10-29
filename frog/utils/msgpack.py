from typing import Any

import msgpack


class _EncoderStore:
    _ext_type_code = 1
    code_to_type_map: dict[int, type] = {}

    @classmethod
    def encoder(cls, obj: Any) -> bytes:
        code = hash(type(obj).__name__)
        tp = cls.code_to_type_map.get(code)
        if not type(obj) == tp:
            msg = f'Unknown type: {obj!r}'
            raise TypeError(msg)
        return msgpack.ExtType(cls._ext_type_code, dumps((code, obj.encode())))

    @classmethod
    def decoder(cls, _ext_type_code: int, data: bytes) -> Any:
        if not _ext_type_code == cls._ext_type_code:
            return msgpack.ExtType(_ext_type_code, data)
        code, encoded = loads(data)
        tp = cls.code_to_type_map.get(code)
        if not tp and not hash(tp.__name__) == code:
            msg = f'Unknown type with code: {code}'
            raise TypeError(msg)
        if not hasattr(tp, 'decode'):

            def decode(encoded):
                return tp(*encoded)

        else:
            decode = tp.decode
        return decode(encoded)


def register(tp: type) -> type:
    code = hash(tp.__name__)
    _EncoderStore.code_to_type_map[code] = tp
    return tp

def loads(data: bytes) -> any:
    return msgpack.loads(
        data,
        ext_hook=_EncoderStore.decoder,
        raw=False,
        strict_map_key=False,
    )


def dumps(obj: any) -> bytes:
    return msgpack.dumps(obj, default=_EncoderStore.encoder, use_bin_type=False)
