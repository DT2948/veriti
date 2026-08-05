# Veriti Performance Benchmarks

This suite measures Veriti's real privacy, upload, verification, and dashboard paths without a telemetry platform. It does not contain published performance claims or favorable hard-coded thresholds. Every output records whether Gemini was **live**, **stubbed**, or **disabled**.

## What Is Measured

| Area | Operations and outputs |
| --- | --- |
| Android privacy | Total processing, copy/encoding, EXIF removal, location coarsening, validation, integrity checks, caption redaction, input/output bytes, and correctness flags |
| FastAPI | Request and submission latency, throughput, status/error rates, and client/server peak concurrency |
| Verification | Total verification, Gemini, clustering/scoring, summary generation, cleanup, fallback state, and final status |
| Dashboard | Full refresh, incidents fetch, map fetch, approximate propagation delay, active refreshes, and peak active refreshes |

Percentiles use linear interpolation at rank **(n - 1) * p**. Median describes typical latency; p95 describes the slower tail.

## Setup

Install the existing backend dependencies:

~~~powershell
cd C:\veriti
python -m pip install -r backend\requirements.txt
~~~

Generate deterministic fixtures. The full profile creates small, medium, and large JPEG/PNG images plus invalid inputs:

~~~powershell
python scripts\generate_privacy_benchmark_fixtures.py --profile full --output benchmark_fixtures\privacy
~~~

Fixtures use seed **20260418** by default. The manifest records dimensions, format, file size, metadata flags, expected outcome, SHA-256, and per-fixture seed. Rendered PII is synthetic. Veriti redacts caption text but does not perform OCR, so the tests do not claim removal of text rendered inside an image.

## Automated Tests

Run backend correctness, instrumentation, statistics, load-runner, and end-to-end-runner tests:

~~~powershell
$env:PYTHONPATH="backend"
python -m unittest discover -s backend\tests -v
~~~

These tests use mock HTTP transports and deterministic Gemini modes. They do not call live Gemini and do not assert timing thresholds.

## Android Benchmark

Generate the fixture assets consumed by the instrumentation APK:

~~~powershell
python scripts\generate_privacy_benchmark_fixtures.py --profile full --output mobile\android\app\src\androidTest\assets\privacy
~~~

Connect a device or emulator, then run the benchmark:

~~~powershell
cd mobile\android
.\gradlew connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.veriti.app.pipeline.PrivacyBenchmarkTest#benchmarkPrivacyPipeline -Pandroid.testInstrumentationRunnerArguments.warmups=5
~~~

The default repetition count automatically produces at least 100 measured samples. Override it with:

~~~powershell
.\gradlew connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.veriti.app.pipeline.PrivacyBenchmarkTest#benchmarkPrivacyPipeline -Pandroid.testInstrumentationRunnerArguments.warmups=5 -Pandroid.testInstrumentationRunnerArguments.repetitions=10
~~~

Run only Android privacy correctness checks:

~~~powershell
.\gradlew connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.veriti.app.pipeline.PrivacyBenchmarkTest#privacyPipelineCorrectness
~~~

Results are written to the app's external files directory on the device. From the repository root, retrieve, validate, archive, and display the latest results with:

~~~powershell
.\scripts\pull_android_benchmark_results.ps1
~~~

The script discovers `adb` and the installed debug application ID, always reads Android user 0, and stores each run under `benchmark_results\android\yyyyMMdd-HHmmss`. It prints overall and grouped latency plus valid-fixture success and intentionally-invalid-fixture rejection rates. It also writes device, Git, package, and retrieval metadata beside the JSON and JSONL output.

To generate fixtures, run the existing instrumentation benchmark, and retrieve its results in one command:

~~~powershell
.\scripts\pull_android_benchmark_results.ps1 -RunBenchmark -Warmups 5 -Repetitions 10 -FixtureDirectory privacy
~~~

The raw file is JSONL and the summary is JSON. The benchmark invokes **LocalPipeline** with deterministic test coordinates, then invokes the same stage classes directly for stage-level timing. Production location acquisition is unchanged.

## Start The Backend

Use a separate terminal. Stubbed mode is deterministic and cannot be selected unless benchmark mode is enabled:

~~~powershell
cd C:\veriti\backend
$env:VERITI_BENCHMARK_MODE="true"
$env:VERITI_PERFORMANCE_METRICS="true"
$env:VERITI_GEMINI_MODE="stubbed"
$env:DATABASE_URL="sqlite:///benchmark.db"
$env:UPLOAD_DIR="benchmark_uploads"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
~~~

Confirm the server mode before a run:

~~~powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
~~~

The benchmark clients refuse to run when the server-reported Gemini mode differs from the requested mode. Benchmark mode bypasses the normal in-memory upload rate limit; do not expose a benchmark-mode server publicly.

## Backend Load Tests

From a second terminal at the repository root, run application-capacity tests with stubbed Gemini:

~~~powershell
python backend\scripts\load_test.py --gemini-mode stubbed --concurrency 10 --duration 30 --rate-limit 20 --fixtures benchmark_fixtures\privacy --output benchmark_results\load-c10.json --notes "Local Windows development server"
python backend\scripts\load_test.py --gemini-mode stubbed --concurrency 25 --duration 30 --rate-limit 50 --fixtures benchmark_fixtures\privacy --output benchmark_results\load-c25.json --notes "Local Windows development server"
python backend\scripts\load_test.py --gemini-mode stubbed --concurrency 50 --duration 30 --rate-limit 100 --fixtures benchmark_fixtures\privacy --output benchmark_results\load-c50.json --notes "Local Windows development server"
~~~

Use **disabled** mode to measure fallback behavior. Restart the server with **VERITI_GEMINI_MODE=disabled**, then run:

~~~powershell
python backend\scripts\load_test.py --gemini-mode disabled --concurrency 10 --total-requests 100 --fixtures benchmark_fixtures\privacy --output benchmark_results\load-disabled.json
~~~

The load runner reports attempted/completed requests, status counts, RPS, median, p95, p99, min/max latency, success/error/timeout rates, and peak client concurrency. Request bodies and response bodies are never printed.

## End-To-End Benchmark

With the stubbed server running:

~~~powershell
python backend\scripts\e2e_benchmark.py --gemini-mode stubbed --submissions 25 --concurrency 5 --poll-interval 0.25 --fixtures benchmark_fixtures\privacy --output benchmark_results\e2e-stubbed.json --notes "Local Windows development server"
~~~

This submits media, captures the safe submission UUID, polls the existing status endpoint, and reports completion, rejection, fallback, timeout, end-to-end latency, and server verification latency.

For an optional controlled live run, restart the backend with **VERITI_GEMINI_MODE=live** and a valid **GEMINI_API_KEY** already present in the backend environment:

~~~powershell
python backend\scripts\e2e_benchmark.py --gemini-mode live --submissions 10 --concurrency 1 --fixtures benchmark_fixtures\privacy --output benchmark_results\e2e-live.json --notes "Local Windows, live Gemini"
~~~

Live runs are capped at 20 submissions and concurrency 2. Do not combine live and stubbed samples into one aggregate.

## Dashboard Timing

Start Next.js with local timing enabled:

~~~powershell
cd C:\veriti\web
$env:NEXT_PUBLIC_PERFORMANCE_METRICS="true"
npm run dev
~~~

The existing five-second polling flow records a bounded maximum of 500 events in:

~~~javascript
window.__VERITI_PERFORMANCE_EVENTS__
~~~

Operations are **dashboard.refresh**, **dashboard.incidents_fetch**, **dashboard.map_fetch**, and **dashboard.propagation**. The propagation measurement compares the API's server timestamp with browser time, so clock skew can affect it. The in-flight guard skips overlapping refreshes rather than creating duplicate requests.

## Recommended Sequence

1. Generate the full fixtures.
2. Run the Python correctness and instrumentation tests.
3. Generate Android test assets and run Android correctness tests.
4. Run the Android privacy benchmark with five warm-ups and at least 100 samples.
5. Run backend load tests at concurrency 10, 25, and 50 with Gemini stubbed.
6. Run the low-volume end-to-end benchmark with Gemini stubbed.
7. Optionally run 10 to 20 live-Gemini submissions at low concurrency.

## Result Hygiene

Generated fixtures, Android benchmark assets, temporary benchmark databases/uploads, and **benchmark_results/** are ignored by Git. A useful run directory contains:

~~~text
benchmark_results/<run-name>/
  android-privacy-raw.jsonl
  android-privacy-summary.json
  backend-load.json
  e2e.json
~~~

The backend JSON bundles include the date/time, Git commit, OS, Python version, command, notes, Gemini mode, fixture manifest version, sample count, and concurrency. Android summaries include device model, API level, manifest version, warm-ups, sample count, and grouped size/format statistics.

For final claims, additionally record CPU, memory, whether the server was local or hosted, and any emulator/device details not captured automatically. Keep the exact command and sample count beside every result.

## Interpretation

- Median is the typical observed latency.
- p95 captures a slower-tail user experience.
- Stubbed Gemini measures Veriti application capacity without external API quota or network variance.
- Disabled Gemini measures deterministic fallback behavior.
- Live Gemini measures real end-to-end behavior but varies with quota, service latency, and network conditions.
- Generated fixtures make comparisons repeatable. Supplement them later with a small set of user-owned or public-domain images for a labeled realism check.
- Smoke-test numbers are not resume-quality claims. Use a stable environment and preserve the resulting JSON before citing a metric.
