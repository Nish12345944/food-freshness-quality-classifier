from pathlib import Path
import shutil

# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCE_DIR = PROJECT_ROOT / "data" / "Processed Data"
OUTPUT_DIR = PROJECT_ROOT / "data" / "food_freshness"

CLASS_MAPPING = {
    "fresh": "Fresh",
    "semi fresh": "Okay",
    "semi_fresh": "Okay",
    "rotten": "Avoid",
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
}


# ============================================================
# Helper functions
# ============================================================

def get_target_class(folder_name: str) -> str | None:
    """
    Convert the original dataset folder name into one of
    the three classes used by our classifier.
    """

    normalized = " ".join(folder_name.lower().replace("_", " ").split())

    if normalized.startswith("fresh "):
        return "Fresh"

    if normalized.startswith("semi fresh "):
        return "Okay"

    if normalized.startswith("rotten "):
        return "Avoid"

    return None


def prepare_output_directories() -> None:
    """Create the three target class directories."""

    for class_name in ("Fresh", "Okay", "Avoid"):
        (OUTPUT_DIR / class_name).mkdir(parents=True, exist_ok=True)


def copy_images() -> None:
    """Copy images from the source dataset into the three classes."""

    if not SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"Dataset directory not found:\n{SOURCE_DIR}\n\n"
            "Make sure the extracted dataset is located at:\n"
            "data/Processed Data/"
        )

    prepare_output_directories()

    counts = {
        "Fresh": 0,
        "Okay": 0,
        "Avoid": 0,
    }

    skipped_folders = []
    skipped_files = 0

    source_folders = sorted(
        folder
        for folder in SOURCE_DIR.iterdir()
        if folder.is_dir()
    )

    print("=" * 60)
    print("FoodFresh AI - Dataset Preparation")
    print("=" * 60)
    print()
    print(f"Source: {SOURCE_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print()
    print(f"Found {len(source_folders)} source folders.")
    print()

    for source_folder in source_folders:
        target_class = get_target_class(source_folder.name)

        if target_class is None:
            skipped_folders.append(source_folder.name)
            continue

        target_dir = OUTPUT_DIR / target_class

        for image_path in source_folder.iterdir():
            if not image_path.is_file():
                continue

            if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
                skipped_files += 1
                continue

            # Prefix the original folder name to prevent filename collisions.
            safe_folder_name = (
                source_folder.name
                .replace(" ", "_")
                .replace("(", "")
                .replace(")", "")
            )

            destination_name = (
                f"{safe_folder_name}_{image_path.name}"
            )

            destination = target_dir / destination_name

            shutil.copy2(image_path, destination)

            counts[target_class] += 1

    print("Dataset preparation completed.")
    print()
    print("Images copied:")
    print(f"  Fresh : {counts['Fresh']}")
    print(f"  Okay  : {counts['Okay']}")
    print(f"  Avoid : {counts['Avoid']}")
    print()
    print(f"Total  : {sum(counts.values())}")
    print()

    if skipped_folders:
        print("WARNING - Skipped folders:")
        for folder in skipped_folders:
            print(f"  - {folder}")
        print()

    if skipped_files:
        print(f"Skipped unsupported files: {skipped_files}")
        print()

    print("Output structure:")
    print(f"  {OUTPUT_DIR / 'Fresh'}")
    print(f"  {OUTPUT_DIR / 'Okay'}")
    print(f"  {OUTPUT_DIR / 'Avoid'}")
    print()

    if not all(counts.values()):
        raise RuntimeError(
            "One or more target classes contain zero images. "
            "Check the dataset structure before training."
        )

    print("SUCCESS: Dataset is ready for training.")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    copy_images()