# WSDL-to-Go executable compatibility specification

The required artifact is a single executable file named exactly `executable`. It is a command-line WSDL 1.1/XML Schema 1.0 to Go source generator. All behavior below is normative, including stream selection, exit status, generated names, file placement, declaration order, and the whitespace called out for generated source. Paths shown as examples stand for the actual path supplied or resolved at run time.

## Spec 1

`executable` uses this command shape and has no subcommands:

```text
executable [options] myservice.wsdl
```

Ordinary words such as `add`, `remove`, `help`, and `version` are input filenames, not commands. The supported options are:

- `-d string`: parent directory under which the package directory is created; default `./`.
- `-i`: disable TLS certificate verification for HTTPS downloads; default false.
- `-make-public`: a boolean controlling whether eligible generated schema identifiers whose XML names begin lowercase are exported; default true. The field-name exception is specified in Spec 9. It accepts a bare flag as true and explicit forms such as `-make-public=true` and `-make-public=false`.
- `-o string`: client output filename; default `myservice.go`.
- `-p string`: generated Go package name and package-directory name; default `myservice`.
- `-v`: print the version and stop.
- `-h` and `--help`: print help and stop.

Short flags cannot be combined: for example, `-iv` is unknown rather than meaning `-i -v`.

## Spec 2

With no arguments, `-h`, or `--help`, exit zero, write nothing to stdout, and write the following text to stderr, followed by a newline. The program-name portion is the invocation path in `argv[0]` (normally `/workspace/executable` or `./executable`). Indentation before each long description consists of four spaces followed by a tab.

```text
Usage: <argv[0]> [options] myservice.wsdl
  -d string
    	Directory under which package directory will be created (default "./")
  -i	Skips TLS Verification
  -make-public
    	Make the generated types public/exported (default true)
  -o string
    	File where the generated code will be saved (default "myservice.go")
  -p string
    	Package under which code will be generated (default "myservice")
  -v	Shows gowsdl version
```

Help takes precedence over other tokens: `--help --unknown` still displays help and exits zero without an unknown-flag error. Help contains no command/subcommand listing.

## Spec 3

`-v` exits zero and writes exactly this one newline-terminated line to stdout, with no help or other output:

```text
🍀  v0.5.0
```

Version does not require an input, and preceding valid flags such as `-i` do not change it. Unknown flags and malformed flag values are diagnosed on stderr using Go's standard `flag`-package wording, followed by the usage text, and exit status 2. Required cases include `flag provided but not defined`, `flag needs an argument: -d` (likewise `-o` and `-p`), and `invalid boolean value "wat" for -make-public`. Flag parsing stops at the first positional argument. Every remaining token is positional, even if it starts with `-`. After successful option/control handling, the WSDL location is always the final raw command-line token, even when that token was consumed as a string option's value. Thus `first.wsdl second.wsdl` processes `second.wsdl`, `first.wsdl -v` attempts to open a file literally named `-v`, and `-p testpkg` (with no separate input) attempts to read `testpkg`. `--` terminates flag parsing and the last following token is the filename.

An invocation with a single empty-string positional argument is an error: write `🍀  WSDL file is required to generate Go proxy` and a newline to stdout and exit 1. This is distinct from the no-argument help case.

## Spec 4

Normal work and handled run-time errors are reported only on stdout, one newline-terminated line per event, each beginning `🍀  ` (clover plus two spaces). For a local resource, emit `🍀  Reading file <absolute-or-cleaned-path>`. For a URL resource, emit `🍀  Downloading file <url>`. Emit a line for the primary WSDL and for every external schema actually loaded. On complete success, the final line is exactly `🍀  Done 👍`, and the exit status is 0. On any handled acquisition, parsing, formatting, or writing error, emit `🍀  <underlying-error-text>`, omit `Done`, and exit 1. The malformed-location panic in Spec 6 is the exception.

Do not prefix handled run-time diagnostics with labels such as `error:` and do not print stack traces for handled errors. A missing local file, for example, produces exactly two stdout lines of this form:

```text
🍀  Reading file /nonexistent/file.wsdl
🍀  open /nonexistent/file.wsdl: no such file or directory
```

The only early error before a read is the literal string equality check between `-o` and the selected WSDL argument. If equal, output only `🍀  Output file cannot be the same WSDL file`, exit 1, and do not modify the input.

## Spec 5

Local inputs may be relative or absolute paths and may contain spaces, hyphens, underscores, `@`, and deep directory components. Resolve a relative primary input against the process working directory and report/read the resulting absolute clean path. Directories used as input fail with the platform's `is a directory` read error. Symbolic links are followed normally, while the logged location remains the resolved import path used to open the link.

An input whose parsed URI has a nonempty scheme is treated as remote, including unsupported schemes. Fetch HTTP and HTTPS with GET. Status 200 supplies the XML bytes; any other status fails as `Received response code <numeric-code>`. Preserve URL escaping in requests. HTTPS verifies certificates unless `-i` was supplied. Network errors retain the standard Go-style context, for example:

```text
🍀  Downloading file http://127.0.0.1:1/nonexistent.wsdl
🍀  Get "http://127.0.0.1:1/nonexistent.wsdl": dial tcp 127.0.0.1:1: connect: connection refused
```

Unsupported `ftp://...` is still logged as a download and fails with `Get "...": unsupported protocol scheme "ftp"`. An out-of-range port retains `invalid port` and the number. For a self-signed localhost certificate having only the legacy Common Name and no subject alternative name, normal TLS fails with `tls: failed to verify certificate: x509: certificate relies on legacy Common Name field, use SANs instead`; with `-i`, the same response is downloaded and parsed successfully.

## Spec 6

Parse WSDL 1.1 documents and their embedded XML Schema documents independent of the XML prefix chosen for WSDL, XSD, or SOAP namespaces. Recursively follow XSD `import` and `include` elements having `schemaLocation` and combine their declarations into one generation model.

For a local containing document, resolve a relative `schemaLocation` against that document's directory, cleaning `.` and `..`; preserve an absolute filesystem path; and recognize an absolute HTTP/HTTPS reference as remote. For a remote containing document, resolve a relative reference with normal URL-reference semantics, including parent traversal. Each imported file is logged before loading. Track already loaded resources so repeated or cyclic imports terminate and declarations are not duplicated. Dependency acquisition is deterministic but does not preserve the interleaving of `xs:import` and `xs:include` in the XML: for each schema, acquire its `xs:import` entries before its `xs:include` entries, preserving source order within each group. Thus a schema containing an include of `query-messagetypes.xsd` before an import of `reflect-messagetypes.xsd` nevertheless attempts `reflect-messagetypes.xsd` first. A missing dependency stops generation and reports both the attempted read and the operating-system error. Multi-level import graphs must work; a graph of one WSDL plus nine unique XSDs produces ten `Reading file` lines.

Declaration collection uses a different order from dependency acquisition: emit declarations from the primary WSDL's embedded schemas first, in their schema order, then declarations from acquired external schemas in acquisition order. For a primary schema containing includes of `graph/common.xsd` and `graph/sub/second.xsd` before a local element `Last`, the read log is primary, `common.xsd`, `second.xsd`, but the generated declarations are `Last`, `Common`, `Second`.

The malformed location `://not-a-url.wsdl` is not treated as a local path. Location parsing leaves a nil URL which is dereferenced: the process writes nothing to stdout, exits 2, and writes a Go panic to stderr beginning `panic: runtime error: invalid memory address or nil pointer dereference`, followed by the nil-pointer stack trace. WSDL documents with no `types`, empty schemas, or structurally unrecognized but well-formed content are accepted and still generate the standard source shells.

## Spec 7

The output package directory is `join(d, p)`. The directory named by `-d` must already exist; attempt to create only the final package directory, with normal directory permissions. If it already exists, reuse it. An error from that directory-creation attempt is ignored and generation proceeds to open the client output, so the client-open error determines the diagnostic. Consequently, `-d /dev/null/impossible` with defaults reports `open /dev/null/impossible/myservice/myservice.go: not a directory`, not a `mkdir` error. A nonexistent `-d out` fails with `no such file or directory`, whereas an existing `out` receives `out/<package>/...`. Nested, spaced, and special-character parent directories work when they already exist.

Inside the package directory, write the client/types source at the filename supplied by `-o` exactly, without adding or changing an extension. Write the server source beside it with `server` prepended to that entire filename: `custom.go` gives `servercustom.go`, and `client` gives `serverclient`. Treat even an absolute-looking `-o` as path text joined beneath the package directory (its leading slash does not redirect output); absent intermediate directories therefore cause a `no such file or directory` write error after the package directory has been created.

Output-open errors display the joined path in the same relative or absolute form passed to the operating system; they do not convert a relative output path to absolute form. With the default relative `-d`, `-p pkg -o /nested/file.go` reports `open pkg/nested/file.go: no such file or directory`, an empty `-o` reports `open pkg: is a directory`, and a regular file at `pkg/blocked` with `-o blocked/client.go` reports `open pkg/blocked/client.go: not a directory`. An absolute `-d` produces an absolute attempted path as in the `/dev/null/impossible` case above.

Write both files by truncating/replacing existing files. Repeated runs on identical input are byte-for-byte deterministic. Separate concurrent processes using different package directories must not share mutable generation state or interfere.

## Spec 8

Both generated files begin exactly:

```go
// Code generated by gowsdl DO NOT EDIT.

package <p>
```

The client file then uses this import block and prelude, in this order, even where a particular declaration is otherwise unused:

```go
import (
	"context"
	"encoding/xml"
	"github.com/hooklift/gowsdl/soap"
	"time"
)

// against "unused imports"
var _ time.Time
var _ xml.Name

type AnyType struct {
	InnerXML string `xml:",innerxml"`
}

type AnyURI string

type NCName string
```

After this prelude, emit global element/simple-type declarations, named complex types, and WSDL port types in the deterministic declaration-collection order specified in Spec 6. Within one schema, retain source order. Use tabs as produced by Go formatting, put a blank line between declarations, and intentionally put a blank line between successive struct fields and interface methods. Generated client and server source must be accepted by `gofmt -e`. Do not add timestamps or input paths to the header.

## Spec 9

Convert XML names to Go identifiers as follows. Replace hyphens with underscores, retain legal Unicode letters (for example `Café`, `日本語`, and `über-name` becomes `Über_name` in public mode), and append `_` when a field name would be a Go keyword (`func` to `Func_`, `type` to `Type_`, and so on). Preserve the rest of the spelling and capitalization rather than applying acronym rewriting: public `MNBArfolyamServiceType` has private implementation name `mNBArfolyamServiceType`.

With the default `-make-public=true`, uppercase the first rune of eligible generated schema identifiers whose source name begins lowercase. With `false`, preserve that lowercase first rune. Source names already beginning uppercase, and WSDL service/port interface names required by public constructors, remain exported. This switch applies to schema type declarations, local simple type names, their wrapper methods, and enum constants. For the XML names `elementWithLocalSimpleType` and enum values `enum1`, default mode generates `ElementWithLocalSimpleTypeEnum1`; false mode generates `elementWithLocalSimpleTypeenum1`.

Ordinary element fields in a named complex-type struct are always exported; `-make-public=false` does not lowercase them. For a named complex type `container` containing elements named `func`, `über-name`, and `日本語`, private mode generates `type container struct`, but its fields remain `Func_`, `Über_name`, and `日本語`, respectively. Their XML and JSON tags retain the original element names. This ordinary-field rule does not override specialized anonymous/local-field spellings explicitly specified elsewhere.

Invalid package names are not silently sanitized. Generation reads/parses first, then Go formatting fails and is reported on stdout. Required messages include `4:17: expected ';', found 'package'` for `-p "invalid package name with spaces"`, and `4:9: expected 'IDENT', found 123i` for `-p 123invalid`.

## Spec 10

Map XML Schema primitive types to Go types at least as follows (namespace prefix is irrelevant):

| XSD type | Go type |
|---|---|
| `string`, `token`, and string-like identifiers | `string` |
| `normalizedString` | `NormalizedString` |
| `boolean` | `bool` |
| `byte` | `int8` |
| `short` | `int16` |
| `int`, `integer` | `int32` |
| `long` | `int64` |
| `unsignedByte` | `byte` |
| `unsignedShort` | `uint16` |
| `unsignedInt` | `uint32` |
| `unsignedLong` | `uint64` |
| `float` | `float32` |
| `double`, `decimal` | `float64` |
| `base64Binary`, `hexBinary` | `[]byte` |
| `date` | `soap.XSDDate` |
| `dateTime` | `soap.XSDDateTime` |
| `time` | `soap.XSDTime` |
| `anyURI` | `AnyURI` |
| `QName` | `QName` |
| unconstrained `anyType`/wildcard content | `AnyType` or an inline raw-XML field as appropriate |

For a global element declared directly with type `date`, `dateTime`, or `time`, also generate `MarshalXML` and `UnmarshalXML` methods delegating by conversion to the corresponding `soap` type. Receiver-variable names are `xd`, `xdt`, and `xt`, respectively. For example, a global element named `StartDate` with type `dateTime` generates:

```go
type StartDate soap.XSDDateTime

func (xdt StartDate) MarshalXML(e *xml.Encoder, start xml.StartElement) error {
	return soap.XSDDateTime(xdt).MarshalXML(e, start)
}

func (xdt *StartDate) UnmarshalXML(d *xml.Decoder, start xml.StartElement) error {
	return (*soap.XSDDateTime)(xdt).UnmarshalXML(d, start)
}
```

Do not generate those methods for a named `xs:simpleType` restriction whose base is `date`, `dateTime`, or `time`. Restrictions named `OnlyDate`, `StartDate`, and `OnlyTime` over those respective primitives generate only these declarations:

```go
type OnlyDate soap.XSDDate

type StartDate soap.XSDDateTime

type OnlyTime soap.XSDTime
```

## Spec 11

A global element with a primitive or named simple type becomes a distinct defined type, for example `type IntValue int32` or `type Status StatusType`. A named XSD simple type restriction becomes a defined Go type over the mapped base type. Pattern, length, minimum/maximum length, and numeric bounds do not produce run-time validators; they do not prevent the type declaration.

For each enumeration facet, emit a typed constant in a single `const` block immediately after its type. Its name is the type name plus a Go identifier derived from the lexical value. Preserve the lexical value exactly, including spaces and the empty string. The empty value's identifier suffix is `EmptyString`; words separated by spaces are concatenated in title form; underscores are retained. Required examples are:

```go
type StatusType string

const (
	StatusTypeActive StatusType = "Active"

	StatusTypeInactive StatusType = "Inactive"
)
```

`DriveTrain` must include `DriveTrainFrontWheelDrive DriveTrain = "Front Wheel Drive"` and `DriveTrainEmptyString DriveTrain = ""`; `SettingsVersion` must include `SettingsVersionV1_14 SettingsVersion = "v1_14"`. Preserve enumeration documentation immediately above its constant as `// <text>`.

An XSD list using the `itemType` attribute becomes a slice defined type, such as `type IntegerListType []int32`. A list whose item type is instead supplied as a nested anonymous `xs:simpleType` is not resolved and becomes `interface{}`; an inline restriction of `xs:token`, for example, generates `type TokenListType interface{}`. An XSD union becomes a string defined type, including unions made of inline member simple types.

## Spec 12

Generate named and anonymous XSD complex types as Go structs. Preserve sequence, choice, and all-group member order in field order. Every ordinary element field receives both tags using its original XML spelling:

```go
Field GoType `xml:"OriginalName,omitempty" json:"OriginalName,omitempty"`
```

All tested fields use `omitempty`, regardless of whether `minOccurs` is zero. A reference to a named complex type is a pointer (`*AddressType`). `maxOccurs="unbounded"` is a slice; complex members are slices of pointers (`[]*ProductType`) and primitives are slices of values (`[]string`, `[]int32`). Recursive and mutually recursive types therefore remain legal, for example `Children []*TreeNode`, `Products []*Product`, and `Category *Category`. Empty complex types become an empty `struct {}` declaration. Choice members are all retained. `xs:any`, nillable members, deeply nested definitions, local anonymous complex types, element `ref`, and attribute-group references must parse without losing their containing type. An element `ref` is represented as a pointer to the referenced global element's wrapper rather than being collapsed to its underlying primitive; a reference to global element `Shared` generates `Shared *Shared`. An `xs:attributeGroup ref` is accepted but contributes no fields to the generated struct.

Where a named complex type is used only under one distinct element name, make `XMLName xml.Name` its first field with tag `xml:"<schema-target-namespace> <element-name>"`. Request/response global elements always have this field. If the same named complex type is used by differently named elements, omit `XMLName` from that named type because no single name represents it. Thus a type used as both `Address`, `HomeAddress`, `WorkAddress`, and `ShippingAddress` has no `XMLName`, while a type used only as `Contact` has one. For example:

```go
type Query struct {
	XMLName xml.Name `xml:"http://example.com/multiport Query"`

	Text string `xml:"text,omitempty" json:"text,omitempty"`
}
```

When a global element references a named complex type, also emit a defined wrapper such as `type Address AddressType`; do not use Go's `=` alias syntax.

## Spec 13

Emit attributes after element/content fields. An attribute field uses its mapped value type and:

```go
Field T `xml:"<schema-target-namespace> originalName,attr,omitempty" json:"originalName,omitempty"`
```

Resolve direct named attributes and direct `ref` attributes. As specified in Spec 12, an `attributeGroup` reference itself is ignored rather than expanded. Inline anonymous simple-content structs use a `Value` field tagged ``xml:",chardata" json:"-,"`` followed by their attributes. A named `simpleContent` extension similarly has `Value <base-type>` first. A `complexContent` extension embeds the base as an anonymous pointer field, then emits extension elements and direct attributes, for example:

```go
type ExtendedPersonType struct {
	XMLName xml.Name `xml:"http://test.example.com/ ExtendedPerson"`

	*BasePersonType

	Age int32 `xml:"Age,omitempty" json:"Age,omitempty"`

	Id string `xml:"http://test.example.com/ id,attr,omitempty" json:"id,omitempty"`
}
```

The `ResponseStatus` pattern—an unbounded anonymous simple-content element with an attribute—must become a slice of anonymous structs containing `Value string` and the attribute field, with a separately resolved outer attribute.

## Spec 14

Element, enumeration, and WSDL operation documentation are preserved as Go comments without swallowing or commenting out the following declaration. Element documentation is emitted as one or more `//` lines immediately above the field. Enumeration documentation is immediately above the constant. WSDL operation documentation is emitted as `/* <text> */` immediately before the non-context interface method. Documentation attached to a named `xs:complexType` is not emitted; for example, `Documentation for WorkerObjectIDType` does not produce a comment above `type WorkerObjectIDType struct`. Maintain blank lines in the canonical style. In particular, documentation text `this is a comment` must be followed by a live `GetInfoResult string` field, never combined into one commented-out line.

## Spec 15

Build operations by resolving WSDL `portType` operations through `message` references to each message part's XSD `element`, then use that element's resolved Go data type in method signatures rather than its generated global-element wrapper. Consequently, a part referring to global element `OnlyResponse` declared directly as `xs:string` produces response type `*string`, and a part referring to `OnlyRequest` declared the same way produces request type `*string`. An absent side still uses `*EmptyString`. Anonymous complex global elements resolve to their element-named struct types, as in `*TradePriceRequest` and `*TradePrice`. Resolve the operation's SOAP action from the matching SOAP binding operation. Generate one distinct public Go interface per WSDL port type, in WSDL order. For every operation, generate both methods:

```go
Operation(request *InputElement) (*OutputElement, error)

OperationContext(ctx context.Context, request *InputElement) (*OutputElement, error)
```

Then generate a private implementation struct containing `client *soap.Client` and an exported constructor returning the interface:

```go
type stockQuotePortType struct {
	client *soap.Client
}

func NewStockQuotePortType(client *soap.Client) StockQuotePortType {
	return &stockQuotePortType{
		client: client,
	}
}
```

Do this even for port types with no operations, producing an empty interface plus implementation and constructor.

## Spec 16

Each context-aware client implementation allocates the output, calls the SOAP client with the binding action, propagates an error, and returns the response. The convenience method calls it with `context.Background()`. The exact shape is:

```go
func (service *stockQuotePortType) GetLastTradePriceContext(ctx context.Context, request *TradePriceRequest) (*TradePrice, error) {
	response := new(TradePrice)
	err := service.client.CallContext(ctx, "http://example.com/GetLastTradePrice", request, response)
	if err != nil {
		return nil, err
	}

	return response, nil
}

func (service *stockQuotePortType) GetLastTradePrice(request *TradePriceRequest) (*TradePrice, error) {
	return service.GetLastTradePriceContext(
		context.Background(),
		request,
	)
}
```

Use each operation's own action. A missing `soapAction` is represented by the literal Go string `"''"` (two single-quote characters), not the empty Go string. If WSDL input or output is absent, use `*EmptyString` as the respective request or response type, while retaining the same two-method implementation template.

## Spec 17

If an operation declares faults, insert this documentation before its WSDL documentation and non-context method in the interface; list each WSDL operation-fault `name` attribute in source order. Do not resolve the fault message part to its schema element/type. For fault names `division` and `invalid`, the output is:

```go
// Error can be either of the following types:
//
//   - division
//   - invalid
/* Divides two numbers, throws faults on errors */
Divide(request *Divide) (*DivideResponse, error)
```

Fault declarations themselves are normal generated schema types. Multiple port types and multiple operations must not be merged or dropped. Realistic documents must yield all methods and context variants; examples include Ferry operations `GetActiveScheduledSeasons`, `GetAllAlerts`, `GetAllRouteDetails`, `GetAllRoutes`, `GetAllTerminals`, and `GetCacheFlushDate`, and EPCIS operations `GetQueryNames` and `Subscribe`.

## Spec 18

The server filename contains the standard header/package, then exactly these imports in order:

```go
import (
	"encoding/xml"
	"errors"
	"fmt"
	"net/http"
	"reflect"
	"strings"
)
```

Embed the complete original primary WSDL bytes, preserving their text, as a raw string:

```go
var wsdl = `<original WSDL text>`
```

The declaration order after the embedded WSDL is fixed: `WSDLUndefinedError`, `SOAPEnvelopeRequest`, `SOAPBodyRequest`, `SOAPEnvelopeResponse`, `NewSOAPEnvelopResponse`, `Fault`, `SOAPBodyResponse`, the per-operation handler methods, `(*SOAPEnvelopeRequest).call`, and `Endpoint`. First declare exactly:

```go
var WSDLUndefinedError = errors.New("Server was unable to process request. --> Object reference not set to an instance of an object.")

type SOAPEnvelopeRequest struct {
	XMLName xml.Name `xml:"http://schemas.xmlsoap.org/soap/envelope/ Envelope"`
	Body    SOAPBodyRequest
}
```

The generated `SOAPBodyRequest` from Spec 19 comes immediately after `SOAPEnvelopeRequest`. Only then declare:

```go
type SOAPEnvelopeResponse struct {
	XMLName    xml.Name `xml:"soap:Envelope"`
	PrefixSoap string   `xml:"xmlns:soap,attr"`
	PrefixXsi  string   `xml:"xmlns:xsi,attr"`
	PrefixXsd  string   `xml:"xmlns:xsd,attr"`

	Body SOAPBodyResponse
}
```

`NewSOAPEnvelopResponse` (retain the spelling `Envelop`) immediately follows `SOAPEnvelopeResponse` and is formatted exactly as follows:

```go
func NewSOAPEnvelopResponse() *SOAPEnvelopeResponse {
	return &SOAPEnvelopeResponse{
		PrefixSoap: "http://schemas.xmlsoap.org/soap/envelope/",
		PrefixXsd:  "http://www.w3.org/2001/XMLSchema",
		PrefixXsi:  "http://www.w3.org/2001/XMLSchema-instance",
	}
}
```

The `Fault` declaration from Spec 19 follows this constructor, and the generated `SOAPBodyResponse` follows `Fault`.

## Spec 19

`SOAPBodyRequest` starts with its SOAP Body `XMLName`, then has one pointer field for every operation input. Both the field identifier and pointed-to type are the resolved Go input type from Spec 15, and the field is tagged ``xml:,omitempty``. `SOAPBodyResponse` starts with ``XMLName xml.Name `xml:"soap:Body"` `` and ``Fault *Fault `xml:",omitempty"` ``, then has a field with the same identifier as its request field but pointing to the resolved Go output type and tagged ``xml:",omitempty"``. Thus an anonymous complex input/output pair produces `TradePriceRequest *TradePrice`, but global elements `Query`, `QueryResponse`, `AdminCommand`, and `AdminCommandResponse` all declared directly as `xs:string` resolve to `string`: three operations using those elements produce three request fields spelled `string *string`, three response fields spelled `string *string`, and three methods named `stringFunc`. The generator does not deduplicate or rename those declarations.

Use the SOAP 1.1 fault shape:

```go
type Fault struct {
	XMLName xml.Name `xml:"SOAP-ENV:Fault"`
	Space   string   `xml:"xmlns:SOAP-ENV,omitempty,attr"`

	Code   string `xml:"faultcode,omitempty"`
	String string `xml:"faultstring,omitempty"`
	Actor  string `xml:"faultactor,omitempty"`
	Detail string `xml:"detail,omitempty"`
}
```

For each request field, generate a method on `*SOAPBodyRequest` named `<ResolvedInputType>Func`, accepting `*ResolvedInputType`, returning `(*ResolvedOutputType, error)`, and initially containing only `return nil, WSDLUndefinedError`.

For a single operation whose resolved input and output types are `TradePriceRequest` and `TradePrice`, `SOAPBodyRequest` is exactly:

```go
type SOAPBodyRequest struct {
	XMLName xml.Name `xml:"http://schemas.xmlsoap.org/soap/envelope/ Body"`

	TradePriceRequest *TradePriceRequest `xml:,omitempty`
}
```

As ordered in Spec 18, `SOAPEnvelopeResponse`, its constructor, and `Fault` intervene. `SOAPBodyResponse` and the handler then are exactly:

```go
type SOAPBodyResponse struct {
	XMLName xml.Name `xml:"soap:Body"`
	Fault   *Fault   `xml:",omitempty"`

	TradePriceRequest *TradePrice `xml:",omitempty"`
}

func (service *SOAPBodyRequest) TradePriceRequestFunc(request *TradePriceRequest) (*TradePrice, error) {
	return nil, WSDLUndefinedError
}
```

## Spec 20

Generate server dispatch with an exported `func Endpoint(w http.ResponseWriter, r *http.Request)` that constructs `SOAPEnvelopeRequest{}` and calls its `call(w, r)` method. The `call` method must:

1. add `Content-Type: text/xml; charset=utf-8`;
2. on GET, write the embedded WSDL bytes and return;
3. construct `NewSOAPEnvelopResponse()` and defer a recover block that turns panics into a SOAP fault (`Space` envelope namespace, `Code` `soap:Server`, and both `Detail` and `String` from `fmt.Sprintf("%v", recovered)`), then XML-encodes the response;
4. reject a content type containing `application/soap+xml` by panicking with `Could not find an appropriate Transport Binding to invoke.`;
5. XML-decode the request body;
6. reflect over `service.Body`, select the first non-nil pointer field, find `name + "Func"` with `val.Addr().MethodByName`, and invoke it as `m.Call([]reflect.Value{field})`;
7. set the identically named response-body field from a successful first return value, or panic with the handler error; and
8. panic with `WSDLUndefinedError` if no request field or handler is found.

Use the exact structures and flow above so the generated server is deterministic and valid Go.

More precisely, after the per-operation `<InputElement>Func` methods, instantiate this exact formatted template (placeholders denote generated identifiers only):

```go
func (service *SOAPEnvelopeRequest) call(w http.ResponseWriter, r *http.Request) {
	w.Header().Add("Content-Type", "text/xml; charset=utf-8")
	val := reflect.ValueOf(&service.Body).Elem()
	n := val.NumField()
	var field reflect.Value
	var name string
	find := false

	if r.Method == http.MethodGet {
		w.Write([]byte(wsdl))
		return
	}

	resp := NewSOAPEnvelopResponse()
	defer func() {
		if r := recover(); r != nil {
			resp.Body.Fault = &Fault{}
			resp.Body.Fault.Space = "http://schemas.xmlsoap.org/soap/envelope/"
			resp.Body.Fault.Code = "soap:Server"
			resp.Body.Fault.Detail = fmt.Sprintf("%v", r)
			resp.Body.Fault.String = fmt.Sprintf("%v", r)
		}
		xml.NewEncoder(w).Encode(resp)
	}()

	header := r.Header.Get("Content-Type")
	if strings.Index(header, "application/soap+xml") >= 0 {
		panic("Could not find an appropriate Transport Binding to invoke.")
	}

	err := xml.NewDecoder(r.Body).Decode(service)
	if err != nil {
		panic(err)
	}

	for i := 0; i < n; i++ {
		field = val.Field(i)
		name = val.Type().Field(i).Name
		if field.Kind() != reflect.Ptr {
			continue
		}
		if field.IsNil() {
			continue
		}
		if field.IsValid() {
			find = true
			break
		}
	}

	if !find {
		panic(WSDLUndefinedError)
	} else {
		m := val.Addr().MethodByName(name + "Func")
		if !m.IsValid() {
			panic(WSDLUndefinedError)
		}

		vals := m.Call([]reflect.Value{field})
		if vals[1].IsNil() {
			reflect.ValueOf(&resp.Body).Elem().FieldByName(name).Set(vals[0])
		} else {
			panic(vals[1].Interface())
		}
	}

}

func Endpoint(w http.ResponseWriter, r *http.Request) {
	request := SOAPEnvelopeRequest{}
	request.call(w, r)
}
```

## Spec 21

For the canonical MNB-style input whose target namespace is `http://www.mnb.hu/webservices/`, containing global `GetInfo`, `GetInfoResponse`, local-enum element `elementWithLocalSimpleType`, date-time element `startDate`, `ResponseStatus`, and port type `MNBArfolyamServiceType`, the default client declaration body after the standard prelude is normatively:

```go
type GetInfo struct {
	XMLName xml.Name `xml:"http://www.mnb.hu/webservices/ GetInfo"`

	// comment

	Id string `xml:"Id,omitempty" json:"Id,omitempty"`
}

type GetInfoResponse struct {
	XMLName xml.Name `xml:"http://www.mnb.hu/webservices/ GetInfoResponse"`

	// this is a comment
	GetInfoResult string `xml:"GetInfoResult,omitempty" json:"GetInfoResult,omitempty"`
}

type ElementWithLocalSimpleType string

const (

	// First enum value
	ElementWithLocalSimpleTypeEnum1 ElementWithLocalSimpleType = "enum1"

	// Second enum value
	ElementWithLocalSimpleTypeEnum2 ElementWithLocalSimpleType = "enum2"
)

type StartDate soap.XSDDateTime

func (xdt StartDate) MarshalXML(e *xml.Encoder, start xml.StartElement) error {
	return soap.XSDDateTime(xdt).MarshalXML(e, start)
}

func (xdt *StartDate) UnmarshalXML(d *xml.Decoder, start xml.StartElement) error {
	return (*soap.XSDDateTime)(xdt).UnmarshalXML(d, start)
}

type ResponseStatus struct {
	XMLName xml.Name `xml:"http://www.mnb.hu/webservices/ ResponseStatus"`

	Status []struct {
		Value string `xml:",chardata" json:"-,"`

		Code string `xml:"http://www.mnb.hu/webservices/ code,attr,omitempty" json:"code,omitempty"`
	} `xml:"status,omitempty" json:"status,omitempty"`

	ResponseCode string `xml:"http://www.mnb.hu/webservices/ responseCode,attr,omitempty" json:"responseCode,omitempty"`
}
```

It is followed by the interface/implementation for `GetInfoSoap` using the templates above and action `"''"`. Under `-make-public=false`, this output is byte-identical except: `ElementWithLocalSimpleType` becomes `elementWithLocalSimpleType`; its constants become `elementWithLocalSimpleTypeenum1/enum2` with the lowercase type; `StartDate` and its receiver types become `startDate`; and the outer `Status` field becomes `status`. `GetInfo`, `GetInfoResponse`, `ResponseStatus`, `Code`, `ResponseCode`, and the public interface stay as shown.

## Spec 22

For simple-schema inputs, the declaration stream must match these compatibility rules exactly:

- Always include the Spec 8 prelude first.
- Primitive global elements named `StringValue`, `IntValue`, `LongValue`, `BooleanValue`, `FloatValue`, `DoubleValue`, `Base64BinaryValue`, `HexBinaryValue`, `DecimalValue`, `ByteValue`, `ShortValue`, `UnsignedIntValue`, `UnsignedLongValue`, `AnyURIValue`, and `QNameValue` become the corresponding defined types from Spec 10, in input order.
- `DateValue`, `DateTimeValue`, and `TimeValue` additionally receive the wrapper methods from Spec 10 immediately after each declaration.
- Named restrictions are emitted before global-element wrappers. Thus `StatusType`, its `const` block, `ZipCodeType`, `UsernameType`, `AgeType`, `CountryCodeType` precede `Status StatusType`, `ZipCode ZipCodeType`, `Username UsernameType`, `Age AgeType`, `CountryCode CountryCodeType`.
- Named complex types are emitted with their fields in schema order. Complex-content bases are embedded; list and union declarations precede their element wrappers.
- Finally emit the empty or populated service interface, private implementation, constructor, and methods.

Do not introduce validation helpers, alternative JSON casing, pointer primitives merely because `minOccurs=0`, Go alias `=`, extra imports, or extra declarations; complete-file comparisons depend on this declaration order and canonical formatting.

## Spec 23

XML decoding errors are fatal before any output directory is created. Empty input or plain non-XML text reports `EOF`. Preserve `encoding/xml`-style line-aware errors, for example `XML syntax error on line 3: unexpected EOF` and `XML syntax error on line 4: element <unclosed-tag> closed by </definitions>`. A downloaded non-WSDL payload is parsed by the same path. A well-formed XML document need not actually use the `.wsdl` extension and may generate an empty shell.

Strictly parse XSD boolean attributes such as element `nillable` and complex-type `abstract` and `mixed` with the accepted lexical forms `true`, `false`, `1`, and `0`. Any other value aborts at the first such attribute with exactly the underlying form `strconv.ParseBool: parsing "<value>": invalid syntax`. Do not continue to later invalid attributes or write output.

Errors opening an external include/import retain the resolved full path and OS phrase (`no such file or directory`, `not a directory`, or `is a directory`). Output directory/file errors retain the attempted joined path exactly as described in Spec 7, including its relative form when `-d` and `-p` are relative. The initial WSDL read line and all successful preceding dependency-read lines remain in stdout.

## Spec 24

The generator must handle the full scale and variety of ordinary WSDL/XSD inputs rather than keying only on sample filenames. Required supported constructs include namespace-qualified and default-namespace WSDL/XSD, inline and named simple/complex types, sequences/choices/all groups, direct attributes and direct attribute references, restrictions and enumerations, simple/complex content extension, lists, unions, recursive types, multiple schemas, multiple bindings/port types, SOAP actions, faults, and large recursive import graphs, subject to the precise compatibility limitations above for attribute groups and inline list item types.

It must finish comfortably within normal CLI test timeouts and generate syntactically valid Go for large real-world documents with hundreds of types and operations. In particular, data-driven parsing must naturally produce recognizable schema names such as `WorkerObjectIDType` from Workday-style schemas, `DriveTrain` from automotive schemas, and `EPCISQueryDocumentType`, `PartnerIdentification`, `Poll`, and `EPCISServicePortType` plus its constructor from EPCIS schemas. Large EC2-style input must yield more than 50 type declarations; VirtualBox-style input more than 200 and over 10 KB of client source. Preserve enumeration values and the supported element, enumeration, and operation documentation described in Spec 14; omit named-complex-type documentation as specified there.
