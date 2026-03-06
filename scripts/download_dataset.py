import argparse
import os
import shutil
import sys
from pathlib import Path

from agibot.constants import DATA_DIR
from agibot.logger import logger
from huggingface_hub import snapshot_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download (part of) the AgiBotWorldChallenge-2026 dataset from Hugging Face.\n"
            "By default, only the 'Reasoning2Action-Sim/take_wrong_item_shelf' folder "
            "is downloaded to avoid fetching the whole dataset."
        )
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        default="agibot-world/AgiBotWorldChallenge-2026",
        help="Hugging Face dataset repo id.",
    )
    parser.add_argument(
        "--subdir",
        type=str,
        default="Reasoning2Action-Sim/take_wrong_item_shelf",
        help=(
            "Subdirectory inside the dataset repo to download. "
            "Example: 'Reasoning2Action-Sim/take_wrong_item_shelf'. "
            "If empty, the entire dataset snapshot is eligible for download."
        ),
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        default=None,
        help=(
            "Hugging Face token. If not provided, the script will try to use "
            "the HF_TOKEN environment variable or the cached login."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Download a subset of the AgiBotWorldChallenge-2026 dataset.

    What it downloads:
        - By default, only the HF repo subdirectory
          "Reasoning2Action-Sim/take_wrong_item_shelf" is downloaded.
        - This folder contains multiple large tar chunks, e.g.:
              data.tar.gz.000
              meta.tar.gz.000
              videos.tar.gz.000
              videos.tar.gz.001
              ...

    Where and how it is stored:
        - Data is ultimately stored under DATA_DIR (see agibot.constants),
          in a folder named after the last component of the HF subdir.
          With the default settings this becomes:
              data/challenge/take_wrong_item_shelf/
        - Inside that folder, you will find the tar chunk files exactly as
          they are published on Hugging Face (no unpacking is done here).
    """
    args = parse_args()

    token = args.hf_token or os.environ.get("HF_TOKEN")
    if token:
        logger.info("Hugging Face token: provided (hf-token or HF_TOKEN env var)")
    else:
        logger.info("Hugging Face token: not provided (will use cached login if available)")

    allow_patterns = None
    subdir = None
    if args.subdir:
        # Full path inside the HF repo, e.g. "Reasoning2Action-Sim/take_wrong_item_shelf"
        subdir = args.subdir.strip("/ ")
        allow_patterns = [f"{subdir}/**"]
        logger.info(f"Downloading subdir: {subdir}")
    else:
        logger.warning("No --subdir provided; eligible to download the full dataset snapshot.")

    # Local target path where we want the *contents* to live:
    # data/challenge/<last_component_of_subdir>, e.g. data/challenge/take_wrong_item_shelf
    if subdir:
        short_name = subdir.split("/")[-1]
        target_dir = Path(DATA_DIR) / short_name
    else:
        # Fallback if no subdir is provided
        target_dir = Path(DATA_DIR)

    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Target directory: {target_dir.resolve()}")

    # Download into a temporary directory under DATA_DIR to preserve the HF structure,
    # then move the contents of the requested subdir into target_dir so we don't keep
    # nested "Reasoning2Action-Sim/take_wrong_item_shelf" folders.
    tmp_dir = Path(DATA_DIR) / "_tmp_download"
    if tmp_dir.exists():
        logger.warning(f"Removing existing temp directory: {tmp_dir}")
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting snapshot_download(repo_id={args.repo_id})")
    snapshot_download(
        repo_id=args.repo_id,
        repo_type="dataset",
        local_dir=str(tmp_dir),
        local_dir_use_symlinks=False,
        allow_patterns=allow_patterns,
        token=token,
    )
    logger.info("Download finished, moving files into target directory.")

    if subdir:
        downloaded_subdir = tmp_dir / subdir
        if downloaded_subdir.exists():
            for item in downloaded_subdir.iterdir():
                dest = target_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.move(str(item), str(dest))
                else:
                    shutil.move(str(item), str(dest))
        else:
            logger.error(f"Expected downloaded subdir not found: {downloaded_subdir}")
    else:
        # If no specific subdir, move everything one level up into target_dir
        for item in tmp_dir.iterdir():
            dest = target_dir / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(item), str(dest))
            else:
                shutil.move(str(item), str(dest))

    shutil.rmtree(tmp_dir, ignore_errors=True)
    logger.info("Done. Temporary download directory removed.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Dataset download failed.")
        raise SystemExit(1)

