# KEYWORDS: blender, path, cascade, resolve, 路徑解析, find_blender, preflight
<#
.SYNOPSIS
    Blender 可執行檔路徑六級 cascade 解析（跨機器，禁止寫死路徑）。
.DESCRIPTION
    解析順序（命中即停）：
      1. 工作區快取檔（-CacheFile，存在且路徑仍有效）
      2. 環境變數 BLENDER_PATH
      3. PATH（Get-Command blender）
      4. 登錄機碼 Uninstall 項（DisplayName 含 Blender → InstallLocation\blender.exe）
      5. 常見安裝位置 glob（Program Files / LOCALAPPDATA / Steam / Downloads portable）
      6. 全失敗 → exit 1，由 agent 問使用者一次並把答案寫進快取
    成功時輸出兩行：BLENDER_PATH=<exe> 與 BLENDER_VERSION=<version>，
    並（若有給 -CacheFile）把路徑寫進快取檔。
    注意：本檔必須以 UTF-8 BOM 保存——Windows PowerShell 5.1 對無 BOM 的
    UTF-8 中文註解會以 ANSI 誤讀，導致引號被吃掉、整份腳本語法崩壞（實測踩過）。
.EXAMPLE
    powershell -NoProfile -File find_blender.ps1 -CacheFile .capybala\blender-path.txt
#>
param(
    # 工作區快取檔路徑（建議 <workspace>\.capybala\blender-path.txt）；可省略
    [string]$CacheFile = ""
)

# 常見安裝位置 glob（依命中率排序；Steam/Downloads 是 portable 常見落點）
$GLOB_PATTERNS = @(
    'C:\Program Files\Blender Foundation\Blender*\blender.exe',
    'D:\Program Files\Blender Foundation\Blender*\blender.exe',
    'C:\Program Files (x86)\Blender Foundation\Blender*\blender.exe',
    (Join-Path $env:LOCALAPPDATA 'Programs\Blender*\blender.exe'),
    'C:\SteamLibrary\steamapps\common\Blender\blender.exe',
    (Join-Path $env:USERPROFILE 'Downloads\blender*\blender.exe')
)

# 登錄 Uninstall 機碼根（HKLM 64/32 + HKCU）
$REG_ROOTS = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)

function Resolve-BlenderPath {
    # 1. 工作區快取
    if ($CacheFile -and (Test-Path $CacheFile)) {
        $cached = (Get-Content $CacheFile -Raw).Trim()
        if ($cached -and (Test-Path $cached)) {
            Write-Host "RESOLVE_SOURCE=cache"
            return $cached
        }
        Write-Host "WARN: 快取路徑已失效，繼續往下解析: $cached"
    }
    # 2. 環境變數
    if ($env:BLENDER_PATH -and (Test-Path $env:BLENDER_PATH)) {
        Write-Host "RESOLVE_SOURCE=env:BLENDER_PATH"
        return $env:BLENDER_PATH
    }
    # 3. PATH
    $onPath = Get-Command blender -ErrorAction SilentlyContinue
    if ($onPath) {
        Write-Host "RESOLVE_SOURCE=PATH"
        return $onPath.Source
    }
    # 4. 登錄機碼
    foreach ($root in $REG_ROOTS) {
        $hit = Get-ItemProperty $root -ErrorAction SilentlyContinue |
            Where-Object {
                $_.DisplayName -like '*Blender*' -and
                $_.InstallLocation -and
                (Test-Path (Join-Path $_.InstallLocation 'blender.exe'))
            } |
            Select-Object -First 1
        if ($hit) {
            Write-Host "RESOLVE_SOURCE=registry"
            return (Join-Path $hit.InstallLocation 'blender.exe')
        }
    }
    # 5. 常見位置 glob（同 pattern 多版本時取路徑名最大者 = 最新版）
    foreach ($pattern in $GLOB_PATTERNS) {
        $hit = Get-Item $pattern -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($hit) {
            Write-Host "RESOLVE_SOURCE=glob"
            return $hit.FullName
        }
    }
    return $null
}

$exe = Resolve-BlenderPath
if (-not $exe) {
    # 6. 全失敗：人類可讀訊息 + 非零 exit（PROJECT-RULES: fail fast 不 silent）
    [Console]::Error.WriteLine("BLENDER_NOT_FOUND: 六級 cascade（快取/環境變數/PATH/登錄/常見位置 glob）全部失敗。")
    [Console]::Error.WriteLine("請向使用者詢問 blender.exe 的完整路徑一次，並寫入快取檔: $CacheFile")
    exit 1
}

# 驗證可執行檔真的能跑（順帶取得版本，等同 preflight 的一半）
# 注意：不可用 `| Select-Object -First 1` 直接截管線——PS 5.1 會提前終止
# 原生進程導致 LASTEXITCODE=-1（實測踩過）；先收完整輸出再取第一行。
$verOut = & $exe --version 2>$null
$versionLine = if ($verOut) { ($verOut | Select-Object -First 1) } else { $null }
if ($LASTEXITCODE -ne 0 -or -not $versionLine) {
    [Console]::Error.WriteLine("BLENDER_BROKEN: 找到 $exe 但 --version 執行失敗 (exit=$LASTEXITCODE)，請重新確認安裝。")
    exit 1
}

# 寫入快取（下一輪直接命中第 1 級）
if ($CacheFile) {
    $cacheDir = Split-Path $CacheFile -Parent
    if ($cacheDir -and -not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null }
    Set-Content -Path $CacheFile -Value $exe -Encoding UTF8
    Write-Host "CACHE_WRITTEN=$CacheFile"
}

Write-Host "BLENDER_PATH=$exe"
Write-Host "BLENDER_VERSION=$versionLine"
exit 0
