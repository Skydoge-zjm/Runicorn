$body = @{ path = 'D:\RunicornData' } | ConvertTo-Json
try {
  Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/config/user_root_dir' `
    -Method POST -ContentType 'application/json' -Body $body
} catch {
  $resp = $_.Exception.Response
  if ($resp -ne $null) {
    $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
    $text = $reader.ReadToEnd()
    Write-Host "StatusCode:" $resp.StatusCode
    Write-Host "Response body:" $text
  } else {
    Write-Error $_
  }
}