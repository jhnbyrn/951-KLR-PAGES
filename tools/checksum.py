import sys


def checksum(filename):
    with open(filename, "rb") as f:
        data = f.read()

    return sum(data) & 0xFFFF


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <ROM image>")
        sys.exit(1)

    filename = sys.argv[1]
    result = checksum(filename)

    print(f"File:     {filename}")
    print(f"Size:     {len(open(filename, 'rb').read())} bytes")
    print(f"Checksum: {result:04X}")
