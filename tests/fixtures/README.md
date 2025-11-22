# Test Fixtures

This directory contains test audio files and other fixtures for testing.

## Audio Files

Due to the large size of audio files, this directory should contain:
- Small sample audio files (under 1MB each)
- Various formats: MP3, WAV, M4A
- Different durations: short (< 5s), medium (5-30s), long (30-60s)

## Adding Test Audio Files

To add test audio files:

1. Obtain or create small audio samples
2. Ensure they are under 1MB in size
3. Name them clearly (e.g., `sample_5s.mp3`, `sample_wav.wav`)
4. Add them to this directory
5. Update `.gitignore` if needed

## Creating Synthetic Test Data

For integration tests, you can create synthetic audio files:

```python
import numpy as np
import soundfile as sf

# Generate 1 second of silence at 16kHz
sample_rate = 16000
duration = 1.0
t = np.linspace(0, duration, int(sample_rate * duration))
silence = np.zeros_like(t)

# Save as WAV
sf.write("tests/fixtures/silence_1s.wav", silence, sample_rate)
```

## Notes

- Keep files small to avoid bloat in the repository
- Use `.gitignore` to exclude large files if necessary
- Document the source and characteristics of each file
- Ensure all test files have appropriate licenses
