<#
.SYNOPSIS
详细计算项目代码和文档的总行数，并列出代码行数最多的前20个文件。

.DESCRIPTION
此脚本递归地遍历指定目录，根据扩展名列表计算“代码行数”和“文档行数”。
它会精确地跳过所有层级上名称匹配 IgnoreDirectories 列表的文件夹中的所有文件。
最后，它会输出代码行数最多的前20个文件及其行数。

.PARAMETER Path
要开始搜索的根目录。默认为当前目录 (./)。

.PARAMETER CodeExtensions
要包含在“代码”统计中的文件扩展名数组。

.PARAMETER DocExtensions
要包含在“文档”统计中的文件扩展名数组。

.PARAMETER IgnoreDirectories
要跳过的目录名称数组。

.EXAMPLE
# 运行并使用默认的忽略列表（包含 node_modules），确保排除所有子文件。
# 如果运行出现乱码，请确保脚本以 'UTF-8 with BOM' 编码保存，或在执行前运行 $OutputEncoding = [System.Text.Encoding]::UTF8
PS C:\Project> .\Count-ProjectLines_Final.ps1

.NOTES
作者: Gemini (Google AI)
版本修正: 此版本专注于解决 'node_modules' 等目录在任意层级未能被排除的问题。
#>
param(
    [Parameter(Mandatory=$false)]
    [string]$Path = ".",

    [Parameter(Mandatory=$false)]
    [string[]]$CodeExtensions = @("c", "cpp", "h", "hpp", "java", "py", "js", "ts", "cs", "rb", "go", "swift", "php", "sh", "ps1"),

    [Parameter(Mandatory=$false)]
    [string[]]$DocExtensions = @("md", "txt"),
    
    [Parameter(Mandatory=$false)]
    [string[]]$IgnoreDirectories = @("bin", "obj", "node_modules", ".git", ".svn", ".vscode", "vendor", "build", "dist", ".memories", ".cursor", ".backup", "sidecar")
)

# 设置编码以防止乱码 (仅在 Windows PowerShell 中可能需要)
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop' # 确保脚本在 Get-ChildItem 遇到权限问题时停止，而不是继续

# --- 辅助函数 ---

# 函数：根据扩展名列表构建过滤器（*.ext1,*.ext2）
function Get-IncludeFilter ($Extensions) {
    $Filter = @()
    foreach ($ext in $Extensions) {
        $Filter += "*.$($ext.Trimstart('.'))"
    }
    return $Filter
}

# 函数：执行行数统计（返回文件对象列表）
function Measure-CodeFileLines ($SearchPath, $Filter, $IgnoreRegex) {
    # 由于 Get-ChildItem 可能会遇到路径过长或权限问题，使用 try/catch
    try {
        # 1. 递归查找文件
        $files = Get-ChildItem -Path $SearchPath -Recurse -File -Include $Filter -ErrorAction SilentlyContinue | 
                 # 2. 过滤掉位于忽略目录中的文件
                 Where-Object { 
                     # 检查 FullName 属性中是否匹配忽略的目录模式
                     # -notmatch 是大小写不敏感的
                     -not ($_.FullName -match $IgnoreRegex)
                 }
        
        $results = @()
        
        # 3. 遍历文件，逐个统计行数并创建自定义对象
        foreach ($file in $files) {
            # 使用 (Get-Content $file).Length 统计行数
            $LineCount = (Get-Content $file.FullName -ErrorAction SilentlyContinue).Length
            
            if ($LineCount -gt 0) {
                $results += [PSCustomObject]@{
                    # 仅保留相对路径，使输出更简洁
                    Name      = $file.FullName.Replace($SearchPath + [IO.Path]::DirectorySeparatorChar, "")
                    LineCount = $LineCount
                }
            }
        }

        return $results
    }
    catch {
        Write-Error "在路径 $SearchPath 统计代码文件时发生错误: $($_.Exception.Message)"
        return @()
    }
}

# 函数：执行行数统计（仅返回总行数）
function Measure-DocTotalLines ($SearchPath, $Filter, $IgnoreRegex) {
    try {
        # 1. 查找文件并过滤忽略目录
        $files = Get-ChildItem -Path $SearchPath -Recurse -File -Include $Filter -ErrorAction SilentlyContinue | 
                 Where-Object { 
                     -not ($_.FullName -match $IgnoreRegex)
                 }
        
        # 2. 获取内容并统计总行数
        $TotalLines = $files | 
                      Get-Content -ErrorAction SilentlyContinue | 
                      Measure-Object -Line

        return $TotalLines.Lines
    }
    catch {
        Write-Error "在路径 $SearchPath 统计文档文件时发生错误: $($_.Exception.Message)"
        return 0
    }
}

# --- 主逻辑开始 ---

# 1. 设置搜索路径
$SearchPath = Get-Item -Path $Path | Select-Object -ExpandProperty FullName

# 2. 构造忽略目录的正则表达式 (关键改进)
# 目标模式：(\\|/) (目录1|目录2|...) (\\|/)
# 确保匹配的是路径分隔符 ' \ ' 或 ' / ' 之间的完整目录名称
$EscapedIgnores = $IgnoreDirectories | ForEach-Object { [regex]::Escape($_) }
$PatternPart = $EscapedIgnores -join '|'

# 正则表达式解释:
# (?:\\|/)    -> 匹配一个 Windows 或 Unix/Linux 的路径分隔符 (非捕获组)
# $PatternPart -> 匹配 'node_modules' 或 'bin' 等
$IgnoreRegexPattern = "(?:\\|/)$PatternPart(?:\\|/)"

Write-Host "开始详细统计目录: $SearchPath" -ForegroundColor Yellow
Write-Host "将精确忽略所有层级上的以下目录中的文件: $($IgnoreDirectories -join ', ')" -ForegroundColor Yellow
Write-Host "----------------------------------------"

# 3. 统计代码行数（返回详细列表）
Write-Host "-> 统计代码文件 (Code Extensions): $($CodeExtensions -join ', ')..." -ForegroundColor Cyan
$CodeFilter = Get-IncludeFilter -Extensions $CodeExtensions
$CodeFiles = Measure-CodeFileLines -SearchPath $SearchPath -Filter $CodeFilter -IgnoreRegex $IgnoreRegexPattern
$TotalCodeLines = ($CodeFiles | Measure-Object -Property LineCount -Sum).Sum

# 4. 统计文档行数（返回总行数）
Write-Host "-> 统计文档文件 (Document Extensions): $($DocExtensions -join ', ')..." -ForegroundColor Cyan
$DocFilter = Get-IncludeFilter -Extensions $DocExtensions
$TotalDocLines = Measure-DocTotalLines -SearchPath $SearchPath -Filter $DocFilter -IgnoreRegex $IgnoreRegexPattern

# 5. 汇总和输出结果
$TotalAllLines = $TotalCodeLines + $TotalDocLines

# ... (输出部分保持不变) ...

Write-Host ""
Write-Host "================ 统计结果 ================" -ForegroundColor Green
Write-Host "项目路径: $SearchPath" -ForegroundColor Green
Write-Host "----------------------------------------"
Write-Host " 代码总行数 (Code Lines): $TotalCodeLines" -ForegroundColor Cyan
Write-Host " 文档总行数 (Doc Lines):  $TotalDocLines" -ForegroundColor Cyan
Write-Host "----------------------------------------"
Write-Host " 全部文件总行数 (Total):  $TotalAllLines" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""


# 6. 输出代码量最多的前 20 个文件
if ($TotalCodeLines -gt 0) {
    Write-Host "========== 代码行数最多的前 20 个文件 ==========" -ForegroundColor Yellow
    
    # 排序并选择前20个
    $TopFiles = $CodeFiles | 
                Sort-Object -Property LineCount -Descending | 
                Select-Object -First 20 -Property LineCount, Name
    
    # 格式化输出
    $TopFiles | Format-Table -AutoSize -Property @{
        Label = "行数"; Expression = {$_.LineCount}
    }, @{
        Label = "文件名 (相对路径)"; Expression = {$_.Name}
    }
    
    Write-Host "==============================================" -ForegroundColor Yellow
}