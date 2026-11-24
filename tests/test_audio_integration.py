"""Actual WAV -> ffmpeg -> MP4 -> ffmpeg -> librosa round trip."""
import subprocess
import wave

import numpy as np
import pytest


@pytest.mark.parametrize('frequency', [0, 150])
def test_actual_video_audio_round_trip(tmp_path, monkeypatch, frequency):
    imageio_ffmpeg = pytest.importorskip('imageio_ffmpeg')
    pytest.importorskip('librosa')
    from face_engine.featurebank.signals import audio_signals
    executable = imageio_ffmpeg.get_ffmpeg_exe()
    monkeypatch.setenv('FACE_ENGINE_FFMPEG', executable)
    t = np.arange(32000) / 16000
    pcm = (10000 * np.sin(2 * np.pi * frequency * t)).astype('<i2')
    wav, mp4 = tmp_path / 'input.wav', tmp_path / 'input.mp4'
    with wave.open(str(wav), 'wb') as stream:
        stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        stream.writeframes(pcm.tobytes())
    subprocess.run([executable, '-v', 'error', '-f', 'lavfi', '-i',
                    'color=c=black:s=64x64:r=30:d=2', '-i', str(wav),
                    '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(mp4)], check=True, capture_output=True)
    signals = audio_signals(str(mp4), 60, 30)
    assert all(len(v) == 60 for k, v in signals.items() if k != '_audio_raw')
    assert np.isfinite(signals['voice.loudness_db']).all()
    assert not any(np.isinf(v).any() for v in signals.values())
    if frequency:
        assert np.nanmedian(signals['voice.pitch_hz']) == pytest.approx(150, abs=5)
    else:
        assert np.isnan(signals['voice.pitch_hz']).all()
