[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ReceiptSchema = 'phase40-comparison-launch-receipt-v3'
$FinalAuthorityRelative = 'data/models/phase40/final-comparison-authority.json'
$RequestRelative = 'data/models/phase40/full-run-request.json'
$AmendmentRelative = 'data/models/phase40/two-full-model-scope-amendment.json'
$PhoBertCapsuleRootRelative = 'data/models/phase40/request-authority-roots/phobert-v12'
$PhoBertRequestRelative = "$PhoBertCapsuleRootRelative/data/models/phase40/full-run-request.json"
$PhoBertCapsuleAssetRelatives = @(
    "$PhoBertCapsuleRootRelative/data/models/phase40/source/phase40-source.zip",
    "$PhoBertCapsuleRootRelative/data/models/phase40/source/phase40-source-manifest.json",
    "$PhoBertCapsuleRootRelative/data/models/phase40/input/phase40-train-validation.zip"
)
$ReceiptRelative = 'data/models/phase40/comparison-launch-receipt.json'
$ClaimRelative = 'data/models/phase40/comparison-launch-capability.claim'
$CapabilityTtlSeconds = 60
$CapabilityNonceEnvironment = 'PHASE40_COMPARISON_LAUNCH_NONCE'
$CapabilityLauncherPidEnvironment = 'PHASE40_COMPARISON_LAUNCHER_PID'
$CapabilityPendingHashEnvironment = 'PHASE40_COMPARISON_PENDING_RECEIPT_SHA256'
$LauncherRelative = 'scripts/phase40_comparison_launcher.ps1'
$TreeDomain = "phase40-comparison-finalizer-source-v1`0"
$AllowedHostSha256 = '057a2754877cd356159ea891883179f8620ffdc89d3c70d2c4d1f3ba3f6c49b0'
$AllowedHostVersion = '7.6.1'
$AllowedPythonSha256 = 'dc7ecf75280678175b4f931ce05f1ef9c10d48984399ca7de6beee69d71bcb1b'
$AllowedPythonVersion = '3.13.13'
$ExpectedActiveRunIds = @(
    'phase40-qwen-qlora-full-seed42-v1',
    'phase40-phobert-full-seed42-v12'
)
$ExpectedActiveRoots = @(
    'data/models/phase40/full/qwen-qlora',
    'data/models/phase40/full/phobert'
)
$ExpectedFinalizerSourcePaths = @(
    'pyproject.toml',
    'scripts/phase40_comparison_launcher.ps1',
    'src/__init__.py',
    'src/config/__init__.py',
    'src/config/settings.py',
    'src/data_pipeline/__init__.py',
    'src/data_pipeline/schemas.py',
    'src/model_adaptation/__init__.py',
    'src/model_adaptation/catalog.py',
    'src/model_adaptation/data.py',
    'src/model_adaptation/phase40_callbacks.py',
    'src/model_adaptation/phase40_comparison_launch.py',
    'src/model_adaptation/phase40_contract.py',
    'src/model_adaptation/phase40_evidence.py',
    'src/model_adaptation/phase40_final_authority.py',
    'src/model_adaptation/phase40_finalize.py',
    'src/model_adaptation/phase40_gguf.py',
    'src/model_adaptation/phase40_graphs.py',
    'src/model_adaptation/phase40_handoff.py',
    'src/model_adaptation/phase40_metrics.py',
    'src/model_adaptation/phase40_modes.py',
    'src/model_adaptation/phase40_phobert_release.py',
    'src/model_adaptation/phase40_production_authorities.py',
    'src/model_adaptation/phase40_release_authorities.py',
    'src/model_adaptation/phase40_runtime_materialize.py',
    'src/model_adaptation/phobert_training.py',
    'src/model_adaptation/pilot.py',
    'src/model_adaptation/prompts.py',
    'src/model_adaptation/registry.py',
    'src/model_adaptation/schemas.py',
    'src/model_adaptation/training.py',
    'src/runtime/__init__.py',
    'src/runtime/contracts.py'
)
$FinalizerArguments = @(
    '-s',
    '-B',
    '-m',
    'src.model_adaptation.phase40_finalize',
    '--repo-root',
    '.',
    '--output-root',
    'data/models/phase40',
    '--bundle-root',
    'phase40-qwen-qlora-full-seed42-v1=data/models/phase40/full/qwen-qlora',
    '--bundle-root',
    'phase40-phobert-full-seed42-v12=data/models/phase40/full/phobert',
    '--gpu-identity',
    'phase40-qwen-qlora-full-seed42-v1=NVIDIA GeForce RTX 5050 Laptop GPU',
    '--gpu-identity',
    'phase40-phobert-full-seed42-v12=NVIDIA GeForce RTX 5050 Laptop GPU'
)

function Get-LowerSha256Bytes {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [byte[]]$Payload
    )
    return [System.Convert]::ToHexString(
        [System.Security.Cryptography.SHA256]::HashData($Payload)
    ).ToLowerInvariant()
}

function Get-LowerSha256Text {
    param([Parameter(Mandatory = $true)][string]$Text)
    return Get-LowerSha256Bytes -Payload (
        [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
    )
}

function Get-CombinedSha256 {
    param(
        [Parameter(Mandatory = $true)][byte[]]$Prefix,
        [Parameter(Mandatory = $true)][byte[]]$Payload
    )
    $Combined = [byte[]]::new($Prefix.Length + $Payload.Length)
    [System.Buffer]::BlockCopy($Prefix, 0, $Combined, 0, $Prefix.Length)
    [System.Buffer]::BlockCopy($Payload, 0, $Combined, $Prefix.Length, $Payload.Length)
    return Get-LowerSha256Bytes -Payload $Combined
}

function Assert-NoDuplicateJsonProperties {
    param(
        [Parameter(Mandatory = $true)][System.Text.Json.JsonElement]$Element,
        [string]$Context = '$'
    )
    if ($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Object) {
        $Names = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::Ordinal
        )
        foreach ($Property in $Element.EnumerateObject()) {
            foreach ($Character in $Property.Name.ToCharArray()) {
                if ([char]::IsSurrogate($Character)) {
                    throw "Supplementary Unicode JSON property names are forbidden at $Context"
                }
            }
            if (-not $Names.Add($Property.Name)) {
                throw "Duplicate JSON property at ${Context}: $($Property.Name)"
            }
            Assert-NoDuplicateJsonProperties `
                -Element $Property.Value `
                -Context "${Context}.$($Property.Name)"
        }
    }
    elseif ($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Array) {
        $Index = 0
        foreach ($Item in $Element.EnumerateArray()) {
            Assert-NoDuplicateJsonProperties -Element $Item -Context "${Context}[$Index]"
            $Index++
        }
    }
}

function ConvertTo-PythonCanonicalJsonNumber {
    param(
        [Parameter(Mandatory = $true)]
        [System.Text.Json.JsonElement]$Element
    )
    $Raw = $Element.GetRawText()
    if ($Raw -cnotmatch '[.eE]') {
        if ($Raw -ceq '-0') {
            return '0'
        }
        return $Raw
    }

    $Invariant = [System.Globalization.CultureInfo]::InvariantCulture
    $Formatted = $Element.GetDouble().ToString('R', $Invariant)
    $Negative = $Formatted.StartsWith('-', [System.StringComparison]::Ordinal)
    $Unsigned = if ($Negative) { $Formatted.Substring(1) } else { $Formatted }
    $Sign = if ($Negative) { '-' } else { '' }

    if ($Unsigned.Contains('E')) {
        $Parts = $Unsigned.Split([char]'E', 2)
        $Mantissa = $Parts[0]
        $Exponent = [int]::Parse(
            $Parts[1],
            [System.Globalization.NumberStyles]::AllowLeadingSign,
            $Invariant
        )
        if ($Exponent -ge -4 -and $Exponent -lt 16) {
            $Digits = $Mantissa.Replace('.', '')
            $DecimalPosition = $Exponent + 1
            if ($DecimalPosition -le 0) {
                $Fixed = '0.' + ('0' * (-$DecimalPosition)) + $Digits
            }
            elseif ($DecimalPosition -ge $Digits.Length) {
                $Fixed = $Digits + ('0' * ($DecimalPosition - $Digits.Length)) + '.0'
            }
            else {
                $Fixed = $Digits.Insert($DecimalPosition, '.')
            }
            return $Sign + $Fixed
        }
        $ExponentSign = if ($Exponent -ge 0) { '+' } else { '-' }
        $ExponentDigits = [Math]::Abs($Exponent).ToString($Invariant).PadLeft(2, '0')
        return $Sign + $Mantissa + 'e' + $ExponentSign + $ExponentDigits
    }

    $Point = $Unsigned.IndexOf('.')
    $IntegerPart = if ($Point -ge 0) { $Unsigned.Substring(0, $Point) } else { $Unsigned }
    $FractionPart = if ($Point -ge 0) { $Unsigned.Substring($Point + 1) } else { '' }
    $CombinedDigits = $IntegerPart + $FractionPart
    $FirstNonzero = -1
    for ($Index = 0; $Index -lt $CombinedDigits.Length; $Index++) {
        if ($CombinedDigits[$Index] -cne '0') {
            $FirstNonzero = $Index
            break
        }
    }
    if ($FirstNonzero -lt 0) {
        return $Sign + '0.0'
    }
    $Exponent = if ($IntegerPart -cne '0') {
        $IntegerPart.Length - 1
    }
    else {
        -($FirstNonzero - $IntegerPart.Length + 1)
    }
    if ($Exponent -ge 16 -or $Exponent -lt -4) {
        $Digits = $CombinedDigits.Substring($FirstNonzero).TrimEnd([char]'0')
        $Mantissa = $Digits.Substring(0, 1)
        if ($Digits.Length -gt 1) {
            $Mantissa += '.' + $Digits.Substring(1)
        }
        $ExponentSign = if ($Exponent -ge 0) { '+' } else { '-' }
        $ExponentDigits = [Math]::Abs($Exponent).ToString($Invariant).PadLeft(2, '0')
        return $Sign + $Mantissa + 'e' + $ExponentSign + $ExponentDigits
    }
    if ($Point -lt 0) {
        return $Formatted + '.0'
    }
    return $Formatted
}

function Write-CanonicalJsonElement {
    param(
        [Parameter(Mandatory = $true)][System.Text.Json.JsonElement]$Element,
        [Parameter(Mandatory = $true)][System.Text.Json.Utf8JsonWriter]$Writer
    )
    switch ($Element.ValueKind) {
        ([System.Text.Json.JsonValueKind]::Object) {
            $Writer.WriteStartObject()
            [string[]]$Names = @(
                $Element.EnumerateObject() | ForEach-Object { $_.Name }
            )
            [Array]::Sort($Names, [System.StringComparer]::Ordinal)
            foreach ($Name in $Names) {
                $Writer.WritePropertyName($Name)
                $Child = $Element.GetProperty($Name)
                Write-CanonicalJsonElement -Element $Child -Writer $Writer
            }
            $Writer.WriteEndObject()
        }
        ([System.Text.Json.JsonValueKind]::Array) {
            $Writer.WriteStartArray()
            foreach ($Item in $Element.EnumerateArray()) {
                Write-CanonicalJsonElement -Element $Item -Writer $Writer
            }
            $Writer.WriteEndArray()
        }
        ([System.Text.Json.JsonValueKind]::String) {
            $Writer.WriteStringValue($Element.GetString())
        }
        ([System.Text.Json.JsonValueKind]::Number) {
            $CanonicalNumber = ConvertTo-PythonCanonicalJsonNumber -Element $Element
            $Writer.WriteRawValue($CanonicalNumber, $false)
        }
        ([System.Text.Json.JsonValueKind]::True) {
            $Writer.WriteBooleanValue($true)
        }
        ([System.Text.Json.JsonValueKind]::False) {
            $Writer.WriteBooleanValue($false)
        }
        ([System.Text.Json.JsonValueKind]::Null) {
            $Writer.WriteNullValue()
        }
        default {
            throw "Unsupported JSON value kind: $($Element.ValueKind)"
        }
    }
}

function Convert-JsonDocumentToCanonicalBytes {
    param([Parameter(Mandatory = $true)][System.Text.Json.JsonDocument]$Document)
    $Stream = [System.IO.MemoryStream]::new()
    $Options = [System.Text.Json.JsonWriterOptions]::new()
    $Options.Indented = $false
    $Options.SkipValidation = $false
    $Options.Encoder = [System.Text.Encodings.Web.JavaScriptEncoder]::UnsafeRelaxedJsonEscaping
    $Writer = [System.Text.Json.Utf8JsonWriter]::new($Stream, $Options)
    try {
        Write-CanonicalJsonElement -Element $Document.RootElement -Writer $Writer
        $Writer.Flush()
        $Raw = $Stream.ToArray()
        $Result = [byte[]]::new($Raw.Length + 1)
        [System.Buffer]::BlockCopy($Raw, 0, $Result, 0, $Raw.Length)
        $Result[$Raw.Length] = 10
        return $Result
    }
    finally {
        $Writer.Dispose()
        $Stream.Dispose()
    }
}

function Convert-CanonicalJsonBytesWithoutRootProperty {
    param(
        [Parameter(Mandatory = $true)][byte[]]$Payload,
        [Parameter(Mandatory = $true)][string]$PropertyName
    )
    $Options = [System.Text.Json.JsonDocumentOptions]::new()
    $Options.AllowTrailingCommas = $false
    $Options.CommentHandling = [System.Text.Json.JsonCommentHandling]::Disallow
    $Text = [System.Text.UTF8Encoding]::new($false, $true).GetString($Payload)
    $Document = [System.Text.Json.JsonDocument]::Parse($Text, $Options)
    $Stream = [System.IO.MemoryStream]::new()
    $WriterOptions = [System.Text.Json.JsonWriterOptions]::new()
    $WriterOptions.Indented = $false
    $WriterOptions.SkipValidation = $false
    $WriterOptions.Encoder = (
        [System.Text.Encodings.Web.JavaScriptEncoder]::UnsafeRelaxedJsonEscaping
    )
    $Writer = [System.Text.Json.Utf8JsonWriter]::new($Stream, $WriterOptions)
    try {
        if ($Document.RootElement.ValueKind -ne [System.Text.Json.JsonValueKind]::Object) {
            throw 'Canonical self-hashed payload must be one JSON object'
        }
        Assert-NoDuplicateJsonProperties -Element $Document.RootElement
        [string[]]$Names = @(
            $Document.RootElement.EnumerateObject() | ForEach-Object { $_.Name }
        )
        if ($Names -cnotcontains $PropertyName) {
            throw "Canonical self-hashed payload lacks $PropertyName"
        }
        [Array]::Sort($Names, [System.StringComparer]::Ordinal)
        $Writer.WriteStartObject()
        foreach ($Name in $Names) {
            if ($Name -ceq $PropertyName) {
                continue
            }
            $Writer.WritePropertyName($Name)
            Write-CanonicalJsonElement `
                -Element $Document.RootElement.GetProperty($Name) `
                -Writer $Writer
        }
        $Writer.WriteEndObject()
        $Writer.Flush()
        $Raw = $Stream.ToArray()
        $Result = [byte[]]::new($Raw.Length + 1)
        [System.Buffer]::BlockCopy($Raw, 0, $Result, 0, $Raw.Length)
        $Result[$Raw.Length] = 10
        return $Result
    }
    finally {
        $Writer.Dispose()
        $Stream.Dispose()
        $Document.Dispose()
    }
}

function ConvertTo-CanonicalJsonBytes {
    param([Parameter(Mandatory = $true)]$Value)
    $Text = ConvertTo-Json -InputObject $Value -Depth 100 -Compress
    $Options = [System.Text.Json.JsonDocumentOptions]::new()
    $Options.AllowTrailingCommas = $false
    $Options.CommentHandling = [System.Text.Json.JsonCommentHandling]::Disallow
    $Document = [System.Text.Json.JsonDocument]::Parse($Text, $Options)
    try {
        Assert-NoDuplicateJsonProperties -Element $Document.RootElement
        return Convert-JsonDocumentToCanonicalBytes -Document $Document
    }
    finally {
        $Document.Dispose()
    }
}

function ConvertFrom-StrictCanonicalJsonBytes {
    param(
        [Parameter(Mandatory = $true)][byte[]]$Payload,
        [Parameter(Mandatory = $true)][string]$Description
    )
    try {
        $Text = [System.Text.UTF8Encoding]::new($false, $true).GetString($Payload)
        $Options = [System.Text.Json.JsonDocumentOptions]::new()
        $Options.AllowTrailingCommas = $false
        $Options.CommentHandling = [System.Text.Json.JsonCommentHandling]::Disallow
        $Document = [System.Text.Json.JsonDocument]::Parse($Text, $Options)
    }
    catch {
        throw "$Description is not strict UTF-8 JSON: $($_.Exception.Message)"
    }
    try {
        if ($Document.RootElement.ValueKind -ne [System.Text.Json.JsonValueKind]::Object) {
            throw "$Description must be one JSON object"
        }
        Assert-NoDuplicateJsonProperties -Element $Document.RootElement
        $Canonical = Convert-JsonDocumentToCanonicalBytes -Document $Document
        if ([System.Convert]::ToBase64String($Canonical) -cne
            [System.Convert]::ToBase64String($Payload)) {
            throw "$Description must be canonical JSON"
        }
    }
    finally {
        $Document.Dispose()
    }
    return ConvertFrom-Json -InputObject $Text -AsHashtable -Depth 100
}

function Assert-ExactKeys {
    param(
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Value,
        [Parameter(Mandatory = $true)][string[]]$Expected,
        [Parameter(Mandatory = $true)][string]$Description
    )
    $ActualKeys = @($Value.Keys | ForEach-Object { [string]$_ } | Sort-Object -CaseSensitive)
    $ExpectedKeys = @($Expected | Sort-Object -CaseSensitive)
    if ([string]::Join("`0", $ActualKeys) -cne [string]::Join("`0", $ExpectedKeys)) {
        throw "$Description keys mismatch"
    }
}

function Assert-CanonicalLowerSha256 {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [object]$Value,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )
    if (-not ($Value -is [string]) -or
        [string]$Value -cnotmatch '^[0-9a-f]{64}$') {
        throw "$Description must be a canonical lowercase SHA-256"
    }
    return [string]$Value
}

function Assert-SafeFinalizerSourcePath {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [object]$Value
    )
    if (-not ($Value -is [string])) {
        throw 'Comparison source path must be a string'
    }
    $Relative = [string]$Value
    if ([string]::IsNullOrEmpty($Relative) -or
        $Relative.Contains('\') -or
        $Relative.Contains([char]0) -or
        $Relative.StartsWith('/', [System.StringComparison]::Ordinal) -or
        $Relative.EndsWith('/', [System.StringComparison]::Ordinal) -or
        $Relative.Contains('//') -or
        [System.IO.Path]::IsPathRooted($Relative)) {
        throw "Comparison source path is not canonical POSIX relative: $Relative"
    }
    $Segments = $Relative.Split(
        [char]'/',
        [System.StringSplitOptions]::None
    )
    foreach ($Segment in $Segments) {
        if ([string]::IsNullOrEmpty($Segment) -or
            $Segment -ceq '.' -or
            $Segment -ceq '..' -or
            $Segment.Contains(':')) {
            throw "Comparison source path is not canonical POSIX relative: $Relative"
        }
        foreach ($Character in $Segment.ToCharArray()) {
            if ([int]$Character -lt 32) {
                throw "Comparison source path contains a control character"
            }
        }
    }
    $InAllowedNamespace = $Relative -ceq 'pyproject.toml' -or `
        $Relative -ceq $LauncherRelative -or (
        $Segments.Count -ge 2 -and
        $Segments[0] -ceq 'src' -and
        $Segments[$Segments.Count - 1].EndsWith(
            '.py',
            [System.StringComparison]::Ordinal
        )
    )
    if (-not $InAllowedNamespace) {
        throw "Comparison source path leaves the allowed Python source namespace: $Relative"
    }
    return $Relative
}

function Assert-NoReparseAncestors {
    param([Parameter(Mandatory = $true)][string]$Path)
    $Current = Get-Item -LiteralPath ([System.IO.Path]::GetFullPath($Path)) -Force
    while ($null -ne $Current) {
        if (($Current.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Authority path contains a reparse point: $($Current.FullName)"
        }
        $Current = if (
            ($Current.Attributes -band [System.IO.FileAttributes]::Directory) -ne 0
        ) {
            $Current.Parent
        }
        else {
            $Current.Directory
        }
    }
}

function Assert-ContainedRegularPath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$AllowMissingLeaf
    )
    $RootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar
    )
    $PathFull = [System.IO.Path]::GetFullPath($Path)
    $Prefix = $RootFull + [System.IO.Path]::DirectorySeparatorChar
    if ($PathFull -cne $RootFull -and
        -not $PathFull.StartsWith($Prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Authority path escaped repository root: $PathFull"
    }
    $Current = if ($AllowMissingLeaf -and -not (Test-Path -LiteralPath $PathFull)) {
        [System.IO.Path]::GetDirectoryName($PathFull)
    }
    else {
        $PathFull
    }
    while ($true) {
        $Item = Get-Item -LiteralPath $Current -Force
        if (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Authority path contains a reparse point: $Current"
        }
        if ($Current.Equals($RootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            break
        }
        $Parent = [System.IO.Path]::GetDirectoryName($Current)
        if (-not $Parent -or $Parent.Equals($Current, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Authority path did not reach repository root: $PathFull"
        }
        $Current = $Parent
    }
    if (-not $AllowMissingLeaf) {
        $Leaf = Get-Item -LiteralPath $PathFull -Force
        if ($Leaf.PSIsContainer -or
            ($Leaf.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Authority source is not one regular file: $PathFull"
        }
    }
    return $PathFull
}

function Open-LockedReadFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    $FullPath = [System.IO.Path]::GetFullPath($Path)
    Assert-NoReparseAncestors -Path $FullPath
    $Stream = [System.IO.File]::Open(
        $FullPath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    try {
        if ($Stream.Length -gt [int]::MaxValue) {
            throw "Authority file is too large: $FullPath"
        }
        $Payload = [byte[]]::new([int]$Stream.Length)
        $Offset = 0
        while ($Offset -lt $Payload.Length) {
            $Read = $Stream.Read($Payload, $Offset, $Payload.Length - $Offset)
            if ($Read -le 0) {
                throw "Authority file ended early: $FullPath"
            }
            $Offset += $Read
        }
        $Stream.Position = 0
        return [PSCustomObject]@{
            Path = $FullPath
            Stream = $Stream
            Payload = $Payload
            Bytes = [long]$Payload.Length
            Sha256 = Get-LowerSha256Bytes -Payload $Payload
        }
    }
    catch {
        $Stream.Dispose()
        throw
    }
}

function Write-ExclusiveBytes {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][byte[]]$Payload
    )
    try {
        $Stream = [System.IO.FileStream]::new(
            $Path,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None,
            4096,
            [System.IO.FileOptions]::WriteThrough
        )
    }
    catch [System.IO.IOException] {
        throw "Refusing to overwrite or race comparison-launch receipt: $Path"
    }
    try {
        $Stream.Write($Payload, 0, $Payload.Length)
        $Stream.Flush($true)
    }
    finally {
        $Stream.Dispose()
    }
}

function Write-AtomicReplacementBytes {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][byte[]]$Payload
    )
    $FullPath = [System.IO.Path]::GetFullPath($Path)
    $Directory = [System.IO.Path]::GetDirectoryName($FullPath)
    $Temporary = [System.IO.Path]::Combine(
        $Directory,
        ".$(Split-Path -Leaf $FullPath).$PID.$([Guid]::NewGuid().ToString('N')).tmp"
    )
    try {
        Write-ExclusiveBytes -Path $Temporary -Payload $Payload
        [System.IO.File]::Move($Temporary, $FullPath, $true)
    }
    finally {
        if ([System.IO.File]::Exists($Temporary)) {
            [System.IO.File]::Delete($Temporary)
        }
    }
}

function Set-FailedComparisonLaunchReceipt {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][int]$ChildProcessId,
        [Parameter(Mandatory = $true)][int]$ExitCode
    )
    $PreviousSha256 = if ([System.IO.File]::Exists($Path)) {
        Get-LowerSha256Bytes -Payload ([System.IO.File]::ReadAllBytes($Path))
    }
    else {
        '0' * 64
    }
    $FailedCore = [ordered]@{
        schema_version = $ReceiptSchema
        status = 'FAILED'
        launcher_process_id = [int]$PID
        child_process_id = $ChildProcessId
        child_exit_code = $ExitCode
        failed_at_utc = Get-CanonicalUtcNow
        previous_receipt_sha256 = $PreviousSha256
    }
    $Failed = [ordered]@{}
    foreach ($Key in $FailedCore.Keys) {
        $Failed[$Key] = $FailedCore[$Key]
    }
    $Failed.receipt_sha256 = Get-LowerSha256Bytes -Payload (
        ConvertTo-CanonicalJsonBytes -Value $FailedCore
    )
    $FailedBytes = ConvertTo-CanonicalJsonBytes -Value $Failed
    try {
        Write-AtomicReplacementBytes -Path $Path -Payload $FailedBytes
    }
    catch {
        if ([System.IO.File]::Exists($Path)) {
            [System.IO.File]::Delete($Path)
        }
        throw
    }
}

function Get-PortablePathSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    $Normalized = [System.IO.Path]::GetFullPath($Path).ToLowerInvariant().Replace('\', '/')
    return Get-LowerSha256Text -Text $Normalized
}

function Format-CanonicalUtcTimestamp {
    param([Parameter(Mandatory = $true)][DateTime]$Value)
    $Utc = $Value.ToUniversalTime()
    $MicrosecondTicks = $Utc.Ticks - ($Utc.Ticks % 10)
    $CanonicalUtc = [DateTime]::new($MicrosecondTicks, [DateTimeKind]::Utc)
    $Format = if (($CanonicalUtc.Ticks % [TimeSpan]::TicksPerSecond) -eq 0) {
        "yyyy-MM-ddTHH:mm:ss'Z'"
    }
    else {
        "yyyy-MM-ddTHH:mm:ss.ffffff'Z'"
    }
    return $CanonicalUtc.ToString(
        $Format,
        [System.Globalization.CultureInfo]::InvariantCulture
    )
}

function Get-CanonicalUtcNow {
    return Format-CanonicalUtcTimestamp -Value ([DateTime]::UtcNow)
}

function ConvertFrom-CanonicalUtcTimestamp {
    param([Parameter(Mandatory = $true)][string]$Value)
    return [DateTime]::ParseExact(
        $Value,
        [string[]]@(
            "yyyy-MM-ddTHH:mm:ss'Z'",
            "yyyy-MM-ddTHH:mm:ss.ffffff'Z'"
        ),
        [System.Globalization.CultureInfo]::InvariantCulture,
        (
            [System.Globalization.DateTimeStyles]::AssumeUniversal -bor
            [System.Globalization.DateTimeStyles]::AdjustToUniversal
        )
    )
}

function Test-StringArrayEqual {
    param(
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)][string[]]$Expected
    )
    if (-not ($Actual -is [object[]]) -or $Actual.Count -ne $Expected.Count) {
        return $false
    }
    for ($Index = 0; $Index -lt $Expected.Count; $Index++) {
        if (-not ($Actual[$Index] -is [string]) -or
            [string]$Actual[$Index] -cne $Expected[$Index]) {
            return $false
        }
    }
    return $true
}

$PreflightStartedAtUtc = Get-CanonicalUtcNow
$LauncherPath = [System.IO.Path]::GetFullPath($PSCommandPath)
if ([System.IO.Path]::GetFileName($LauncherPath) -cne 'phase40_comparison_launcher.ps1') {
    throw 'Comparison launcher filename drifted'
}
$LauncherDirectory = [System.IO.Path]::GetDirectoryName($LauncherPath)
if ([System.IO.Path]::GetFileName($LauncherDirectory) -cne 'scripts') {
    throw 'Comparison launcher is outside its fixed repository scripts directory'
}
$RepositoryRoot = [System.IO.Directory]::GetParent(
    $LauncherDirectory
).FullName
if (-not (Test-Path -LiteralPath $RepositoryRoot -PathType Container)) {
    throw 'Comparison launcher repository root is missing'
}
$ExpectedLauncherPath = [System.IO.Path]::GetFullPath(
    (Join-Path $RepositoryRoot $LauncherRelative)
)
if (-not $LauncherPath.Equals(
    $ExpectedLauncherPath,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw 'Comparison launcher actual path differs from its fixed repository location'
}
Assert-NoReparseAncestors -Path $RepositoryRoot

$Locks = [System.Collections.Generic.List[System.IDisposable]]::new()
$OldPythonPath = $env:PYTHONPATH
$OldPythonHome = $env:PYTHONHOME
$OldNoUserSite = $env:PYTHONNOUSERSITE
try {
    $LauncherLock = Open-LockedReadFile -Path $LauncherPath
    $Locks.Add($LauncherLock.Stream)

    $FinalAuthorityPath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
        Join-Path $RepositoryRoot $FinalAuthorityRelative
    )
    $RequestPath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
        Join-Path $RepositoryRoot $RequestRelative
    )
    $PhoBertRequestPath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
        Join-Path $RepositoryRoot $PhoBertRequestRelative
    )
    $AmendmentPath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
        Join-Path $RepositoryRoot $AmendmentRelative
    )
    $ReceiptPath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
        Join-Path $RepositoryRoot $ReceiptRelative
    ) -AllowMissingLeaf
    $ClaimPath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
        Join-Path $RepositoryRoot $ClaimRelative
    ) -AllowMissingLeaf
    if (Test-Path -LiteralPath $ReceiptPath) {
        throw 'Refusing to overwrite frozen comparison-launch receipt'
    }
    if (Test-Path -LiteralPath $ClaimPath) {
        throw 'Refusing to reuse an existing comparison-launch capability claim'
    }

    $FinalAuthorityLock = Open-LockedReadFile -Path $FinalAuthorityPath
    $Locks.Add($FinalAuthorityLock.Stream)
    $RequestLock = Open-LockedReadFile -Path $RequestPath
    $Locks.Add($RequestLock.Stream)
    $PhoBertRequestLock = Open-LockedReadFile -Path $PhoBertRequestPath
    $Locks.Add($PhoBertRequestLock.Stream)
    $AmendmentLock = Open-LockedReadFile -Path $AmendmentPath
    $Locks.Add($AmendmentLock.Stream)
    $FinalAuthority = ConvertFrom-StrictCanonicalJsonBytes `
        -Payload $FinalAuthorityLock.Payload `
        -Description 'Canonical Phase 40 final comparison authority'
    $Request = ConvertFrom-StrictCanonicalJsonBytes `
        -Payload $RequestLock.Payload `
        -Description 'Canonical Phase 40 Qwen request'
    $PhoBertRequest = ConvertFrom-StrictCanonicalJsonBytes `
        -Payload $PhoBertRequestLock.Payload `
        -Description 'Canonical Phase 40 PhoBERT recovery request'
    $Amendment = ConvertFrom-StrictCanonicalJsonBytes `
        -Payload $AmendmentLock.Payload `
        -Description 'Canonical superseded Phase 40 scope amendment'

    foreach ($RequestGate in @(
        [ordered]@{ Value = $Request; RunId = $ExpectedActiveRunIds[0]; Name = 'Qwen' },
        [ordered]@{ Value = $PhoBertRequest; RunId = $ExpectedActiveRunIds[1]; Name = 'PhoBERT recovery' }
    )) {
        $CurrentRequest = $RequestGate.Value
        Assert-ExactKeys -Value $CurrentRequest -Expected @(
            'schema_version', 'runs', 'source_bundle', 'input_bundle',
            'package_candidates', 'expected_bundle_files', 'control_template_by_run',
            'control_template_digest_by_run', 'no_held_out_boundary', 'git_commit'
        ) -Description "Phase 40 $($RequestGate.Name) request"
        if (-not ($CurrentRequest.schema_version -is [string]) -or
            $CurrentRequest.schema_version -cne 'phase40-full-run-request-v1' -or
            -not ($CurrentRequest.no_held_out_boundary -is [bool]) -or
            $CurrentRequest.no_held_out_boundary -ne $true -or
            -not ($CurrentRequest.runs -is [object[]]) -or
            -not ($CurrentRequest.control_template_by_run -is [System.Collections.IDictionary]) -or
            -not $CurrentRequest.control_template_by_run.Contains($RequestGate.RunId) -or
            -not ($CurrentRequest.control_template_digest_by_run -is [System.Collections.IDictionary]) -or
            -not $CurrentRequest.control_template_digest_by_run.Contains($RequestGate.RunId)) {
            throw "Phase 40 $($RequestGate.Name) request authority drifted"
        }
        $FoundRun = $false
        foreach ($Run in $CurrentRequest.runs) {
            if ($Run -is [System.Collections.IDictionary] -and
                $Run.run_id -is [string] -and
                $Run.run_id -ceq $RequestGate.RunId) {
                $FoundRun = $true
            }
        }
        if (-not $FoundRun) {
            throw "Phase 40 $($RequestGate.Name) request lacks the selected run"
        }
        $ExpectedRequestRunIds = @(
            'phase40-qwen-lora-full-seed42-v1',
            'phase40-qwen-qlora-full-seed42-v1',
            $(if ($RequestGate.Name -ceq 'Qwen') {
                'phase40-phobert-full-seed42-v1'
            }
            else {
                'phase40-phobert-full-seed42-v12'
            })
        )
        $ActualRequestRunIds = @(
            $CurrentRequest.runs | ForEach-Object { $_.run_id }
        )
        if (-not (Test-StringArrayEqual $ActualRequestRunIds $ExpectedRequestRunIds)) {
            throw "Phase 40 $($RequestGate.Name) request run IDs/order drifted"
        }
    }

    Assert-ExactKeys -Value $FinalAuthority -Expected @(
        'schema_version', 'superseded_scope_amendment', 'request_authorities',
        'selected_runs', 'quality_model_run_ids', 'review_model_run_ids',
        'shared_input_authority', 'waived_full_run_id', 'waiver_action',
        'lora_probe_authority', 'comparison_finalizer_authority',
        'recovery_policy', 'execution_policy', 'no_held_out_boundary'
    ) -Description 'Phase 40 final comparison authority'
    if ($FinalAuthority.schema_version -cne 'phase40-final-comparison-authority-v1' -or
        $FinalAuthority.recovery_policy -cne 'additive_per_run_request_authority_no_evidence_rewrite_v1' -or
        $FinalAuthority.execution_policy -cne 'local_primary' -or
        $FinalAuthority.waived_full_run_id -cne 'phase40-qwen-lora-full-seed42-v1' -or
        $FinalAuthority.waiver_action -cne 'withdrawn' -or
        -not ($FinalAuthority.no_held_out_boundary -is [bool]) -or
        $FinalAuthority.no_held_out_boundary -ne $true) {
        throw 'Phase 40 final comparison policy drifted'
    }

    if (-not ($FinalAuthority.request_authorities -is [object[]]) -or
        $FinalAuthority.request_authorities.Count -ne 2) {
        throw 'Final comparison request authorities must be the exact pair'
    }
    $ExpectedRequestAuthorities = @(
        [ordered]@{ authority_id = 'qwen-v1-origin'; root_policy = 'repository_root'; request_sha256 = $RequestLock.Sha256 },
        [ordered]@{ authority_id = 'phobert-v12-recovery'; root_policy = 'fixed_phobert_v12_capsule'; request_sha256 = $PhoBertRequestLock.Sha256 }
    )
    for ($Index = 0; $Index -lt 2; $Index++) {
        $Entry = $FinalAuthority.request_authorities[$Index]
        if (-not ($Entry -is [System.Collections.IDictionary])) {
            throw "Final comparison request authority $Index must be one object"
        }
        Assert-ExactKeys -Value $Entry -Expected @(
            'authority_id', 'root_policy', 'request_sha256'
        ) -Description "Final comparison request authority $Index"
        [void](Assert-CanonicalLowerSha256 -Value $Entry.request_sha256 `
            -Description "Final comparison request authority $Index hash")
        if ([System.Convert]::ToBase64String((ConvertTo-CanonicalJsonBytes $Entry)) -cne
            [System.Convert]::ToBase64String((ConvertTo-CanonicalJsonBytes $ExpectedRequestAuthorities[$Index]))) {
            throw 'Final comparison request authorities drifted'
        }
    }

    if (-not ($FinalAuthority.selected_runs -is [object[]]) -or
        $FinalAuthority.selected_runs.Count -ne 2) {
        throw 'Final comparison selected runs must be the exact pair'
    }
    $ExpectedSelectedRuns = @(
        [ordered]@{ run_id = $ExpectedActiveRunIds[0]; request_authority_id = 'qwen-v1-origin'; requested_run_id = $ExpectedActiveRunIds[0]; returned_root = $ExpectedActiveRoots[0] },
        [ordered]@{ run_id = $ExpectedActiveRunIds[1]; request_authority_id = 'phobert-v12-recovery'; requested_run_id = $ExpectedActiveRunIds[1]; returned_root = $ExpectedActiveRoots[1] }
    )
    for ($Index = 0; $Index -lt 2; $Index++) {
        $Entry = $FinalAuthority.selected_runs[$Index]
        if (-not ($Entry -is [System.Collections.IDictionary])) {
            throw "Final comparison selected run $Index must be one object"
        }
        Assert-ExactKeys -Value $Entry -Expected @(
            'run_id', 'request_authority_id', 'requested_run_id', 'returned_root'
        ) -Description "Final comparison selected run $Index"
        if ([System.Convert]::ToBase64String((ConvertTo-CanonicalJsonBytes $Entry)) -cne
            [System.Convert]::ToBase64String((ConvertTo-CanonicalJsonBytes $ExpectedSelectedRuns[$Index]))) {
            throw 'Final comparison selected runs drifted'
        }
    }
    if (-not (Test-StringArrayEqual $FinalAuthority.quality_model_run_ids $ExpectedActiveRunIds) -or
        -not (Test-StringArrayEqual $FinalAuthority.review_model_run_ids $ExpectedActiveRunIds)) {
        throw 'Final comparison selected model set drifted'
    }

    $Superseded = $FinalAuthority.superseded_scope_amendment
    Assert-ExactKeys -Value $Amendment -Expected @(
        'schema_version', 'original_run_request_path',
        'original_run_request_sha256', 'active_full_run_ids',
        'active_returned_roots', 'waived_full_run_id', 'waived_returned_root',
        'full_lora_disposition', 'waiver_action', 'waiver_basis',
        'lora_probe_authority', 'comparison_finalizer_authority',
        'quality_model_run_ids', 'review_model_run_ids', 'execution_policy',
        'colab_contingency_policy', 'no_held_out_boundary'
    ) -Description 'Historical Phase 40 scope amendment'
    Assert-ExactKeys -Value $Superseded -Expected @(
        'relative_path', 'sha256', 'schema_version'
    ) -Description 'Superseded scope-amendment authority'
    $SupersededSha256 = Assert-CanonicalLowerSha256 -Value $Superseded.sha256 `
        -Description 'Superseded scope-amendment hash'
    if ($Superseded.relative_path -cne $AmendmentRelative -or
        $Superseded.schema_version -cne 'phase40-two-full-model-scope-amendment-v1' -or
        $SupersededSha256 -cne $AmendmentLock.Sha256 -or
        $Amendment.schema_version -cne 'phase40-two-full-model-scope-amendment-v1' -or
        $Amendment.original_run_request_path -cne $RequestRelative -or
        $Amendment.original_run_request_sha256 -cne $RequestLock.Sha256 -or
        -not (Test-StringArrayEqual $Amendment.active_full_run_ids @(
            'phase40-qwen-qlora-full-seed42-v1',
            'phase40-phobert-full-seed42-v1'
        )) -or
        -not (Test-StringArrayEqual $Amendment.quality_model_run_ids @(
            'phase40-qwen-qlora-full-seed42-v1',
            'phase40-phobert-full-seed42-v1'
        )) -or
        -not (Test-StringArrayEqual $Amendment.review_model_run_ids @(
            'phase40-qwen-qlora-full-seed42-v1',
            'phase40-phobert-full-seed42-v1'
        )) -or
        -not (Test-StringArrayEqual $Amendment.active_returned_roots $ExpectedActiveRoots) -or
        $Amendment.waived_full_run_id -cne 'phase40-qwen-lora-full-seed42-v1' -or
        $Amendment.waived_returned_root -cne 'data/models/phase40/full/qwen-lora' -or
        $Amendment.full_lora_disposition -cne 'cancelled_before_start' -or
        $Amendment.waiver_action -cne 'withdrawn' -or
        $Amendment.waiver_basis -cne 'bounded_local_probe_established_resource_pressure_and_deadline_mismatch' -or
        $Amendment.execution_policy -cne 'local_primary' -or
        $Amendment.colab_contingency_policy -cne 'validation_only_before_held_out_open_if_local_quality_unacceptable' -or
        -not ($Amendment.no_held_out_boundary -is [bool]) -or
        $Amendment.no_held_out_boundary -ne $true) {
        throw 'Superseded scope-amendment authority drifted'
    }
    if ([System.Convert]::ToBase64String((ConvertTo-CanonicalJsonBytes $FinalAuthority.lora_probe_authority)) -cne
        [System.Convert]::ToBase64String((ConvertTo-CanonicalJsonBytes $Amendment.lora_probe_authority))) {
        throw 'Final comparison LoRA-probe authority drifted'
    }
    $SharedInputBytes = ConvertTo-CanonicalJsonBytes $FinalAuthority.shared_input_authority
    if ([System.Convert]::ToBase64String($SharedInputBytes) -cne
        [System.Convert]::ToBase64String((ConvertTo-CanonicalJsonBytes $Request.input_bundle)) -or
        [System.Convert]::ToBase64String($SharedInputBytes) -cne
        [System.Convert]::ToBase64String((ConvertTo-CanonicalJsonBytes $PhoBertRequest.input_bundle))) {
        throw 'Final comparison shared-input authority drifted'
    }

    $CapsuleAssetDeclarations = @(
        [ordered]@{ path = 'data/models/phase40/source/phase40-source.zip'; sha256 = $PhoBertRequest.source_bundle.archive_sha256 },
        [ordered]@{ path = 'data/models/phase40/source/phase40-source-manifest.json'; sha256 = $PhoBertRequest.source_bundle.inventory_sha256 },
        [ordered]@{ path = 'data/models/phase40/input/phase40-train-validation.zip'; sha256 = $PhoBertRequest.input_bundle.archive_sha256 }
    )
    $DeclaredCapsulePaths = @(
        $PhoBertRequest.source_bundle.repository_relative_archive_path,
        $PhoBertRequest.source_bundle.repository_relative_inventory_path,
        $PhoBertRequest.input_bundle.repository_relative_path
    )
    if (-not (Test-StringArrayEqual $DeclaredCapsulePaths @(
        'data/models/phase40/source/phase40-source.zip',
        'data/models/phase40/source/phase40-source-manifest.json',
        'data/models/phase40/input/phase40-train-validation.zip'
    ))) {
        throw 'PhoBERT recovery request names alternate capsule assets'
    }
    $VerifiedCapsuleAssets = [System.Collections.Generic.List[object]]::new()
    for ($Index = 0; $Index -lt 3; $Index++) {
        $AssetPath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
            Join-Path $RepositoryRoot $PhoBertCapsuleAssetRelatives[$Index]
        )
        $AssetLock = Open-LockedReadFile -Path $AssetPath
        $Locks.Add($AssetLock.Stream)
        $ExpectedAssetSha256 = Assert-CanonicalLowerSha256 `
            -Value $CapsuleAssetDeclarations[$Index].sha256 `
            -Description "PhoBERT capsule asset $Index hash"
        if ($AssetLock.Sha256 -cne $ExpectedAssetSha256) {
            throw "PhoBERT capsule asset identity mismatch: $($CapsuleAssetDeclarations[$Index].path)"
        }
        if ($Index -eq 1) {
            [void](ConvertFrom-StrictCanonicalJsonBytes -Payload $AssetLock.Payload `
                -Description 'PhoBERT capsule source inventory')
        }
        $VerifiedCapsuleAssets.Add([ordered]@{
            relative_path = $PhoBertCapsuleAssetRelatives[$Index]
            bytes = $AssetLock.Bytes
            sha256 = $AssetLock.Sha256
        })
    }

    $Authority = $FinalAuthority.comparison_finalizer_authority
    Assert-ExactKeys -Value $Authority -Expected @(
        'schema_version', 'runtime_origin', 'files', 'source_tree_sha256'
    ) -Description 'Comparison-finalizer authority'
    if (-not ($Authority.schema_version -is [string]) -or
        $Authority.schema_version -cne 'phase40-comparison-finalizer-authority-v1' -or
        -not ($Authority.runtime_origin -is [string]) -or
        $Authority.runtime_origin -cne 'local_hash_pinned_source_not_training_runtime_v3') {
        throw 'Comparison-finalizer authority schema or origin drifted'
    }
    $BoundSourceTreeSha256 = Assert-CanonicalLowerSha256 `
        -Value $Authority.source_tree_sha256 `
        -Description 'Comparison-finalizer source-tree hash'
    if (-not ($Authority.files -is [object[]]) -or
        $Authority.files.Count -ne $ExpectedFinalizerSourcePaths.Count) {
        throw 'Comparison-finalizer files must be the exact code-fixed source array'
    }

    # Validate the complete declared namespace and raw JSON token shapes before
    # any source path is statted or opened.  A hostile late entry therefore
    # cannot trigger reads of earlier valid entries or any reserved data path.
    $DeclaredFiles = [System.Collections.Generic.List[object]]::new()
    for ($Index = 0; $Index -lt $Authority.files.Count; $Index++) {
        $Entry = $Authority.files[$Index]
        if (-not ($Entry -is [System.Collections.IDictionary])) {
            throw "Comparison source entry $Index must be one JSON object"
        }
        Assert-ExactKeys -Value $Entry -Expected @('path', 'bytes', 'sha256') `
            -Description 'Comparison source entry'
        $Relative = Assert-SafeFinalizerSourcePath -Value $Entry.path
        if ($Relative -cne $ExpectedFinalizerSourcePaths[$Index]) {
            throw 'Comparison source inventory differs from the code-fixed source allowlist'
        }
        if (-not ($Entry.bytes -is [long]) -or [long]$Entry.bytes -lt 0) {
            throw "Comparison source byte count is not a nonnegative integer: $Relative"
        }
        $EntrySha256 = Assert-CanonicalLowerSha256 `
            -Value $Entry.sha256 `
            -Description "Comparison source SHA-256 for $Relative"
        $DeclaredFiles.Add([ordered]@{
            path = $Relative
            bytes = [long]$Entry.bytes
            sha256 = $EntrySha256
        })
    }
    $DeclaredFileArray = [object[]]$DeclaredFiles.ToArray()
    $RawInventoryBytes = ConvertTo-CanonicalJsonBytes -Value $Authority.files
    $DeclaredInventoryBytes = ConvertTo-CanonicalJsonBytes -Value $DeclaredFileArray
    if ([System.Convert]::ToBase64String($RawInventoryBytes) -cne
        [System.Convert]::ToBase64String($DeclaredInventoryBytes)) {
        throw 'Comparison source inventory uses noncanonical JSON token types'
    }
    $TreeSha256 = Get-CombinedSha256 -Prefix (
        [System.Text.UTF8Encoding]::new($false).GetBytes($TreeDomain)
    ) -Payload $DeclaredInventoryBytes
    if ($TreeSha256 -cne $BoundSourceTreeSha256) {
        throw 'Comparison-finalizer source-tree hash mismatch'
    }

    $VerifiedFiles = [System.Collections.Generic.List[object]]::new()
    foreach ($Entry in $DeclaredFileArray) {
        $Relative = [string]$Entry.path
        $SourcePath = Assert-ContainedRegularPath -Root $RepositoryRoot -Path (
            Join-Path $RepositoryRoot $Relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        )
        $SourceLock = Open-LockedReadFile -Path $SourcePath
        $Locks.Add($SourceLock.Stream)
        if ($SourceLock.Bytes -ne [long]$Entry.bytes -or
            $SourceLock.Sha256 -cne [string]$Entry.sha256) {
            throw "Comparison source identity mismatch: $Relative"
        }
        $VerifiedFiles.Add([ordered]@{
            path = $Relative
            bytes = $SourceLock.Bytes
            sha256 = $SourceLock.Sha256
        })
    }
    $VerifiedFileArray = [object[]]$VerifiedFiles.ToArray()
    $InventoryBytes = ConvertTo-CanonicalJsonBytes -Value $VerifiedFileArray
    if ([System.Convert]::ToBase64String($InventoryBytes) -cne
        [System.Convert]::ToBase64String($DeclaredInventoryBytes)) {
        throw 'Verified source inventory changed after source locks were acquired'
    }

    $ProgramFiles = [Environment]::GetFolderPath(
        [Environment+SpecialFolder]::ProgramFiles
    )
    $ExpectedHostPath = [System.IO.Path]::GetFullPath(
        (Join-Path $ProgramFiles 'PowerShell\7\pwsh.exe')
    )
    $ActualHostPath = [System.IO.Path]::GetFullPath((Get-Process -Id $PID).Path)
    if (-not $ActualHostPath.Equals(
        $ExpectedHostPath,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw 'Comparison launcher host path differs from its allowed authority'
    }
    $HostLock = Open-LockedReadFile -Path $ActualHostPath
    $Locks.Add($HostLock.Stream)
    if ($HostLock.Sha256 -cne $AllowedHostSha256 -or
        $PSVersionTable.PSVersion.ToString() -cne $AllowedHostVersion) {
        throw 'Comparison launcher host hash or version differs from its allowed authority'
    }

    $PythonCommand = Get-Command python -CommandType Application -ErrorAction Stop
    $PythonPath = [System.IO.Path]::GetFullPath($PythonCommand.Source)
    if ([System.IO.Path]::GetFileName($PythonPath) -cne 'python.exe') {
        throw 'Canonical Phase 40 Python filename drifted'
    }
    $PythonLock = Open-LockedReadFile -Path $PythonPath
    $Locks.Add($PythonLock.Stream)
    $PythonVersion = (Get-Item -LiteralPath $PythonPath).VersionInfo.ProductVersion
    if ($PythonLock.Sha256 -cne $AllowedPythonSha256 -or
        $PythonVersion -cne $AllowedPythonVersion) {
        throw 'Canonical Phase 40 Python hash or version drifted'
    }

    $PreflightCompletedAtUtc = Get-CanonicalUtcNow
    $ReceiptCreatedAtUtc = Get-CanonicalUtcNow
    $StartedAt = ConvertFrom-CanonicalUtcTimestamp -Value $PreflightStartedAtUtc
    $CompletedAt = ConvertFrom-CanonicalUtcTimestamp -Value $PreflightCompletedAtUtc
    $CreatedAt = ConvertFrom-CanonicalUtcTimestamp -Value $ReceiptCreatedAtUtc
    if ($CompletedAt -lt $StartedAt -or $CreatedAt -lt $CompletedAt) {
        throw 'Comparison-launch receipt chronology is invalid'
    }
    $CapabilityExpiresAtUtc = Format-CanonicalUtcTimestamp -Value (
        $CreatedAt.AddSeconds($CapabilityTtlSeconds)
    )
    $NonceBytes = [byte[]]::new(32)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($NonceBytes)
    $CapabilityNonce = [System.Convert]::ToBase64String($NonceBytes)
    $CapabilityNonceSha256 = Get-LowerSha256Bytes -Payload $NonceBytes
    $Core = [ordered]@{
        schema_version = $ReceiptSchema
        status = 'PENDING'
        final_comparison_authority = [ordered]@{
            relative_path = $FinalAuthorityRelative
            sha256 = $FinalAuthorityLock.Sha256
        }
        request_authorities = @(
            [ordered]@{
                authority_id = 'qwen-v1-origin'
                root_policy = 'repository_root'
                request = [ordered]@{
                    relative_path = $RequestRelative
                    sha256 = $RequestLock.Sha256
                }
                assets = @()
            },
            [ordered]@{
                authority_id = 'phobert-v12-recovery'
                root_policy = 'fixed_phobert_v12_capsule'
                request = [ordered]@{
                    relative_path = $PhoBertRequestRelative
                    sha256 = $PhoBertRequestLock.Sha256
                }
                assets = [object[]]$VerifiedCapsuleAssets.ToArray()
            }
        )
        superseded_scope_amendment = [ordered]@{
            relative_path = $AmendmentRelative
            sha256 = $AmendmentLock.Sha256
            schema_version = 'phase40-two-full-model-scope-amendment-v1'
        }
        finalizer_authority = [ordered]@{
            schema_version = 'phase40-comparison-finalizer-authority-v1'
            runtime_origin = 'local_hash_pinned_source_not_training_runtime_v3'
            files = $VerifiedFileArray
            source_tree_sha256 = $TreeSha256
        }
        launcher = [ordered]@{
            relative_path = $LauncherRelative
            bytes = $LauncherLock.Bytes
            sha256 = $LauncherLock.Sha256
        }
        launcher_host = [ordered]@{
            path_policy = 'windows_known_folder_program_files'
            portable_path = 'PowerShell/7/pwsh.exe'
            path_sha256 = Get-PortablePathSha256 -Path $ActualHostPath
            bytes = $HostLock.Bytes
            sha256 = $HostLock.Sha256
            version = $AllowedHostVersion
        }
        python = [ordered]@{
            path_policy = 'path_resolution_exact_hash'
            portable_path = 'python.exe'
            path_sha256 = Get-PortablePathSha256 -Path $PythonPath
            bytes = $PythonLock.Bytes
            sha256 = $PythonLock.Sha256
            version = $AllowedPythonVersion
        }
        finalizer_command = @('python') + $FinalizerArguments
        preflight_started_at_utc = $PreflightStartedAtUtc
        preflight_completed_at_utc = $PreflightCompletedAtUtc
        receipt_created_at_utc = $ReceiptCreatedAtUtc
        prelaunch_state = [ordered]@{
            python_launched = $false
            model_bundle_opened = $false
            reserved_split_access_attempted = $false
        }
        launch_capability = [ordered]@{
            state = 'pending'
            nonce_sha256 = $CapabilityNonceSha256
            launcher_process_id = [int]$PID
            child_process_id = $null
            issued_at_utc = $ReceiptCreatedAtUtc
            expires_at_utc = $CapabilityExpiresAtUtc
            consumed_at_utc = $null
            pending_receipt_sha256 = $null
            claim_relative_path = $ClaimRelative
        }
    }
    $CoreBytes = ConvertTo-CanonicalJsonBytes -Value $Core
    $Receipt = [ordered]@{}
    foreach ($Key in $Core.Keys) {
        $Receipt[$Key] = $Core[$Key]
    }
    $Receipt.receipt_sha256 = Get-LowerSha256Bytes -Payload $CoreBytes
    $ReceiptBytes = ConvertTo-CanonicalJsonBytes -Value $Receipt
    $PendingReceiptFileSha256 = Get-LowerSha256Bytes -Payload $ReceiptBytes
    Write-ExclusiveBytes -Path $ReceiptPath -Payload $ReceiptBytes
    $ReceiptLock = Open-LockedReadFile -Path $ReceiptPath
    try {
        if ([System.Convert]::ToBase64String($ReceiptLock.Payload) -cne
            [System.Convert]::ToBase64String($ReceiptBytes)) {
            throw 'Comparison-launch receipt changed after durable creation'
        }
    }
    finally {
        $ReceiptLock.Stream.Dispose()
    }

    $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $StartInfo.FileName = $PythonPath
    $StartInfo.WorkingDirectory = $RepositoryRoot
    $StartInfo.UseShellExecute = $false
    foreach ($Argument in $FinalizerArguments) {
        [void]$StartInfo.ArgumentList.Add($Argument)
    }
    [void]$StartInfo.Environment.Remove('PYTHONPATH')
    [void]$StartInfo.Environment.Remove('PYTHONHOME')
    $StartInfo.Environment['PYTHONNOUSERSITE'] = '1'
    $StartInfo.Environment[$CapabilityNonceEnvironment] = $CapabilityNonce
    $StartInfo.Environment[$CapabilityLauncherPidEnvironment] = [string]$PID
    $StartInfo.Environment[$CapabilityPendingHashEnvironment] = $PendingReceiptFileSha256
    $Process = [System.Diagnostics.Process]::Start($StartInfo)
    if ($null -eq $Process) {
        throw 'Failed to start the fixed Phase 40 comparison finalizer'
    }
    $ChildProcessId = [int]$Process.Id
    [void]$StartInfo.Environment.Remove($CapabilityNonceEnvironment)
    [void]$StartInfo.Environment.Remove($CapabilityLauncherPidEnvironment)
    [void]$StartInfo.Environment.Remove($CapabilityPendingHashEnvironment)
    [Array]::Clear($NonceBytes, 0, $NonceBytes.Length)
    $NonceBytes = $null
    $CapabilityNonce = $null
    $Process.WaitForExit()
    $ExitCode = $Process.ExitCode
    $Process.Dispose()
    if ($ExitCode -ne 0) {
        Set-FailedComparisonLaunchReceipt `
            -Path $ReceiptPath `
            -ChildProcessId $ChildProcessId `
            -ExitCode $ExitCode
        [Console]::Error.WriteLine(
            "Phase 40 comparison finalizer exited with code $ExitCode"
        )
        exit $ExitCode
    }

    try {
        $CompletedReceiptLock = Open-LockedReadFile -Path $ReceiptPath
        try {
            $CompletedReceipt = ConvertFrom-StrictCanonicalJsonBytes `
                -Payload $CompletedReceiptLock.Payload `
                -Description 'Consumed Phase 40 comparison-launch receipt'
            Assert-ExactKeys -Value $CompletedReceipt -Expected @(
                'schema_version', 'status', 'final_comparison_authority',
                'request_authorities', 'superseded_scope_amendment',
                'finalizer_authority', 'launcher', 'launcher_host', 'python',
                'finalizer_command', 'preflight_started_at_utc',
                'preflight_completed_at_utc', 'receipt_created_at_utc',
                'prelaunch_state', 'launch_capability', 'receipt_sha256'
            ) -Description 'Consumed Phase 40 comparison-launch receipt'
            Assert-ExactKeys -Value $CompletedReceipt.launch_capability -Expected @(
                'state', 'nonce_sha256', 'launcher_process_id',
                'child_process_id', 'issued_at_utc', 'expires_at_utc',
                'consumed_at_utc', 'pending_receipt_sha256',
                'claim_relative_path'
            ) -Description 'Consumed comparison-launch capability'
            $CompletedSelfHash = Get-LowerSha256Bytes -Payload (
                Convert-CanonicalJsonBytesWithoutRootProperty `
                    -Payload $CompletedReceiptLock.Payload `
                    -PropertyName 'receipt_sha256'
            )
            if ($CompletedReceipt.schema_version -cne $ReceiptSchema -or
                $CompletedReceipt.status -cne 'PASS') {
                throw 'Finalizer did not leave a v3 PASS receipt'
            }
            if ($CompletedReceipt.receipt_sha256 -cne $CompletedSelfHash) {
                throw 'Finalizer PASS receipt self-hash mismatch'
            }
            if ($CompletedReceipt.launch_capability.state -cne 'consumed' -or
                $CompletedReceipt.launch_capability.nonce_sha256 -cne $CapabilityNonceSha256 -or
                $CompletedReceipt.launch_capability.pending_receipt_sha256 -cne $PendingReceiptFileSha256) {
                throw 'Finalizer PASS receipt capability binding mismatch'
            }
            if ($CompletedReceipt.launch_capability.launcher_process_id -ne [int]$PID -or
                $CompletedReceipt.launch_capability.child_process_id -ne $ChildProcessId) {
                throw 'Finalizer PASS receipt process binding mismatch'
            }
            if ($CompletedReceipt.prelaunch_state.python_launched -ne $true -or
                $CompletedReceipt.prelaunch_state.model_bundle_opened -ne $false -or
                $CompletedReceipt.prelaunch_state.reserved_split_access_attempted -ne $false) {
                throw 'Finalizer PASS receipt prelaunch state mismatch'
            }
        }
        finally {
            $CompletedReceiptLock.Stream.Dispose()
        }

        $ClaimLock = Open-LockedReadFile -Path $ClaimPath
        try {
            $Claim = ConvertFrom-StrictCanonicalJsonBytes `
                -Payload $ClaimLock.Payload `
                -Description 'Phase 40 comparison-launch capability claim'
            Assert-ExactKeys -Value $Claim -Expected @(
                'schema_version', 'state', 'nonce_sha256',
                'launcher_process_id', 'child_process_id',
                'pending_receipt_sha256', 'claimed_at_utc', 'claim_sha256'
            ) -Description 'Phase 40 comparison-launch capability claim'
            $ClaimSelfHash = Get-LowerSha256Bytes -Payload (
                Convert-CanonicalJsonBytesWithoutRootProperty `
                    -Payload $ClaimLock.Payload `
                    -PropertyName 'claim_sha256'
            )
            if ($Claim.schema_version -cne 'phase40-comparison-launch-capability-claim-v1' -or
                $Claim.state -cne 'consumed' -or
                $Claim.claim_sha256 -cne $ClaimSelfHash -or
                $Claim.nonce_sha256 -cne $CapabilityNonceSha256 -or
                $Claim.launcher_process_id -ne [int]$PID -or
                $Claim.child_process_id -ne $ChildProcessId -or
                $Claim.pending_receipt_sha256 -cne $PendingReceiptFileSha256) {
                throw 'Finalizer capability claim differs from the consumed PASS receipt'
            }
        }
        finally {
            $ClaimLock.Stream.Dispose()
        }
    }
    catch {
        Set-FailedComparisonLaunchReceipt `
            -Path $ReceiptPath `
            -ChildProcessId $ChildProcessId `
            -ExitCode 1
        throw
    }
    Write-Output 'PASS comparison preflight; fixed finalizer completed'
    exit 0
}
finally {
    $env:PYTHONPATH = $OldPythonPath
    $env:PYTHONHOME = $OldPythonHome
    $env:PYTHONNOUSERSITE = $OldNoUserSite
    for ($Index = $Locks.Count - 1; $Index -ge 0; $Index--) {
        $Locks[$Index].Dispose()
    }
}
