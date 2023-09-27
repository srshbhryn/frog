from typing import Optional
from typing import Callable

import msgpack


class _EncoderStore:
    next_code = 1
    type_to_code_map: dict[type, int] = {}
    code_to_type_map: dict[int, type] = {}
    code_to_encoder_map: dict[int, Callable] = {}
    code_to_decoder_map: dict[int, Callable] = {}

    @staticmethod
    def get_next_code_for(tp: type) -> int:
        code = _EncoderStore.next_code
        _EncoderStore.next_code += 1
        _EncoderStore.type_to_code_map[tp] = code
        _EncoderStore.code_to_type_map[code] = tp
        return code

    @staticmethod
    def encoder(obj: any) -> bytes:
        code = _EncoderStore.type_to_code_map.get(type(obj))
        if code is None:
            raise TypeError('Unknown type: %r' % (obj,))
        return msgpack.ExtType(
            code,
            _EncoderStore.code_to_encoder_map[code](obj),
        )

    @staticmethod
    def decoder(code: int, data: bytes) -> any:
        decoder = _EncoderStore.code_to_decoder_map.get(code)
        if decoder is None:
            return msgpack.ExtType(code, data)
        return decoder(data)


def register(tp: type, encoder: callable, decoder: Optional[callable] = None) -> None:
    code = _EncoderStore.type_to_code_map.get(tp) or _EncoderStore.get_next_code_for(tp)
    _EncoderStore.code_to_encoder_map[code] = encoder
    if decoder is None:

        def decoder(encoded: bytes) -> tp:
            return tp(**loads(encoded))

    _EncoderStore.code_to_decoder_map[code] = decoder


def loads(data: bytes) -> any:
    return msgpack.loads(data, ext_hook=_EncoderStore.decoder, raw=False)


def dumps(obj: any) -> bytes:
    return msgpack.dumps(obj, default=_EncoderStore.encoder, use_bin_type=False)
