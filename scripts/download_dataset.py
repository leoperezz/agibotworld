import argparse
import os
from pathlib import Path
from agibot.constants import DATA_DIR
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
    args = parse_args()

    token = args.hf_token or os.environ.get("HF_TOKEN")

    allow_patterns = None
    subdir = None
    if args.subdir:
        # Full path inside the HF repo, e.g. "Reasoning2Action-Sim/take_wrong_item_shelf"
        subdir = args.subdir.strip("/ ")
        allow_patterns = [f"{subdir}/**"]

    # Local path: keep only the last component of the subdir, e.g. "take_wrong_item_shelf"
    if subdir:
        short_name = subdir.split("/")[-1]
        local_dir = Path(DATA_DIR) / short_name
    else:
        # Fallback if no subdir is provided
        local_dir = Path(DATA_DIR)

    local_dir.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=args.repo_id,
        repo_type="dataset",
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        allow_patterns=allow_patterns,
        token=token,
    )


if __name__ == "__main__":
    main()

