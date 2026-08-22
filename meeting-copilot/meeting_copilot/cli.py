from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from meeting_copilot.config import DEFAULT_CONFIG, PACKAGE_ROOT, load_config
from meeting_copilot.diff import read_delta_file, write_baseline
from meeting_copilot.llm import CLOSE_SCHEMA, CREATE_SCHEMA, UPDATE_SCHEMA, run_llm
from meeting_copilot.session import create_session, apply_update, write_close_summary
from meeting_copilot.translate import translate_lines


def cmd_live(args: argparse.Namespace) -> int:
    if args.list_devices:
        try:
            import sounddevice as sd
        except ImportError:
            print("Install live extras: pip install meeting-copilot[live]", file=sys.stderr)
            return 2
        print(sd.query_devices())
        return 0

    config = load_config(Path(args.config) if args.config else DEFAULT_CONFIG)
    from meeting_copilot.live.pipeline import LivePipeline, LiveSegment
    from meeting_copilot.live.server import LiveHub, run_live_server

    hub = LiveHub()
    server = run_live_server(hub, args.host, args.port)

    def on_segment(seg: LiveSegment) -> None:
        hub.publish(
            {
                "text": seg.text,
                "translated": seg.translated,
                "lang": seg.lang,
                "target_lang": seg.target_lang,
                "partial": seg.partial,
                "ts": seg.ts,
            }
        )
        if not seg.partial:
            print(f"[{seg.lang}] {seg.text}")
            print(f"[{seg.target_lang}] {seg.translated}\n")

    pipeline = LivePipeline(
        config,
        lang_a=args.from_lang,
        lang_b=args.to_lang,
        whisper_model=args.whisper_model,
        chunk_seconds=args.chunk_seconds,
        device_index=args.device,
        on_segment=on_segment,
    )

    print(f"실시간 대면 번역: http://{args.host}:{args.port}")
    print(f"언어: {args.from_lang} ↔ {args.to_lang} (자동 감지)")
    print("종료: Ctrl+C")
    pipeline.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n종료 중…")
    finally:
        pipeline.stop()
        server.shutdown()
    return 0


def _read_stdin() -> str:
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def cmd_create(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config) if args.config else DEFAULT_CONFIG)
    participants = [p.strip() for p in args.participants.split(",") if p.strip()]
    prompt = (
        f"Prepare a meeting briefing.\nTitle: {args.title}\nType: {args.type}\n"
        f"Participants: {', '.join(participants) or 'unknown'}\n{CREATE_SCHEMA}"
    )
    llm_data = run_llm(prompt, config, context_dir=args.context_dir)
    root = create_session(args.title, args.type, participants, llm_data)
    print(f"session: {root}")
    print(f"dashboard: cd {root / 'app'} && python3 -m http.server {args.port}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    session = Path(args.session)
    config = load_config(Path(args.config) if args.config else DEFAULT_CONFIG)
    new_text = args.text or _read_stdin()
    if not new_text.strip():
        print("Error: no transcript text. Pipe stdin or use --text.", file=sys.stderr)
        print("  cat chunk.txt | python -m meeting_copilot update --session <dir>", file=sys.stderr)
        return 2

    baseline = session / "state" / "transcript.txt"
    delta = read_delta_file(baseline, new_text)
    if not delta.strip():
        print("no new delta")
        return 0

    translate_delta = delta
    if args.translate:
        lines = [ln for ln in delta.splitlines() if ln.strip()]
        translated = translate_lines(
            lines,
            config,
            target_lang=args.target_lang,
        )
        translate_delta = "\n".join(translated)

    prompt = (
        f"Meeting transcript DELTA (new only):\n{delta}\n\n"
        f"Translated delta (optional):\n{translate_delta}\n\n{UPDATE_SCHEMA}"
    )
    llm_data = run_llm(prompt, config, context_dir=args.context_dir)
    if args.translate and translate_delta:
        llm_data.setdefault(
            "translation_lines",
            [ln for ln in translate_delta.splitlines() if ln.strip()],
        )
    apply_update(session, llm_data)
    write_baseline(baseline, new_text)
    print(f"updated: {session}")
    print(f"delta_chars: {len(delta)}")
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    session = Path(args.session)
    config = load_config(Path(args.config) if args.config else DEFAULT_CONFIG)
    transcript = (session / "state" / "transcript.txt").read_text(encoding="utf-8")
    prompt = f"Full transcript:\n{transcript}\n\n{CLOSE_SCHEMA}"
    llm_data = run_llm(prompt, config, context_dir=args.context_dir)
    out = write_close_summary(session, llm_data)
    print(f"summary: {out}")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    session = Path(args.session)
    captions = Path(args.captions_file)
    if not captions.is_file():
        captions.parent.mkdir(parents=True, exist_ok=True)
        captions.write_text("", encoding="utf-8")

    last_size = captions.stat().st_size
    print(f"watching: {captions} (interval {args.interval}s)")

    while True:
        time.sleep(args.interval)
        size = captions.stat().st_size
        if size <= last_size:
            continue
        last_size = size
        text = captions.read_text(encoding="utf-8")
        ns = argparse.Namespace(
            session=str(session),
            config=args.config,
            context_dir=args.context_dir,
            text=text,
            translate=args.translate,
            target_lang=args.target_lang,
        )
        cmd_update(ns)


def cmd_stt(args: argparse.Namespace) -> int:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("Install STT extras: pip install meeting-copilot[stt]", file=sys.stderr)
        return 2

    if not args.audio:
        print("Error: --audio required (WAV/MP3 path). For Teams, use watch + captions.log.", file=sys.stderr)
        print("  python -m meeting_copilot stt --session <dir> --audio recording.wav", file=sys.stderr)
        return 2

    session = Path(args.session)
    captions = session / "state" / "captions.log"
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    print(f"STT {args.audio} → {captions}")
    segments, _ = model.transcribe(args.audio, beam_size=1, vad_filter=True)
    with captions.open("a", encoding="utf-8") as fh:
        for seg in segments:
            line = seg.text.strip()
            if line:
                fh.write(line + "\n")
                print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="meeting-copilot",
        description="Local Mac meeting copilot (Teams captions, ontology context, free translation)",
    )
    p.add_argument("--config", help="Path to config.yaml")
    p.add_argument("--context-dir", default=str(PACKAGE_ROOT / "context"), help="ontology + memory dir")

    sub = p.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create session and briefing dashboard")
    create.add_argument("--title", required=True)
    create.add_argument("--type", default="discovery")
    create.add_argument("--participants", default="")
    create.add_argument("--port", type=int, default=8080)
    create.set_defaults(func=cmd_create)

    update = sub.add_parser("update", help="Process transcript delta and refresh tabs")
    update.add_argument("--session", required=True)
    update.add_argument("--text", default="")
    update.add_argument("--translate", action="store_true")
    update.add_argument("--target-lang", default=None)
    update.set_defaults(func=cmd_update)

    close = sub.add_parser("close", help="Write final summary.md")
    close.add_argument("--session", required=True)
    close.set_defaults(func=cmd_close)

    watch = sub.add_parser("watch", help="Poll captions file and run update loop")
    watch.add_argument("--session", required=True)
    watch.add_argument("--captions-file", required=True)
    watch.add_argument("--interval", type=float, default=3.0)
    watch.add_argument("--translate", action="store_true")
    watch.add_argument("--target-lang", default=None)
    watch.set_defaults(func=cmd_watch)

    stt = sub.add_parser("stt", help="Transcribe audio file append to captions.log")
    stt.add_argument("--session", required=True)
    stt.add_argument("--audio", required=True, help="Path to WAV/MP3")
    stt.add_argument("--model", default="base")
    stt.set_defaults(func=cmd_stt)

    live = sub.add_parser("live", help="Real-time face-to-face mic STT + translation UI")
    live.add_argument("--from-lang", default="ko", help="Language A (e.g. ko, en)")
    live.add_argument("--to-lang", default="en", help="Language B (bidirectional)")
    live.add_argument("--host", default="127.0.0.1")
    live.add_argument("--port", type=int, default=8765)
    live.add_argument("--whisper-model", default="base", help="tiny/base/small — smaller = lower latency")
    live.add_argument("--chunk-seconds", type=float, default=1.2, help="Audio window size (seconds)")
    live.add_argument("--list-devices", action="store_true", help="List audio input devices and exit")
    live.add_argument("--device", type=int, default=None, help="Input device index")
    live.set_defaults(func=cmd_live)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
