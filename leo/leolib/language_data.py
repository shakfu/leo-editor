# @+leo-ver=5-thin
# @+node:sa.20260906150000.1: * @file ../leolib/language_data.py
"""
Language data: comment delimiters and file extensions.

Pure data, and model data: the readers and writers of external files need to
know that a .py file is Python and that Python comments start with '#', and
they need to know it with no application running. It lived on the LeoApp
singleton, which meant leolib could not read an @file node without booting an
application it has no use for.

leo.leolib.state holds the live copies, and both LeoApp and leolib's minimal
app point their own attributes at those same dicts -- the same objects, not
copies, so a user who extends g.app.language_delims_dict extends the one the
readers consult. The names on g.app stay what the rest of Leo uses.
"""

# @+<< language_data declarations >>
# @+node:sa.20260906150000.2: ** << language_data declarations >>
from __future__ import annotations
# @-<< language_data declarations >>

# @+others
# @+node:sa.20260906150000.3: ** extension_dict
extension_dict: dict[str, str] = {
        # "ada":    "ada",
        "ada":      "ada95",  # modes/ada95.py exists.
        "ahk":      "autohotkey",
        "aj":       "aspect_j",
        "apdl":     "apdl",
        "as":       "actionscript",  # jason 2003-07-03
        "asp":      "asp",
        "awk":      "awk",
        "b":        "b",
        "bas":      "rapidq",  # fil 2004-march-11
        "bash":     "shellscript",
        "bat":      "batch",
        "bbj":      "bbj",
        "bcel":     "bcel",
        "bib":      "bibtex",
        "c":        "c",
        "c++":      "cplusplus",
        "cbl":      "cobol",  # Only one extension is valid: .cob
        "cob":      "cobol",
        "cc":       "cplusplus",
        "cfg":      "config",
        "cfm":      "coldfusion",
        "ch":       "chill",    # Other extensions, .c186,.c286
        "clj":      "clojure",  # 2013/09/25: Fix bug 879338.
        "cljc":     "clojure",
        "cljs":     "clojure",
        "cmd":      "batch",
        "codon":    "codon",
        "coffee":   "coffeescript",
        "comp":     "glsl",
        "conf":     "apacheconf",
        "cpp":      "cplusplus",  # 2020/08/12: was cpp.
        "css":      "css",
        "d":        "d",
        "dart":     "dart",
        "e":        "eiffel",
        "el":       "elisp",
        "eml":      "mail",
        "erl":      "erlang",
        "ex":       "elixir",
        "f":        "fortran",
        "f90":      "fortran90",
        "factor":   "factor",
        "forth":    "forth",
        "frag":     "glsl",
        "g":        "antlr",
        "geom":     "glsl",
        "glsl":     "glsl",
        "go":       "go",
        "groovy":   "groovy",
        "h":        "c",  # 2012/05/23.
        "hh":       "cplusplus",
        "handlebars": "html",  # McNab.
        "hbs":      "html",    # McNab.
        "hs":       "haskell",
        "html":     "html",
        "hx":       "haxe",
        "i":        "swig",
        "i4gl":     "i4gl",
        "icn":      "icon",
        "idl":      "idl",
        "inf":      "inform",
        "info":     "texinfo",
        "ini":      "ini",
        "io":       "io",
        "ipynb":    "jupytext",
        "iss":      "inno_setup",
        "java":     "java",
        "jhtml":    "jhtml",
        "jl":       "julia",
        "jmk":      "jmk",
        "js":       "javascript",  # For javascript import test.
        "jsp":      "javaserverpage",
        "json":     "json",
        # "jsp":      "jsp",
        "ksh":      "kshell",
        "kv":       "kivy",  # PeckJ 2014/05/05
        "latex":    "latex",
        "less":     "css",  # McNab
        "lua":      "lua",  # ddm 13/02/06
        "ly":       "lilypond",
        "m":        "matlab",
        "mak":      "makefile",
        "md":       "md",  # PeckJ 2013/02/07
        "ml":       "ml",  # Also ocaml.
        "mm":       "objective_c",  # Only one extension is valid: .m
        "mod":      "modula3",
        "mpl":      "maple",
        "mqsc":     "mqsc",
        "nqc":      "nqc",
        "nim":      "nim",
        "nsi":      "nsi",  # EKR: 2010/10/27
        # "nsi":      "nsis2",
        "nw":       "noweb",
        "occ":      "occam",
        "otl":      "vimoutline",  # TL 8/25/08 Vim's outline plugin
        "p":        "pascal",
        # "p":      "pop11", # Conflicts with pascal.
        "php":      "php",
        "pike":     "pike",
        "pl":       "perl",
        "pl1":      "pl1",
        "po":       "gettext",
        "pod":      "perlpod",
        "pov":      "povray",
        "prg":      "foxpro",
        "pro":      "prolog",
        "ps":       "postscript",
        "psp":      "psp",
        "pug":      "pug",
        "jade":     "pug",
        "ptl":      "ptl",
        "py":       "python",
        "pyx":      "cython",  # Other extensions, .pyd,.pyi
        # "pyx":    "pyrex",
        # "r":      "r", # modes/r.py does not exist.
        "r":        "rebol",  # jason 2003-07-03
        "rb":       "ruby",  # thyrsus 2008-11-05
        "rest":     "rst",
        "rex":      "objectrexx",
        "rhtml":    "rhtml",
        "rib":      "rib",
        "rs":       "rust",  # EKR: 2019/08/11
        "sas":      "sas",
        "scad":     "openscad",  # PeckJ 2024/11/13
        "scala":    "scala",
        "scm":      "scheme",
        "scpt":     "applescript",
        "sgml":     "sgml",
        "sh":       "shell",  # DS 4/1/04. modes/shell.py exists.
        "shtml":    "shtml",
        "sm":       "smalltalk",
        "splus":    "splus",
        "sql":      "plsql",  # qt02537 2005-05-27
        "sqr":      "sqr",
        "ss":       "ssharp",
        "ssi":      "shtml",
        "sty":      "latex",
        "tcl":      "tcl",  # modes/tcl.py exists.
        # "tcl":    "tcltk",
        "tesc":     "glsl",
        "tese":     "glsl",
        "tex":      "latex",
        # "tex":      "tex",
        "toml":     "toml",
        "tpl":      "tpl",
        "ts":       "typescript",
        "txt":      "plain",
        # "txt":      "text",
        # "txt":      "unknown", # Set when @comment is seen.
        "typ":      "typst",
        "typst":    "typst",
        "uc":       "uscript",
        "v":        "verilog",
        "vbs":      "vbscript",
        "vhd":      "vhdl",
        "vhdl":     "vhdl",
        "vim":      "vim",
        "vtl":      "velocity",
        "w":        "cweb",
        "wiki":     "moin",
        "xml":      "xml",
        "xom":      "omnimark",
        "xsl":      "xsl",
        "yaml":     "yaml",
        "vert":     "glsl",
        "vue":      "javascript",
        "zpt":      "zpt",

        # UPPERCASE VARIANTS: legacy languages that suported, or even expected, uppercase extensions.
        "BAS":      "rapidq",
        "BAT":      "batch",
        "CBL":      "cobol",
        "CMD":      "batch",

        "F":        "fortran",
        "F90":      "fortran90",

        "H":        "c",
        "C":        "cplusplus",
        "CC":       "cplusplus",
        "CPP":      "cplusplus",

        "MAK":      "makefile",
        "P":        "pascal",
        "PL1":      "pl1",
        "PRG":      "foxpro",
        "REX":      "objectrexx",

        "VHD":      "vhdl",
        "VHDL":     "vhdl",

        "ADA":      "ada95",
        "IDL":      "idl",
        "INI":      "ini",
        "MOD":      "modula3",
        "PRO":      "prolog",
        "PS":       "postscript",
        "SQL":      "plsql",
        "TCL":      "tcl",
        "TEX":      "latex",
        "TXT":      "plain",

        "JSON":     "json",
        "MD":       "md",
        "YAML":     "yaml",
        "VIM":      "vim",
        "SH":       "shell",
        "PL":       "perl",
        "RB":       "ruby",


    }  # fmt: skip

# @+node:sa.20260906150000.4: ** language_delims_dict
language_delims_dict: dict[str, str] = {
        # Internally, lower case is used for all language names.
        # Keys are languages, values are strings that contain 1, 2 or 3 delims separated by spaces.
        "actionscript"       : "// /* */",  # jason 2003-07-03
        "ada"                : "--",
        "ada95"              : "--",
        "ahk"                : ";",
        "antlr"              : "// /* */",
        "apacheconf"         : "#",
        "apdl"               : "!",
        "applescript"        : "-- (* *)",
        "asp"                : "<!-- -->",
        "aspect_j"           : "// /* */",
        "assembly_6502"      : ";",
        "assembly_macro32"   : ";",
        "assembly_mcs51"     : ";",
        "assembly_parrot"    : "#",
        "assembly_r2000"     : "#",
        "assembly_x86"       : ";",
        "autohotkey"         : "; /* */",  # TL - AutoHotkey language
        "awk"                : "#",
        "b"                  : "// /* */",
        "batch"              : "REM_",  # Use the REM hack.
        "bbj"                : "/* */",
        "bcel"               : "// /* */",
        "bibtex"             : "%",
        "c"                  : "// /* */",  # C, C++ or objective C.
        "chill"              : "/* */",
        "clojure"            : ";",  # 2013/09/25: Fix bug 879338.
        "cobol"              : "*",
        "codon"              : "#",
        "coldfusion"         : "<!-- -->",
        "coffeescript"       : "#",  # 2016/02/26.
        "config"             : "#",  # Leo 4.5.1
        "cplusplus"          : "// /* */",
        "cpp"                : "// /* */",  # C++.
        "csharp"             : "// /* */",  # C#
        "css"                : "/* */",   # 4/1/04
        "cweb"               : "@q@ @>",  # Use the "cweb hack"
        "cython"             : "#",
        "d"                  : "// /* */",
        "dart"               : "// /* */",  # Leo 5.0.
        "doxygen"            : "#",
        "eiffel"             : "--",
        "elisp"              : ";",
        "erlang"             : "%",
        "elixir"             : "#",
        "factor"             : "!_ ( )",  # Use the rem hack.
        "forth"              : "\\_ _(_ _)",  # Use the "REM hack"
        "fortran"            : "C",
        "fortran90"          : "!",
        "foxpro"             : "&&",
        "gettext"            : "# ",
        "glsl"               : "// /* */",  # Same as C.
        "go"                 : "//",
        "groovy"             : "// /* */",
        "handlebars"         : "<!-- -->",  # McNab: delegate to html.
        "haskell"            : "--_ {-_ _-}",
        "haxe"               : "// /* */",
        "hbs"                : "<!-- -->",  # McNab: delegate to html.
        "html"               : "<!-- -->",
        "i4gl"               : "-- { }",
        "icon"               : "#",
        "idl"                : "// /* */",
        "inform"             : "!",
        "ini"                : ";",
        "inno_setup"         : ";",
        "interlis"           : "/* */",
        "io"                 : "// */",
        "java"               : "// /* */",
        "javascript"         : "// /* */",   # EKR: 2011/11/12: For javascript import test.
        "javaserverpage"     : "<%-- --%>",  # EKR: 2011/11/25 (See also, jsp)
        "jhtml"              : "<!-- -->",
        "jmk"                : "#",
        "json"               : "#",  # EKR: 2020/07/27: Json has no delims. This is a dummy entry.
        "jsp"                : "<%-- --%>",
        "julia"              : "#",
        "jupyter"            : "<%-- --%>",  # Default to markdown?
        "jupytext"           : "#",
        "katex"              : "%",  # Leo 6.8.7.
        "kivy"               : "#",  # PeckJ 2014/05/05
        "kshell"             : "#",  # Leo 4.5.1.
        "latex"              : "%",
        "less"               : "/* */",  # NcNab: delegate to css.
        "lilypond"           : "% %{ %}",
        "lisp"               : ";",  # EKR: 2010/09/29
        "lotos"              : "(* *)",
        "lua"                : "--",  # ddm 13/02/06
        "mail"               : ">",
        "makefile"           : "#",
        "maple"              : "//",
        "markdown"           : "<!-- -->",  # EKR, 2018/03/03: html comments.
        "matlab"             : "%",  # EKR: 2011/10/21
        "mathjax"            : "% <!-- -->",  # EKR: 2024/12/27: latex & html comments.
        "md"                 : "<!-- -->",  # PeckJ: 2013/02/08
        "ml"                 : "(* *)",
        "modula3"            : "(* *)",
        "moin"               : "##",
        "mqsc"               : "*",
        "netrexx"            : "-- /* */",
        "nim"                : "#",
        "noweb"              : "%",  # EKR: 2009-01-30. Use Latex for doc chunks.
        "nqc"                : "// /* */",
        "nsi"                : ";",  # EKR: 2010/10/27
        "nsis2"              : ";",
        "objective_c"        : "// /* */",
        "objectrexx"         : "-- /* */",
        "occam"              : "--",
        "ocaml"              : "(* *)",
        "omnimark"           : ";",
        "pandoc"             : "<!-- -->",
        "openscad"           : "// /* */",  # EKR: 2024/11/13: same as "C".
        "pascal"             : "// { }",
        "perl"               : "#",
        "perlpod"            : "# __=pod__ __=cut__",  # 9/25/02: The perlpod hack.
        "php"                : "// /* */",  # 6/23/07: was "//",
        "pike"               : "// /* */",
        "pl1"                : "/* */",
        "plain"              : "#",  # We must pick something.
        "plsql"              : "-- /* */",  # SQL scripts qt02537 2005-05-27
        "pop11"              : ";;; /* */",
        "postscript"         : "%",
        "povray"             : "// /* */",
        "powerdynamo"        : "// <!-- -->",
        "prolog"             : "% /* */",
        "psp"                : "<!-- -->",
        "ptl"                : "#",
        "pvwave"             : ";",
        "pyrex"              : "#",
        "pug"                : "//-",
        "python"             : "#",
        "r"                  : "#",
        "rapidq"             : "'",  # fil 2004-march-11
        "rebol"              : ";",  # jason 2003-07-03
        "redcode"            : ";",
        "rest"               : ".._",
        "rhtml"              : "<%# %>",
        "rib"                : "#",
        "rpmspec"            : "#",
        "rst"                : ".._",
        "rust"               : "// /* */",
        "ruby"               : "#",  # thyrsus 2008-11-05
        "rview"              : "// /* */",
        "sas"                : "* /* */",
        "scala"              : "// /* */",
        "scheme"             : "; #| |#",
        "sdl_pr"             : "/* */",
        "sgml"               : "<!-- -->",
        "shell"              : "#",  # shell scripts
        "shellscript"        : "#",
        "shtml"              : "<!-- -->",
        "smalltalk"          : '" "',  # Comments are enclosed in double quotes(!!)
        "smi_mib"            : "--",
        "splus"              : "#",
        "sqr"                : "!",
        "squidconf"          : "#",
        "ssharp"             : "#",
        "swig"               : "// /* */",
        "tcl"                : "#",
        "tcltk"              : "#",
        "tex"                : "%",  # Bug fix: 2008-1-30: Fixed Mark Edginton's bug.
        "text"               : "#",  # We must pick something.
        "texinfo"            : "@c",
        "toml"               : "#",
        "tpl"                : "<!-- -->",
        "tsql"               : "-- /* */",
        "typst"              : "//",
        "typescript"         : "// /* */",  # For typescript import test.
        "unknown"            : "#",  # Set when @comment is seen.
        "unknown_language"   : '#--unknown-language--',  # For unknown extensions in @shadow files.
        "uscript"            : "// /* */",
        "vbscript"           : "'",
        "velocity"           : "## #* *#",
        "verilog"            : "// /* */",
        "vhdl"               : "--",
        "vim"                : "\"",
        "vimoutline"         : "#",  # TL 8/25/08 Vim's outline plugin
        "xml"                : "<!-- -->",
        "xsl"                : "<!-- -->",
        "xslt"               : "<!-- -->",
        "yaml"               : "#",
        "zpt"                : "<!-- -->",

        # These aren't real languages, or have no delims...
        # "cvs_commit"         : "",
        # "dsssl"              : "; <!-- -->",
        # "embperl"            : "<!-- -->",  # Internal colorizing state.
        # "freemarker"         : "",
        # "hex"                : "",
        # "jcl"                : "",
        # "patch"              : "",
        # "phpsection"         : "<!-- -->",  # Internal colorizing state.
        # "props"              : "#",         # Unknown language.
        # "pseudoplain"        : "",
        # "relax_ng_compact"   : "#",         # An xml schema.
        # "rtf"                : "",
        # "svn_commit"         : "",
    }  # fmt: skip

# @+node:sa.20260906150000.5: ** language_extension_dict
language_extension_dict: dict[str, str] = {
        "actionscript"  : "as",  # jason 2003-07-03
        "ada"           : "ada",
        "ada95"         : "ada",
        "ahk"           : "ahk",
        "antlr"         : "g",
        "apacheconf"    : "conf",
        "apdl"          : "apdl",
        "applescript"   : "scpt",
        "asp"           : "asp",
        "aspect_j"      : "aj",
        "autohotkey"    : "ahk",  # TL - AutoHotkey language
        "awk"           : "awk",
        "b"             : "b",
        "batch"         : "bat",  # Leo 4.5.1.
        "bbj"           : "bbj",
        "bcel"          : "bcel",
        "bibtex"        : "bib",
        "c"             : "c",
        "chill"         : "ch",   # Only one extension is valid: .c186, .c286
        "clojure"       : "clj",  # 2013/09/25: Fix bug 879338.
        "cobol"         : "cbl",  # Only one extension is valid: .cob
        "codon"         : "codon",
        "coldfusion"    : "cfm",
        "coffeescript"  : "coffee",
        "config"        : "cfg",
        "cplusplus"     : "c++",
        "cpp"           : "cpp",
        "css"           : "css",
        "cweb"          : "w",
        "cython"        : "pyx",  # Only one extension is valid at present: .pyi, .pyd.
        "d"             : "d",
        "dart"          : "dart",
        "eiffel"        : "e",
        "elisp"         : "el",
        "erlang"        : "erl",
        "elixir"        : "ex",
        "factor"        : "factor",
        "forth"         : "forth",
        "fortran"       : "f",
        "fortran90"     : "f90",
        "foxpro"        : "prg",
        "gettext"       : "po",
        "glsl"          : "glsl",  # .comp, .frag, .geom, .tesc, .tese, .vert.
        "go"            : "go",
        "groovy"        : "groovy",
        "haskell"       : "hs",
        "haxe"          : "hx",
        "html"          : "html",
        "i4gl"          : "i4gl",
        "icon"          : "icn",
        "idl"           : "idl",
        "inform"        : "inf",
        "ini"           : "ini",
        "inno_setup"    : "iss",
        "io"            : "io",
        "java"          : "java",
        "javascript"    : "js",   # EKR: 2011/11/12: For javascript import test.
        "javaserverpage": "jsp",  # EKR: 2011/11/25
        "jhtml"         : "jhtml",
        "jmk"           : "jmk",
        "json"          : "json",
        "jsp"           : "jsp",
        "julia"         : "jl",
        "jupytext"      : "ipynb",
        "kivy"          : "kv",   # PeckJ 2014/05/05
        "kshell"        : "ksh",  # Leo 4.5.1.
        "latex"         : "tex",  # 1/8/04
        "lilypond"      : "ly",
        "lua"           : "lua",  # ddm 13/02/06
        "mail"          : "eml",
        "makefile"      : "mak",
        "maple"         : "mpl",
        "matlab"        : "m",
        "md"            : "md",  # PeckJ: 2013/02/07
        "ml"            : "ml",  # Also ocaml.
        "modula3"       : "mod",
        "moin"          : "wiki",
        "mqsc"          : "mqsc",
        "nim"           : "nim",
        "noweb"         : "nw",
        "nqc"           : "nqc",
        "nsi"           : "nsi",  # EKR: 2010/10/27
        "nsis2"         : "nsi",
        "objective_c"   : "mm",  # Only one extension is valid: .m
        "objectrexx"    : "rex",
        "occam"         : "occ",
        "ocaml"         : "ml",
        "omnimark"      : "xom",
        "openscad"      : "scad",  # EKR, per PeckJ 2024/11/13
        "pascal"        : "p",
        "perl"          : "pl",
        "perlpod"       : "pod",
        "php"           : "php",
        "pike"          : "pike",
        "pl1"           : "pl1",
        "plain"         : "txt",
        "plsql"         : "sql",  # qt02537 2005-05-27
        # "pop11"       : "p", # Conflicts with pascal.
        "postscript"    : "ps",
        "povray"        : "pov",
        "prolog"        : "pro",
        "psp"           : "psp",
        "ptl"           : "ptl",
        "pyrex"         : "pyx",
        "pug"           : "pug",
        "python"        : "py",
        "r"             : "r",
        "rapidq"        : "bas",  # fil 2004-march-11
        "rebol"         : "r",  # jason 2003-07-03
        "rhtml"         : "rhtml",
        "rib"           : "rib",
        "rst"           : "rest",
        "ruby"          : "rb",  # thyrsus 2008-11-05
        "rust"          : "rs",  # EKR: 2019/08/11
        "sas"           : "sas",
        "scala"         : "scala",
        "scheme"        : "scm",
        "sgml"          : "sgml",
        "shell"         : "sh",  # DS 4/1/04
        "shellscript"   : "bash",
        "shtml"         : "ssi",  # Only one extension is valid: .shtml
        "smalltalk"     : "sm",
        "splus"         : "splus",
        "sqr"           : "sqr",
        "ssharp"        : "ss",
        "swig"          : "i",
        "tcl"           : "tcl",
        "tcltk"         : "tcl",
        "tex"           : "tex",
        "texinfo"       : "info",
        "text"          : "txt",
        "toml"          : "toml",
        "tpl"           : "tpl",
        "tsql"          : "sql",  # A guess.
        "typescript"    : "ts",
        "typst"         : "typ",
        "unknown"       : "txt",  # Set when @comment is seen.
        "uscript"       : "uc",
        "vbscript"      : "vbs",
        "velocity"      : "vtl",
        "verilog"       : "v",
        "vhdl"          : "vhd",  # Only one extension is valid: .vhdl
        "vim"           : "vim",
        "vimoutline"    : "otl",  # TL 8/25/08 Vim's outline plugin
        "xml"           : "xml",
        "xsl"           : "xsl",
        "xslt"          : "xsl",
        "yaml"          : "yaml",
        "zpt"           : "zpt",
    }  # fmt: skip

# @-others
# @@language python
# @@tabwidth -4
# @-leo
