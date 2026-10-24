$ErrorActionPreference = "Stop"
$repo = if ($env:HACHE_REPO) { $env:HACHE_REPO } else { "https://github.com/rfi-irfos/claude-cache-idiocracy.git" }
$dir = if ($env:HACHE_DIR) { $env:HACHE_DIR } else { Join-Path $HOME ".claude\claude-cache-idiocracy" }
if (Test-Path (Join-Path $dir ".git")) { git -C $dir pull --ff-only }
elseif (Get-Command gh -ErrorAction SilentlyContinue) { gh repo clone rfi-irfos/claude-cache-idiocracy $dir }
else { git clone $repo $dir }
if ($LASTEXITCODE -ne 0) { throw "Repository checkout failed" }
$python = (Get-Command python -ErrorAction Stop).Source
& $python -m pip install --user --upgrade $dir
if ($LASTEXITCODE -ne 0) { throw "Python package installation failed" }
& $python -m hache_guard install
if ($LASTEXITCODE -ne 0) { throw "Claude settings installation failed" }
Write-Output "claude-cache-idiocracy installed; restart Claude Code."
