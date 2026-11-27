"""Bounds-checked PE import names, no library loading or disassembly."""

import struct


def pe_imports(raw):
    def unpack(fmt, at):
        if at < 0 or at + struct.calcsize(fmt) > len(raw):
            raise ValueError("TRUNCATED_PE_METADATA")
        return struct.unpack_from(fmt, raw, at)

    def string(at):
        if not 0 <= at < len(raw):
            raise ValueError("PE_STRING_OUT_OF_BOUNDS")
        end = raw.find(b"\0", at, min(at + 256, len(raw)))
        if end < 0:
            raise ValueError("UNTERMINATED_PE_NAME")
        return raw[at:end].decode("ascii", errors="replace")

    if raw[:2] != b"MZ":
        return dict(status="NOT_A_PE_CONTAINER", imports=[])
    try:
        pe = unpack("<I", 60)[0]
        if raw[pe : pe + 4] != b"PE\0\0":
            raise ValueError("INVALID_PE_SIGNATURE")
        n = unpack("<H", pe + 6)[0]
        size = unpack("<H", pe + 20)[0]
        optional = pe + 24
        magic = unpack("<H", optional)[0]
        if n > 96 or magic not in (0x10B, 0x20B):
            raise ValueError("UNSUPPORTED_PE_LAYOUT")
        data = optional + (96 if magic == 0x10B else 112)
        if data + 16 > optional + size:
            raise ValueError("PE_IMPORT_DIRECTORY_UNAVAILABLE")
        rva, length = unpack("<II", data + 8)
        sections = []
        for j in range(n):
            off = optional + size + 40 * j
            virtual_size, virtual, physical_size, physical = unpack("<IIII", off + 8)
            sections.append((virtual, max(virtual_size, physical_size), physical, physical_size))

        def offset(value):
            for virtual, sec_size, physical, rawsize in sections:
                if virtual <= value < virtual + sec_size and value - virtual < rawsize:
                    return physical + value - virtual
            raise ValueError("PE_RVA_OUTSIDE_RAW_SECTION")

        names = []
        if rva:
            start = offset(rva)
            for j in range(min(length // 20, 128)):
                orig, stamp, chain, name, first = unpack("<IIIII", start + 20 * j)
                if not any((orig, stamp, chain, name, first)):
                    break
                dll = string(offset(name))
                symbols = []
                thunk = offset(orig or first)
                width = 8 if magic == 0x20B else 4
                for k in range(256):
                    ptr = unpack("<Q" if width == 8 else "<I", thunk + k * width)[0]
                    if not ptr:
                        break
                    symbols.append("ordinal:" + str(ptr & 65535) if ptr >> (width * 8 - 1) else string(offset(ptr) + 2))
                names.append(dict(library=dll, symbols=symbols))
        return dict(status="PE_IMPORT_NAMES_PARSED_STATIC", imports=names, bounded=True)
    except (ValueError, struct.error) as exc:
        return dict(status="MALFORMED_OR_UNSUPPORTED_PE", imports=[], reason=str(exc))
