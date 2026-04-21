$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$baseUrl = "http://127.0.0.1:5000/api"
$stdoutLog = Join-Path $projectRoot "backend_stdout.log"
$stderrLog = Join-Path $projectRoot "backend_stderr.log"

if (-not (Test-Path $pythonPath)) {
    throw "No se encontro Python en: $pythonPath"
}

if (Test-Path $stdoutLog) {
    Remove-Item $stdoutLog -Force
}
if (Test-Path $stderrLog) {
    Remove-Item $stderrLog -Force
}

& $pythonPath seed_rooms.py | Out-Null

function Post-Json {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [hashtable]$Body
    )

    Invoke-RestMethod -Uri $Url -Method Post -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 10)
}

$serverProcess = $null

try {
    $escapedPythonPath = $pythonPath.Replace('"', '""')
    $escapedStdoutLog = $stdoutLog.Replace('"', '""')
    $escapedStderrLog = $stderrLog.Replace('"', '""')
    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = "cmd.exe"
    $processInfo.Arguments = "/c """"$escapedPythonPath"" run_server.py 1>> ""$escapedStdoutLog"" 2>> ""$escapedStderrLog"""""
    $processInfo.WorkingDirectory = $projectRoot
    $processInfo.UseShellExecute = $false
    $processInfo.CreateNoWindow = $true

    $serverProcess = New-Object System.Diagnostics.Process
    $serverProcess.StartInfo = $processInfo
    $null = $serverProcess.Start()

    $healthy = $false
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Milliseconds 700
        try {
            $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
            if ($health.status -eq "ok") {
                $healthy = $true
                break
            }
        } catch {
        }
    }

    if (-not $healthy) {
        $stderrText = if (Test-Path $stderrLog) { Get-Content $stderrLog -Raw } else { "" }
        throw "El backend no inicio correctamente. $stderrText"
    }

    $stamp = Get-Date -Format "yyyyMMddHHmmss"
    $email = "qa+$stamp@example.com"
    $results = @()

    $register = Post-Json "$baseUrl/auth/register" @{
        first_name = "QA"
        last_name = "Flow"
        email = $email
        phone = "+59170000000"
        password = "TestPass123!"
    }
    $results += [pscustomobject]@{ step = "register"; ok = ($null -ne $register.access_token); detail = $register.message }

    $login = Post-Json "$baseUrl/auth/login" @{
        email = $email
        password = "TestPass123!"
    }
    $results += [pscustomobject]@{ step = "login"; ok = ($null -ne $login.access_token); detail = $login.message }

    $me = Invoke-RestMethod -Uri "$baseUrl/auth/me" -Method Get -Headers @{ Authorization = "Bearer $($login.access_token)" }
    $results += [pscustomobject]@{ step = "me"; ok = ($me.user.email -eq $email); detail = $me.user.email }

    $checkIn = (Get-Date).AddDays(2).ToString("yyyy-MM-dd")
    $checkOut = (Get-Date).AddDays(4).ToString("yyyy-MM-dd")
    $rooms = Invoke-RestMethod -Uri "$baseUrl/rooms" -Method Get
    $results += [pscustomobject]@{ step = "rooms"; ok = ($rooms.total -gt 0); detail = "total=$($rooms.total)" }

    $availableRooms = Invoke-RestMethod -Uri "$baseUrl/rooms/availability?check_in=$checkIn&check_out=$checkOut" -Method Get
    $room = $availableRooms.items | Select-Object -First 1
    $results += [pscustomobject]@{ step = "availability"; ok = ($availableRooms.total -gt 0 -and $null -ne $room.id); detail = "room_id=$($room.id) available_total=$($availableRooms.total)" }

    $reservation = Post-Json "$baseUrl/reservations" @{
        room_id = $room.id
        check_in = $checkIn
        check_out = $checkOut
        adults = 2
        children = 0
        first_name = "QA"
        last_name = "Flow"
        email = $email
        phone = "+59170000000"
        country = "Bolivia"
        document_id = "DOC-$stamp"
        travel_reason = "vacation"
        special_requests = "Late check-in"
        services = @(
            @{ name = "Desayuno buffet"; price = 20 },
            @{ name = "Spa"; price = 35 }
        )
    }
    $results += [pscustomobject]@{ step = "reservation"; ok = ($null -ne $reservation.reservation.id); detail = $reservation.reservation.reservation_code }

    $paymentReservation = Post-Json "$baseUrl/payments/simulate" @{
        context_type = "reservation"
        reservation_id = $reservation.reservation.id
        method = "card"
    }
    $results += [pscustomobject]@{ step = "reservation_payment"; ok = ($paymentReservation.reservation.status -eq "confirmed"); detail = $paymentReservation.payment.payment_code }

    $plans = Invoke-RestMethod -Uri "$baseUrl/ads/plans" -Method Get
    $plan = $plans.items | Select-Object -First 1
    $results += [pscustomobject]@{ step = "ad_plans"; ok = ($plans.total -gt 0 -and $null -ne $plan.id); detail = "plan=$($plan.name)" }

    $ad = Post-Json "$baseUrl/ads" @{
        ad_plan_id = $plan.id
        company_name = "QA Company"
        contact_name = "QA Contact"
        contact_email = $email
        contact_phone = "+59170000000"
        title = "Promo QA"
        category = "turismo"
        description = "Anuncio de prueba end to end"
    }
    $results += [pscustomobject]@{ step = "ad_create"; ok = ($ad.ad.status -eq "pending_payment"); detail = "ad_id=$($ad.ad.id)" }

    $paymentAd = Post-Json "$baseUrl/payments/simulate" @{
        context_type = "ad"
        ad_id = $ad.ad.id
        method = "card"
    }
    $results += [pscustomobject]@{ step = "ad_payment"; ok = ($paymentAd.ad.status -eq "active" -and $paymentAd.ad.is_paid); detail = $paymentAd.payment.payment_code }

    $ads = Invoke-RestMethod -Uri "$baseUrl/ads?include_plans=true" -Method Get
    $createdAd = $ads.items | Where-Object { $_.id -eq $ad.ad.id } | Select-Object -First 1
    $results += [pscustomobject]@{ step = "ad_list"; ok = ($null -ne $createdAd -and $ads.plans.Count -gt 0); detail = "listed=$($null -ne $createdAd) plans=$($ads.plans.Count)" }

    $failed = $results | Where-Object { -not $_.ok }
    $results | Format-Table -AutoSize

    if ($failed) {
        throw "El smoke test detecto fallos en: $($failed.step -join ', ')"
    }
} finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
