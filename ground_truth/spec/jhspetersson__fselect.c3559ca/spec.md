# Clarified executable specification

The required program is a command-line file search utility named `fselect`. It accepts a relaxed, SQL-like query, walks one or more filesystem roots, evaluates file metadata and expressions, and writes rows in a selected format. This document is the complete behavioral contract. Examples use `fselect` as the executable name; the compiled executable must behave the same regardless of its actual filename.

## Spec 1

### Invocation, global options, and informational commands

The general invocation is:

```text
fselect [GLOBAL_OPTIONS] [select] FIELD[, FIELD...] [from ROOT[, ROOT...]]
        [where EXPR] [group by FIELD[, FIELD...]]
        [having EXPR] [order by EXPR [asc|desc][, ...]] [limit N] [offset N]
        [into FORMAT]
```

After global-option processing, separate command-line arguments that contribute query text are concatenated without inserting whitespace. The lexer can nevertheless recognize adjacent keywords, field names, punctuation, paths, and numbers, so splitting a query across arguments does not by itself make it invalid. In particular, the seven arguments `select`, `name,`, `size`, `from`, `ROOT`, `limit`, and `1` form the concatenated query text `selectname,sizefromROOTlimit1` and execute successfully. When `ROOT` contains only a zero-byte file named `empty`, this invocation returns 0, writes `empty\t0\n` to stdout, and writes nothing to stderr. Supplying leading whitespace inside later arguments also forms a valid query. Non-informational global options may be combined and may occur in any order before the query; the help, version, and completion forms have the first-raw-argument restriction described below.

Recognize these options:

| Option | Effect |
|---|---|
| `-i`, `/i`, `--interactive` | Enter the interactive mode in Spec 24. |
| `-c PATH`, `/c PATH`, `--config PATH` | Read the TOML configuration in Spec 23. |
| `--nocolor`, `--no-color`, `/nocolor` | Disable ANSI styling. |
| `--no-error`, `--no-errors` | Suppress filesystem/evaluation error messages, but not the exit status. |
| `--us-date`, `--us-dates` | Interpret ambiguous slash dates in month/day order. |
| `-h`, `/h`, `/?`, `--help`, `help` | Print full help and exit successfully. |
| `-v`, `-V`, `--version`, `version` | Print version information and exit successfully. |
| `--fields` | Print the field-completion list below. |
| `--functions` | Print the function-completion list below. |
| `--root-options` | Print the root-option list below. |
| `--output-formats` | Print the output-format list below. |

Help/version detection is deliberately permissive but occurs before global-option processing and examines only the process's first raw argument. Lowercase that argument; one containing `help` requests full help and one containing `version` requests version information. Thus `-v`, `-V`, `version`, and `--some-version-suffix` print version information when they are the first argument, while `--nocolor -v`, `--nocolor -V`, and `--nocolor version` execute one-token literal select queries and print `-v`, `-V`, and `version`, respectively. Likewise, `--help`, `/h`, `/?`, `help`, and `anything-helpful` print help when first; after `--nocolor`, the first three return 2 with `query: could not parse tokens at the end of the query`, while the last two print their literal text when they are the only query argument. Later separate arguments remain subject to the concatenation and lexing rule above: for example, after `--nocolor`, the separate query arguments `-v`, `from`, `ROOT`, `limit`, and `1` form and execute a query, and for a nonempty `ROOT` return 0 with `-v\n` on stdout and no stderr. A query beginning after `--nocolor` is not mistaken for an informational command merely because its text contains a field such as `exif_version`. The completion options also accept a suffix, such as `--fields-list`, `--functions-list`, and `--output-formats-list`, when they are the first raw argument.

With no query (including after only `--nocolor`, `--no-error`, or `--us-dates`), print this short usage to stdout and return 0:

```text
fselect 0.10.0
Find files with SQL-like queries.
https://github.com/jhspetersson/fselect

Usage: fselect [ARGS] COLUMN[, COLUMN...] [from PATH[, PATH...]] [where EXPR] [group by COLUMN, ...] [order by COLUMN (asc|desc), ...] [limit N] [offset N] [into FORMAT]

For more detailed instructions please refer to the URL above or run fselect --help
```

The version command prints exactly the identity block and usage line below, ending in `\n` but omitting the longer-help hint:

```text
fselect 0.10.0
Find files with SQL-like queries.
https://github.com/jhspetersson/fselect

Usage: fselect [ARGS] COLUMN[, COLUMN...] [from PATH[, PATH...]] [where EXPR] [group by COLUMN, ...] [order by COLUMN (asc|desc), ...] [limit N] [offset N] [into FORMAT]
```

Full help begins with the same identity block and usage line, then describes, in this exact order, the eight default extension-category lists from Spec 13, `Path Options:`, `Regex syntax:`, `Column Options:`, `Functions:`, `Expressions:`, `Format:`, and `Interactive mode:`. It includes every field, alias, function, operator, root option, and format named in this document. Its descriptions must state the meanings given in the corresponding specs. Color is enabled by default. Color-enabled version/help output styles each `0.10.0` yellow (`\x1b[33m...\x1b[0m`) and the project and regex-documentation URLs underlined cyan (`\x1b[4;36m...\x1b[0m`); `NO_COLOR` or a no-color flag removes all escapes.

For byte-for-byte compatibility, the complete no-color full-help output is the following block (including one final LF after the last line):

```text
fselect 0.10.0
Find files with SQL-like queries.
https://github.com/jhspetersson/fselect

Usage: fselect [ARGS] COLUMN[, COLUMN...] [from PATH[, PATH...]] [where EXPR] [group by COLUMN, ...] [order by COLUMN (asc|desc), ...] [limit N] [offset N] [into FORMAT]

Files Detected as Archives: .7z, .bz2, .bzip2, .gz, .gzip, .lz, .rar, .tar, .xz, .zip
Files Detected as Audio: .aac, .aiff, .amr, .flac, .gsm, .m4a, .m4b, .m4p, .mp3, .ogg, .wav, .wma
Files Detected as Book: .azw3, .chm, .djv, .djvu, .epub, .fb2, .mobi, .pdf
Files Detected as Document: .accdb, .doc, .docm, .docx, .dot, .dotm, .dotx, .mdb, .odp, .ods, .odt, .pdf, .potm, .potx, .ppt, .pptm, .pptx, .rtf, .xlm, .xls, .xlsm, .xlsx, .xlt, .xltm, .xltx, .xps
Files Detected as Fonts: .eot, .fon, .otc, .otf, .ttc, .ttf, .woff, .woff2
Files Detected as Image: .bmp, .exr, .gif, .heic, .jpeg, .jpg, .jxl, .png, .psb, .psd, .svg, .tga, .tiff, .webp
Files Detected as Source Code: .asm, .awk, .bas, .c, .cc, .ceylon, .clj, .coffee, .cpp, .cs, .d, .dart, .elm, .erl, .go, .gradle, .groovy, .h, .hh, .hpp, .java, .jl, .js, .jsp, .jsx, .kt, .kts, .lua, .nim, .pas, .php, .pl, .pm, .py, .rb, .rs, .scala, .sol, .swift, .tcl, .ts, .tsx, .vala, .vb, .zig
Files Detected as Video: .3gp, .avi, .flv, .m4p, .m4v, .mkv, .mov, .mp4, .mpeg, .mpg, .webm, .wmv

Path Options:
    mindepth                        Minimum depth to search
    maxdepth | depth                Maximum depth to search
    archives | arc                  Whether to search archives
    symlinks | sym                  Whether to follow symlinks
    gitignore | git                 Search respects .gitignore files found
    nogitignore | nogit             Disable .gitignore parsing during the search
    hgignore | hg                   Search respects .hgignore files found
    nohgignore | nohg               Disable .hgignore parsing during the search
    dockerignore | docker           Search respects .dockerignore files found
    nodockerignore | nodocker       Disable .dockerignore parsing during the search
    dfs                             Depth-first search mode
    bfs                             Breadth-first search mode (default)
    regexp | rx                     Treat the path as a regular expression
    as                              Alias for the root path

Regex syntax:
    https://docs.rs/regex/1.10.2/regex/#syntax

Column Options:
    name                            Returns the name (with extension) of the file
    filename | fname                Returns the file name without extension
    ext | extension                 Returns the extension of the file
    path                            Returns the relative path of the file
    abspath                         Returns the absolute path of the file
    dir | directory | dirname       Returns the directory of the file
    absdir                          Returns the absolute directory of the file
    size                            Returns the size of the file in bytes
    fsize | hsize                   Returns the size of the file accompanied with the unit
    uid                             Returns the UID of the owner
    gid                             Returns the GID of the owner's group
    user                            Returns the name of the owner for this file
    group                           Returns the name of the owner's group for this file
    created                         Returns the file creation date (YYYY-MM-DD HH:MM:SS)
    accessed                        Returns the time the file was last accessed (YYYY-MM-DD HH:MM:SS)
    modified                        Returns the time the file was last modified (YYYY-MM-DD HH:MM:SS)
    is_dir                          Returns a boolean signifying whether the file path is a directory
    is_file                         Returns a boolean signifying whether the file path is a file
    is_symlink                      Returns a boolean signifying whether the file path is a symlink
    is_pipe | is_fifo               Returns a boolean signifying whether the file path is a FIFO or pipe file
    is_char | is_character          Returns a boolean signifying whether the file path is a character device or character special file
    is_block                        Returns a boolean signifying whether the file path is a block or block special file
    is_socket                       Returns a boolean signifying whether the file path is a socket file
    device                          Returns the code of device the file is stored on
    rdev                            Returns the device ID for special files (character and block devices)
    inode                           Returns the number of inode
    blocks                          Returns the number of blocks (256 bytes) the file occupies
    hardlinks                       Returns the number of hardlinks of the file
    atime                           Returns the last access time as a Unix timestamp (seconds since epoch)
    mtime                           Returns the last modification time as a Unix timestamp (seconds since epoch)
    ctime                           Returns the last status change time as a Unix timestamp (seconds since epoch)
    mode                            Returns the permissions of the owner, group, and everybody (similar to the first field in `ls -la`)
    user_read                       Returns a boolean signifying whether the file can be read by the owner
    user_write                      Returns a boolean signifying whether the file can be written by the owner
    user_exec                       Returns a boolean signifying whether the file can be executed by the owner
    user_all | user_rwx             Returns a boolean signifying whether the file can be fully accessed by the owner
    group_read                      Returns a boolean signifying whether the file can be read by the owner's group
    group_write                     Returns a boolean signifying whether the file can be written by the owner's group
    group_exec                      Returns a boolean signifying whether the file can be executed by the owner's group
    group_all | group_rwx           Returns a boolean signifying whether the file can be fully accessed by the group
    other_read                      Returns a boolean signifying whether the file can be read by others
    other_write                     Returns a boolean signifying whether the file can be written by others
    other_exec                      Returns a boolean signifying whether the file can be executed by others
    other_all | other_rwx           Returns a boolean signifying whether the file can be fully accessed by the others
    suid | is_suid                  Returns a boolean signifying whether the file permissions have a SUID bit set
    sgid | is_sgid                  Returns a boolean signifying whether the file permissions have a SGID bit set
    is_sticky | sticky              Returns a boolean signifying whether the file permissions have a sticky bit set
    is_hidden                       Returns a boolean signifying whether the file is a hidden file (e.g., files that start with a dot on *nix)
    has_xattrs                      Returns a boolean signifying whether the file has extended attributes
    xattr_count                     Returns the count of extended attributes on the file or alternate data streams on Windows
    extattrs                        Returns the extended file attributes as a string of chattr/lsattr flag letters
    has_extattrs                    Returns a boolean signifying whether the file has any extended file attributes set
    acl                             Returns all POSIX ACL entries in standard form
    has_acl                         Returns a boolean signifying whether the file has POSIX ACL entries beyond standard permissions or Windows explicit ACEs
    default_acl                     Returns all default POSIX ACL entries in standard form
    has_default_acl                 Returns a boolean signifying whether the directory has default POSIX ACL entries
    has_capabilities | has_caps     Returns a boolean signifying whether the file has capabilities
    capabilities | caps             Returns a string describing Linux capabilities assigned to a file
    is_shebang                      Returns a boolean signifying whether the file starts with a shebang (#!)
    is_empty                        Returns a boolean signifying whether the file is empty or the directory is empty
    width                           Returns the number of pixels along the width of the photo or MP4 file
    height                          Returns the number of pixels along the height of the photo or MP4 file
    duration                        Returns the duration of audio file in seconds
    mp3_bitrate | bitrate           Returns the bitrate of the audio file in kbps
    mp3_freq | freq                 Returns the sampling rate of audio or video file
    mp3_title | title               Returns the title of the audio file taken from the file's metadata
    mp3_artist | artist             Returns the artist of the audio file taken from the file's metadata
    mp3_album | album               Returns the album name of the audio file taken from the file's metadata
    mp3_year                        Returns the year of the audio file taken from the file's metadata
    mp3_genre | genre               Returns the genre of the audio file taken from the file's metadata
    exif_datetime                   Returns date and time of taken photo
    exif_datetime_original | exif_dto Returns original date and time when the photo was taken
    exif_altitude | exif_alt        Returns GPS altitude of taken photo
    exif_latitude | exif_lat        Returns GPS latitude of taken photo
    exif_longitude | exif_lon | exif_lng Returns GPS longitude of taken photo
    exif_make                       Returns name of the camera manufacturer
    exif_model                      Returns camera model
    exif_software                   Returns software name with which the photo was taken
    exif_version                    Returns the version of EXIF metadata
    exif_exposure_time | exif_exptime Returns exposure time of the photo taken
    exif_aperture                   Returns aperture value of the photo taken
    exif_shutter_speed              Returns shutter speed of the photo taken
    exif_f_number | exif_f_num      Returns F-number of the photo taken
    exif_iso_speed | exif_iso       Returns ISO speed of the photo taken (EXIF 2.3 ISOSpeed tag)
    exif_sensitivity | exif_photo_sensitivity Returns photographic sensitivity (ISO) of the photo taken
    exif_focal_length | exif_focal_len Returns focal length of the photo taken
    exif_lens_make                  Returns lens manufacturer used to take the photo
    exif_lens_model                 Returns lens model used to take the photo
    exif_description | exif_desc    Returns image description from EXIF metadata
    exif_artist                     Returns the artist or photographer name
    exif_copyright                  Returns the copyright information
    exif_orientation                Returns the image orientation
    exif_flash                      Returns the flash status when the photo was taken
    exif_color_space                Returns the color space of the image
    exif_exposure_program | exif_exp_program Returns the exposure program used
    exif_exposure_bias | exif_exp_bias Returns the exposure bias value
    exif_white_balance | exif_wb    Returns the white balance mode
    exif_metering_mode              Returns the metering mode
    exif_scene_type | exif_scene    Returns the scene capture type
    exif_contrast                   Returns the contrast setting
    exif_saturation                 Returns the saturation setting
    exif_sharpness                  Returns the sharpness setting
    exif_body_serial | exif_serial  Returns the camera body serial number
    exif_lens_serial                Returns the lens serial number
    exif_user_comment | exif_comment Returns the user comment from EXIF metadata
    exif_image_width | exif_width   Returns the image width from EXIF metadata
    exif_image_height | exif_height Returns the image height from EXIF metadata
    exif_max_aperture               Returns the max aperture value of the lens
    exif_digital_zoom | exif_dzoom  Returns the digital zoom ratio
    mime                            Returns MIME type of the file
    line_count                      Returns a number of lines in a text file
    is_binary                       Returns a boolean signifying whether the file has binary contents
    is_text                         Returns a boolean signifying whether the file has text contents
    is_archive                      Returns a boolean signifying whether the file is an archival file
    is_audio                        Returns a boolean signifying whether the file is an audio file
    is_book                         Returns a boolean signifying whether the file is a book
    is_doc                          Returns a boolean signifying whether the file is a document
    is_font                         Returns a boolean signifying whether the file is a font
    is_image                        Returns a boolean signifying whether the file is an image
    is_source                       Returns a boolean signifying whether the file is source code
    is_video                        Returns a boolean signifying whether the file is a video file
    sha1                            Returns SHA-1 digest of a file
    sha2_256 | sha256               Returns SHA2-256 digest of a file
    sha2_512 | sha512               Returns SHA2-512 digest of a file
    sha3_512 | sha3                 Returns SHA-3 digest of a file

Functions:
    String:
        LOWER | LOWERCASE | LCASE   Convert the value to lowercase
        UPPER | UPPERCASE | UCASE   Convert the value to UPPERCASE
        INITCAP                     Capitalize the first letter of each word (Title Case)
        LENGTH | LEN                Get the length of the string
        TO_BASE64 | BASE64          Convert the value to base64
        FROM_BASE64                 Read the value as base64
        CONCAT                      Concatenate the value with the arguments
        CONCAT_WS                   Concatenate the arguments, separated by the value
        LOCATE | POSITION           Get the position of a substring in the value
        SUBSTR | SUBSTRING          Get a substring of the value, from a position and length
        REPLACE                     Replace a substring in the value with another string
        TRIM                        Trim whitespace from the value
        LTRIM                       Trim whitespace from the start of the value
        RTRIM                       Trim whitespace from the end of the value

    Japanese string:
        CONTAINS_JAPANESE | JAPANESE Check if the string contains Japanese characters
        CONTAINS_HIRAGANA | HIRAGANA Check if the string contains Hiragana characters
        CONTAINS_KATAKANA | KATAKANA Check if the string contains Katakana characters
        CONTAINS_KANA | KANA        Check if the string contains Kana characters
        CONTAINS_KANJI | KANJI      Check if the string contains Kanji characters

    Greek string:
        CONTAINS_GREEK | GREEK      Check if the string contains Greek characters

    Numeric:
        BIN                         Get the binary representation of the value
        HEX                         Get the hexadecimal representation of the value
        OCT                         Get the octal representation of the value
        ABS                         Get the absolute value of the number
        POWER | POW                 Raise the value to the power of another value
        SQRT                        Get the square root of the value
        LOG                         Get the logarithm of the value with a specific base
        LN                          Get the natural logarithm of the value
        EXP                         Get e raised to the power of the specified number
        LEAST                       Get the smallest value
        GREATEST                    Get the largest value
        PI                          Get the value of Pi (π)
        FLOOR                       Round down to the nearest integer
        CEIL | CEILING              Round up to the nearest integer
        ROUND                       Round to the nearest integer, or to a given number of decimal places
        RAND | RANDOM               Gets a random number from 0 to the value, or between two values

    Datetime:
        CURRENT_DATE | CUR_DATE | CURDATE Get the current date
        CURRENT_TIME | CUR_TIME | CURTIME Get the current time (HH:MM:SS)
        CURRENT_TIMESTAMP | NOW     Get the current timestamp (YYYY-MM-DD HH:MM:SS)
        DAY                         Get the day from a date
        MONTH                       Get the month from a date
        YEAR                        Get the year from a date
        DAYOFWEEK | DOW             Get the day of the week from a date
        DAYNAME                     Get the name of the day of the week from a date
        DAYOFYEAR | DOY             Get the day of the year from a date (1-366)
        DATE_ADD | DATEADD          Add days to a date and return the resulting date
        DATE_SUB | DATESUB          Subtract days from a date and return the resulting date
        DATE_DIFF | DATEDIFF        Get the number of days between two dates
        FROM_UNIXTIME               Convert a Unix timestamp to a datetime string
        LAST_DAY | LAST_DATE        Get the last day of the month for a given date

    Aggregate:
        MIN                         Get the minimum value
        MAX                         Get the maximum value
        AVG                         Get the average value
        SUM                         Get the sum of all values
        COUNT                       Get the number of values
        STDDEV_POP | STDDEV | STD   Get the population standard deviation
        STDDEV_SAMP                 Get the sample standard deviation
        VAR_POP | VARIANCE          Get the population variance
        VAR_SAMP                    Get the sample variance

    Xattr:
        HAS_XATTR                   Check if the file has a specific extended attribute
        XATTR                       Get the value of an extended attribute
        HAS_EXTATTR                 Check if the file has a specific extended file attribute flag
        HAS_ACL_ENTRY               Check if a specific POSIX ACL entry exists
        ACL_ENTRY                   Get permissions of a specific POSIX ACL entry
        HAS_DEFAULT_ACL_ENTRY       Check if a specific default POSIX ACL entry exists
        DEFAULT_ACL_ENTRY           Get permissions of a specific default POSIX ACL entry
        HAS_CAPABILITY | HAS_CAP    Check if the file has a specific capability (security.capability xattr)

    Other:
        FORMAT_SIZE | FORMAT_FILESIZE Format a file size in human-readable format
        FORMAT_TIME | PRETTY_TIME   Format a time duration in human-readable format
        CURRENT_UID                 Get the current user ID
        CURRENT_USER                Get the current username
        CURRENT_GID                 Get the current group ID
        CURRENT_GROUP               Get the current group name
        CONTAINS                    Checks if a file contains a substring
        COALESCE                    Return the first non-empty value

Expressions:
    Operators:
        = | == | eq                 Used to check for equality between the column field and value
        === | eeq                   Used to check for strict equality between column field and value irregardless of any special regex characters
        != | <> | ne                Used to check for inequality between column field and value
        !== | ene                   Used to check for inequality between column field and value irregardless of any special regex characters
        < | lt                      Used to check whether the column value is less than the value
        <= | lte | le               Used to check whether the column value is less than or equal to the value
        > | gt                      Used to check whether the column value is greater than the value
        >= | gte | ge               Used to check whether the column value is greater than or equal to the value
        ~= | =~ | regexp | rx       Used to check if the column value matches the regex pattern
        !=~ | !~= | notrx           Used to check if the column value doesn't match the regex pattern
        like                        Used to check if the column value matches the pattern which follows SQL conventions
        notlike                     Used to check if the column value doesn't match the pattern which follows SQL conventions
        between                     Used to check if the column value lies between two values inclusive
        in                          Used to check if the column value is in the list of values
        exists                      Used to check if there is results in the subquery (optionally bound with the main query)
    Logical Operators:
        and                         Used as an AND operator for two conditions made with the above operators
        or                          Used as an OR operator for two conditions made with the above operators

Format:
    tabs                            Tab-separated values (default)
    lines                           One item per line
    list                            Entire output onto a single line for xargs
    csv                             Comma-separated values
    json                            JSON format
    html                            HTML format

Interactive mode:
    help            Get usage help
    pwd             Print the current working directory
    cd PATH         Change the current working directory to PATH
    errors [ON|OFF] Toggle whether errors are shown or not
    exit | quit     Exit fselect
    
```

The completion outputs are one space-separated line terminated by `\n`:

```text
--root-options: mindepth maxdepth depth archives arc symlinks sym gitignore git nogitignore nogit hgignore hg nohgignore nohg dockerignore docker nodockerignore nodocker dfs bfs regexp rx as
--output-formats: tabs lines list csv json html
```

`--fields` prints the following exact space-separated line (plus newline):

```text
name filename fname ext extension path abspath dir directory dirname absdir size fsize hsize uid gid user group created accessed modified is_dir is_file is_symlink is_pipe is_fifo is_char is_character is_block is_socket device rdev inode blocks hardlinks atime mtime ctime mode user_read user_write user_exec user_all user_rwx group_read group_write group_exec group_all group_rwx other_read other_write other_exec other_all other_rwx suid is_suid sgid is_sgid is_sticky sticky is_hidden has_xattrs xattr_count extattrs has_extattrs acl has_acl default_acl has_default_acl has_capabilities has_caps capabilities caps is_shebang is_empty width height duration mp3_bitrate bitrate mp3_freq freq mp3_title title mp3_artist artist mp3_album album mp3_year mp3_genre genre exif_datetime exif_datetime_original exif_dto exif_altitude exif_alt exif_latitude exif_lat exif_longitude exif_lon exif_lng exif_make exif_model exif_software exif_version exif_exposure_time exif_exptime exif_aperture exif_shutter_speed exif_f_number exif_f_num exif_iso_speed exif_iso exif_sensitivity exif_photo_sensitivity exif_focal_length exif_focal_len exif_lens_make exif_lens_model exif_description exif_desc exif_artist exif_copyright exif_orientation exif_flash exif_color_space exif_exposure_program exif_exp_program exif_exposure_bias exif_exp_bias exif_white_balance exif_wb exif_metering_mode exif_scene_type exif_scene exif_contrast exif_saturation exif_sharpness exif_body_serial exif_serial exif_lens_serial exif_user_comment exif_comment exif_image_width exif_width exif_image_height exif_height exif_max_aperture exif_digital_zoom exif_dzoom mime line_count is_binary is_text is_archive is_audio is_book is_doc is_font is_image is_source is_video sha1 sha2_256 sha256 sha2_512 sha512 sha3_512 sha3
```

`--functions` prints exactly this set, space-separated on one line and terminated by `\n`; ordering need not be stable:

```text
CONTAINS_GREEK GREEK CURRENT_DATE CUR_DATE CURDATE CURRENT_TIME CUR_TIME CURTIME CURRENT_TIMESTAMP NOW DAY MONTH YEAR DAYOFWEEK DOW DAYNAME DAYOFYEAR DOY DATE_ADD DATEADD DATE_SUB DATESUB DATE_DIFF DATEDIFF FROM_UNIXTIME LAST_DAY LAST_DATE BIN HEX OCT ABS POWER POW SQRT LOG LN EXP LEAST GREATEST PI FLOOR CEIL CEILING ROUND RAND RANDOM MIN MAX AVG SUM COUNT STDDEV_POP STDDEV STD STDDEV_SAMP VAR_POP VARIANCE VAR_SAMP HAS_XATTR XATTR HAS_EXTATTR HAS_ACL_ENTRY ACL_ENTRY HAS_DEFAULT_ACL_ENTRY DEFAULT_ACL_ENTRY HAS_CAPABILITY HAS_CAP LOWER LOWERCASE LCASE UPPER UPPERCASE UCASE INITCAP LENGTH LEN TO_BASE64 BASE64 FROM_BASE64 CONCAT CONCAT_WS LOCATE POSITION SUBSTR SUBSTRING REPLACE TRIM LTRIM RTRIM CONTAINS_JAPANESE JAPANESE CONTAINS_HIRAGANA HIRAGANA CONTAINS_KATAKANA KATAKANA CONTAINS_KANA KANA CONTAINS_KANJI KANJI FORMAT_SIZE FORMAT_FILESIZE FORMAT_TIME PRETTY_TIME CURRENT_UID CURRENT_USER CURRENT_GID CURRENT_GROUP CONTAINS COALESCE
```

If `--config`, `-c`, or `/c` lacks a following path, write exactly `Error: --config requires a path argument\n` to stderr, nothing to stdout, and return 2.

When stdout is a terminal, path/name-like values may be ANSI-colored by file type. Piped/captured data must remain machine-readable, and JSON/CSV/HTML/list formats never contain ANSI codes even on a terminal. `NO_COLOR` with any value, a no-color option, or `no_color = true` disables all ANSI escapes in help, errors, queries, and interactive output.

## Spec 2

### Lexing and relaxed query syntax

Keywords, field names, function names, boolean words, directions, formats, and word-form operators are ASCII case-insensitive. Filenames and literal string contents retain their case and Unicode. UTF-8 names (including combining marks, RTL scripts, CJK, emoji, quotes, commas, tabs, and newlines) must not crash the program.

`select` is optional. Commas between selected expressions are accepted but not required when token boundaries are unambiguous. Parentheses and curly braces are interchangeable for grouping, function arguments, and value lists. Nested calls and nested parentheses/braces are supported. A comma attached to another token is still a separator.

Single quotes, double quotes, and backticks delimit strings and paths and preserve whitespace and reserved words. The delimiters are removed. Empty quoted strings are valid. An unquoted token not recognized as a field or function is a literal string; selecting an unknown identifier therefore repeats that literal rather than producing an unknown-column error (for example, the unsupported identifier `md5` prints `md5`). A token that is a recognized function name is not such an unknown literal even when written without call parentheses: in particular, `where ext = bin` matches no rows, while `where ext = 'bin'` matches `.bin` names. Numeric literals support signed integers, decimals, and scientific notation such as `1.7e308`; `true`, `false`, `1`, and `0` are usable as booleans.

Selected expressions may be aliased with `AS alias`. A root may be named using `ROOT AS alias`, enabling `alias.field` references. An alias is a label/context name; ordinary tabular output contains only values. JSON uses the select alias as its property name.

The select-list token `*` expands to the ls-like set `mode, user, group, size, modified, path`. In aggregate calls, `count(*)` means all rows and does not expand.

Constants and context-free functions are valid selected expressions; examples are `select 1`, `select 'hello world'`, `select pi()`, and current-user/date functions. They are evaluated for each otherwise-selected row, so callers may use `limit 1` when they need one copy. Both a query without `from` and an explicit relative root `from .` search the process's actual current working directory; a conflicting `PWD` environment value does not redirect either search. For example, if the process directory contains only `real` while `PWD` names another directory containing only `pwd-entry`, both `name order by name` and `name from . order by name` return 0 with `real\n` on stdout and no stderr.

The clause order is select list, `from`, `where`, `group by`, `having`, `order by`, `limit`, `offset`, `into`. A `where` before `from` is not accepted: for example, `name where size <> 100 from . limit 1` returns 2 with `query: could not parse tokens at the end of the query`. Any tokens left after a complete query are a parse error rather than silently ignored.

## Spec 3

### Filesystem roots, traversal, depth, and aliases

Each root is a directory path followed by zero or more root options. Multiple roots are comma-separated and their result streams are concatenated; they do not form a Cartesian product. Paths containing spaces or commas must be quoted. The root itself is not emitted—its children are depth 1.

Root options are:

| Syntax | Required behavior |
|---|---|
| `mindepth N` | Do not emit entries shallower than depth N, but still traverse them. Depth 1 includes immediate children. |
| `maxdepth N`, `depth N` | Do not traverse/emit deeper than N. `1` means immediate children only, `2` also includes grandchildren. `0` means unlimited, as does omission. |
| `symlinks`, `sym` | Follow directory symlink targets. Without it, emit the symlink itself but do not recurse through it. Detect cycles and never loop. Broken links are emitted and do not abort traversal. |
| `archives`, `arc` | Add ZIP members as virtual result rows; see Spec 22. |
| `gitignore`, `git`; `hgignore`, `hg`; `dockerignore`, `docker` | Enable the corresponding ignore-file processing described in Spec 21 (including the reference's inert Git behavior). |
| `nogitignore`, `nogit`; `nohgignore`, `nohg`; `nodockerignore`, `nodocker` | Explicitly disable that ignore mechanism. |
| `bfs` | Breadth-first traversal; this is the default. Emit a directory's entries in enumeration order, queueing child directories for later. |
| `dfs` | Pre-order depth-first traversal using the implementation's LIFO work stack. Recursively complete the selected directory's subtree before emitting or visiting the next sibling. For immediate directories created in the order `first`, `second`, each containing `leaf`, the exact rows are `second`, `second/leaf`, `first`, `first/leaf`; it does not emit both immediate directories before descending. |
| `regexp`, `regex` | Treat the root string as a regular expression selecting matching directories rather than one literal root. Although informational output advertises `rx`, the query parser does not accept `rx` as a root-option alias. |
| `as NAME` | Bind the root's row context to NAME. |

An ordinary false filter and `mindepth` do not prevent traversal into a directory that could contain a match. A filter evaluation error on a directory does prevent descent through that directory. For example, with 21 immediate entries including two directories that contain two more files, `where size / 0 > 0` and `where size % 0 = 0` each report exactly 21 `Division by zero` diagnostics, omit the two nested files, emit no rows, and return 1. Archive-member depth is not charged against the filesystem maximum depth: a ZIP encountered at an allowed depth can contribute all of its nested members.

Canonicalization/open/read errors are reported per path and traversal continues where possible. On Linux, a nonexistent only root yields no stdout, exit 1, and exactly `<path>: could not canonicalize path: No such file or directory (os error 2)\n`; for example `/nonexistent123456789: could not canonicalize path: No such file or directory (os error 2)\n`. `--no-error` suppresses the line. With `regexp` or `regex`, invalid root regexes are reported as `result: invalid regex in root path: PATTERN`; `PATTERN` is the regex-bearing path component (for example `level1_[invalid`), not its literal parent directory. This setup diagnostic is nonfatal and leaves status 0 if no other failure occurs. The same root followed by `rx` instead returns 2, produces no stdout, and writes exactly `query: could not parse tokens at the end of the query\n`.

`path` and root-regexp behavior must work with absolute and relative roots, multiple matching directories, paths containing spaces, and roots whose text includes words such as `group` or `order` when quoted.

## Spec 4

### Expressions, operators, patterns, and coercion

The comparison operators and aliases are:

| Operation | Spellings |
|---|---|
| ordinary equality | `=`, `==`, `eq` |
| ordinary inequality | `!=`, `<>`, `ne` |
| strict literal equality | `===`, `eeq` |
| strict literal inequality | `!==`, `ene` |
| greater / greater-or-equal | `>`, `gt`; `>=`, `gte`, `ge` |
| less / less-or-equal | `<`, `lt`; `<=`, `lte`, `le` |
| regex match | `=~`, `~=`, `regexp`, `rx` |
| regex non-match | `!=~`, `!~=`, `notrx` |
| SQL pattern | `like`, `notlike`, also `not like` |
| inclusive range | `between LOW and HIGH`, `notbetween`, `not between` |
| membership | `in LIST`, `notin LIST`, `not in LIST` |
| collection existence | `exists VALUE_OR_SUBQUERY`, `not exists VALUE_OR_SUBQUERY` |

Numeric fields compare numerically, booleans compare as booleans, date fields compare chronologically, and strings compare lexicographically by Unicode/code-point ordering. File-size literals are converted as in Spec 12. `BETWEEN` includes both endpoints. `IN` accepts comma-separated values in `(...)` or `{...}` and preserves value types. `x IN ()` is false, while `x NOT IN ()` is true. `EXISTS` on a nonempty literal list is true; `NOT EXISTS {}` is true.

Ordinary string `=`/`!=` use a whole-value glob comparison. When the pattern contains no wildcard, comparison is case-sensitive: among `FILE.TXT`, `File.txt`, and `FiLe.TxT`, `name = 'FILE.TXT'` selects only `FILE.TXT`. When `*` or `?` is present, glob matching is case-insensitive. Glob `*` matches zero or more characters and `?` exactly one: over `FILE.TXT`, `File.txt`, `FiLe.TxT`, `a+b.txt`, and `ab.txt`, `name = '*.TXT'` selects all five in name order, not only the three case variants. All other regex metacharacters—brackets, braces, parentheses, `+`, `|`, `^`, `$`, and ordinary dots—are literal in globs. Backslash escapes a character. `===` and `!==` disable glob interpretation and perform case-sensitive, code-point-exact string comparison, so an asterisk is literal. Regex operators are case-sensitive unless their pattern explicitly enables case-insensitive mode.

`LIKE` is case-insensitive SQL-style matching: `%` is zero or more characters and `_` is exactly one; `*` and `?` are literal. Escape regex-special characters when converting LIKE to a matcher. An empty LIKE pattern is an evaluation error rather than “match all.”

Regex operators use a Rust-regex-compatible syntax and search the complete field value. Support anchors, groups, alternation, dot, character classes/ranges, quantifiers, and backslash escapes. Invalid regexes are reported as evaluation/search errors without a crash.

`NOT` can precede a boolean, comparison, operator, or parenthesized logical expression. Negation maps equality to inequality, comparisons to their complements, regex/LIKE/BETWEEN/IN/EXISTS to their negated forms, and applies De Morgan's law to logical expressions. These comparison, range, membership, existence, and logical forms are condition grammar for `where` and `having`; they are not boolean-valued select-list expressions. In particular, selecting `size between 3 and 3, size in {2,3}, size not in (), exists {'x'}, not exists {}` returns 2 with no stdout and exactly `query: could not parse tokens at the end of the query\n` on stderr, although the individual forms are valid as conditions.

`AND` binds more tightly than `OR`; parentheses override precedence. The function-name token rule above still applies inside either branch. Thus, over `a.txt` of size 1 and `b.bin` of size 2, `size = 1 or size = 2 and ext = bin` emits only `a.txt` because bare `bin` is not the string `bin`; quoting it as `ext = 'bin'` emits both files and demonstrates the stated precedence. Evaluation is asymmetric: a false left side skips the right side of `AND`, but a true left side does not skip the right side of `OR`. Consequently, `where false and 1 / 0 = 1` succeeds with no rows or diagnostic, whereas `where true or 1 / 0 = 1` evaluates the division, reports `Division by zero`, emits no row for that file, and returns 1. Boolean fields may appear alone (`where is_file`) and are then tested for true.

## Spec 5

### Arithmetic expressions

Support signed numeric literals and binary `+ - * / %`, with word aliases `plus`, `minus`, `mul`, `div`, and `mod`. A leading minus directly on a field token is accepted but does not negate the field: selecting `-size` for a five-byte file renders `5`. Signed literals do retain their sign (`-5` renders `-5`), and binary subtraction may produce a negative result (`0 - size` renders `-5`). Multiplication, division, and modulo bind more tightly than addition/subtraction. Parentheses around an arithmetic subexpression are accepted but do not override that precedence: `(2 + 3) * 4` is evaluated like `2 + 3 * 4`. Arithmetic can appear in selected expressions, function arguments, comparisons, and `order by`, and can operate on aggregate results such as `count(*) * 2`.

Use integer arithmetic when both values are integers except that `/` is floating division (`5 / 2` is `2.5`, while an integral result such as `12 / 2` renders `6`). Decimals produce floating arithmetic. Preserve negative signed literals and binary-operation results. Examples: `12 % 5` is `2`, `2 + 3 * 4` is `14`, `(2 + 3) * 4` is also `14`, and `size / 1024.0 > 1.5` is a floating comparison.

Division or modulo by zero and finite-number overflow are row evaluation errors: emit no value/row for the failed expression, report an error unless suppressed, and make the process return 1. An arithmetic error while evaluating a selected expression terminates the query at that first failing row; later rows are not evaluated or diagnosed. Thus, for a root whose enumeration order is the two files `a` then `b`, each of `1/0 from ROOT` and `1%0 from ROOT` returns 1 with no stdout and exactly one diagnostic, `ROOT/a: Division by zero\n`. Both zero-divisor operations use the message `Division by zero`. A nonfinite arithmetic result uses `Arithmetic overflow: result is inf` or `Arithmetic overflow: result is -inf`. Parsing an operator with a missing operand is a query error (return 2).

## Spec 6

### Subqueries and correlated roots

`IN`, `NOT IN`, `EXISTS`, and `NOT EXISTS` accept a nested select in parentheses or braces. The inner query has the same grammar and may itself contain a nested subquery or aggregate. `IN` compares the outer value with the inner query's first selected column. `EXISTS` tests whether the inner query returns at least one row.

Correlated queries use root aliases:

```text
name from DATA as data
where exists (select * from BACKUP as backup where backup.name = data.name)
```

The inner expression can reference both inner and outer aliases. Evaluate it for the current outer row (caching only when doing so does not change semantics). An unknown alias qualifier is silently accepted without a diagnostic; for example, over a directory containing `item.txt`, `where missing.name = name` emits `item.txt`, leaves stderr empty, and returns 0. Nested uncorrelated queries and comparisons against aggregate subqueries such as `size = (select max(size) from ROOT)` are supported. A parenthesized nested `select` is also valid directly in the outer select list. For a one-column nested query it renders the first inner row's value, or an empty cell when the inner query has no row; for example `(select name from ROOT where name = 'file3.txt') from ROOT limit 1` renders `file3.txt`.

## Spec 7

### Ordering, grouping, limits, and execution order

Apply operations in this semantic order: traverse roots, compute row metadata, apply `where`, form groups/aggregates, apply `having`, sort, apply offset, apply limit, then format.

`order by` accepts one or more fields, arbitrary expressions, aggregate expressions, select aliases, or 1-based selected-column indices. Each key independently accepts `asc` (default) or `desc`. Direct numeric expressions and 1-based selected-column indices retain numeric sorting, while a select alias is resolved through its rendered selected value and sorts lexicographically as a string. Thus, for sizes 2, 2, and 10, `name,size as bytes ... order by bytes desc, name asc` puts the two rendered `2` values before rendered `10`, with the names breaking the tie; `order by size desc, name asc` and `order by 2 desc, 1` put numeric 10 first. Strings use case-sensitive lexicographic order and empty values sort consistently as empty strings. Later keys break ties. A positional index outside the selected columns is a parse error.

`group by` accepts one or more fields/expressions and emits one row per distinct tuple after filtering. Aggregate state is independent per group. A selected group-key expression and aggregates have values; an ordinary row-level expression that is neither grouped nor aggregated renders empty. `having EXPR` filters the formed groups and may use aggregate calls even when they are not selected. Aggregate evaluation in `having` has one observable reuse quirk: when `having count(*) > 0` admits a group, a selected `count(*)` for that group renders `0`, although other aggregates retain their values. Thus the filtered/grouped query `ext,count(*),sum(size) ... where size >= 2 group by ext having count(*) > 0 order by sum(size) desc limit 1` over two `.two` files of sizes 3 and 4 renders exactly `two\t0\t7\n`. Without the identical `count(*)` call in `having`, selected grouped counts retain their ordinary values. No-match grouped queries emit no rows. A no-group aggregate query always emits one row, even on an empty input.

`limit N` takes at most N rows after sorting and offset. `limit 0` means no restriction. `offset N` skips the first N final rows; an offset at or beyond the row count produces no output. Also accept `limit OFFSET,COUNT`; for example `limit 2,1` skips two and emits one. Combining comma-form limit with an explicit `offset` is a query error: `query: Ambiguous offset specified`. Negative or nonnumeric limit/offset values are query errors.

## Spec 8

### Output formats and value rendering

An unavailable/null metadata value renders as an empty cell. Booleans render lowercase `true` or `false`. Integers have no grouping separators; finite floats use a concise decimal representation. Every normal row ends in `\n`.

`into tabs` is the default and joins cells with `\t`. `into lines` writes each cell on its own line, with no extra blank separator between rows. `into list` writes every selected cell separated and terminated by NUL (`\0`), with no newline. Empty tab/line/list/CSV results produce zero bytes.

`into csv` uses standard RFC-4180-style cell quoting without a header: comma-separated cells and `\n` records; quote a cell containing comma, quote, CR, or LF and double embedded quotes. For example the two cells `file,"name.txt` and `14` render as `"file,""name.txt",14`.

`into json` emits exactly one compact JSON array with no trailing newline. Each row is an object. All values are JSON strings (including numbers and booleans). Property names are PascalCase versions of selected field names (`name` → `Name`, `is_dir` → `IsDir`, `line_count` → `LineCount`), or the select alias. Properties within each object are lexicographically sorted by key. Escape JSON correctly and preserve Unicode. Empty input is exactly `[]`. Example:

```json
[{"IsDir":"false","Name":"a.txt","Size":"3"}]
```

`into html` emits one compact HTML document with no trailing newline:

```text
<html><head><title>QUERY</title></head><body><table><tr><th colspan="N">QUERY</th></tr><tr><td>V1</td>...</tr></table></body></html>
```

`QUERY` is the query text formed after global-option removal using the no-inserted-whitespace argument handling from Spec 1; preserve its keyword case and whether the optional `select` was present. N is the number of selected cells, and there is one data row per result. Escape at least `& < > " '` in query and values. Even empty results include the document, table, and heading row.

Any unknown or missing output format is a parse error. The supported list is exactly `tabs lines list csv json html`.

## Spec 9

### Naming and basic metadata fields

These fields and aliases are required:

| Names | Value |
|---|---|
| `name` | Last path component, including all extensions. |
| `filename`, `fname` | `name` without its final extension. Dotfiles such as `.hidden` have no extension and retain `.hidden` as filename. A trailing dot is an empty final extension and its separator is removed, so `file.` has filename `file` and an empty `ext`. |
| `ext`, `extension` | Final extension without the dot, or empty. For `archive.tar.gz`, this is `gz`. |
| `path` | Normally the path relative to the search root, with nested components. When `symlinks` follows a directory link, descendants are instead named from the canonical target traversal path. For a root entry `linked` pointing to an external directory containing `child`, ordered output is the absolute target path ending in `/outside/child`, followed by `linked`; it is not `linked/child`. |
| `abspath` | Canonical absolute path. For archive members, a stable virtual absolute path containing the archive and member. |
| `dir`, `directory`, `dirname` | Parent portion of `path`, relative to the search root; empty for immediate children. |
| `absdir` | Absolute parent directory. |
| `size` | Filesystem byte length. Directories use their metadata length. Without the root's `symlinks`/`sym` option, a symlink uses its own link-metadata length (the byte length of the stored target text), even when valid; a link whose target text is `target.txt` therefore has size `10`. With `symlinks`/`sym`, a valid symlink uses target metadata length, but a broken symlink has no available size and renders an empty cell. Archive members use uncompressed member size. |
| `is_dir`, `is_file`, `is_symlink` | File-kind predicates. A symlink is `is_symlink=true`; it is not treated as a regular file even when its metadata fields follow the target. |
| `is_hidden` | On Unix, true iff the final name begins with `.`; applies to files and directories. |
| `is_empty` | True for a zero-byte file or a directory with no entries; false for nonempty files/directories. |
| `is_shebang` | True iff a regular readable file starts with bytes `#!` (text after it is irrelevant). False for empty, one-byte, directory, and binary values. |

All field aliases yield identical values and may be used in selection, filtering, grouping, ordering, arithmetic where typed, and functions.

## Spec 10

### Time, identity, and Unix metadata fields

`accessed`, `created`, and `modified` render local filesystem times as `YYYY-MM-DD HH:MM:SS`. `created` is empty when the platform/filesystem exposes no birth time. `atime`, `mtime`, and `ctime` are integer Unix seconds (on Unix, `ctime` is status-change time). Timestamp zero renders `1970-01-01 00:00:00` in UTC test environments.

Unix fields are:

| Field | Value |
|---|---|
| `uid`, `gid` | Numeric owner and group IDs. |
| `user`, `group` | Resolved owner/group name; numeric fallback if lookup fails. |
| `device` | Filesystem device number. |
| `rdev` | Special-device ID, normally 0 for a regular file. |
| `inode` | Inode number; hard links share it. |
| `hardlinks` | Link count (`st_nlink`). |
| `blocks` | Allocated block count reported by filesystem metadata. |

Metadata queries must work for zero-size files, sparse/large files, hard links, permission-denied files where stat is still possible, FIFOs, Unix sockets, devices, symlinks, and broken symlinks without hanging or opening FIFOs.

## Spec 11

### Mode and permissions

`mode` is the 10-character `ls -l` style type/permission string. The first character is `-`, `d`, `l`, `p`, `c`, `b`, or `s` for regular, directory, symlink, FIFO, character device, block device, or socket. The remaining positions are user/group/other `rwx`. Set-ID/sticky replace execute with `s`/`t` when execute is set and uppercase `S`/`T` when it is not.

Required predicates and aliases are:

```text
user_read user_write user_exec user_all user_rwx
group_read group_write group_exec group_all group_rwx
other_read other_write other_exec other_all other_rwx
suid is_suid sgid is_sgid sticky is_sticky
is_pipe is_fifo is_char is_character is_block is_socket
```

Each single-permission predicate checks exactly its bit. Each `*_all`/`*_rwx` is true only when all three corresponding bits are present. Special-bit predicates are independent of execute bits. Archive member modes are decoded from the ZIP Unix external-attributes high word using the same formatter. For a ZIP entry with Windows creator metadata and no supplied Unix mode, the implementation fabricates mode `-rw-------`: `user_read` and `user_write` are `true`, while user execute/all, every group/other predicate, and set-ID/sticky predicates are `false`. The `uid`, `gid`, `user`, and `group` cells remain empty.

## Spec 12

### Sizes and human-readable formatting

Size literals in comparisons are case-insensitive and support:

| Suffix | Multiplier |
|---|---:|
| `b` or none | 1 |
| `k`, `kib` | 1024 |
| `kb` | 1000 |
| `m`, `mib` | 1024² |
| `mb` | 1000² |
| `g`, `gib` | 1024³ |
| `gb` | 1000³ |
| `t`, `tib` / `tb` | 1024⁴ / 1000⁴ |
| `p`, `pib` / `pb` | 1024⁵ / 1000⁵ |
| `e`, `eib` / `eb` | 1024⁶ / 1000⁶ |

Reject malformed suffixes rather than guessing.

`fsize` and `hsize` are identical to `format_size(size)` and automatically choose the largest 1024-based unit that keeps the absolute value at least 1, using `B, KiB, MiB, GiB, TiB, PiB, EiB`; omit redundant decimal zeros (for example `0B`, `12B`, `1KiB`, `10KiB`, `100MiB`, `1GiB`). Ordering by these fields is numeric.

`FORMAT_SIZE`/`FORMAT_FILESIZE(number [, format])` accepts format text composed of:

- `%.N` for up to N fractional digits, retaining trailing zeroes when a fractional part remains but omitting the entire all-zero fractional part;
- a literal space to place a space before the unit;
- `d` for divisor 1000 and SI units;
- `c` for divisor 1024 but conventional labels (`KB`, `MB`, ...);
- `s` for one-letter labels (`K`, `M`, ...);
- an explicit unit `b`, `k/kib/kb`, `m/mib/mb`, `g/gib/gb`, `t/tib/tb`, `p/pib/pb`, or `e/eib/eb` rather than automatic scaling.

Examples that define formatting:

| Call | Result |
|---|---|
| `format_size(1678123)` | `1.60MiB` |
| `format_size(1678123, ' ')` | `1.60 MiB` |
| `format_size(1678123, '%.0')` | `2MiB` |
| `format_size(1678123, '%.1')` | `1.6MiB` |
| `format_size(1678123, '%.2 d')` | `1.68 MB` |
| `format_size(1678123, '%.2 ck')` | `1638.79 KB` |
| `format_size(1678123, '%.0 kb')` | `1678 KB` |
| `format_size(1678123, '%.0s')` | `2M` |
| `format_size(1000, '%.2 d')` | `1 KB` |
| `format_size(1500, '%.2 d')` | `1.50 KB` |

An empty/nonnumeric input or invalid format yields an empty value without crashing.

When `%.N` is omitted, precision is chosen by the formatter and is not uniformly two digits for an explicitly forced unit. The following observed results are exact and define the boundary cases:

| Call | Result |
|---|---|
| `format_size(2097152, 'kb')` | `2097KB` |
| `format_size(2097152, 'mb')` | `2MB` |
| `format_size(2097152, 'gb')` | `0.00GB` |
| `format_size(1, 'eb')` | `0EB` |
| `format_size(1, 'eib')` | `0EiB` |

## Spec 13

### Content, MIME, hashes, and extension categories

`mime` is detected from a mixture of content and filename information. It recognizes at least plain UTF-8 text (`text/plain`), HTML (`text/html`), PNG (`image/png`), XML (`application/xml`), executables (`application/x-executable`), and arbitrary binary (`application/octet-stream`). SVG markup, including `<svg xmlns="http://www.w3.org/2000/svg"></svg>` stored in either `vector.dat` or `vector.svg`, is classified as `text/plain`, with `is_text=true` and `is_binary=false`; it is not labeled `image/svg+xml`. Ordinary shebang files named `script.sh`, `script.pl`, `script.rb`, and `script.py` use `application/x-shellscript`, `application/x-perl`, `application/x-ruby`, and `text/x-python3`, respectively. The analogous `script.php` beginning `#!/usr/bin/php` is instead `text/plain`; PHP source identified through other filename/content evidence can still be `application/x-php`. Python must not render `text/x-python`. Directories are `inode/directory`. Symlinks use target content. Empty/zero-byte ordinary files are `text/plain`.

`is_text` is true for `text/*`, `image/svg+xml`, MIME suffixes `+xml`/`-xml`, and textual script application types (shell, Perl, PHP, Ruby); it is false for `application/xml` and arbitrary binary. `is_binary` is the complement for ordinary files, but both predicates are false for directories. `line_count` counts LF bytes; a CRLF therefore counts once through its LF, while a lone CR does not count. An unterminated final line contributes zero; thus `a\rb\r` and a nonempty one-line file without a newline both have count 0, while `a\r\nb\r\n` and `a\nb\n` both have count 2. Directories yield empty line count. Binary data safely yields 0. Handle large and UTF-8 files.

The extension-based booleans use case-insensitive final extensions and are configurable (Spec 23):

| Field | Default extensions |
|---|---|
| `is_archive` | `.7z .bz2 .bzip2 .gz .gzip .lz .rar .tar .xz .zip` |
| `is_audio` | `.aac .aiff .amr .flac .gsm .m4a .m4b .m4p .mp3 .ogg .wav .wma` |
| `is_book` | `.azw3 .chm .djv .djvu .epub .fb2 .mobi .pdf` |
| `is_doc` | `.accdb .doc .docm .docx .dot .dotm .dotx .mdb .odp .ods .odt .pdf .potm .potx .ppt .pptm .pptx .rtf .xlm .xls .xlsm .xlsx .xlt .xltm .xltx .xps` |
| `is_font` | `.eot .fon .otc .otf .ttc .ttf .woff .woff2` |
| `is_image` | `.bmp .exr .gif .heic .jpeg .jpg .jxl .png .psb .psd .svg .tga .tiff .webp` |
| `is_source` | `.asm .awk .bas .c .cc .ceylon .clj .coffee .cpp .cs .d .dart .elm .erl .go .gradle .groovy .h .hh .hpp .java .jl .js .jsp .jsx .kt .kts .lua .nim .pas .php .pl .pm .py .rb .rs .scala .sol .swift .tcl .ts .tsx .vala .vb .zig` |
| `is_video` | `.3gp .avi .flv .m4p .m4v .mkv .mov .mp4 .mpeg .mpg .webm .wmv` |

Hashes are lowercase hexadecimal over exact file bytes: `sha1` (40 hex), `sha2_256`/`sha256` (64), `sha2_512`/`sha512` (128), and `sha3_512`/`sha3` (128). Empty and large/binary files are supported; unavailable values for directories/archive contexts are empty.

## Spec 14

### Image, audio, video, and EXIF metadata

`width` and `height` return pixel dimensions as integers for PNG, BMP, JPEG/JPG, GIF, TIFF, WebP, MP4, and MKV where encoded. They also read numeric width/height attributes from SVG markup when the filename has the `.svg` extension. SVG content is not recognized for these fields solely from its markup: `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="7"></svg>` stored as `vector.svg` yields `12` and `7`, but the identical bytes stored as `vector.dat` yield two empty cells. Invalid, truncated, empty, or merely extension-renamed media returns empty rather than crashing. These numeric fields work in arithmetic, filtering, ordering, grouping, and aggregates; nonmedia values are empty.

Audio/video fields are `duration` (seconds, numeric), `mp3_bitrate`/`bitrate` (kbps), `mp3_freq`/`freq` (Hz), `mp3_title`/`title`, `mp3_artist`/`artist`, `mp3_album`/`album`, `mp3_year`, and `mp3_genre`/`genre`. Parse MP3 frames and ID3 metadata and MP4/MKV dimensions/duration/frequency. PCM WAV metadata is not exposed through these fields: a one-second mono 8-bit 8000-Hz PCM WAV renders `duration,freq` as `\t\n`. Missing tags are empty.

JPEG EXIF fields and aliases are:

```text
exif_datetime
exif_datetime_original exif_dto
exif_altitude exif_alt
exif_latitude exif_lat
exif_longitude exif_lon exif_lng
exif_make exif_model exif_software exif_version
exif_exposure_time exif_exptime
exif_aperture exif_shutter_speed
exif_f_number exif_f_num
exif_iso_speed exif_iso
exif_sensitivity exif_photo_sensitivity
exif_focal_length exif_focal_len
exif_lens_make exif_lens_model
exif_description exif_desc
exif_artist exif_copyright exif_orientation exif_flash exif_color_space
exif_exposure_program exif_exp_program
exif_exposure_bias exif_exp_bias
exif_white_balance exif_wb
exif_metering_mode
exif_scene_type exif_scene
exif_contrast exif_saturation exif_sharpness
exif_body_serial exif_serial
exif_lens_serial
exif_user_comment exif_comment
exif_image_width exif_width
exif_image_height exif_height
exif_max_aperture
exif_digital_zoom exif_dzoom
```

Decode ASCII, integer, signed/unsigned rational, endian, GPS, nested EXIF/GPS IFD, and common enumerated values. Normalize EXIF `YYYY:MM:DD HH:MM:SS` to `YYYY-MM-DD HH:MM:SS`; render rationals readably (`1/100` for exposure or decimal where conventional, `2.8` aperture, numeric focal length), GPS coordinates as signed decimal degrees and altitude numerically, orientation/flash/color-space/exposure-program/metering/white-balance/scene settings as human-readable values. Missing EXIF, unsupported files, or individual missing tags yield empty cells; multiple EXIF fields in one query share the parsed metadata and never fail the row.

## Spec 15

### String and script-detection functions

Functions are case-insensitive and may use parentheses or braces.

| Names | Behavior |
|---|---|
| `LOWER`, `LOWERCASE`, `LCASE` | Unicode lowercase. |
| `UPPER`, `UPPERCASE`, `UCASE` | Unicode uppercase. |
| `LENGTH`, `LEN` | Unicode character count, not UTF-8 byte count. |
| `INITCAP` | Lowercase then title-case the first character of every alphanumeric word; punctuation such as `.` starts a word (`hello.txt` → `Hello.Txt`). |
| `TO_BASE64`, `BASE64` | Standard padded Base64 of UTF-8 bytes. |
| `FROM_BASE64` | Decode standard Base64 to UTF-8; invalid input is empty. |
| `CONCAT(args...)` | String concatenation; empty arguments contribute nothing. |
| `CONCAT_WS(sep, args...)` | Join all value arguments using sep. |
| `LOCATE`, `POSITION` | `LOCATE(haystack, needle [, start])`; return the 1-based character position or 0. Start is 1-based and out-of-range returns 0. Matching is case-sensitive. |
| `SUBSTR`, `SUBSTRING` | `SUBSTR(string [, position [, length]])`; position is 1-based, omission/0 means the whole string, negative positions count backward from the end, omitted length means through the end. |
| `REPLACE` | `REPLACE(string, search, replacement)`, replacing all nonoverlapping occurrences; empty search returns input unchanged. |
| `TRIM`, `LTRIM`, `RTRIM` | Strip Unicode whitespace on both, left, or right side respectively. |
| `COALESCE` | Return the first nonempty/non-null argument, or empty if none, but eagerly evaluate every argument before choosing. Thus `coalesce('', 'chosen', 1 / 0)` reports `Division by zero`, emits no row, and returns 1 rather than emitting `chosen`. |

`CONTAINS(needle)` searches the current file's bytes/text for the exact, case-sensitive substring and returns a boolean. It is usable in `where`; it returns empty/false where file content is unavailable, including archive contexts that do not expose content.

Unicode classifier functions return booleans and have aliases: `CONTAINS_JAPANESE`/`JAPANESE` (any Japanese script), `CONTAINS_HIRAGANA`/`HIRAGANA`, `CONTAINS_KATAKANA`/`KATAKANA`, `CONTAINS_KANA`/`KANA` (either kana), `CONTAINS_KANJI`/`KANJI` (CJK ideographs), and `CONTAINS_GREEK`/`GREEK`.

Nonnumeric/invalid arguments that a pure conversion cannot interpret generally yield an empty cell. Missing required secondary arguments that make a valid call impossible are evaluation errors as detailed in Spec 25.

## Spec 16

### Numeric and random functions

| Names | Behavior |
|---|---|
| `BIN`, `HEX`, `OCT` | Convert an integer to base 2, lowercase base 16, or base 8 text. |
| `ABS` | Absolute numeric value. |
| `POWER`, `POW` | Base raised to exponent; omitted exponent defaults to 0, hence result 1. |
| `SQRT` | Nonnegative square root. |
| `LOG` | `LOG(value [, base])`; default base 10. Base must be positive and not 1; value must be positive. |
| `LN` | Natural logarithm of a positive value. |
| `EXP` | e raised to value. |
| `LEAST`, `GREATEST` | Minimum/maximum numeric argument; one argument returns itself. The first argument must be finite numeric or the result is empty. After a valid first argument, nonnumeric/nonfinite later arguments are ignored. |
| `PI` | IEEE double-precision π. |
| `FLOOR` | Greatest integer ≤ value. |
| `CEIL`, `CEILING` | Smallest integer ≥ value. |
| `ROUND` | Nearest value at optional decimal precision; halfway values round away from zero (`round(-1.5)` is `-2`). Positive precision rounds fractional decimal places and negative precision rounds positions left of the decimal. If an extremely large positive precision overflows its scaling factor, return the original value; if an extremely negative precision underflows it, return 0. |
| `RAND`, `RANDOM` | No args: nonnegative machine integer. One arg: integer in the closed range `[0, max]`; a zero or negative max yields 0. Two args: integer in the closed range from the first bound through the second bound. Repeated calls therefore produce both `0` and `1` for `rand(1)`, and both `4` and `5` for `random(4,5)`. |

Render mathematically integral floating results without a `.0` (for example `sqrt(9)` → `3`); otherwise emit enough decimal precision for normal double calculations. Reject NaN/infinity from square root, power, logarithm, exponent, or arithmetic as an evaluation error rather than printing a nonfinite token.

## Spec 17

### Date/time, duration, and current-user functions

Context-free functions may omit parentheses.

| Names | Behavior/output |
|---|---|
| `CURRENT_DATE`, `CUR_DATE`, `CURDATE` | Current local `YYYY-MM-DD`. |
| `CURRENT_TIME`, `CUR_TIME`, `CURTIME` | Current local `HH:MM:SS`. |
| `CURRENT_TIMESTAMP`, `NOW` | Current local `YYYY-MM-DD HH:MM:SS`. |
| `YEAR`, `MONTH`, `DAY` | Calendar component as integer. |
| `DAYOFWEEK`, `DOW` | Sunday=1 through Saturday=7. |
| `DAYNAME` | English `Sunday` ... `Saturday`. |
| `DAYOFYEAR`, `DOY` | 1 through 366. |
| `DATE_ADD`, `DATEADD` | Add signed integer days and return `YYYY-MM-DD HH:MM:SS`. |
| `DATE_SUB`, `DATESUB` | Subtract signed integer days in the same format. |
| `DATE_DIFF`, `DATEDIFF` | Whole signed day difference, first date minus second. |
| `FROM_UNIXTIME` | Convert integer Unix seconds to local `YYYY-MM-DD HH:MM:SS`. |
| `LAST_DAY`, `LAST_DATE` | Last date of the input month as `YYYY-MM-DD`; leap years apply. |
| `FORMAT_TIME`, `PRETTY_TIME` | Human duration from seconds using compact nonzero `d`, `h`, `m`, `s` components separated by commas: `format_time(3661)` is `1h,1m,1s`, and `pretty_time(61)` is `1m,1s`. |
| `CURRENT_UID`, `CURRENT_GID` | Current real numeric Unix ID. |
| `CURRENT_USER`, `CURRENT_GROUP` | Current real user/group name, with numeric fallback. |

Invalid dates passed to these scalar functions, timestamps outside the platform range, and nonnumeric pure-conversion arguments yield empty. Missing day/date arguments, invalid day counts, out-of-range day counts, and nonnumeric `RAND` bounds are evaluation errors.

## Spec 18

### Date literals and date comparisons

Accept ISO `YYYY-MM-DD`, `YYYY-MM-DD HH`, `YYYY-MM-DD HH:MM`, and `YYYY-MM-DD HH:MM:SS`, including `:` as the date separator only when used consistently. Reject impossible month/day/hour/minute/second values, mixed date separators, and non-leap February 29. When such a value is being coerced for a date-field comparison, rejection is a per-row evaluation error with status 1 and message `Can't parse datetime: VALUE`; this differs from invalid input to a pure date function, which yields empty. A two-digit-year form is handled differently: comparing a date field with `24-02-08` simply matches no rows, writes no diagnostic, and returns 0.

Also accept `today`, `yesterday`, signed relative day integers (`0`, `+N`, `-N`), and common English dates such as month names and `last fri`. By default slash dates are UK day/month (`08/02` is 8 February); `--us-dates` or config switches to month/day.

For `=` and `!=`, an imprecise literal denotes its entire precision interval: a date denotes its whole day, date+hour its whole hour, and date+hour+minute its whole minute. Strict equality and order comparisons use the exact lower-bound instant. Date output and comparisons are second precision and use the process local timezone.

## Spec 19

### Aggregate functions

Required aggregates are:

| Names | Behavior |
|---|---|
| `COUNT(*)` | Count all filtered rows. |
| `COUNT(expr)` | Count every filtered row, even when `expr` is empty/null. Thus `COUNT(ext)` equals `COUNT(*)` when some names have no extension, and `COUNT('')` also equals `COUNT(*)`. |
| `SUM` | Numeric sum. |
| `AVG` | Numeric arithmetic mean. |
| `MIN`, `MAX` | Typed numeric/date minimum/maximum. Nonnumeric strings do not participate; `min(name),max(name)` over names `a`, `B`, and `c` renders two empty cells (`\t\n`). |
| `STDDEV_POP`, `STDDEV`, `STD` | Population standard deviation (divide by N). |
| `STDDEV_SAMP` | Sample standard deviation (divide by N-1). |
| `VAR_POP`, `VARIANCE` | Population variance. |
| `VAR_SAMP` | Sample variance. |

Aggregates may wrap expressions/functions and may be nested inside ordinary scalar functions where the resulting type permits it. Without group-by, any aggregate collapses the filtered rows to one result. With group-by, compute all aggregates per group and allow aggregate expressions in `having` and ordering. An aggregate appearing only in `having` still causes aggregate evaluation. Apply `where` before aggregation, `having` after it, and `limit` after grouping and ordering.

On empty input, `COUNT` is `0`; other aggregates are empty (a tab cell may therefore be blank). The variance and standard-deviation aggregates ignore nonnumeric/nonconvertible expression values without a diagnostic. If no numeric values remain—for example `stddev_pop(name)` over one file named `test.txt`—they emit one empty row and return 0. Population variance/deviation of one numeric value is 0. Sample variance/deviation with fewer than two numeric values is empty. Use floating arithmetic for averages/statistics and do not round except normal rendering.

## Spec 20

### Extended attributes, ACLs, capabilities, and file flags

`has_xattrs` is boolean and `xattr_count` is the platform xattr/alternate-stream count. `HAS_XATTR(name)` tests existence and `XATTR(name)` returns the attribute bytes only when they are valid UTF-8 text; a missing, unreadable, or non-UTF-8 attribute yields false/empty as applicable. They work as selected expressions and predicates.

On Linux, `extattrs` contains set `chattr`/`lsattr` flag letters in conventional order and `has_extattrs` says whether any are set. Support flags `s u c S i a d A E I j t D T e V C x N P F`. `HAS_EXTATTR(letter)` tests one single-character flag; invalid/multicharacter arguments return false.

On Linux, read binary POSIX ACL xattrs `system.posix_acl_access` and `system.posix_acl_default` (little/native-endian version 2 entries). Render comma-separated `user[:qualifier]:rwx`, `group[:qualifier]:rwx`, `mask::rwx`, and `other::rwx`, resolving UID/GID names when possible. `acl`, `has_acl`, `default_acl`, and `has_default_acl` expose these. `has_acl` is `true` for an extended ACL (named user/group or mask beyond base mode). If a regular file has no access ACL, both `has_acl` and `acl` render empty cells, not `false`. If a regular file has no default ACL, or a directory has no default ACL, both `has_default_acl` and `default_acl` likewise render empty cells.

`HAS_ACL_ENTRY`, `ACL_ENTRY`, `HAS_DEFAULT_ACL_ENTRY`, and `DEFAULT_ACL_ENTRY` accept `type[:qualifier]`. Types accept `user/u`, `group/g`, `mask/m`, and `other/o`; mask/other may be written without a colon. When the relevant ACL data exists, the `HAS_` forms return booleans and value forms return the matching entry's permissions/representation or empty. When a file has no ACL xattr at all, both `HAS_ACL_ENTRY(...)` and `ACL_ENTRY(...)` render empty rather than the former rendering `false`.

On Windows, `acl` represents explicit, noninherited DACL ACEs as comma-separated `allow|deny:trustee:permissions`, where permissions are `full`, `modify`, `rx`, `read`, `write`, or a hex mask.

Linux `capabilities`/`caps` decodes `security.capability` revision 1/2/3 xattrs into conventional lowercase capability names and effective/permitted/inheritable suffixes; `has_capabilities`/`has_caps` is boolean. `HAS_CAPABILITY`/`HAS_CAP(name)` tests a named capability such as `cap_net_bind_service`. With no capability xattr, `capabilities`/`caps` and `HAS_CAPABILITY(...)`/`HAS_CAP(...)` render empty, while the `has_capabilities`/`has_caps` fields render `false`. Malformed capability data is handled without an error.

## Spec 21

### Ignore files

Ignore processing only activates when its root option/config is enabled; explicit `no...` root options override it.

The `gitignore`/`git` root options are accepted, but this executable does not exclude filesystem entries using `.gitignore`. Even with a `.git` directory at the root, a root-level `ignored.txt` rule leaves `.git`, `.gitignore`, `ignored.txt`, and `kept.txt` in a depth-1 name-sorted result. Likewise, `build/**/*.log` followed by `!build/deep/keep.log` leaves both `build/a.log` and `build/deep/keep.log` in the result. A following `nogitignore`/`nogit` remains accepted and produces the same unfiltered traversal.

`.hgignore` activates only when a `.hg` directory exists at or above the root. Its default syntax is regexp. Honor `syntax: regexp` and `syntax: glob` changes, comments/blank lines, anchored regex, and glob wildcards/directory paths. A `subinclude:PATH` line does not load or apply the referenced file and produces no diagnostic. For example, an active regexp `.hgignore` containing `^drop[0-9]\.txt$` and `subinclude:more.ignore`, with `more.ignore` containing the glob `*.log`, excludes `drop1.txt` but still emits `a.log` and `more.ignore`. A glob directory pattern ending in `/` or `/**`, such as `build/` or `build/**`, prunes everything below `build` but still emits the `build` directory row itself; the same applies to multiple such directory patterns such as `build/**` and `cache/**`. A bare glob `build` instead excludes the directory row. Invalid directives report a line containing `Error parsing syntax directive` and the root path and are nonfatal. After an invalid syntax directive, do not separately diagnose a following invalid regex in the same file: an `.hgignore` containing `syntax: nonsense` followed by `[invalid` writes only `<root>: Error parsing syntax directive\n`, continues ordinary results, and returns 0. An invalid regex reached under a valid regexp syntax reports `Error creating regex pattern` and its offending pattern. Explicit `nohgignore` searches normally even if files exist.

`.dockerignore` needs no repository marker and may be found in the root or an ancestor. Process lines in order; the last matching rule wins among entries traversal actually reaches. A leading `!` re-includes, while a later ordinary rule may ignore again; `!!name` is a negation whose pattern itself begins `!`. Re-inclusion cannot recover a descendant after an earlier rule prunes traversal of its ancestor: `logs/**` followed by `!logs/deep/keep.log` emits the `logs` directory but neither `logs/a.log` nor `logs/deep/keep.log`. Ignore blank lines and lines whose first nonescaped character is `#`; escaped `\#` and `\!` are literal. Remove one leading `/` for root anchoring, ignore a pattern that becomes empty after slash removal, and treat a trailing `/` as directory-only. A trailing-slash directory pattern such as `build/`, and a descendant pattern such as `fixtures/**`, emit the directory row but prune its descendants. `*` does not cross `/`, `?` matches one non-slash character, and `**` crosses directories (including a trailing `/**`); three or more consecutive stars have the same recursive behavior as `**`. A bare pattern is a basename-prefix match: `node_modules` excludes both a directory named `node_modules` and a file named `node_modules.txt`, but not `xnode_modules.txt`; unlike the trailing-slash/descendant cases, the directly matched directory row is not emitted. Regex punctuation in patterns is literal. Preserve otherwise meaningful leading/trailing whitespace. Invalid patterns report a line containing `Error creating regex while parsing .dockerignore glob`, remain nonfatal, and do not suppress ordinary result rows. The ignore file itself remains an ordinary searchable entry unless a rule excludes it.

## Spec 22

### ZIP archive search

Only ZIP containers need content traversal. Without `archives`/`arc`, a `.zip` is one ordinary filesystem row. With the option, still emit the ZIP row and additionally emit every file member and explicit directory member, including nested members; malformed or empty ZIPs do not crash and generate no virtual members.

In normal tab-separated output, every virtual member row has one automatic leading context cell, before the selected expressions: the source archive path enclosed in square brackets. The path is the discovered archive path in the same absolute/relative form used during traversal. Thus selecting `name,path` can produce `[/tmp/a.zip]\tfile.txt\tdir/file.txt\n`, while ordinary filesystem rows still have only the two requested cells. The same archive-source marker precedes values in the other flat textual formats.

For member rows, `name`, `filename`, `ext`, `path`, `dir`, size/fsize, modification time, mode, `is_dir`, `is_file`, `is_empty`, and extension-category predicates derive from ZIP metadata. `path` is the member name inside the archive and is separate from the automatic context marker. Regular members are files, not symlinks or archives merely because they are inside an archive. Member size is uncompressed bytes. `modified` comes from the ZIP timestamp, while `created` and `accessed` are empty. Decode Unix mode/type from external attributes, including setuid/setgid/sticky and rwx bits. When Windows creator metadata supplies no Unix mode, use the fabricated `-rw-------` mode and permission predicates specified in Spec 11 while leaving ownership cells empty. Content/media/hash/xattr/ACL fields that cannot be obtained are empty or false, not errors. ZIPs created with Windows creator/version metadata and DOS attributes are supported.

## Spec 23

### Configuration

Read a flat TOML file selected by `--config`/`-c`/`/c`. Supported scalar keys are `no_color`, `us_dates`, `gitignore`, `hgignore`, `dockerignore`, `check_for_updates`, and `default_file_size_format`. Supported extension-array keys are `is_archive`, `is_audio`, `is_book`, `is_doc`, `is_font`, `is_image`, `is_source`, and `is_video`; supplying one replaces that category's defaults. Extensions include their leading dots.

If an explicit file cannot be opened, write exactly `Could not open config file. Using default settings.\n` to stderr, use defaults, continue the query, and do not change a successful query's exit code. If TOML is malformed, use defaults and continue without changing an otherwise successful status. Emit the TOML parser's diagnostic verbatim, beginning directly with its parser heading and with no added prefix or contextual text. The input `[broken syntax this is not valid toml` produces this exact stderr, including the final blank line:

```text
TOML parse error at line 1, column 8
  |
1 | [broken syntax this is not valid toml
  |        ^
unclosed table, expected `]`

```

Unknown/misnested keys must not crash.

Without an explicit file, look in the platform user-config location and then for `config.toml` beside the executable; absence is silent and defaults are used. `default_file_size_format` supplies the format used by `fsize`/`hsize` (the automatic binary-unit format is the default), with the all-zero fractional-part omission from Spec 12: `default_file_size_format = "%.2 d"` renders a 1000-byte file as `1 KB`, not with two zero fractional digits. Command-line options override configuration. Do not require or perform a network update check during normal tests.

## Spec 24

### Interactive mode

Interactive mode is a persistent line-oriented REPL on stdin/stdout. It displays exactly `query> ` as its prompt (terminal snapshots see `query>`). Every submitted line is parsed as a command or normal query. After a command/query, print a fresh prompt. EOF, Ctrl-C, `exit`, or `quit` exits successfully. A truly empty line, and a line containing spaces only, is not ignored: it writes `query: Error parsing fields, no selector found\n` to stderr and then re-prompts; ending the session afterward still returns 0. A line containing a horizontal tab is not classified the same way: a tab-only line is processed as a relaxed query, writes one tab followed by a newline to stdout, emits no diagnostic, and then re-prompts.

Commands are:

| Command | Behavior |
|---|---|
| `help` | Print the full help from Spec 1. |
| `pwd` | Print the current absolute working directory. |
| `cd PATH` | Change the process directory persistently; relative paths resolve against current directory. On Linux, `cd /nonexistent_dir_xyz` writes exactly `cd: No such file or directory (os error 2)\n` to stderr. With no path, report `cd: no path specified`. |
| `errors on`, `errors off`, `errors` | Set or report persistent error visibility and print `Errors are ON` or `Errors are OFF`. |
| `debug on`, `debug off`, `debug` | Set or report persistent diagnostics and print `DEBUG IS ON` or `DEBUG IS OFF`. When enabled, parsing/search timing or query diagnostics go to stderr. |

Queries use the current directory established by `cd`, preserve global config/no-color settings, and may use all shell metacharacters without shell escaping. An unrecognized bare line is parsed as a normal relaxed query (and an unknown selected identifier is therefore printed literally).

## Spec 25

### Errors, exit status, and edge behavior

Return 0 for success, including a valid query with no matches, silently accepted unknown alias qualifiers, and informational/interactive commands. Invalid root regular expressions using `regexp`/`regex` are reported but are nonfatal and therefore also return 0 when no other failure occurs. Return 1 if filesystem canonicalization/traversal, file reading, or a validated per-row function/arithmetic evaluation produced an error. Return 2 for command-line/query parse errors. Continue past recoverable filesystem/search errors and emit other valid rows. A selected-expression arithmetic error is instead terminal at its first failing row, as specified in Spec 5. `--no-error` suppresses filesystem/search diagnostics but preserves status; parse diagnostics may still be printed.

Uncolored query-parse diagnostics use `query: MESSAGE\n`. Default color mode wraps the diagnostic source label—`query`, a row path, `expression`, or `result`—in yellow ANSI and leaves the message itself unstyled. Required messages include:

```text
query: Ambiguous offset specified
query: Error parsing BETWEEN operator
query: Error parsing expression, expecting string
query: Error parsing fields, no selector found
query: Error parsing output format
query: Unknown output format
query: Error parsing root options
query: Error parsing offset
query: Error parsing offset, offset value not found
query: Order by field index is out of range
query: Unmatched parenthesis
query: Unterminated quoted string: VALUE
query: could not parse tokens at the end of the query
query: Unknown operator: >>
```

Detect unterminated quotes, missing select fields, missing operands, unbalanced round/curly delimiters, incomplete `AND`/`OR`/`BETWEEN`/`IN`, missing aliases, function trailing commas, malformed limit/offset/depth, and missing/unknown formats. Never panic.

The following malformed forms all return 2 and write exactly `query: could not parse tokens at the end of the query\n` in no-color mode; do not substitute another diagnostic from the list above:

| Malformed form | Case covered |
|---|---|
| `select from` | no selected fields |
| a valid query followed by `limit abc` | nonnumeric limit |
| a valid query followed by `limit -1` | negative limit |
| a valid query followed by `limit 1,abc` | invalid second comma-form limit value |
| `name where size * from .` | multiplication with missing right operand |
| `name where (size + 1 > 0 from .` | arithmetic expression with missing right parenthesis |
| `name where concat(name,) = x from .` | function argument list with a trailing comma |
| `name where size in from .` | `IN` with no list |
| `size as from .` | `AS` with no alias name |
| `{size from .` | unmatched opening curly brace |
| `name where size <> 100 from . limit 1` | misplaced `where` before `from` (even though `<>` itself is a valid operator) |
| `name from 'unfinished` | unterminated quoted root text |

Per-record evaluation diagnostics are prefixed by the row path. An invalid regex used as an expression is instead prefixed by the literal label `expression`; an invalid root regex uses the `result` form from Spec 3. Required validation includes:

```text
LOCATE requires a search substring argument
Could not parse position argument of LOCATE function: VALUE
Could not parse position argument of SUBSTRING function: VALUE
Could not parse length argument of SUBSTRING function: VALUE
REPLACE requires two arguments: search string and replacement string
Could not parse exponent argument of POWER function: VALUE
POWER(RENDERED_BASE, RENDERED_EXP) produces a non-finite result
SQRT of a negative number: VALUE
LOG of a non-positive number: VALUE
LOG with invalid base: VALUE
Could not parse base argument of LOG function: VALUE
LN of a non-positive number: VALUE
EXP(VALUE) overflows to infinity
Could not parse precision argument of ROUND function: VALUE
DATE_ADD requires a second argument (number of days)
DATE_SUB requires a second argument (number of days)
DATE_DIFF requires a second argument (date)
Invalid number of days: VALUE
Number of days out of range: VALUE
Could not parse an argument of RANDOM function: VALUE
Could not parse limit argument of RANDOM function: VALUE
Division by zero
Arithmetic overflow: result is inf
Arithmetic overflow: result is -inf
Can't parse datetime: VALUE
Incorrect regex expression: VALUE
```

Pure one-argument conversions (`BIN`, `HEX`, `OCT`, `ABS`, date extractors, `FROM_UNIXTIME`, `LAST_DAY`, `FORMAT_SIZE`, `FORMAT_TIME`, invalid Base64, and similar) yield an empty value for nonconvertible input unless a specific error above applies. A zero-argument `CONCAT()` yields empty. An unclosed apparent call such as `sum(size` may be tokenized as literal columns (`sum` and `.`) under the relaxed grammar; it must not crash.

The POWER non-finite diagnostic substitutes the rendered operands; `BASE` and `EXP` are not printed literally. In particular, `power(1e308,2)` reports `POWER(` followed by the full 309-digit decimal base (a `1` and 308 zeroes), then `, 2) produces a non-finite result`.

For `RANDOM`/`RAND`, a nonnumeric sole bound or first bound uses `Could not parse an argument of RANDOM function: VALUE`; a nonnumeric second (upper/limit) bound uses `Could not parse limit argument of RANDOM function: VALUE`. Thus `random('bad')` and `random('bad',2)` use the former, while `random(2,'bad')` uses the latter.
