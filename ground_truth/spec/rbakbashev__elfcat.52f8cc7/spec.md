# Clarified specification for `executable`

The required artifact is a directly runnable program named exactly `executable`. It is a command-line ELF visualizer compatible with elfcat 0.1.10. In the rules below, “input name” means the one filename argument exactly as supplied, “basename” means its final path component without removing any extensions, and all output text and files are UTF-8 with Unix newlines.

## Spec 1

The program accepts exactly one command-line argument. With one argument equal to `-h` or `--help`, it must write exactly the following two lines to standard output, write nothing to standard error, create no file, and exit with status 0:

```text
Usage: elfcat <filename>
Writes <filename>.html to CWD.
```

With one argument equal to `-v` or `--version`, it must write exactly `elfcat 0.1.10\n` to standard output, write nothing to standard error, create no file, and exit 0. The displayed program name is always `elfcat`, even though the artifact is named `executable`.

With zero arguments or more than one argument, it must print exactly the same two-line usage text to standard output, print nothing to standard error, create no file, and exit 1. Arity is checked before interpreting flags, so `--help extra` and `--version extra` are usage errors. Every other single argument—including an empty string, `-`, `--`, and a string beginning with `-`—is treated literally as an input pathname, not as an option.

## Spec 2

For an ordinary filename argument, read the complete named file in binary mode. Follow symbolic links, but continue to use the supplied link name for naming and presentation. A successful conversion is silent on both stdout and stderr and exits 0.

On a filesystem read failure, write one line to stderr and nothing to stdout, then exit 1:

```text
Failed to read file "<input name>": <operating-system error text>
```

The input name is inserted literally between double quotes. On Linux, missing files therefore produce `No such file or directory (os error 2)` and directories produce `Is a directory (os error 21)`. Examples include `Failed to read file "-": No such file or directory (os error 2)`. Do not create an HTML file on any read or parse failure.

## Spec 3

For a valid input, create exactly one output file in the process's current working directory. Its name is `<basename of input name>.html`; append `.html` rather than replacing or stripping an existing suffix. Thus `/a/b/lib.so.6` produces `./lib.so.6.html`, `./thing` produces `./thing.html`, and a symlink named `link.elf` produces `./link.elf.html`. Support relative paths, absolute paths, `./` paths, nested paths, dotfiles, spaces, quotes, Unicode, multiple dots, and long path components.

Never write the report beside an input located in another directory. Replace an existing output file rather than append to it, and leave no temporary or auxiliary files behind. Repeated runs for identical bytes and the same displayed input name must be byte-for-byte deterministic and independent of the current directory's absolute location. Separate simultaneous conversions with different basenames must not interfere. If output creation or writing fails, report the failure on stderr and exit 1.

## Spec 4

Validate ELF data in this order. First require at least 16 bytes for `e_ident`; otherwise fail with exactly `Failed to parse ELF: file is smaller than ELF header's e_ident\n`. Then require bytes 0–3 to be `7f 45 4c 46`; otherwise fail with exactly `Failed to parse ELF: mismatched magic: not an ELF file\n`. Accept `EI_CLASS` byte 4 only as 1 (ELF32) or 2 (ELF64); another value N fails as `Failed to parse ELF: Unknown bitness: N\n`. Accept `EI_DATA` byte 5 only as 1 (little endian) or 2 (big endian); another value N fails as `Failed to parse ELF: Unknown endianness: N\n`.

After identification, require the complete class-specific ELF file header: 52 bytes for ELF32 and 64 for ELF64. A shorter file fails with exactly `Failed to parse ELF: file is smaller than ELF file header\n`.

The reference does not turn later program-header or section-header bounds failures into parse errors. It directly slices each class-standard entry described in Specs 10 and 13. If a nonzero-count table begins beyond EOF, contains fewer class-standard entries than its count requires, or ends partway through an entry, the Rust bounds check panics: the process writes nothing to stdout, creates no report, emits a bounds-panic diagnostic on stderr, and exits 101. For example, an ELF32 program table declaring two entries but containing one produces the diagnostic line `range end index 116 out of range for slice of length 84`; an ELF64 equivalent produces `range end index 176 out of range for slice of length 120`. The analogous truncated section tables report ends 132/length 92 and 192/length 128. A huge nonzero-count table offset likewise exits 101: offsets `4294967295` in 52-byte ELF32 files and `18446744073709551615` in 64-byte ELF64 files produce `range start index ... out of range for slice of length ...`. These panic cases terminate promptly and leave no partial HTML file.

## Spec 5

Decode all multibyte integers using `EI_DATA`. For ELF32, parse the file header at these byte offsets and widths: `e_type` 16/u16, `e_machine` 18/u16, `e_version` 20/u32, `e_entry` 24/u32, `e_phoff` 28/u32, `e_shoff` 32/u32, `e_flags` 36/u32, `e_ehsize` 40/u16, `e_phentsize` 42/u16, `e_phnum` 44/u16, `e_shentsize` 46/u16, `e_shnum` 48/u16, and `e_shstrndx` 50/u16.

For ELF64, use `e_type` 16/u16, `e_machine` 18/u16, `e_version` 20/u32, `e_entry` 24/u64, `e_phoff` 32/u64, `e_shoff` 40/u64, `e_flags` 48/u32, `e_ehsize` 52/u16, `e_phentsize` 54/u16, `e_phnum` 56/u16, `e_shentsize` 58/u16, `e_shnum` 60/u16, and `e_shstrndx` 62/u16. Zero program or section counts are valid, as are a zero entrypoint, unusual alignments, reordered sections, gaps, overlapping in-file ranges, and large unsigned entry, virtual-address, physical-address, and alignment values. File offsets and file sizes are subject to the direct-indexing panic behavior in Specs 4, 12, and 16.

The raw hexdump marking must retain the original byte order. For example, ELF32 little-endian `e_entry=0x08048000` is shown as `00 80 04 08`, while big-endian `e_type=2`, `e_machine=8`, `e_entry=0x10000000` are shown as `00 02`, `00 08`, `10 00 00 00`. Eight-byte big-endian fields likewise appear in their original order.

## Spec 6

Begin the report with a file-information table. Its rows, in order, use these labels and row classes:

```text
fileinfo_file_name  File name:
fileinfo_file_size  File size:
fileinfo_class      Object class:
fileinfo_data       Data encoding:
[conditional identification version row]
fileinfo_abi        ABI: or Uncommon ABI(!):, as specified below
[conditional ABI version row]
fileinfo_e_type     Type:
fileinfo_e_machine  Architecture:
fileinfo_e_entry    Entrypoint:
fileinfo_ph         Program headers:
fileinfo_sh         Section headers:
[conditional] fileinfo_e_flags  Flags:
```

The file-name value is the input name as supplied, while the HTML `<title>` is its basename. Both are inserted verbatim, without HTML escaping. For example, basename `a<&"'.elf` produces source `<title>a<&"'.elf</title>`, and supplied name `inputs/quo'te` appears unchanged in the file-name cell. Display class as `32-bit` or `64-bit`, data encoding as `Little endian` or `Big endian`, and the entrypoint as lowercase hexadecimal. If `e_flags` is nonzero, append the `fileinfo_e_flags` row after both header-summary rows and show its value as lowercase `0x...`; omit that row when it is zero. `EI_VERSION=1` needs no separate warning row; another value is displayed with the label `Uncommon version(!)`. The `fileinfo_abi` row label is exactly `ABI:` only when `EI_OSABI` is 0 (`SysV`); for every other known or unknown OSABI it is exactly `Uncommon ABI(!):`. For SysV, ABI version zero is omitted and nonzero uses `Uncommon ABI version(!)`; for a non-SysV ABI, display a nonzero ABI version as `ABI version:`.

The program-header summary value is `COUNT * ENTRY_SIZE @ OFFSET`, and the section-header summary is analogous. The count and entry size are decimal and offset is decimal, each wrapped in the numeric tooltip convention from Spec 9 and carrying classes `fileinfo_e_phnum`, `fileinfo_e_phentsize`, `fileinfo_e_phoff`, or their `sh` equivalents.

## Spec 7

Map `e_type` to the following exact display strings:

| Value | Display |
|---:|---|
| 0 | `None (NONE)` |
| 1 | `Relocatable object file (REL)` |
| 2 | `Executable file (EXEC)` |
| 3 | `Shared object file (DYN)` |
| 4 | `Core file (CORE)` |
| `0xfe00` or `0xfeff` | `Environment-specific use` |
| `0xff00` or `0xffff` | `Processor-specific use` |

Other values are valid and display as `Unknown N`, with N in decimal. The boundary values above are names in their own right; do not reject non-executable ELF types.

## Spec 8

Map `EI_OSABI` to these exact strings: 0 `SysV`, 1 `HP-UX`, 2 `NetBSD`, 3 `Linux`, 4 `Hurd`, 6 `Solaris`, 7 `AIX`, 8 `IRIX`, 9 `FreeBSD`, 10 `Tru64`, 11 `Modesto`, 12 `OpenBSD`, 13 `OpenVMS`, and 255 `Standalone`. Any other value is accepted and displayed as `Unknown: N` in decimal.

Map `e_machine` to these exact strings: 0 `None`; 1 `AT&T WE 32100`; 2 `SPARC`; 3 `x86`; 4 `Motorolla 68000`; 5 `Motorolla 88000`; 6 `Intel MCU`; 7 `Intel 80860`; 8 `MIPS`; 9 `IBM System/370`; 10 `MIPS RS3000 little-endian`; 14 `HP PA-RISC`; 19 `Intel 80960`; 20 `PowerPC`; 21 `PowerPC 64-bit`; 22 `S390`; 40 `ARM Aarch32`; 50 `Itanium IA-64`; 62 `x86-64`; 183 `ARM Aarch64`; 190 `CUDA`; 224 `AMDGPU`; and 243 `RISC-V`. Display any other machine as `Unknown: N` in decimal. Preserve the tested spelling `Motorolla`. These fixed display strings are inserted as literal source text: machine 1 therefore produces `<td>AT&T WE 32100</td>`, not `AT&amp;T`.

## Spec 9

Use lowercase, unpadded hexadecimal for interpreted addresses and alignments (`0x0`, `0x8`, `0xffff0000`) and decimal for sizes and counts. Every interpreted numeric value represented by `<span class='number'>` must have a correct opposite-base `title`: visible hex has a decimal title and visible decimal has a lowercase `0x...` title. A zero entrypoint is valid and is rendered as `0x0` with title `0`.

Human-readable whole-file sizes use base 1024. Values below 1024 are exactly `N B`. At 1024 and above, use one decimal place and retain exact bytes in parentheses: examples are `1.0 KiB (1024 B)`, `713.8 KiB (730888 B)`, and `5.0 MiB (5242944 B)`. Apply successive binary units as needed.

## Spec 10

Parse `e_phnum` program-header entries from `e_phoff`, stepping by the class-standard width—32 bytes for ELF32 and 56 bytes for ELF64—rather than by declared `e_phentsize`. The declared size is still decoded and displayed in the file-information summary, but it neither changes the stride nor receives a minimum-width validation. Thus two entries padded by eight bytes are mis-stepped: the second header begins in `PADDING!`, and in both tested little-endian cases its type is displayed as `Unknown: 1145323856` rather than the following header's `TLS`. If the file supplies only a declared 31/55-byte program entry, the attempted 32/56-byte slice panics, exits 101, and produces no report. ELF32 fields are `p_type`/u32, `p_offset`/u32, `p_vaddr`/u32, `p_paddr`/u32, `p_filesz`/u32, `p_memsz`/u32, `p_flags`/u32, `p_align`/u32 at relative offsets 0, 4, 8, 12, 16, 20, 24, 28. ELF64 fields are `p_type`/u32, `p_flags`/u32, then `p_offset`, `p_vaddr`, `p_paddr`, `p_filesz`, `p_memsz`, `p_align` as u64 at 8, 16, 24, 32, 40, 48.

For each index N, create a program-header table `<table class='conceal itable' id='info_phdrN'>` with `<th colspan='2' class='phdr_itable'></th>`, followed in order by `Type:`, `Flags:`, `Offset in file:`, `Size in file:`, `Vaddr in memory:`, `Size in memory:`, and `Alignment:` rows. Offset, vaddr, and alignment are visible hex; both sizes are visible decimal. Also mark that exact raw table entry in the dump with a `bin_phdrN phdr` span, subdivided into spans named `p_type`, `p_flags`, `p_offset`, `p_vaddr`, `p_paddr`, `p_filesz`, `p_memsz`, and `p_align` at their real class-specific byte boundaries.

## Spec 11

Map program-header types exactly as follows: 0 `NULL`, 1 `LOAD`, 2 `DYNAMIC`, 3 `INTERP`, 4 `NOTE`, 5 `SHLIB`, 6 `PHDR`, 7 `TLS`, `0x60000000` `LOOS`, `0x6474e550` `GNU_EH_FRAME (OS-specific)`, `0x6474e551` `GNU_STACK (OS-specific)`, `0x6474e552` `GNU_RELRO (OS-specific)`, `0x6fffffff` `HIOS`, `0x70000000` `LOPROC`, and `0x7fffffff` `HIPROC`. Other values display as `Unknown: N` in decimal.

Format `p_flags` by concatenating recognized letters in the order `R`, `W`, `X`, using bits 4, 2, and 1 respectively. Thus values 7, 6, 5, 4, 3, 2, 1 display as `RWX`, `RW`, `RX`, `R`, `WX`, `W`, `X`; zero displays as an empty cell.

## Spec 12

Each program header also defines a file segment `[p_offset, p_offset+p_filesz)`. On a successful conversion, create `<table class='conceal itable' id='info_segmentN'>` with a `segment_itable` heading and `Type:`, `Size in file:`, and `Size in memory:` rows. A nonempty segment wholly inside the file and beginning at a nonzero offset is marked in the dump with exactly `bin_segmentN segment`, without `hover`; overlapping in-file segments use nested range spans carrying those same two-class strings. A zero-sized ordinary segment gets its info table but no range span.

The dump-range renderer suppresses every segment whose `p_offset` is zero: it still creates both information tables, but creates no `bin_segmentN segment` range span. Consequently, a zero-offset segment type with no extra content decoder does not index its declared end and succeeds even when `p_filesz` exceeds the file length. In the observed 120-byte ELF64 vectors, a `PT_LOAD` with `p_offset=0` and `p_filesz=152` exits 0 with empty stdout and stderr, creates the report, and has no `bin_segment0 segment` span. This applies equally to the little-endian, big-endian, nonzero-ABI-version, and Linux-ABI variants.

Other nonempty segment ranges are indexed without clipping. A segment whose nonzero start is outside the file, or whose nonzero-start range extends beyond EOF, panics during report generation, exits 101, writes nothing to stdout, and creates no report. Observed examples include offset 65536 in a 120-byte file (`index out of bounds: the len is 120 but the index is 65536`) and a 20-byte segment starting at 120 in a 123-byte file (`index out of bounds: the len is 123 but the index is 139`). Maximum offsets likewise panic at index `4294967295` for the 84-byte ELF32 vector and `18446744073709551615` for the 120-byte ELF64 vector. Type-specific decoding described below can still index a zero-offset segment independently of dump-range suppression.

For type `INTERP`, assume that the final declared segment byte is the terminator: remove exactly that last byte and add `Interpreter:` with the remaining bytes rendered in the report's byte-string form. Do not search for or stop at an earlier NUL. Thus the 35-byte content `/lib64/ld-linux-x86-64.so.2\0ignored` produces exactly `<tr> <td>Interpreter:</td> <td>/lib64/ld-linux-x86-64.so.2<b>00</b> ignore</td> </tr>`: the internal NUL is rendered and the final `d` is the byte discarded. A normally formed segment ending immediately after `/lib64/ld-linux-x86-64.so.2\0` displays just `/lib64/ld-linux-x86-64.so.2`. A zero-sized `INTERP` at offset zero is a reference limitation: subtracting one from its empty range panics with `range end index 18446744073709551615 out of range for slice of length 120`, exits 101, and leaves no report. Other ordinary segment types receive no fabricated special-detail rows.

## Spec 13

Parse `e_shnum` section headers from `e_shoff`, stepping by the class-standard width—40 bytes for ELF32 and 64 bytes for ELF64—rather than by declared `e_shentsize`. The declared size is displayed but does not control the stride or receive minimum-width validation. Two entries padded by eight bytes are consequently mis-stepped; in both tested little-endian cases the second header begins in `PADDING!` and its type is `Unknown: 558321225`, not the following header's `NOBITS`. Supplying only a declared 39/63-byte section entry causes the attempted 40/64-byte slice to panic with status 101 and no report. ELF32 relative fields are `sh_name` u32@0, `sh_type` u32@4, `sh_flags` u32@8, `sh_addr` u32@12, `sh_offset` u32@16, `sh_size` u32@20, `sh_link` u32@24, `sh_info` u32@28, `sh_addralign` u32@32, `sh_entsize` u32@36. ELF64 uses u32 at 0 and 4, u64 `sh_flags`@8, `sh_addr`@16, `sh_offset`@24, `sh_size`@32, u32 `sh_link`@40 and `sh_info`@44, and u64 `sh_addralign`@48 and `sh_entsize`@56.

When `e_shstrndx` is nonzero, resolve section names through the section at that index, taking a NUL-terminated byte string at each `sh_name` offset. Handle an empty string table, empty names, 255-character names, invalid UTF-8 without crashing, nonstandard section order, and large counts (at least 101 sections). Insert the decoded section name verbatim into its `Name:` cell without HTML escaping. In the observed nonstandard-order vector, the name bytes `<&evil>` produce exactly `<tr> <td>Name:</td> <td><&evil></td> </tr>` in `info_shdr3`, not `&lt;&amp;evil&gt;`.

The reserved value `e_shstrndx=0` means that no section-name string table exists; do not use section header zero as a string table even if its type is `STRTAB`. Every section then receives an empty `Name:` cell. In the observed two-section vector, section zero is an `STRTAB` containing a leading NUL and 255 `x` bytes, section one has `sh_name=1`, and both rows are exactly `<tr> <td>Name:</td> <td></td> </tr>`.

## Spec 14

For each index N create `<table class='conceal itable' id='info_shdrN'>` with a `shdr_itable` heading, then these rows in order: `Index:`, `Name:`, `Type:`, `Flags:`, `Vaddr in memory:`, `Offset in file:`, `Size in file:`, `Linked section:`, `Extra info:`, `Alignment:`, and `Size of entries:`. Index and linked-section index are plain decimal. Vaddr, file offset, and alignment use visible hex numeric spans; size, extra info, and entry size use visible decimal numeric spans.

Mark every raw section-header entry with `bin_shdrN shdr` and field spans `sh_name`, `sh_type`, `sh_flags`, `sh_addr`, `sh_offset`, `sh_size`, `sh_link`, `sh_info`, `sh_addralign`, and `sh_entsize`. Do not reorder headers. The raw spans show exactly 40 bytes for ELF32 or 64 for ELF64 in original endianness.

## Spec 15

Map section types to: 0 `NULL`, 1 `PROGBITS`, 2 `SYMTAB`, 3 `STRTAB`, 4 `RELA`, 5 `HASH`, 6 `DYNAMIC`, 7 `NOTE`, 8 `NOBITS`, 9 `REL`, 10 `SHLIB`, 11 `DYNSYM`, 14 `INIT_ARRAY`, 15 `FINI_ARRAY`, `0x60000000` `LOOS`, `0x6ffffff6` `GNU_HASH (OS-specific)`, `0x6fffffff` `HIOS`, `0x70000000` `LOPROC`, and `0x7fffffff` `HIPROC`. Other values display as `Unknown: N` in decimal.

Format recognized section flag bits by concatenating in `WAX` order: bit 1 is `W`, bit 2 is `A`, bit 4 is `X`. No recognized flags displays `0`. Common combinations must consequently appear as `W`, `A`, `X`, `WA`, `WX`, `AX`, or `WAX`.

## Spec 16

Each section header creates `<table class='conceal itable' id='info_sectionN'>` with a `section_itable` heading and at least `Type:` and `Size:` rows. The size is decimal with a hexadecimal tooltip. For every nonempty section other than `NOBITS`, mark the existing file range `[sh_offset, sh_offset+sh_size)` with exactly one opening span whose classes are `bin_sectionN section hover`. That single span may enclose dump row line breaks and nested segment markup; do not split one section into a separate `bin_sectionN` span per row or chunk. Correctly represent sections separated by gaps and sections nested in or overlapping segments. `NOBITS` has no file bytes to mark but still gets both info tables and its declared size (for example a 1024-byte `.bss`) is displayed. Zero-sized sections likewise remain represented but have no range span.

For an `STRTAB` section, add a detail block listing each nonempty NUL-delimited string in order on its own line. Decode invalid UTF-8 lossily enough to preserve later valid strings. This must expose normal section and symbol strings such as `.shstrtab`, `.text`, `.data`, `.rodata`, `.bss`, `.dynsym`, `.strtab`, and `.dynstr` when present.

Section-content ranges are indexed without clipping. A nonempty non-`NOBITS` section whose start is outside the file, or whose range extends beyond EOF, panics during report generation, exits 101, writes nothing to stdout, and creates no report. In the exact one-section maximum-value vectors, the ELF32 file is 92 bytes and `sh_offset=sh_size=4294967295`; it emits the diagnostic line `index out of bounds: the len is 92 but the index is 4294967295`. The ELF64 file is 128 bytes and `sh_offset=sh_size=18446744073709551615`; it emits `index out of bounds: the len is 128 but the index is 18446744073709551615`. Both exit 101 without producing `sample.elf.html`.

## Spec 17

For every `NOTE` program segment, parse consecutive ELF note records from its file range. Each record has three endian-aware u32 fields (`namesz`, `descsz`, `type`), followed by the name and descriptor; both payloads advance to the next 4-byte boundary. Remove a trailing NUL from a nonempty name. A `namesz` of zero is valid and renders an empty `Name:` cell. The observed little-endian two-note vector with an empty first name, type 1, descriptor `desc`, and a following `GNU` note succeeds silently; its first rows include exactly `<tr> <td>Name:</td> <td></td> </tr>`, `<tr> <td>Type:</td> <td>0x1</td> </tr>`, and `<tr> <td>Desc:</td> <td>desc</td> </tr>`.

The note-name parser handles zero and positive `namesz` values divisible by four, but has a direct-slicing limitation for a positive `namesz` that is not divisible by four. In the observed consecutive-note vector, the first name `GNU\0` has `namesz=4`, while the second name `ACME\0` has `namesz=5`; for both little- and big-endian encodings the latter triggers `range end index 8 out of range for slice of length 4`, exits 101, writes nothing to stdout, and creates no report. A declared payload length that exceeds the remaining segment is instead abandoned safely rather than rendered past the segment.

In the segment detail table, insert a separator row before note details and between notes. For each note display `Name:` and `Type:` (lowercase hex such as `0x3`). If the name is `GNU` and type is 3, label the descriptor `Build ID:` and render it as one continuous lowercase hexadecimal string. Otherwise label it `Desc:` and use the byte-string renderer: printable bytes appear as their characters, while nonprintable bytes appear as two-digit lowercase values in individual `<b>` elements followed by spaces. Thus `desc` remains `desc`, while bytes 00 10 ff render as `<b>00</b> <b>10</b> <b>ff</b> `. Big-endian notes use big-endian header fields but descriptor bytes remain in file order.

## Spec 18

The generated document is standalone HTML5. It begins and indents exactly as follows; these are source newlines and spaces, not merely an equivalent DOM:

```html
<!doctype html>
<html>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=900, initial-scale=1'>
    <title>minimal32.elf</title>
    <style>
```

The title line above is the observed form for the `minimal32.elf` serialization vector in Spec 21; for another invocation, substitute its verbatim, unescaped basename without changing the line's indentation or tags. In particular, never compact this to `<html><head>` or place either tag on the same source line as another tag. The `</style>`, `</head>`, and `<body>` lines have respectively four, two, and two leading spaces. The document contains exactly one `<html>`, `<head>`, and `<body>` pair and ends with the exact three lines `    </script>\n  </body>\n</html>\n`, where that `</script>` closes the final settings/help script. Do not omit the final newline. Do not load external CSS, JavaScript, fonts, images, or other runtime dependencies.

At the start of the body include an SVG overlay with marker id `arrowhead` and group id `arrows`. Include a right-side menu `<div id='rightmenu'>` containing, in order, the exact link `<a id='credits' href='https://github.com/rbakbashev/elfcat'>generated with elfcat 0.1.10</a>`, Settings and Help buttons with ids `settings_toggle` and `help_toggle`, a hidden `settings` div, and a hidden `help` div. Settings contains range input `arrow_opacity_range` with min 0, max 100, and initial value 100.

## Spec 19

The Help panel explains the visualization and includes these exact sentences: `The leftmost column shows offsets within the file.` and `The middle column is the file dump.` It must explain that the rightmost column is printable ASCII, that structures/sections/segments are highlighted, and that references are clickable and connected by arrows. Its `Legend` list contains `ELF Identification`, `ELF Header`, `Program Header`, `Section Header`, `Segment`, `Section`, and the source text `Segment &amp; Section overlap`, paired with classes `ident`, `ehdr`, `phdr`, `shdr`, `segment`, `section`, and `segm_sect_legend`.

The embedded CSS uses the exact source token `font-family: monospace;` (including the space after the colon) and provides visible, distinct highlighting for those classes. It includes the exact rule, indentation, and line breaks:

```css
      #headertable {
        width: 100%;
      }
```

Other required selectors/behaviors include `#bytes` as a 47-character, preformatted 16-byte-wide column, `#ascii` as a 16-character preformatted column, `#sticky_table` as sticky, `.hover:hover { background-color: #ee9; }`, `.conceal { display: none; ... }`, styling for `.itable`, `#offsets`, `#rightmenu`, and the alternating segment/section overlap. The SVG is absolutely positioned and does not intercept pointer events. The layout must remain usable at the declared fixed viewport width.

## Spec 20

After the file-info table, emit three aligned `<div>` elements with ids `offsets`, `bytes`, and `ascii`. Render the complete input—do not abbreviate large binaries. Break all three columns every 16 input bytes. `offsets` contains lowercase hexadecimal row starts without `0x`: `0`, `10`, `20`, and so on. Every full row has exactly 16 bytes/ASCII characters and the final row contains the remainder.

In `bytes`, ordinary bytes are lowercase two-digit hex separated by single spaces. The four magic bytes are specially grouped in `<span class='magic'>` as source text `7f &nbsp;E &nbsp;L &nbsp;F`; this still visibly represents 7f 45 4c 46. Surround the first 16 bytes with `ident` inside the overall `ehdr` range. Give identification subfields classes `magic`, `class`, `data`, `ver`, `abi`, `abi_ver`, and `pad`; give the remaining header fields their `e_*` class names. Program/section table fields and file ranges use the classes described above. The `ident`, `ehdr`, `bin_phdrN phdr`, `bin_shdrN shdr`, and `bin_segmentN segment` spans do not carry `hover`; section-content ranges carry it as specified in Spec 16.

In `ascii`, render bytes 0x21 through 0x7e as their characters and every other byte—including 0x20—as `.`. Thus the first line begins `.ELF`. In this byte-derived ASCII column, encode printable metacharacters using `&amp;`, `&lt;`, `&gt;`, `&quot;`, and `&apos;`, so raw file bytes cannot inject a tag such as `<script>`. This escaping rule does not apply to decoded section names, the supplied input name, its title basename, or the fixed machine display strings described in Specs 6, 8, 13, and 18.

## Spec 21

Following the dump columns, emit `<table id='sticky_table' cellspacing='0'>` with one row and three cells: `td#desc`, a program/section-header info-table column, and a segment/section-content info-table column. Every generated id must be unique. On conversions that reach report generation successfully, generate one `info_phdrN` and one `info_segmentN` per program header, and one `info_shdrN` and one `info_sectionN` per section header, including index zero and zero-sized entries except for the zero-sized `INTERP` panic described in Spec 12. Their class must include both `itable` and `conceal`.

Canonical row source formatting uses single-quoted attributes and forms such as `<tr> <td>Type:</td> <td>LOAD</td> </tr>` and `<tr class='fileinfo_class'> <td>Object class:</td> <td>64-bit</td> </tr>`. HTML template elements are line-oriented and use two spaces per HTML nesting level: body children have four leading spaces, ordinary file-information rows have six, the children of the sticky table row have eight, nested info tables have ten, and their data rows have twelve. Outer-document and table-scaffolding container tags occupy separate source lines. The intentionally inline row contents and the offset, byte-dump, and ASCII `div` contents remain inline as shown in the canonical vector; this indentation rule does not add whitespace inside their rendered values. Serialization, table ordering, attribute spelling, numeric formatting, and whitespace must be stable; the same ELF and displayed name must always yield byte-identical HTML.

For a complete byte-level serialization vector, create a file whose supplied name is exactly `minimal32.elf` and whose 84 bytes are the following single hexadecimal sequence:

```text
7f454c460101010000000000000000000200030001000000008004083400000000000000000000003400200001002800000000000100000000000000008004080080040810000000100000000500000004000000
```

A successful invocation produces exactly [`canonical-minimal32.html`](canonical-minimal32.html), including all static CSS and JavaScript text, indentation, blank lines, attribute order, and its final newline. Dynamic reports use that same static template and source-formatting conventions, substituting or repeating only the input-dependent rows, dump contents, info tables, numeric connection calls, and `fileLen` value required by the preceding specs.

## Spec 22

Embed at least five `type='text/javascript'` script blocks implementing all interaction locally. One defines `function highlightClasses(primaryClass, secondaryClass)` and mouseenter/mouseleave pair highlighting via `style.backgroundColor`. It must invoke at least:

```javascript
highlightClasses('fileinfo_class', 'class')
highlightClasses('fileinfo_data', 'data')
highlightClasses('fileinfo_e_type', 'e_type')
```

and analogous pairs for ABI and all `e_*` fields. A description script populates `#desc` from the hovered element and ancestor class names, with descriptions for ELF identification/header fields, program headers/segments, section headers/sections, and overlap.

## Spec 23

Embed a conceal/reveal script containing functions with the signatures `function showIfMatches(cl, prefix, newPrefix, indirect = false)` and `function hidePreviousTables()`, plus a `document.addEventListener("mouseover"` handler. Hovering a `bin_N`-style region displays its corresponding `info_N` table using `table.style.display = "block"`. Hovering a segment or section must also reveal the indirectly referenced program/section header and add class `indirect`; moving to another range hides prior tables.

Embed an offsets script containing `let fileLen = N`, where N is the exact byte length, and `populateOffsets(columns)` to produce 16-byte row offsets. Embed an arrows script defining `connect`, `pushArrowElems`, resize redraw, scrolling callbacks, and SVG lines. Connect `e_phoff` to `bin_phdr0` and `e_shoff` to `bin_shdr0` when those tables exist; connect each header's offset field to its segment/section range, and section link fields to linked section headers when applicable. Finally embed settings/help toggle logic and make the opacity range update the `arrows` group's opacity.

## Spec 24

The parser and renderer must handle both real-world and synthetic ELF files: normal and position-independent executables, shared libraries, relocatable objects, core files, stripped files, debug-heavy files, TLS, many program/section headers, large gaps, in-file overlaps, uncommon alignments, empty string tables, and files several megabytes long, subject to the explicit panic cases above. The executable must also be capable of analyzing its own ELF binary. The delivered `executable` itself must retain a section named `.symtab`; self-analysis succeeds silently and its generated report contains `.symtab` (as well as `.strtab` and `.shstrtab`). A stripped artifact whose self-report omits `.symtab` does not satisfy this requirement. Output size must scale linearly because every input byte appears once in both hex and ASCII views; it must not collapse the dump, duplicate the entire file superlinearly, or impose a small fixed input limit. As a concrete large-file vector, invoking the program with `/usr/bin/python3` in the evaluation image (5,937,704 input bytes) succeeds silently and creates `python3.html` of exactly 26,980,871 bytes; in particular, its size is greater than 10,000,000 and less than 50,000,000 bytes.

Successful cases remain quiet and complete when there are no program headers, no section headers, or only a class-sized header. Preserve every byte and avoid dependence on host endianness. Header-table, segment-range, section-range, and note arithmetic deliberately has the direct-indexing limitations documented in Specs 4, 10, 12, 13, 16, and 17. Reports for two different ELF byte sequences must reflect their actual class, metadata, tables, and bytes rather than being a constant page.
