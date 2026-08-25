#!/usr/bin/env bash
# Mac audio setup for Zoom/Teams + Meeting Copilot (BlackHole multi-output)
set -euo pipefail

echo "Meeting Copilot — Mac 오디오 설정"
echo ""
echo "1) BlackHole 2ch 설치:"
echo "   brew install blackhole-2ch"
echo "   또는 https://existential.audio/blackhole/"
echo ""
echo "2) Audio MIDI Setup → + → Create Multi-Output Device"
echo "   - MacBook Speakers + BlackHole 2ch 체크"
echo ""
echo "3) 시스템 설정 → 사운드 → 출력: Multi-Output Device"
echo ""
echo "4) meeting-copilot에서 BlackHole 입력 선택:"
echo "   python -m meeting_copilot overlay --list-devices"
echo "   python -m meeting_copilot overlay --device <BlackHole index> --from-lang ko --to-lang en"
echo ""
echo "5) 마이크 권한: 시스템 설정 → 개인정보 → 마이크 → Terminal/iTerm 허용"

if command -v brew >/dev/null 2>&1; then
  if brew list blackhole-2ch >/dev/null 2>&1; then
    echo "✓ blackhole-2ch already installed"
  else
    read -r -p "Install blackhole-2ch now? [y/N] " ans
    if [[ "${ans,,}" == "y" ]]; then
      brew install blackhole-2ch
    fi
  fi
fi
