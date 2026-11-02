# Runs DAX queries against a local Analysis Services instance (Power BI Desktop with the model pbix open).
# Usage: run_dax.ps1 -Port 65523 -In queries.json -Out results.json
# queries.json: [{ "id": "...", "dax": "EVALUATE ..." }, ...]  ->  results.json: [{ id, ok, error, rows }]
param([int]$Port, [string]$In, [string]$Out, [int]$MaxRows = 5)
Add-Type -Path "C:\Program Files\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll"
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Port")
$conn.Open()
$queries = Get-Content -Raw -Encoding UTF8 $In | ConvertFrom-Json
$results = New-Object System.Collections.ArrayList
foreach ($q in $queries) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $q.dax
    $cmd.CommandTimeout = 120
    try {
        $reader = $cmd.ExecuteReader()
        $rows = New-Object System.Collections.ArrayList
        $n = 0
        while ($reader.Read()) {
            if ($n -lt $MaxRows) {
                $row = [ordered]@{}
                for ($c = 0; $c -lt $reader.FieldCount; $c++) {
                    $v = $reader.GetValue($c)
                    $row[$reader.GetName($c)] = if ($v -is [DBNull]) { $null } else { "$v" }
                }
                [void]$rows.Add($row)
            }
            $n++
        }
        $reader.Close()
        [void]$results.Add([ordered]@{ id = $q.id; ok = $true; count = $n; rows = $rows })
    } catch {
        [void]$results.Add([ordered]@{ id = $q.id; ok = $false; error = $_.Exception.Message })
    }
}
$conn.Close()
$results | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $Out
