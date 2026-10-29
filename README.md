# libsigrokdecode, with extra decoders

[libsigrokdecode](https://github.com/sigrokproject/libsigrokdecode) is the
protocol decoder library behind [sigrok-cli](https://sigrok.org/wiki/Sigrok-cli)
and [PulseView](https://sigrok.org/wiki/PulseView). This fork is upstream
libsigrokdecode with decoders that aren't upstream (yet) merged in.

It's the companion of [nemanjan00/libsigrok](https://github.com/nemanjan00/libsigrok)
(one libsigrok with all the newer hardware support), and it's maintained the
same way. It tracks upstream `master` and is bleeding edge, not a release.

`master` is upstream libsigrokdecode with everything merged on top. Upstream
code isn't rewritten: every addition comes in as a merge, so `git log --graph`
shows where each change came from. The API stays the same, so it's a drop-in
replacement and PulseView and sigrok-cli work with it unchanged.

## Added decoders

| Decoder | What it does | Stacks on | Source |
|---|---|---|---|
| `saleae_hla` | Runs Saleae Logic 2 [High Level Analyzer](https://support.saleae.com/extensions/high-level-analyzer-extensions) extensions unchanged | `uart`, `i2c`, `spi` | this fork |

### saleae_hla

Logic 2's HLA extensions are small Python classes that turn the frames of
Logic 2's own analyzers into higher-level results. There are many of them in
Saleae's marketplace and on GitHub. `saleae_hla` feeds them the output of
sigrok's `uart`, `i2c` or `spi` decoder (converted to the frames Logic 2's
Async Serial, I2C and SPI analyzers produce) and shows what they return as
annotations, using the extension's own `result_types` formats.

```sh
sigrok-cli -i capture.sr \
    -P "uart:rx=0:baudrate=115200,saleae_hla:extension=/path/to/extension:settings=packet_timeout=0.01" \
    -A saleae_hla
```

- **`extension`:** the extension directory (the one with `extension.json`),
  or a single `.py` file with a `HighLevelAnalyzer` subclass.
- **`analyzer`:** which analyzer to run, if the extension has several.
- **`settings`:** the extension's settings, as `name=value; name2=value2`.
- **`uart_dir`, `cs_polarity`:** UART direction and SPI chip select polarity.

The `saleae` Python package that Logic 2 provides to extensions is
re-implemented from Saleae's public documentation; none of Logic 2's own code
is used. The decoder's docstring
([`decoders/saleae_hla/__init__.py`](decoders/saleae_hla/__init__.py)) has
the details.

**Only run extensions you trust.** An extension is arbitrary Python that runs
with your privileges, the same as in Logic 2. Some ship pickled data files,
which can also run code when loaded.

## Installing

On Arch Linux, the fork is on the AUR as
[`libsigrokdecode-nemanjan00-git`](https://aur.archlinux.org/packages/libsigrokdecode-nemanjan00-git).
It builds this repo's `master` and replaces `libsigrokdecode`/`libsigrokdecode-git`,
so PulseView and sigrok-cli pick it up:

```sh
yay -S libsigrokdecode-nemanjan00-git
```

Together with [`libsigrok-nemanjan00-git`](https://aur.archlinux.org/packages/libsigrok-nemanjan00-git),
that's the full fork. For anything else, build from source.

## Building

```sh
git clone https://github.com/nemanjan00/libsigrokdecode.git
cd libsigrokdecode
./autogen.sh
mkdir build && cd build
../configure
make -j$(nproc)
sudo make install
```

If PulseView or sigrok-cli were built against another libsigrokdecode, rebuild
them against this one or make sure it's found first. The
[sigrok wiki](https://sigrok.org/wiki/Building) has OS-specific build
instructions.

### Requirements

- gcc (>= 4.0) or clang, make, pkg-config >= 0.22
- glib >= 2.34
- Python >= 3.2, with development files
- When building from git: git, autoconf >= 2.63, automake >= 1.11, libtool
- Optional: check >= 0.9.4 for the unit tests (`make check`); doxygen and
  graphviz for the C API documentation

**sigrok-cli 0.7.2**, as some distributions package it, is built against an
older libsigrok and fails every decoder with a `g_variant_get_type`
assertion. Use a sigrok-cli built from git.

## Branches

- **`master`:** upstream plus everything above. This is the one to use.
- **Topic branches** (`saleae-hla`): one per decoder, kept upstreamable.
  They're based on upstream `master` and never carry fork-only files.

Fork-only files live on `master` only: this README and `AGENTS.md`.

## License

libsigrokdecode is licensed under the GNU General Public License, version 3 or
later. The protocol decoders are an integral part of the library (they share
data structures and call into it, and can't run without it), so they're
GPLv3+ as part of it. Some individual files are GPLv2+; the library as a whole
is GPLv3+. See the individual source files for the copyright holders.

## Upstream

- Website: <https://sigrok.org/wiki/Libsigrokdecode>
- Source: <https://github.com/sigrokproject/libsigrokdecode>
- Mailing list: <https://lists.sourceforge.net/lists/listinfo/sigrok-devel>
- IRC: `#sigrok` on Libera.Chat
