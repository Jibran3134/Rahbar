[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [ValidateSet('setup','tools','test','lint','manifests','cluster','images','apply','index','eval','check','e2e','dev')]
    [string]$Task = 'test',
    [string]$Tag,
    [ValidateSet('dev','prod','ci')][string]$Overlay = 'dev',
    [string]$Context = 'rahbar',
    [string]$Api = 'http://127.0.0.1:8085',
    [string]$Registry = '',
    [string]$OllamaUrl = 'http://host.minikube.internal:11434',
    [string]$HostCidr = '192.168.65.254/32'
)
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
$Python = Join-Path $RepoRoot '.venv/Scripts/python.exe'
function Invoke-Native([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe exited with native status $LASTEXITCODE" }
}
function Find-Tool([string]$Name) {
    foreach ($candidate in @((Join-Path $RepoRoot ".venv/tools/bin/$Name.exe"), (Join-Path $RepoRoot ".venv/tools/$Name.exe"))) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw "$Name is missing. Run scripts/dev.ps1 tools first."
}
Push-Location $RepoRoot
try {
    if (-not $Tag) {
        $Tag = (& git rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0) { throw 'Cannot determine image revision' }
    }
    switch ($Task) {
        'setup' {
            if (-not (Test-Path -LiteralPath $Python)) { Invoke-Native 'py' @('-3.12','-m','venv','.venv') }
            Invoke-Native $Python @('-m','pip','install','-r','api/requirements-dev.txt','-r','indexer/requirements-dev.txt')
        }
        'tools' { Invoke-Native $Python @('scripts/bootstrap_tools.py','minikube','kubeconform','trivy','kind','--manifests') }
        'test' {
            foreach ($part in @('api','indexer')) {
                Push-Location $part
                try { Invoke-Native $Python @('-m','pytest','-q','-p','no:cacheprovider') } finally { Pop-Location }
            }
            Invoke-Native $Python @('-m','pytest','eval/tests','scripts/tests','-q','-p','no:cacheprovider')
            Invoke-Native 'node' @('scripts/ui.test.cjs')
        }
        'lint' {
            Invoke-Native $Python @('-m','ruff','check','api','indexer','eval','corpus','scripts')
            foreach ($part in @(@('api','app'),@('indexer','pipeline'))) {
                Push-Location $part[0]
                try { Invoke-Native $Python @('-m','mypy',$part[1]) } finally { Pop-Location }
            }
        }
        'manifests' {
            Invoke-Native $Python @('scripts/check_platform.py')
            foreach ($profile in @('dev','prod','ci')) {
                Invoke-Native $Python @('scripts/deploy.py','render','--overlay',$profile,'--tag',$Tag,'--registry',$Registry)
                Invoke-Native (Find-Tool 'kubeconform') @('-strict','-summary','-kubernetes-version','1.35.0',".venv/platform/$profile/rendered.yaml")
            }
        }
        'cluster' {
            Invoke-Native (Find-Tool 'minikube') @('start','-p','rahbar','--driver=docker','--cni=calico','--memory=6144','--cpus=4','--keep-context','--kubernetes-version=v1.37.0')
            Invoke-Native (Find-Tool 'minikube') @('addons','enable','ingress','-p','rahbar')
            Invoke-Native (Find-Tool 'minikube') @('addons','enable','metrics-server','-p','rahbar')
        }
        'images' {
            $names = @()
            foreach ($part in @('api','indexer','ui')) {
                $image = "rahbar-${part}:$Tag"
                Invoke-Native 'docker' @('build','-t',$image,$part)
                $names += $image
            }
            Invoke-Native (Find-Tool 'minikube') (@('image','load','-p','rahbar') + $names)
        }
        'apply' {
            Invoke-Native $Python @('scripts/deploy.py','apply','--overlay',$Overlay,'--tag',$Tag,'--registry',$Registry,'--context',$Context,'--ollama-url',$OllamaUrl,'--host-cidr',$HostCidr)
        }
        'index' {
            $job = 'manual-reindex-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
            Invoke-Native 'kubectl' @('--context',$Context,'-n','rahbar','create','job','--from=cronjob/reindex',$job)
            Invoke-Native 'kubectl' @('--context',$Context,'-n','rahbar','wait','--for=condition=complete',"job/$job",'--timeout=1800s')
        }
        'eval' { Invoke-Native $Python @('eval/run_eval.py','--api',$Api,'--host','rahbar.local','--golden','eval/golden.yaml','--baseline','eval/baseline.json','--out','.venv/real-results.json','--bypass-cache') }
        'check' { Invoke-Native $Python @('scripts/check_submission.py') }
        'e2e' { Invoke-Native $Python @('scripts/ci_e2e.py','--tag',$Tag,'--registry',$Registry) }
        'dev' {
            $env:RETRIEVER='stub'; $env:LLM_PROVIDER='stub'; $env:SERVE_UI_DIR='../ui'
            Push-Location api
            try { Invoke-Native $Python @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') } finally { Pop-Location }
        }
    }
} finally { Pop-Location }
