function ConvertTo-RunicornHashtable($Value) {
  if ($null -eq $Value) {
    return $null
  }
  if ($Value -is [System.Collections.IDictionary]) {
    $result = @{}
    foreach ($key in $Value.Keys) {
      $result[$key] = ConvertTo-RunicornHashtable $Value[$key]
    }
    return $result
  }
  if ($Value -is [System.Management.Automation.PSCustomObject]) {
    $result = @{}
    foreach ($prop in $Value.PSObject.Properties) {
      $result[$prop.Name] = ConvertTo-RunicornHashtable $prop.Value
    }
    return $result
  }
  if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
    $items = @()
    foreach ($item in $Value) {
      $items += ,(ConvertTo-RunicornHashtable $item)
    }
    return $items
  }
  return $Value
}

function Merge-RunicornHashtable([hashtable]$Base, [hashtable]$Override) {
  $merged = @{}
  foreach ($key in $Base.Keys) {
    $merged[$key] = $Base[$key]
  }
  foreach ($key in $Override.Keys) {
    if ($merged.ContainsKey($key) -and $merged[$key] -is [hashtable] -and $Override[$key] -is [hashtable]) {
      $merged[$key] = Merge-RunicornHashtable $merged[$key] $Override[$key]
    } else {
      $merged[$key] = $Override[$key]
    }
  }
  return $merged
}

function Get-RunicornBuildConfig([string]$ConfigDir) {
  $basePath = Join-Path $ConfigDir "build_config.json"
  if (-not (Test-Path $basePath)) {
    throw "Missing build config: $basePath"
  }
  $baseConfig = ConvertTo-RunicornHashtable (Get-Content -Raw -Encoding UTF8 $basePath | ConvertFrom-Json)

  $localPath = Join-Path $ConfigDir "build_config.local.json"
  if (Test-Path $localPath) {
    $localConfig = ConvertTo-RunicornHashtable (Get-Content -Raw -Encoding UTF8 $localPath | ConvertFrom-Json)
    return Merge-RunicornHashtable $baseConfig $localConfig
  }
  return $baseConfig
}

function Push-RunicornProxyEnv([hashtable]$CommonConfig) {
  $tracked = @("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy")
  $backup = @{}
  foreach ($name in $tracked) {
    $backup[$name] = [System.Environment]::GetEnvironmentVariable($name, "Process")
  }

  $httpProxy = $CommonConfig["httpProxy"]
  $httpsProxy = $CommonConfig["httpsProxy"]
  $noProxy = $CommonConfig["noProxy"]

  foreach ($name in @("HTTP_PROXY", "http_proxy")) {
    [System.Environment]::SetEnvironmentVariable($name, $httpProxy, "Process")
  }
  foreach ($name in @("HTTPS_PROXY", "https_proxy")) {
    [System.Environment]::SetEnvironmentVariable($name, $httpsProxy, "Process")
  }
  foreach ($name in @("NO_PROXY", "no_proxy")) {
    [System.Environment]::SetEnvironmentVariable($name, $noProxy, "Process")
  }
  return $backup
}

function Pop-RunicornProxyEnv([hashtable]$Backup) {
  foreach ($name in $Backup.Keys) {
    [System.Environment]::SetEnvironmentVariable($name, $Backup[$name], "Process")
  }
}
