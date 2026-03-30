#!/usr/bin/env python3
"""
Extract prefixPack.txz from the reference Proton .wcp build.
Used by GitHub Actions to get the default Wine prefix without downloading the full archive.
"""
import zstandard
import tarfile
import sys
import os
import urllib.request

REF_URL = "https://github.com/K11MCH1/Winlator101/releases/download/wine_col/Proton-10-arm64ec-controller-fix.wcp"
OUT_PATH = "wine-install/prefixPack.txz"


def main():
    print("Downloading reference .wcp to extract prefixPack.txz...")
    with urllib.request.urlopen(REF_URL) as response:
        dctx = zstandard.ZstdDecompressor()
        with dctx.stream_reader(response) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as tf:
                for member in tf:
                    name = member.name.lstrip("./")
                    if name == "prefixPack.txz":
                        f = tf.extractfile(member)
                        if f:
                            with open(OUT_PATH, "wb") as out:
                                out.write(f.read())
                            size = os.path.getsize(OUT_PATH)
                            print(f"Extracted prefixPack.txz ({size:,} bytes)")
                            return
    print("WARNING: prefixPack.txz not found in reference build")
    sys.exit(1)


if __name__ == "__main__":
    main()
