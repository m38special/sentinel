#!/usr/bin/env python3
"""
SENTINEL Voice Alert Module (v2.1)
Uses ChatTTS for voice synthesis
"""

import os
import io
import base64
from typing import Optional
from pathlib import Path

# ChatTTS import
try:
    import ChatTTS
    CHATTTS_AVAILABLE = True
except ImportError:
    CHATTTS_AVAILABLE = False
    print("ChatTTS not installed. Run: pip install ChatTTS")


class VoiceAlerter:
    """Generate voice alerts for trading signals"""
    
    def __init__(self, voice_path: Optional[str] = None):
        self.chat = None
        self.voice_path = voice_path or "/tmp/sentinel_voice.wav"
        
        if CHATTTS_AVAILABLE:
            self._initialize()
    
    def _initialize(self):
        """Initialize ChatTTS"""
        try:
            self.chat = ChatTTS.Chat()
            self.chat.load()
            print("✓ VoiceAlerter initialized")
        except Exception as e:
            print(f"✗ ChatTTS init failed: {e}")
    
    def generate_speech(self, text: str, output_path: Optional[str] = None) -> Optional[bytes]:
        """Generate speech from text"""
        if not self.chat:
            print("ChatTTS not available")
            return None
        
        try:
            # Generate speech
            wavs = self.chat.generate(text)
            
            # Convert to audio
            import torch
            import numpy as np
            
            # Save to file
            output = output_path or self.voice_path
            import scipy.io.wavfile as wavfile
            
            # Handle different return formats
            if isinstance(wavs, list):
                audio_data = wavs[0]
            else:
                audio_data = wavs
            
            # Convert to 16-bit PCM
            if isinstance(audio_data, torch.Tensor):
                audio_data = audio_data.cpu().numpy()
            
            audio_int16 = (audio_data * 32767).astype('int16')
            
            wavfile.write(output, 24000, audio_int16)
            
            # Read back as bytes
            with open(output, 'rb') as f:
                return f.read()
                
        except Exception as e:
            print(f"Speech generation failed: {e}")
            return None
    
    def alert_new_token(self, token_symbol: str, score: float, dex: str = "pump.fun") -> Optional[bytes]:
        """Alert for new token detection"""
        text = f"New token detected. {token_symbol} on {dex}. Risk score {int(score * 100)} percent."
        return self.generate_speech(text)
    
    def alert_security_threat(self, threat_type: str, details: str) -> Optional[bytes]:
        """Alert for security threats"""
        text = f"Security alert. {threat_type}. {details}"
        return self.generate_speech(text)
    
    def alert_high_score(self, token_symbol: str, score: float, reason: str) -> Optional[bytes]:
        """Alert for high-scoring token"""
        text = f"High opportunity alert. {token_symbol}. Score {int(score * 100)} percent. {reason}"
        return self.generate_speech(text)
    
    def get_audio_base64(self, audio_bytes: bytes) -> str:
        """Get base64-encoded audio for web/API delivery"""
        return base64.b64encode(audio_bytes).decode()


# Preset voice configurations
VOICE_PRESETS = {
    'alert': {
        'temperature': 0.3,
        'top_P': 0.9,
        'top_K': 20
    },
    'calm': {
        'temperature': 0.1,
        'top_P': 0.7,
        'top_K': 10
    },
    'urgent': {
        'temperature': 0.5,
        'top_P': 0.95,
        'top_K': 50
    }
}


async def test_voice():
    """Test voice synthesis"""
    alerter = VoiceAlerter()
    
    test_cases = [
        ("New token detected on pump.fun", "test_alert.wav"),
        ("Security threat: rug pull indicator detected", "test_security.wav"),
        ("High opportunity: score 95 percent", "test_high.wav")
    ]
    
    for text, filename in test_cases:
        print(f"\nGenerating: {text}")
        audio = alerter.generate_speech(text, f"/tmp/{filename}")
        if audio:
            print(f"✓ Saved to /tmp/{filename}")


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_voice())
