Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$v9Controller = Join-Path $PSScriptRoot 'phase40-qwen-to-phobert-chain-v9.ps1'
$v12Controller = Join-Path $PSScriptRoot 'phase40-qwen-to-phobert-chain-v12.ps1'
$expectedV9Sha256 = '63f47598fe81749b961ca7c5f056fe4e63925f2ad93f94f9beabafd047246b26'
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    'phase40-controller-v12-' + [Guid]::NewGuid().ToString('N')
)
$loadedModule = $null

function Assert-True {
    param(
        [Parameter(Mandatory)][bool]$Condition,
        [Parameter(Mandatory)][string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

function Assert-ThrowsLike {
    param(
        [Parameter(Mandatory)][scriptblock]$Action,
        [Parameter(Mandatory)][string]$Pattern,
        [Parameter(Mandatory)][string]$Message
    )
    $didThrow = $false
    $actualMessage = ''
    try {
        $null = & $Action
    }
    catch {
        $didThrow = $true
        $actualMessage = $_.Exception.Message
    }
    if (-not $didThrow) {
        throw "$Message (no exception)"
    }
    if ($actualMessage -notlike $Pattern) {
        throw "$Message (unexpected exception: $actualMessage)"
    }
}

function Get-ControllerFunctionText {
    param(
        [Parameter(Mandatory)][string]$ControllerPath,
        [Parameter(Mandatory)][string]$FunctionName
    )
    $tokens = $null
    $errors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseFile(
        $ControllerPath,
        [ref]$tokens,
        [ref]$errors
    )
    Assert-True ($errors.Count -eq 0) "$ControllerPath does not parse"
    $matches = @($ast.FindAll({
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $node.Name -eq $FunctionName
    }, $true))
    Assert-True ($matches.Count -eq 1) `
        "expected exactly one $FunctionName function in $ControllerPath"
    return $matches[0].Extent.Text
}

function Import-SyntheticTrainingModule {
    param(
        [Parameter(Mandatory)][string]$ControllerPath,
        [Parameter(Mandatory)][string]$Label
    )
    $trainingFunction = Get-ControllerFunctionText `
        -ControllerPath $ControllerPath `
        -FunctionName 'Invoke-PhoBertTraining'
    $modulePath = Join-Path $testRoot "$Label-training.psm1"
    $moduleWrappers = @'
$script:runId = 'synthetic-run'
$script:lastPythonInvocation = $null

function Invoke-PythonCaptured {
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$Name
    )
    $script:lastPythonInvocation = [pscustomobject]@{
        Name = $Name
        Arguments = [string[]]$Arguments
    }
    return 0
}

function Invoke-SyntheticFreshTraining {
    return Invoke-PhoBertTraining
}

function Invoke-SyntheticResumeTraining {
    param([Parameter(Mandatory)][string]$Checkpoint)
    return Invoke-PhoBertTraining `
        -ResumeFromCheckpoint $Checkpoint `
        -Name 'synthetic-resume'
}

function Get-SyntheticPythonInvocation {
    return $script:lastPythonInvocation
}

Export-ModuleMember -Function @(
    'Invoke-SyntheticFreshTraining',
    'Invoke-SyntheticResumeTraining',
    'Get-SyntheticPythonInvocation'
)
'@
    $moduleText = $trainingFunction + "`n`n" + $moduleWrappers
    [System.IO.File]::WriteAllText(
        $modulePath,
        $moduleText,
        [System.Text.UTF8Encoding]::new($false)
    )
    return Import-Module -Name $modulePath -Force -PassThru -DisableNameChecking
}

try {
    [void](New-Item -ItemType Directory -Path $testRoot)
    Assert-True ((Get-FileHash -LiteralPath $v9Controller -Algorithm SHA256).Hash.ToLowerInvariant() -eq
        $expectedV9Sha256) 'frozen v9 controller SHA-256 changed'

    $loadedModule = Import-SyntheticTrainingModule `
        -ControllerPath $v9Controller `
        -Label 'v9'
    Assert-ThrowsLike {
        Invoke-SyntheticFreshTraining
    } '*The path is empty*' 'v9 fresh launch no longer reproduces its frozen failure'
    Assert-True ($null -eq (Get-SyntheticPythonInvocation)) `
        'v9 reached the synthetic Python launcher despite the empty-path failure'
    Remove-Module -ModuleInfo $loadedModule -Force
    $loadedModule = $null

    $loadedModule = Import-SyntheticTrainingModule `
        -ControllerPath $v12Controller `
        -Label 'v12'
    $freshExit = Invoke-SyntheticFreshTraining
    Assert-True ($freshExit -eq 0) 'v12 fresh launch did not reach the synthetic launcher'
    $freshInvocation = Get-SyntheticPythonInvocation
    $freshArguments = [string[]]$freshInvocation.Arguments
    Assert-True ($freshInvocation.Name -eq 'phobert-train-fresh') `
        'v12 fresh operation name changed'
    Assert-True ($freshArguments -notcontains '--resume-from-checkpoint') `
        'v12 fresh arguments contain a resume flag'
    Assert-True ($freshArguments -contains '..\phobert-work-v12\phase40-phobert-full-seed42-v12') `
        'v12 fresh arguments do not target the v12 work root'
    Assert-True ($freshArguments -notcontains '..\phobert-work-v11\phase40-phobert-full-seed42-v11') `
        'v12 fresh arguments still target the failed v11 work root'
    Assert-True ($freshArguments -contains '..\transfer-root-v5\data\models\phase40\full-run-request.json') `
        'v12 fresh arguments do not use the v5 request'
    Assert-True ($freshArguments -contains '..\transfer-root-v5\data\models\phase40\input\phase40-train-validation.zip') `
        'v12 fresh arguments do not use the v5 input authority'
    Assert-True ($freshArguments -contains '..\transfer-root-v5\data\models\phase40\base\phobert-base-v2') `
        'v12 fresh arguments do not use the request-bound v5 base model'
    Assert-True ($freshArguments -notcontains '..\transfer-root-v3\data\models\phase40\base\phobert-base-v2') `
        'v12 fresh arguments still cross request roots to the v3 base model'

    # Boundary neighbor for the empty-string defect: the smallest non-empty
    # checkpoint must still take the resume branch and be canonicalized.
    $checkpoint = 'c'
    $resumeExit = Invoke-SyntheticResumeTraining -Checkpoint $checkpoint
    Assert-True ($resumeExit -eq 0) 'v12 resume launch did not reach the synthetic launcher'
    $resumeInvocation = Get-SyntheticPythonInvocation
    $resumeArguments = [string[]]$resumeInvocation.Arguments
    $resumeFlagIndex = [Array]::IndexOf(
        $resumeArguments,
        '--resume-from-checkpoint'
    )
    Assert-True ($resumeInvocation.Name -eq 'synthetic-resume') `
        'v12 resume operation name changed'
    Assert-True ($resumeFlagIndex -ge 0 -and
        $resumeFlagIndex + 1 -lt $resumeArguments.Count) `
        'v12 resume arguments omit the checkpoint value'
    Assert-True ($resumeArguments[$resumeFlagIndex + 1] -eq
        [System.IO.Path]::GetFullPath($checkpoint)) `
        'v12 resume checkpoint is not canonicalized'

    Write-Output 'PASS phase40 controller v12 CPU-only launch scenarios=3'
}
finally {
    if ($null -ne $loadedModule) {
        Remove-Module -ModuleInfo $loadedModule -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $testRoot) {
        $resolvedTestRoot = [System.IO.Path]::GetFullPath($testRoot)
        $resolvedTemp = [System.IO.Path]::GetFullPath(
            [System.IO.Path]::GetTempPath()
        ).TrimEnd([System.IO.Path]::DirectorySeparatorChar) +
            [System.IO.Path]::DirectorySeparatorChar
        if (-not $resolvedTestRoot.StartsWith(
            $resolvedTemp,
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
            throw "Refusing unsafe test cleanup target: $resolvedTestRoot"
        }
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
    }
}
