#!/usr/bin/env python3
"""
dedupe_videos.py – perceptual duplicate finder for a video folder

Examples:
  python dedupe_videos.py /path/to/videos --threshold 8 --action move --dupe-dir ./dupes
  python dedupe_videos.py /path/to/videos --n-frames 7 --workers 8 --csv-out report.csv
  python dedupe_videos.py /path/to/videos --action delete --trash --dry-run

Requirements:
- ffmpeg and ffprobe on PATH
- Python packages: numpy, opencv-contrib-python (for cv2.img_hash), tqdm (optional), Send2Trash (optional for --trash)
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Third-party
try:
    import cv2
    import numpy as np
except Exception as e:
    print("Error: numpy and OpenCV are required. Try: pip install numpy opencv-contrib-python", file=sys.stderr)
    raise

# Validate img_hash availability
if not hasattr(cv2, "img_hash") or not hasattr(cv2.img_hash, "PHash_create"):
    print("Error: cv2.img_hash.PHash_create is missing. Install opencv-contrib-python.", file=sys.stderr)
    sys.exit(1)

try:
    from tqdm import tqdm
except Exception:
    def tqdm(x, **kwargs):
        return x

try:
    from send2trash import send2trash  # optional, used only with --trash
    _HAS_SEND2TRASH = True
except Exception:
    _HAS_SEND2TRASH = False


SUPPORTED_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".3gp", ".3g2"}


@dataclass(frozen=True)
class VideoMeta:
    duration: float  # seconds
    pixels: int      # width * height
    size: int        # bytes


def which_or_die(name: str):
    from shutil import which
    if which(name) is None:
        print(f"Error: '{name}' not found on PATH. Please install FFmpeg and ensure '{name}' is available.", file=sys.stderr)
        sys.exit(1)


def parse_extensions(exts: str) -> set:
    if not exts:
        return SUPPORTED_EXTS
    out = set()
    for e in exts.split(","):
        e = e.strip().lower()
        if not e:
            continue
        if not e.startswith("."):
            e = "." + e
        out.add(e)
    return out


def try_probe_video(path: Path, timeout: int = 10) -> Optional[VideoMeta]:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format=duration,size:stream=width,height",
        "-of", "json", str(path)
    ]
    try:
        data = json.loads(subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout))
    except subprocess.CalledProcessError:
        return None
    except subprocess.TimeoutExpired:
        return None
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    if not streams:
        return None
    try:
        w = int(streams[0].get("width") or 0)
        h = int(streams[0].get("height") or 0)
        dur = float(fmt.get("duration") or 0.0)
        size = int(fmt.get("size") or 0)
    except Exception:
        return None
    if dur <= 0 or w <= 0 or h <= 0:
        return None
    return VideoMeta(duration=dur, pixels=w * h, size=size)


def extract_keyframes(video_path: Path, n_frames: int, per_frame_timeout=12, hwaccel: Optional[str] = None, downscale: bool = True) -> List[np.ndarray]:
    """
    Extract n_frames evenly spaced frames using ffmpeg, return as in-memory images.
    Robust to decode failures; skips frames that fail to extract.
    """
    meta = try_probe_video(video_path)
    if meta is None or meta.duration <= 0:
        return []

    duration = meta.duration
    step = duration / (n_frames + 1)
    timestamps = [i * step for i in range(1, n_frames + 1)]

    frames = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        for idx, ts in enumerate(timestamps, 1):
            out = tmpdir / f"frame{idx}.png"
            ff_cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            ]
            if hwaccel:
                ff_cmd += ["-hwaccel", hwaccel]
            ff_cmd += [
                "-ss", f"{ts}",
                "-noautorotate",
                "-i", str(video_path),
                "-frames:v", "1",
            ]
            if downscale:
                # reduce decode/scale load and speed up hashing
                ff_cmd += ["-vf", "scale='min(640,iw)':-2"]
            ff_cmd += [
                "-q:v", "2",
                str(out),
            ]
            try:
                subprocess.run(ff_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=per_frame_timeout)
            except subprocess.TimeoutExpired:
                continue
            except subprocess.CalledProcessError:
                # try a fallback without hwaccel if it was specified
                if hwaccel:
                    try:
                        ff_cmd2 = [
                            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                            "-hwaccel", "none",
                            "-ss", f"{ts}", "-noautorotate",
                            "-i", str(video_path),
                            "-frames:v", "1",
                        ]
                        if downscale:
                            ff_cmd2 += ["-vf", "scale='min(640,iw)':-2"]
                        ff_cmd2 += ["-q:v", "2", str(out)]
                        subprocess.run(ff_cmd2, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=per_frame_timeout)
                    except Exception:
                        continue
                else:
                    continue

            if out.exists() and out.stat().st_size > 0:
                img = cv2.imread(str(out), cv2.IMREAD_COLOR)
                if img is not None:
                    frames.append(img)
    return frames


def hash_video(frames: List[np.ndarray]) -> Optional[bytes]:
    """Compute a 64-bit video hash: per-frame PHash (8 bytes), bitwise-majority fuse."""
    if not frames:
        return None
    phasher = cv2.img_hash.PHash_create()
    bits_list = []
    for img in frames:
        if img is None:
            continue
        h = phasher.compute(img).ravel().astype(np.uint8)  # 8 bytes
        b = np.unpackbits(h, bitorder="big")  # -> 64 bits
        bits_list.append(b)
    if not bits_list:
        return None
    M = np.vstack(bits_list)  # [n_frames, 64]
    majority = (M.sum(axis=0) >= (M.shape[0] / 2)).astype(np.uint8)
    packed = np.packbits(majority, bitorder="big")
    return bytes(packed)  # 8 bytes


def hamming(a: bytes, b: bytes) -> int:
    return bin(int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).count("1")


class DSU:
    def __init__(self, n: int):
        self.p = list(range(n))
        self.r = [0] * n

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int):
        pa, pb = self.find(a), self.find(b)
        if pa == pb:
            return
        if self.r[pa] < self.r[pb]:
            pa, pb = pb, pa
        self.p[pb] = pa
        if self.r[pa] == self.r[pb]:
            self.r[pa] += 1


def group_duplicates(paths: List[Path], hashes: List[bytes], threshold: int) -> List[List[int]]:
    n = len(paths)
    dsu = DSU(n)
    for i in range(n):
        hi = hashes[i]
        for j in range(i + 1, n):
            if hamming(hi, hashes[j]) <= threshold:
                dsu.union(i, j)
    comps = {}
    for i in range(n):
        r = dsu.find(i)
        comps.setdefault(r, []).append(i)
    return list(comps.values())


def safe_move(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    base, ext = src.stem, src.suffix
    dst = dst_dir / src.name
    k = 1
    while dst.exists():
        dst = dst_dir / f"{base} ({k}){ext}"
        k += 1
    shutil.move(str(src), str(dst))
    return dst


def safe_delete(p: Path, use_trash: bool):
    if use_trash:
        if not _HAS_SEND2TRASH:
            raise RuntimeError("send2trash not installed. pip install Send2Trash or omit --trash.")
        send2trash(str(p))
    else:
        p.unlink()


def process_one(vid: Path, n_frames: int, hwaccel_opt: Optional[str], per_frame_timeout: int, downscale: bool) -> Optional[Tuple[Path, bytes, VideoMeta]]:
    try:
        frames = extract_keyframes(vid, n_frames=n_frames, per_frame_timeout=per_frame_timeout, hwaccel=hwaccel_opt, downscale=downscale)
        if not frames:
            return None
        vhash = hash_video(frames)
        if vhash is None:
            return None
        meta = try_probe_video(vid)
        if meta is None:
            return None
        return vid, vhash, meta
    except Exception as e:
        print(f"⚠️ {vid.name}: {e}", file=sys.stderr)
        return None


def main():
    which_or_die("ffmpeg")
    which_or_die("ffprobe")

    ap = argparse.ArgumentParser(description="Perceptual duplicate finder for a video folder.")
    ap.add_argument("folder", type=Path, help="Directory of videos")
    ap.add_argument("--threshold", type=int, default=8, help="Max Hamming distance to call duplicates")
    ap.add_argument("--action", choices=["none", "move", "delete"], default="none", help="What to do with duplicates")
    ap.add_argument("--dupe-dir", type=Path, default=Path("./duplicates"), help="Target dir for moved duplicates")
    ap.add_argument("--n-frames", dest="n_frames", type=int, default=5, help="Number of keyframes to hash per video")
    ap.add_argument("--extensions", type=str, default="", help="Comma-separated list of file extensions (e.g. .mp4,.mkv)")
    ap.add_argument("--workers", type=int, default=max(os.cpu_count() or 4, 4), help="Parallel workers for hashing")
    ap.add_argument("--csv-out", dest="csv_out", type=Path, default=Path("./duplicates.csv"), help="CSV report path")
    ap.add_argument("--skipped-out", dest="skipped_out", type=Path, default=Path("./skipped.csv"), help="CSV of skipped/unreadable files")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true", help="Log actions, do not move or delete files")
    ap.add_argument("--trash", action="store_true", help="Send deletions to recycle bin (requires Send2Trash)")
    ap.add_argument("--hwaccel", type=str, default="none", help="FFmpeg hwaccel (e.g., none, vaapi, cuda). Default: none")
    ap.add_argument("--per-frame-timeout", dest="per_frame_timeout", type=int, default=12, help="Seconds per frame extraction timeout")
    ap.add_argument("--no-downscale", dest="no_downscale", action="store_true", help="Do not downscale frames before hashing")
    # NEW: helpful troubleshooting flags
    ap.add_argument("--exclude-dir", action="append", default=[], help="Directory paths to exclude from scanning (can be repeated)")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = ap.parse_args()

    if not args.folder.exists() or not args.folder.is_dir():
        print(f"Error: folder not found or not a directory: {args.folder}", file=sys.stderr)
        sys.exit(1)

    # Normalize paths
    root = args.folder.resolve()
    dupe_dir = args.dupe_dir.resolve()
    # Auto-exclude dupe-dir if it resides inside the scanned folder to avoid reprocessing moved files
    excludes = [Path(p).resolve() for p in args.exclude_dir]
    if dupe_dir.is_relative_to(root) if hasattr(dupe_dir, "is_relative_to") else str(dupe_dir).startswith(str(root) + os.sep):
        excludes.append(dupe_dir)

    # Build file list honoring excludes
    exts = parse_extensions(args.extensions)
    videos = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        # skip excluded directories
        parent = p.parent.resolve()
        if any(str(parent).startswith(str(e) + os.sep) or parent == e for e in excludes):
            continue
        if p.suffix.lower() in exts:
            videos.append(p)
    videos = sorted(videos)

    if args.verbose:
        print(f"Scanning {len(videos)} files (excludes: {', '.join(map(str, set(excludes))) or 'none'})…")

    fingerprints: List[bytes] = []
    metas: List[VideoMeta] = []
    paths: List[Path] = []
    skipped_rows: List[Tuple[str, str]] = []

    hwaccel_opt = args.hwaccel if args.hwaccel else None
    downscale = not args.no_downscale

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(process_one, v, args.n_frames, hwaccel_opt, args.per_frame_timeout, downscale): v for v in videos}
            for fut in tqdm(as_completed(futures), total=len(futures), desc="Hashing"):
                res = None
                try:
                    res = fut.result()
                except Exception as e:
                    vid = futures[fut]
                    skipped_rows.append((str(vid.resolve()), f"worker_error: {e}"))
                    continue
                if not res:
                    vid = futures[fut]
                    if args.verbose:
                        print(f"Skipped (hash/probe failed): {vid}")
                    skipped_rows.append((str(vid.resolve()), "probe/extract/hash_failed"))
                    continue
                vid, vhash, meta = res
                paths.append(vid)
                fingerprints.append(vhash)
                metas.append(meta)
    except KeyboardInterrupt:
        print("\nInterrupted. Shutting down workers…", file=sys.stderr)
        # proceed to finalize any collected results
    except Exception as e:
        print(f"Fatal error during hashing: {e}", file=sys.stderr)

    if not paths:
        print("No videos hashed successfully. Exiting.")
        # write skipped if any
        if skipped_rows:
            args.skipped_out.parent.mkdir(parents=True, exist_ok=True)
            with args.skipped_out.open("w", newline="", encoding="utf-8") as sf:
                wrs = csv.writer(sf)
                wrs.writerow(["path", "reason"])
                wrs.writerows(skipped_rows)
        return

    # Group by threshold using union-find
    index_groups = group_duplicates(paths, fingerprints, args.threshold)

    # Ensure dupe dir exists ahead of actions that may need it
    try:
        if args.action == "move" and not args.dry_run:
            dupe_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error creating dupe directory '{dupe_dir}': {e}", file=sys.stderr)
        if args.action == "move" and not args.dry_run:
            print("Aborting due to dupe-dir creation failure.", file=sys.stderr)
            sys.exit(1)

    # Write CSV and perform actions
    args.csv_out.parent.mkdir(parents=True, exist_ok=True)
    permission_errors = 0
    with args.csv_out.open("w", newline="", encoding="utf-8") as csvfile:
        wr = csv.writer(csvfile)
        wr.writerow(["keeper", "duplicate", "distance"])

        dupes_found = 0
        acted = 0
        for idxs in index_groups:
            if len(idxs) <= 1:
                continue
            # Choose best by (duration, pixels, size) desc
            best_idx = max(idxs, key=lambda i: (metas[i].duration, metas[i].pixels, metas[i].size))
            keeper = paths[best_idx]
            if args.verbose:
                print(f"Group with keeper: {keeper}")
            for i in idxs:
                if i == best_idx:
                    continue
                dupe = paths[i]
                dist = hamming(fingerprints[best_idx], fingerprints[i])
                wr.writerow([str(keeper.resolve()), str(dupe.resolve()), dist])
                dupes_found += 1

                if args.verbose or args.dry_run:
                    print(f"Duplicate: {dupe} (keeper: {keeper}, dist={dist})")

                if args.action == "none":
                    continue

                if args.action == "move":
                    if args.dry_run:
                        print(f"[DRY-RUN] Move: {dupe} -> {dupe_dir}")
                    else:
                        try:
                            new_path = safe_move(dupe, dupe_dir)
                            acted += 1
                            if args.verbose:
                                print(f"Moved: {dupe} -> {new_path}")
                        except PermissionError as e:
                            permission_errors += 1
                            print(f"Move failed for {dupe}: Permission denied", file=sys.stderr)
                        except Exception as e:
                            print(f"Move failed for {dupe}: {e}", file=sys.stderr)

                elif args.action == "delete":
                    if args.dry_run:
                        mode = "trash" if args.trash else "permanent"
                        print(f"[DRY-RUN] Delete ({mode}): {dupe}")
                    else:
                        try:
                            safe_delete(dupe, use_trash=args.trash)
                            acted += 1
                            if args.verbose:
                                print(f"Deleted: {dupe} ({'trash' if args.trash else 'permanent'})")
                        except PermissionError as e:
                            permission_errors += 1
                            print(f"Delete failed for {dupe}: Permission denied", file=sys.stderr)
                        except Exception as e:
                            print(f"Delete failed for {dupe}: {e}", file=sys.stderr)

    # Write skipped CSV
    if skipped_rows:
        args.skipped_out.parent.mkdir(parents=True, exist_ok=True)
        with args.skipped_out.open("w", newline="", encoding="utf-8") as sf:
            wrs = csv.writer(sf)
            wrs.writerow(["path", "reason"])
            wrs.writerows(skipped_rows)

    # Summary with actions performed - FIXED: len(g) > 1 instead of len(g>1)
    print(f"Done. Duplicate groups: {sum(1 for g in index_groups if len(g) > 1)}. Report: {args.csv_out}")
    if dupes_found and args.action != "none":
        print(f"Duplicates acted on: {acted} ({'moved' if args.action=='move' else 'deleted'})")
    if permission_errors > 0:
        print(f"\n⚠️  Permission denied for {permission_errors} files.", file=sys.stderr)
        print(f"    Try running with sudo: sudo python {__file__} ...", file=sys.stderr)
    if skipped_rows:
        print(f"Skipped files: {len(skipped_rows)}. See: {args.skipped_out}")

    # Usage examples (run these in your shell):
    # 1) Dry run to inspect duplicates found
    #    python /home/azureuser/mcprag/finddupes.py \
    #      /var/lib/plexmediaserver/Library/videos \
    #      --threshold 8 \
    #      --n-frames 5 \
    #      --workers 8 \
    #      --csv-out /home/azureuser/mcprag/duplicates.csv \
    #      --skipped-out /home/azureuser/mcprag/skipped.csv \
    #      --dry-run --verbose
    #
    # 2) Move duplicates to a safe folder outside the scanned tree
    #    mkdir -p /home/azureuser/plex-dupes
    #    python /home/azureuser/mcprag/finddupes.py \
    #      /var/lib/plexmediaserver/Library/videos \
    #      --action move \
    #      --dupe-dir /home/azureuser/plex-dupes \
    #      --threshold 8 --n-frames 5 --workers 8 \
    #      --csv-out /home/azureuser/mcprag/duplicates.csv \
    #      --skipped-out /home/azureuser/mcprag/skipped.csv \
    #      --verbose
    #
    # 3) If you must keep dupe-dir inside the root, exclude it from scanning
    #    python /home/azureuser/mcprag/finddupes.py \
    #      /var/lib/plexmediaserver/Library/videos \
    #      --action move \
    #      --dupe-dir /var/lib/plexmediaserver/Library/videos/duplicates \
    #      --exclude-dir /var/lib/plexmediaserver/Library/videos/duplicates \
    #      --threshold 8 --n-frames 5 --workers 8 --verbose
    #
    # 4) Delete duplicates permanently (dangerous; do a dry run first)
    #    python /home/azureuser/mcprag/finddupes.py \
    #      /var/lib/plexmediaserver/Library/videos \
    #      --action delete \
    #      --threshold 8 --n-frames 5 --workers 8 \
    #      --csv-out /home/azureuser/mcprag/duplicates.csv \
    #      --skipped-out /home/azureuser/mcprag/skipped.csv \
    #      --dry-run --verbose
    #    # Then actually delete
    #    python /home/azureuser/mcprag/finddupes.py \
    #      /var/lib/plexmediaserver/Library/videos \
    #      --action delete \
    #      --threshold 8 --n-frames 5 --workers 8 \
    #      --csv-out /home/azureuser/mcprag/duplicates.csv \
    #      --skipped-out /home/azureuser/mcprag/skipped.csv \
    #      --verbose
    #
    # 5) Delete to trash (requires Send2Trash)
    #    pip install Send2Trash
    #    python /home/azureuser/mcprag/finddupes.py \
    #      /var/lib/plexmediaserver/Library/videos \
    #      --action delete --trash --verbose
    #
    # 6) Delete with sudo for permission issues
    #    sudo python /home/azureuser/mcprag/finddupes.py \
    #      /var/lib/plexmediaserver/Library/videos \
    #      --action delete \
    #      --threshold 8 --n-frames 5 --workers 8 \
    #      --csv-out /home/azureuser/mcprag/duplicates.csv \
    #      --skipped-out /home/azureuser/mcprag/skipped.csv \
    #      --verbose
    #
    # Notes:
    # - Keep dupe-dir outside the scanned folder to avoid reprocessing moved files.
    # - Use --extensions ".mp4,.mkv" to restrict formats if needed.
    # - Tweak --threshold if too strict/lenient; typical range 6–12.
    # - If you get permission errors, use sudo to run the script.


if __name__ == "__main__":
    main()
