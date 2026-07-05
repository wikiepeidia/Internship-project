# Phase 30 Cold-Latency Runbook

Use this runbook only after Plan 30-01 has landed. It measures true post-reboot cold-boot-to-first-answer latency through the real `vnphish demo` browser path.

Diagnostic runs without reboot are allowed for script testing, but they do not satisfy PERF-01 or PERF-03.

## AC / High Performance Evidence Run

1. Plug in AC power.
2. Set Windows power mode to High Performance or best performance.
3. Reboot the laptop.
4. After login, open a fresh PowerShell terminal.
5. Change to the project root:

```powershell
cd "C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project"
```

6. Run the evidence measurement:

```powershell
python scripts\measure_cold_latency.py --condition ac-high-performance --run-purpose evidence --post-reboot-confirmed
```

7. Copy the JSON path printed by the script.

## Battery / Balanced Evidence Run

1. Unplug AC power.
2. Set Windows power mode to Balanced.
3. Reboot the laptop.
4. After login, open a fresh PowerShell terminal.
5. Change to the project root:

```powershell
cd "C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project"
```

6. Run the evidence measurement:

```powershell
python scripts\measure_cold_latency.py --condition battery-balanced --run-purpose evidence --post-reboot-confirmed
```

7. Copy the JSON path printed by the script.

## Resume Signal

Reply with:

```text
latency-evidence-ready
AC: <path to ac-high-performance JSON>
Battery: <path to battery-balanced JSON>
```

If either run fails, paste the script output and say which condition failed.

## Important

Do not apply any source-code performance fix before these two evidence artifacts are compared. PERF-02 allows no blind tuning: either the comparison identifies one specific measured bottleneck, or the correct result is "no fix applied."
