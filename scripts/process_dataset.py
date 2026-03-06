import argparse
import os
import re
import shutil
import sys
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from agibot.logger import logger


@dataclass(frozen=True)
class ChunkSet:
    base_name: str  # e.g. "videos.tar.gz"
    parts: list[Path]  # sorted by numeric suffix


_CHUNK_RE = re.compile(r"^(?P<base>.+\.tar\.gz)\.(?P<idx>\d+)$")
_COPY_CHUNK_SIZE_BYTES = 8 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Recombine split tar.gz chunks from data/challenge/<subdir> and extract them into "
            "data/lerobot/<subdir>. This keeps the original chunk files untouched and creates a "
            "separate, processed folder suitable for downstream pipelines. Progress is always "
            "printed during concatenation and extraction."
        )
    )
    parser.add_argument(
        "--subdirs",
        nargs="+",
        default=["take_wrong_item_shelf"],
        help=(
            "List of dataset subdirectories to process. Each must exist under the challenge root, "
            "e.g. take_wrong_item_shelf."
        ),
    )
    parser.add_argument(
        "--challenge-root",
        type=str,
        default="data/challenge",
        help="Root folder containing the downloaded chunk files.",
    )
    parser.add_argument(
        "--lerobot-root",
        type=str,
        default="data/lerobot",
        help="Root folder where extracted, processed datasets will be written.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild concatenated archives and re-extract even if already processed.",
    )
    parser.add_argument(
        "--keep-joined-archives",
        action="store_true",
        help="Keep the recombined *.tar.gz files after extraction (stored under _joined_archives/).",
    )
    return parser.parse_args()


def _format_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    for u in units:
        if v < 1024.0 or u == units[-1]:
            return f"{v:.2f}{u}"
        v /= 1024.0
    return f"{v:.2f}TB"


class _Progress:
    def __init__(
        self,
        label: str,
        total_bytes: int | None,
        min_interval_s: float = 0.5,
    ) -> None:
        self.label = label
        self.total_bytes = total_bytes
        self.min_interval_s = min_interval_s
        self._last_print = 0.0
        self._last_line_len = 0

    def update(self, done_bytes: int) -> None:
        now = time.time()
        if now - self._last_print < self.min_interval_s:
            return
        self._last_print = now

        if self.total_bytes and self.total_bytes > 0:
            pct = 100.0 * (done_bytes / self.total_bytes)
            msg = (
                f"{self.label}: {pct:6.2f}% "
                f"({ _format_bytes(done_bytes) } / { _format_bytes(self.total_bytes) })"
            )
        else:
            msg = f"{self.label}: { _format_bytes(done_bytes) }"

        pad = max(0, self._last_line_len - len(msg))
        self._last_line_len = len(msg)
        print("\r" + msg + (" " * pad), end="", flush=True)

    def done(self, done_bytes: int | None = None) -> None:
        if done_bytes is None:
            done_bytes = self.total_bytes or 0
        self.update(done_bytes)
        print("", flush=True)


def _find_chunk_sets(input_dir: Path) -> list[ChunkSet]:
    candidates: dict[str, dict[int, Path]] = {}
    for p in input_dir.iterdir():
        if not p.is_file():
            continue
        m = _CHUNK_RE.match(p.name)
        if not m:
            continue
        base = m.group("base")
        idx = int(m.group("idx"))
        candidates.setdefault(base, {})
        if idx in candidates[base]:
            raise RuntimeError(f"Duplicate chunk index for {base}: {idx}")
        candidates[base][idx] = p

    sets: list[ChunkSet] = []
    for base, by_idx in candidates.items():
        if not by_idx:
            continue
        expected = list(range(0, max(by_idx.keys()) + 1))
        missing = [i for i in expected if i not in by_idx]
        if missing:
            raise RuntimeError(f"Missing chunks for {base}: {missing}")
        parts = [by_idx[i] for i in expected]
        sets.append(ChunkSet(base_name=base, parts=parts))

    # Stable order for reproducibility
    return sorted(sets, key=lambda cs: cs.base_name)


def _atomic_concat(parts: list[Path], out_path: Path, *, progress: _Progress | None = None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    with tmp_path.open("wb") as w:
        written = 0
        for part in parts:
            with part.open("rb") as r:
                while True:
                    buf = r.read(_COPY_CHUNK_SIZE_BYTES)
                    if not buf:
                        break
                    w.write(buf)
                    written += len(buf)
                    if progress is not None:
                        progress.update(written)
    os.replace(tmp_path, out_path)


def _safe_members(tar: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members: list[tarfile.TarInfo] = []
    for m in tar.getmembers():
        name = m.name
        if name.startswith("/") or name.startswith("\\"):
            raise RuntimeError(f"Unsafe absolute path in tar member: {name}")
        # Normalize and reject traversal
        norm = Path(name)
        if any(part == ".." for part in norm.parts):
            raise RuntimeError(f"Unsafe path traversal in tar member: {name}")
        members.append(m)
    return members


def _common_top_level_dir(members: Iterable[tarfile.TarInfo]) -> str | None:
    top_levels: set[str] = set()
    for m in members:
        parts = Path(m.name).parts
        if not parts:
            continue
        top_levels.add(parts[0])
    if len(top_levels) == 1:
        return next(iter(top_levels))
    return None


def _extract_with_optional_strip(
    tar_path: Path,
    out_dir: Path,
    expected_strip_prefix: str | None,
    *,
    progress: _Progress | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, mode="r:gz") as tar:
        members = _safe_members(tar)
        if not members:
            return

        strip_prefix = None
        common = _common_top_level_dir(members)
        if expected_strip_prefix and common == expected_strip_prefix:
            strip_prefix = expected_strip_prefix

        extracted = 0
        for m in members:
            rel_name = m.name
            if strip_prefix:
                rel = Path(rel_name)
                rel_parts = rel.parts
                if rel_parts and rel_parts[0] == strip_prefix:
                    rel_name = str(Path(*rel_parts[1:])) if len(rel_parts) > 1 else ""

            if rel_name == "":
                continue

            dest = out_dir / rel_name
            dest_parent = dest.parent
            dest_parent.mkdir(parents=True, exist_ok=True)

            if m.isdir():
                dest.mkdir(parents=True, exist_ok=True)
                continue

            # Disallow links to avoid writing outside of out_dir.
            if m.issym() or m.islnk():
                raise RuntimeError(f"Refusing to extract link member: {m.name}")

            f = tar.extractfile(m)
            if f is None:
                continue
            with f:
                with dest.open("wb") as w:
                    while True:
                        buf = f.read(_COPY_CHUNK_SIZE_BYTES)
                        if not buf:
                            break
                        w.write(buf)
                        extracted += len(buf)
                        if progress is not None:
                            progress.update(extracted)


def _process_one_subdir(
    challenge_root: Path, lerobot_root: Path, subdir: str, force: bool, keep_joined: bool
) -> None:
    input_dir = challenge_root / subdir
    output_dir = lerobot_root / subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean up legacy layout if it exists from a previous version of this script.
    legacy_extracted = output_dir / "_extracted"
    if legacy_extracted.exists():
        shutil.rmtree(legacy_extracted)

    marker = output_dir / ".processed_ok"
    if marker.exists() and not force:
        return

    chunk_sets = _find_chunk_sets(input_dir)
    if not chunk_sets:
        raise RuntimeError(
            f"No chunk files found under {input_dir}. Expected files like data.tar.gz.000"
        )

    joined_dir = output_dir / "_joined_archives"

    for cs in chunk_sets:
        joined_path = joined_dir / cs.base_name
        if force or not joined_path.exists():
            _atomic_concat(cs.parts, joined_path)
        _extract_with_optional_strip(
            joined_path,
            output_dir,
            expected_strip_prefix=subdir,
        )
        if not keep_joined:
            try:
                joined_path.unlink()
            except FileNotFoundError:
                pass

    # If we do not want to keep the joined archives, remove the helper directory as well.
    if not keep_joined and joined_dir.exists():
        shutil.rmtree(joined_dir, ignore_errors=True)

    marker.write_text("ok\n", encoding="utf-8")


def main() -> None:
    args = parse_args()

    challenge_root = Path(args.challenge_root)
    lerobot_root = Path(args.lerobot_root)
    lerobot_root.mkdir(parents=True, exist_ok=True)

    logger.info(f"Challenge root: {challenge_root.resolve()}")
    logger.info(f"LeRobot root:  {lerobot_root.resolve()}")
    logger.info(f"Subdirs to process: {args.subdirs}")

    for subdir in args.subdirs:
        # Always create the output folder for each requested subdir.
        (lerobot_root / subdir).mkdir(parents=True, exist_ok=True)

        input_dir = challenge_root / subdir
        if not input_dir.exists():
            logger.error(f"Input directory does not exist: {input_dir}")
            raise RuntimeError(
                f"Input directory does not exist: {input_dir}. "
                f"Download it first (e.g. scripts/download_dataset.py --subdir Reasoning2Action-Sim/{subdir})."
            )

        # Inline the per-subdir loop to provide useful progress output per archive.
        input_dir = challenge_root / subdir
        output_dir = lerobot_root / subdir

        logger.info(f"Processing subdir: {subdir}")
        logger.info(f"Input:  {input_dir.resolve()}")
        logger.info(f"Output: {output_dir.resolve()}")

        legacy_extracted = output_dir / "_extracted"
        if legacy_extracted.exists():
            logger.warning(f"Removing legacy folder: {legacy_extracted}")
            shutil.rmtree(legacy_extracted)

        marker = output_dir / ".processed_ok"
        if marker.exists() and not args.force:
            logger.info(f"Already processed, skipping (marker exists): {marker}")
            continue

        chunk_sets = _find_chunk_sets(input_dir)
        if not chunk_sets:
            logger.error(f"No chunk files found under: {input_dir}")
            raise RuntimeError(
                f"No chunk files found under {input_dir}. Expected files like data.tar.gz.000"
            )

        joined_dir = output_dir / "_joined_archives"
        logger.info(f"Found {len(chunk_sets)} archive group(s) to process.")

        for cs in chunk_sets:
            joined_path = joined_dir / cs.base_name

            total_concat = sum(p.stat().st_size for p in cs.parts)
            concat_prog = _Progress(
                label=f"[{subdir}] join {cs.base_name}",
                total_bytes=total_concat,
            )
            if args.force or not joined_path.exists():
                logger.info(
                    f"Joining {len(cs.parts)} chunk(s) into {joined_path.name} ({_format_bytes(total_concat)})"
                )
                _atomic_concat(cs.parts, joined_path, progress=concat_prog)
            concat_prog.done(total_concat)

            # Estimate total extracted bytes from tar headers (regular files only).
            total_extract = None
            try:
                with tarfile.open(joined_path, mode="r:gz") as tar:
                    total_extract = sum(
                        m.size for m in tar.getmembers() if m.isreg() and m.size is not None
                    )
            except tarfile.TarError:
                total_extract = None

            extract_prog = _Progress(
                label=f"[{subdir}] extract {cs.base_name}",
                total_bytes=total_extract,
            )
            logger.info(
                f"Extracting {cs.base_name} into {output_dir} "
                f"(estimated {_format_bytes(total_extract)} of regular files)"
                if total_extract is not None
                else f"Extracting {cs.base_name} into {output_dir}"
            )
            _extract_with_optional_strip(
                joined_path,
                output_dir,
                expected_strip_prefix=subdir,
                progress=extract_prog,
            )
            extract_prog.done(total_extract)

            if not args.keep_joined_archives:
                try:
                    joined_path.unlink()
                except FileNotFoundError:
                    pass

        if not args.keep_joined_archives and joined_dir.exists():
            logger.info(f"Removing temporary folder: {joined_dir}")
            shutil.rmtree(joined_dir, ignore_errors=True)

        marker.write_text("ok\n", encoding="utf-8")
        logger.info(f"Done. Wrote marker: {marker}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Ensure we do not log over a carriage-return progress line.
        print("", flush=True)
        logger.exception("Dataset processing failed.")
        raise SystemExit(1)

