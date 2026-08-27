[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ReportRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Push-Location $ReportRoot
try {
    $Steps = @(
        @{ Tool = "xelatex"; Args = @("-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "main.tex") },
        @{ Tool = "bibtex"; Args = @("main") },
        @{ Tool = "xelatex"; Args = @("-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "main.tex") },
        @{ Tool = "xelatex"; Args = @("-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "main.tex") }
    )

    foreach ($Step in $Steps) {
        & $Step.Tool @($Step.Args)
        if ($LASTEXITCODE -ne 0) {
            throw "$($Step.Tool) failed with exit code $LASTEXITCODE"
        }
    }

    $Pdf = Get-Item -LiteralPath "main.pdf"
    $Hash = Get-FileHash -Algorithm SHA256 -LiteralPath $Pdf.FullName
    $Receipt = [ordered]@{
        schema = "vnphish.report-build-receipt.v1"
        generated_at = [DateTimeOffset]::Now.ToString("o")
        source = "documents/reports/latex/main.tex"
        output = "documents/reports/latex/main.pdf"
        bytes = $Pdf.Length
        sha256 = $Hash.Hash.ToLowerInvariant()
        compiler = (& xelatex --version | Select-Object -First 1)
        status = "passed"
    }
    $Receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "report-build-receipt.json" -Encoding utf8
    $Receipt | ConvertTo-Json -Depth 4
}
finally {
    Pop-Location
}
