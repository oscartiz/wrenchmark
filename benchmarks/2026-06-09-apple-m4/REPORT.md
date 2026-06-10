# wrenchmark results

| Model | Overall | T1 single call | T2 judgment | T3 chains | Malformed calls | Avg latency |
|---|---|---|---|---|---|---|
| qwen2.5:3b | 80% ± 5 | 92% ± 6 | 92% ± 6 | 50% ± 12 | 0.0% | 1.8s |
| qwen2.5:1.5b | 67% ± 6 | 88% ± 7 | 79% ± 8 | 22% ± 10 | 16.9% | 1.2s |
| llama3.2:3b | 58% ± 6 | 79% ± 8 | 67% ± 10 | 17% ± 9 | 0.0% | 2.4s |
| smollm2:1.7b | 27% ± 5 | 33% ± 10 | 25% ± 9 | 22% ± 10 | 0.0% | 2.1s |
| llama3.2:1b | 26% ± 5 | 46% ± 10 | 17% ± 8 | 11% ± 7 | 22.5% | 1.7s |

![success by tier](success_by_tier.png)
