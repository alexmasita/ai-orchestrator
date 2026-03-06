


That's it — everything else (STT, TTS, control API, idle monitor, health checks, self-destroy) remains identical. The only differences are the model name, the model path, and the --gpu-memory-utilization values (0.35/0.42 vs 0.45/0.45). Total VRAM usage: ~77% leaving comfortable headroom for kokoro-tts on the 48GB card.